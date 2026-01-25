"""
Tests for Identity Containment Window (ICW) API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from identity_containment.icw_api import IdentityContainmentAPI
from spec.contracts.models_v1 import IdentityContainmentScopeV1


class TestICWAPI:
    """Test ICW API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_icw_api(self):
        """Mock ICW API"""
        api = Mock(spec=IdentityContainmentAPI)
        api.feature_flag_enabled = True
        # Configure async methods to return coroutines
        api.get_containment_status = AsyncMock()
        api.create_recommendation = AsyncMock()
        api.create_intent_from_recommendation = AsyncMock()
        api.get_intent = AsyncMock()
        api.tick = AsyncMock()
        api.execute_approval = AsyncMock()
        return api
    
    def test_feature_flag_off_returns_404(self, client):
        """Test that feature flag OFF returns 404"""
        # Mock ICW API with feature flag disabled
        with patch('main.get_icw_api') as mock_get_api:
            mock_api = Mock(spec=IdentityContainmentAPI)
            mock_api._check_feature_flag.side_effect = HTTPException(status_code=404, detail="Feature not enabled")
            # Configure async methods to avoid recursion
            mock_api.get_containment_status = AsyncMock(side_effect=HTTPException(status_code=404, detail="Feature not enabled"))
            mock_get_api.return_value = mock_api
            
            # Try to access ICW endpoint
            response = client.get("/api/v2/identity_containment/status?subject_id=test&provider=test")
            
            # Should return 404
            assert response.status_code == 404
            assert "Feature not enabled" in response.json()["detail"]
    
    def test_get_containment_status_not_contained(self, client, mock_icw_api):
        """Test getting containment status for non-contained subject"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.get_containment_status.return_value = {
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "status": "not_contained"
            }
            
            response = client.get("/api/v2/identity_containment/status?subject_id=test_user&provider=okta")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_contained"
            assert data["subject_id"] == "test_user"
            assert data["provider"] == "okta"
    
    def test_get_containment_status_contained(self, client, mock_icw_api):
        """Test getting containment status for contained subject"""
        from datetime import datetime
        
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.get_containment_status.return_value = {
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "status": "contained",
                "applied_at": "2023-01-01T12:00:00",
                "expires_at": "2023-01-01T13:00:00",
                "approval_id": "apr_123"
            }
            
            response = client.get("/api/v2/identity_containment/status?subject_id=test_user&provider=okta")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "contained"
            assert data["applied_at"] == "2023-01-01T12:00:00"
            assert data["expires_at"] == "2023-01-01T13:00:00"
            assert data["approval_id"] == "apr_123"
    
    def test_create_recommendation(self, client, mock_icw_api):
        """Test creating containment recommendation"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.create_recommendation.return_value = {
                "recommendation_id": "rec_123",
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "suggested_ttl_seconds": 1800,
                "risk_level": "HIGH",
                "confidence": 0.95,
                "evidence_refs": ["obs_001"],
                "belief_refs": ["belief_001"]
            }
            
            request_data = {
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions"
            }
            
            response = client.post("/api/v2/identity_containment/recommendations", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["recommendation_id"] == "rec_123"
            assert data["subject_id"] == "test_user"
            assert data["suggested_ttl_seconds"] == 1800
            assert data["risk_level"] == "HIGH"
    
    def test_create_intent_from_recommendation(self, client, mock_icw_api):
        """Test creating intent from recommendation"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.create_intent_from_recommendation.return_value = {
                "intent_id": "int_123",
                "intent_hash": "hash_abc123",
                "approval_id": "apr_123",
                "correlation_id": "corr_123",
                "ttl_seconds": 1800,
                "expires_at": "2023-01-01T13:00:00"
            }
            
            request_data = {"recommendation_id": "rec_123"}
            
            response = client.post("/api/v2/identity_containment/intents/from_recommendation", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["intent_id"] == "int_123"
            assert data["approval_id"] == "apr_123"
            assert data["intent_hash"] == "hash_abc123"
    
    def test_get_intent(self, client, mock_icw_api):
        """Test getting intent details"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.get_intent.return_value = {
                "intent_id": "int_123",
                "correlation_id": "corr_123",
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "ttl_seconds": 1800,
                "created_at": "2023-01-01T12:00:00",
                "expires_at": "2023-01-01T13:00:00",
                "intent_hash": "hash_abc123",
                "approval_id": "apr_123"
            }
            
            response = client.get("/api/v2/identity_containment/intents/int_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["intent_id"] == "int_123"
            assert data["subject_id"] == "test_user"
            assert data["ttl_seconds"] == 1800
    
    def test_tick(self, client, mock_icw_api):
        """Test tick operation for processing expirations"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.tick.return_value = {
                "processed_count": 2,
                "reverted_records": [
                    {
                        "intent_id": "int_123",
                        "subject_id": "test_user",
                        "provider": "okta",
                        "reason": "expired",
                        "reverted_at": "2023-01-01T13:00:00"
                    },
                    {
                        "intent_id": "int_456",
                        "subject_id": "test_user2",
                        "provider": "okta",
                        "reason": "expired",
                        "reverted_at": "2023-01-01T13:01:00"
                    }
                ]
            }
            
            response = client.post("/api/v2/identity_containment/tick")
            
            assert response.status_code == 200
            data = response.json()
            assert data["processed_count"] == 2
            assert len(data["reverted_records"]) == 2
            assert data["reverted_records"][0]["reason"] == "expired"
    
    def test_execute_approval_success(self, client, mock_icw_api):
        """Test successful execution with approval"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            mock_icw_api.execute_approval.return_value = {
                "success": True,
                "intent_id": "int_123",
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "applied_at": "2023-01-01T12:00:00",
                "expires_at": "2023-01-01T13:00:00",
                "approval_id": "apr_123"
            }
            
            response = client.post("/api/v2/identity_containment/execute/apr_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["intent_id"] == "int_123"
            assert data["approval_id"] == "apr_123"
    
    def test_execute_approval_blocked(self, client, mock_icw_api):
        """Test execution blocked without approval"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            from fastapi import HTTPException
            mock_icw_api.execute_approval.side_effect = HTTPException(
                status_code=403,
                detail="Execution blocked - approval not found or not approved"
            )
            
            response = client.post("/api/v2/identity_containment/execute/apr_invalid")
            
            assert response.status_code == 403
            assert "Execution blocked" in response.json()["detail"]
    
    def test_status_reflects_applied_then_reverted_after_tick(self, client, mock_icw_api):
        """Test that status reflects applied and then reverted after tick"""
        with patch('main.get_icw_api', return_value=mock_icw_api):
            # Initial status - contained
            mock_icw_api.get_containment_status.return_value = {
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "status": "contained",
                "applied_at": "2023-01-01T12:00:00",
                "expires_at": "2023-01-01T12:01:00",
                "approval_id": "apr_123"
            }
            
            # Check initial status
            response = client.get("/api/v2/identity_containment/status?subject_id=test_user&provider=okta")
            assert response.status_code == 200
            assert response.json()["status"] == "contained"
            
            # Simulate tick that processes expiration
            mock_icw_api.tick.return_value = {
                "processed_count": 1,
                "reverted_records": [
                    {
                        "intent_id": "int_123",
                        "subject_id": "test_user",
                        "provider": "okta",
                        "reason": "expired",
                        "reverted_at": "2023-01-01T12:01:00"
                    }
                ]
            }
            
            # Process tick
            response = client.post("/api/v2/identity_containment/tick")
            assert response.status_code == 200
            
            # Update status to reverted
            mock_icw_api.get_containment_status.return_value = {
                "subject_id": "test_user",
                "provider": "okta",
                "scope": "sessions",
                "status": "not_contained"
            }
            
            # Check status after tick
            response = client.get("/api/v2/identity_containment/status?subject_id=test_user&provider=okta")
            assert response.status_code == 200
            assert response.json()["status"] == "not_contained"


if __name__ == "__main__":
    pytest.main([__file__])
