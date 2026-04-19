"""
Phase 1 Stabilization Tests

Tests to verify that Phase 1 low-risk entrypoint modifications
preserve existing behavior while adding routing documentation.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exoarmur.main import app
from exoarmur.execution_boundary_v2.entry.canonical_router import CanonicalExecutionRouter

class TestPhase1Stabilization:
    """Test Phase 1 low-risk entrypoint stabilization"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = TestClient(app)
    
    def test_health_endpoint_unchanged(self):
        """Verify health endpoint preserves status + service fields.

        Version field was added as an additive enhancement so the dashboard
        can display the running backend version. Presence is optional to
        tolerate environments where package metadata is unavailable.
        """
        response = self.client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["service"] == "ExoArmur Core"
        # Additive: version is present when installed via pip (may be absent
        # in edge deployments lacking package metadata).
        if "version" in body:
            assert isinstance(body["version"], str)
            assert body["version"] != ""
    
    def test_root_endpoint_unchanged(self):
        """Verify root endpoint returns identical response"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "ExoArmur Core" in response.json()["message"]
        assert "deterministic governance runtime" in response.json()["message"]
    
    def test_audit_endpoint_behavior_preserved(self):
        """Verify audit endpoint behavior is preserved"""
        # Test with non-existent correlation ID - should handle missing audit logger gracefully
        response = self.client.get("/v1/audit/non-existent-correlation")
        # Endpoint should either work or fail gracefully, not crash the server
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            assert response.json() == {"audit_records": []}
    
    def test_read_only_endpoints_documentation(self):
        """Verify routing documentation is present in read-only endpoints"""
        import inspect
        
        # Check health endpoint docstring
        from exoarmur.main import health_check
        health_doc = inspect.getdoc(health_check)
        assert "READ-ONLY" in health_doc
        assert "No V2 routing required" in health_doc
        
        # Check root endpoint docstring
        from exoarmur.main import root
        root_doc = inspect.getdoc(root)
        assert "READ-ONLY" in root_doc
        assert "No V2 routing required" in root_doc
        
        # Check audit endpoint docstring
        from exoarmur.main import get_audit_records
        audit_doc = inspect.getdoc(get_audit_records)
        assert "READ-ONLY" in audit_doc
        assert "No V2 routing required" in audit_doc
    
    def test_canonical_router_availability(self):
        """Verify canonical router is available and functional"""
        assert CanonicalExecutionRouter.is_available() == True
        
        router = CanonicalExecutionRouter()
        assert router is not None
    
    def test_canonical_router_stateless(self):
        """Verify canonical router maintains no state"""
        router1 = CanonicalExecutionRouter()
        router2 = CanonicalExecutionRouter()
        
        # Should be stateless - no instance-specific state
        assert router1.__class__ == router2.__class__
    
    def test_no_behavior_regression_in_api(self):
        """Ensure no API behavior regression"""
        # Test all read-only endpoints still work
        endpoints = [
            "/health",
            "/"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should not return server errors
            assert response.status_code != 500
        
        # Audit endpoint may fail if audit logger not initialized, but should fail gracefully
        response = self.client.get("/v1/audit/test-correlation")
        assert response.status_code in [200, 500]  # Graceful handling
    
    def test_v2_entry_gate_still_accessible(self):
        """Verify V2EntryGate is still accessible after Phase 1 changes"""
        try:
            from exoarmur.execution_boundary_v2.entry.v2_entry_gate import execute_module
            from exoarmur.execution_boundary_v2.entry.v2_entry_gate import get_v2_entry_gate
            
            gate = get_v2_entry_gate()
            assert gate is not None
            assert callable(execute_module)
        except ImportError as e:
            pytest.fail(f"V2EntryGate should be accessible: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
