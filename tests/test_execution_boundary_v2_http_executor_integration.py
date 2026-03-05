"""
Integration test for HTTP Executor Plugin with ExoArmur Core ProxyPipeline.

Tests that the Core pipeline can import and use the external HTTP executor plugin.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add the HTTP executor to the path for testing
http_executor_path = Path(__file__).resolve().parents[2] / "exoarmur-executors-http" / "src"
if str(http_executor_path) not in sys.path:
    sys.path.insert(0, str(http_executor_path))

from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, AuditEmitter
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
from exoarmur.safety.safety_gate import SafetyGate, SafetyVerdict, PolicyState, TrustState, EnvironmentState

try:
    from exoarmur_executors_http import HTTPExecutorPlugin
    HTTP_EXECUTOR_AVAILABLE = True
except ImportError:
    HTTP_EXECUTOR_AVAILABLE = False
    pytest.skip("HTTP Executor Plugin not available", allow_module_level=True)


class FakePDP:
    """Fake PolicyDecisionPoint for testing."""
    
    def __init__(self, verdict: PolicyVerdict, rationale: str = None):
        self.verdict = verdict
        self.rationale = rationale or f"Test {verdict.value}"
        self.evaluate_called = False
        self.evaluate_intent = None
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        self.evaluate_called = True
        self.evaluate_intent = intent
        
        return PolicyDecision(
            verdict=self.verdict,
            rationale=self.rationale,
            confidence=0.95,
            approval_required=False,
            policy_version="1.0.0"
        )
    
    def approval_status(self, intent_id: str):
        return "not_required"


@pytest.mark.skipif(not HTTP_EXECUTOR_AVAILABLE, reason="HTTP Executor Plugin not available")
class TestHTTPExecutorIntegration:
    """Test HTTP Executor Plugin integration with Core ProxyPipeline."""
    
    @pytest.fixture
    def http_executor(self):
        """Create HTTP executor for testing."""
        return HTTPExecutorPlugin(default_timeout=5.0)
    
    @pytest.fixture
    def fake_pdp(self):
        """Create fake PDP that allows all actions."""
        return FakePDP(PolicyVerdict.ALLOW, "Low risk action")
    
    @pytest.fixture
    def fake_safety_gate(self):
        """Create fake safety gate that passes all checks."""
        class FakeSafetyGate:
            def __init__(self):
                self.evaluate_called = False
            
            def evaluate_safety(self, intent, local_decision, collective_state, policy_state, trust_state, environment_state):
                self.evaluate_called = True
                return SafetyVerdict(
                    verdict="allow",
                    rationale="Safety check passed",
                    rule_ids=[]
                )
        
        return FakeSafetyGate()
    
    @pytest.fixture
    def audit_emitter(self):
        """Create audit emitter for testing."""
        return AuditEmitter()
    
    @pytest.fixture
    def sample_http_intent(self):
        """Create sample HTTP ActionIntent."""
        return ActionIntent(
            intent_id="test-http-123",
            actor_id="agent-001",
            actor_type="agent",
            action_type="http_request",
            target="https://api.example.com/health",
            parameters={
                "method": "GET",
                "headers": {"Authorization": "Bearer token123"},
                "timeout": 10.0
            },
            safety_context={"risk_level": "low"},
            timestamp=datetime.now(timezone.utc)
        )
    
    def test_http_executor_integration_with_proxy_pipeline(
        self, http_executor, fake_pdp, fake_safety_gate, audit_emitter, sample_http_intent
    ):
        """Test HTTP executor integration with ProxyPipeline using MockTransport."""
        # Create mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.url = "https://api.example.com/health"
        mock_response.elapsed.total_seconds.return_value = 0.15
        mock_response.raise_for_status.return_value = None
        
        # Mock the HTTP executor's _execute_http_request method
        with patch.object(http_executor, '_execute_http_request', return_value=mock_response):
            # Create proxy pipeline with HTTP executor
            pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, http_executor, audit_emitter)
            
            # Execute intent through pipeline
            result = pipeline.execute(sample_http_intent)
            
            # Verify pipeline execution
            assert result.success is True
            assert result.output["status_code"] == 200
            assert result.output["method"] == "GET"
            assert result.output["url"] == "https://api.example.com/health"
            assert result.output["response_time"] == 0.15
            assert result.error is None
            
            # Verify all pipeline components were called
            assert fake_pdp.evaluate_called is True
            assert fake_pdp.evaluate_intent == sample_http_intent
            assert fake_safety_gate.evaluate_called is True
            assert http_executor.name() == "http-executor"
            
            # Verify audit record was emitted
            assert len(audit_emitter.audit_records) == 1
            audit_record = audit_emitter.audit_records[0]
            assert audit_record.event_kind == "execution"
            assert audit_record.payload_ref["ref"] == sample_http_intent.intent_id
            assert audit_record.payload_ref["details"]["execution_success"] is True
            assert audit_record.payload_ref["details"]["executor_name"] == "http-executor"
            
            # Verify HTTP executor evidence
            evidence = result.evidence
            assert evidence["executor"] == "http-executor"
            assert evidence["intent_id"] == "test-http-123"
            assert evidence["method"] == "GET"
            assert evidence["timeout"] == 10.0
            # Check that headers were sanitized (authorization should be redacted)
            assert evidence["headers_sanitized"].get("Authorization", "") == "[REDACTED]"
    
    def test_http_executor_error_handling_in_pipeline(
        self, http_executor, fake_pdp, fake_safety_gate, audit_emitter, sample_http_intent
    ):
        """Test HTTP executor error handling within ProxyPipeline."""
        # Mock HTTP executor to raise an exception
        with patch.object(http_executor, '_execute_http_request') as mock_execute:
            mock_execute.side_effect = Exception("Connection timeout")
            
            # Create proxy pipeline with HTTP executor
            pipeline = ProxyPipeline(fake_pdp, fake_safety_gate, http_executor, audit_emitter)
            
            # Execute intent through pipeline
            result = pipeline.execute(sample_http_intent)
            
            # Verify error handling
            assert result.success is False
            assert "Connection timeout" in result.error
            assert result.output == {}
            
            # Verify audit record was emitted with failure
            assert len(audit_emitter.audit_records) == 1
            audit_record = audit_emitter.audit_records[0]
            assert audit_record.event_kind == "execution"
            assert audit_record.payload_ref["details"]["execution_success"] is False
            assert audit_record.payload_ref["details"]["execution_error"] == "Connection timeout"
    
    def test_http_executor_capabilities(self, http_executor):
        """Test HTTP executor capabilities."""
        capabilities = http_executor.capabilities()
        
        assert capabilities["capabilities"] == ["http.request", "http.get", "http.post", "http.put", "http.patch", "http.delete"]
        assert capabilities["constraints"]["allowed_methods"] == ["GET", "POST", "PUT", "PATCH", "DELETE"]
        assert capabilities["constraints"]["allowed_schemes"] == ["http", "https"]
        assert capabilities["constraints"]["default_timeout"] == 5.0
        assert capabilities["constraints"]["requires_explicit_method"] is True
    
    def test_http_executor_name(self, http_executor):
        """Test HTTP executor name."""
        assert http_executor.name() == "http-executor"
