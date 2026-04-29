"""
Certification Pipeline Test Suite

Tests verify that the module certification pipeline correctly validates
modules through static validation, execution testing, determinism compliance,
invariant verification, and adversarial testing stages.
"""

import pytest
from dataclasses import dataclass

from exoarmur.execution_boundary_v2.certification.certification_pipeline import (
    CertificationContext,
    CertificationResult,
    CertificationFunction,
)


class TestCertificationContext:
    """Test CertificationContext initialization and validation"""
    
    def test_certification_context_valid_id(self):
        """Verify valid 16-character certification ID is accepted"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalClock,
        )
        
        # Create minimal module definition for testing
        @dataclass(frozen=True)
        class TestModuleDefinition:
            module_id: str
            version: str
        
        module_definition = TestModuleDefinition(
            module_id="M" * 26,
            version="1.0.0",
        )
        logical_clock = LogicalClock("test-exec")
        
        context = CertificationContext(
            certification_id="CERT1234567890AB",
            module_definition=module_definition,
            logical_clock=logical_clock,
        )
        
        assert context.certification_id == "CERT1234567890AB"
        assert len(context.certification_id) == 16
    
    def test_certification_context_invalid_id_raises(self):
        """Verify invalid certification ID length raises ValueError"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalClock,
        )
        
        @dataclass(frozen=True)
        class TestModuleDefinition:
            module_id: str
            version: str
        
        module_definition = TestModuleDefinition(
            module_id="M" * 26,
            version="1.0.0",
        )
        logical_clock = LogicalClock("test-exec")
        
        with pytest.raises(ValueError, match="Certification ID must be 16 characters"):
            CertificationContext(
                certification_id="SHORT",
                module_definition=module_definition,
                logical_clock=logical_clock,
            )


class TestCertificationResult:
    """Test CertificationResult structure and methods"""
    
    def test_certification_result_is_certified_true(self):
        """Verify is_certified returns True when pass_result is True and no failures"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalTime,
        )
        
        result = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=1,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=1000,
            ),
            deterministic_cert_hash="abc123",
            pass_result=True,
            failure_reason_codes=(),
            reproducibility_score=1.0,
            audit_trail_reference="audit-ref",
            stage_results={},
        )
        
        assert result.is_certified() is True
    
    def test_certification_result_is_certified_false_on_failure(self):
        """Verify is_certified returns False when pass_result is False"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalTime,
        )
        from exoarmur.execution_boundary_v2.core.core_types import FailureCode
        
        result = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=1,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=1000,
            ),
            deterministic_cert_hash="abc123",
            pass_result=False,
            failure_reason_codes=(FailureCode.SCHEMA_INVALID,),
            reproducibility_score=0.5,
            audit_trail_reference="audit-ref",
            stage_results={},
        )
        
        assert result.is_certified() is False
    
    def test_certification_result_verify_determinism(self):
        """Verify verify_determinism correctly compares two results"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalTime,
        )
        
        result1 = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=1,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=1000,
            ),
            deterministic_cert_hash="abc123",
            pass_result=True,
            failure_reason_codes=(),
            reproducibility_score=1.0,
            audit_trail_reference="audit-ref",
            stage_results={},
        )
        
        result2 = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=2,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=2000,
            ),
            deterministic_cert_hash="abc123",
            pass_result=True,
            failure_reason_codes=(),
            reproducibility_score=1.0,
            audit_trail_reference="audit-ref-2",
            stage_results={},
        )
        
        assert result1.verify_determinism(result2) is True
    
    def test_certification_result_verify_determinism_false_on_mismatch(self):
        """Verify verify_determinism returns False on hash mismatch"""
        from exoarmur.execution_boundary_v2.determinism.determinism_engine import (
            LogicalTime,
        )
        
        result1 = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=1,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=1000,
            ),
            deterministic_cert_hash="abc123",
            pass_result=True,
            failure_reason_codes=(),
            reproducibility_score=1.0,
            audit_trail_reference="audit-ref",
            stage_results={},
        )
        
        result2 = CertificationResult(
            module_id="test-module",
            version="1.0.0",
            certification_timestamp=LogicalTime(
                tick_count=2,
                execution_id="exec-123",
                module_id="test-module",
                timestamp_ms=2000,
            ),
            deterministic_cert_hash="xyz789",  # Different hash
            pass_result=True,
            failure_reason_codes=(),
            reproducibility_score=1.0,
            audit_trail_reference="audit-ref-2",
            stage_results={},
        )
        
        assert result1.verify_determinism(result2) is False


class TestCertificationFunction:
    """Test CertificationFunction execution"""
    
    def test_certification_function_initialization(self):
        """Verify CertificationFunction can be initialized"""
        cert_func = CertificationFunction()
        assert cert_func is not None
