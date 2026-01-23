"""
Tests for V2 Federation Identity Models
Validate Pydantic models match contract requirements
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from federation.models.federation_identity_v2 import (
    CellIdentity,
    FederationRole,
    CellStatus,
    CapabilityType,
    HandshakeState,
    IdentityExchangeMessage,
    CapabilityNegotiateMessage,
    TrustEstablishMessage,
    FederationConfirmMessage,
    HandshakeSession,
    FederationIdentityMessage,
)


class TestCellIdentityModel:
    """Test CellIdentity model validation and contract compliance"""
    
    def test_cell_identity_valid_creation(self):
        """Test valid cell identity creation"""
        identity = CellIdentity(
            cell_id="cell-us-east-1-cluster-01-node-01",
            cell_public_key="base64ed25519publickey",
            cell_certificate_chain=["-----BEGIN CERTIFICATE-----", "-----END CERTIFICATE-----"],
            capabilities=[CapabilityType.BELIEF_AGGREGATION, CapabilityType.POLICY_DISTRIBUTION],
            trust_score=0.8
        )
        
        assert identity.cell_id == "cell-us-east-1-cluster-01-node-01"
        assert identity.federation_role == FederationRole.MEMBER
        assert identity.status == CellStatus.ACTIVE
        assert identity.trust_score == 0.8
        assert len(identity.capabilities) == 2
    
    def test_cell_id_format_validation(self):
        """Test cell_id format validation"""
        # Invalid format - doesn't start with cell-
        with pytest.raises(ValidationError, match="cell_id must start with"):
            CellIdentity(
                cell_id="invalid-id",
                cell_public_key="key",
                cell_certificate_chain=["cert"],
                capabilities=[CapabilityType.BELIEF_AGGREGATION]
            )
        
        # Invalid format - not enough parts
        with pytest.raises(ValidationError, match="cell_id must have format"):
            CellIdentity(
                cell_id="cell-us-east",
                cell_public_key="key",
                cell_certificate_chain=["cert"],
                capabilities=[CapabilityType.BELIEF_AGGREGATION]
            )
    
    def test_trust_score_bounds(self):
        """Test trust score bounds validation"""
        # Below minimum
        with pytest.raises(ValidationError) as exc_info:
            CellIdentity(
                cell_id="cell-us-east-1-cluster-01-node-01",
                cell_public_key="key",
                cell_certificate_chain=["cert"],
                capabilities=[CapabilityType.BELIEF_AGGREGATION],
                trust_score=-0.1
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # Above maximum
        with pytest.raises(ValidationError) as exc_info:
            CellIdentity(
                cell_id="cell-us-east-1-cluster-01-node-01",
                cell_public_key="key",
                cell_certificate_chain=["cert"],
                capabilities=[CapabilityType.BELIEF_AGGREGATION],
                trust_score=1.1
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)


class TestIdentityMessageModels:
    """Test identity message models"""
    
    def test_identity_exchange_message(self):
        """Test identity exchange message structure"""
        identity = CellIdentity(
            cell_id="cell-us-east-1-cluster-01-node-01",
            cell_public_key="key",
            cell_certificate_chain=["cert"],
            capabilities=[CapabilityType.BELIEF_AGGREGATION]
        )
        
        message = IdentityExchangeMessage(
            cell_identity=identity,
            signature="signature",
            nonce="nonce123"
        )
        
        assert message.cell_identity.cell_id == "cell-us-east-1-cluster-01-node-01"
        assert message.signature == "signature"
        assert message.nonce == "nonce123"
        assert isinstance(message.timestamp, datetime)
    
    def test_capability_negotiate_message(self):
        """Test capability negotiation message structure"""
        message = CapabilityNegotiateMessage(
            supported_capabilities=[CapabilityType.BELIEF_AGGREGATION],
            required_capabilities=[CapabilityType.POLICY_DISTRIBUTION],
            priority=5,
            signature="signature",
            nonce="nonce123"
        )
        
        assert len(message.supported_capabilities) == 1
        assert len(message.required_capabilities) == 1
        assert message.priority == 5
    
    def test_trust_establish_message(self):
        """Test trust establishment message structure"""
        expiration = datetime.now(timezone.utc)
        message = TrustEstablishMessage(
            trust_score=0.8,
            trust_reasons=["good_behavior", "successful_interactions"],
            expiration=expiration,
            signature="signature",
            nonce="nonce123"
        )
        
        assert message.trust_score == 0.8
        assert len(message.trust_reasons) == 2
        assert message.expiration == expiration
    
    def test_federation_confirm_message(self):
        """Test federation confirmation message structure"""
        message = FederationConfirmMessage(
            federation_id="fed-123",
            member_cells=["cell-1", "cell-2"],
            coordinator_cell="cell-1",
            terms={"version": "2.0"},
            signature="signature",
            nonce="nonce123"
        )
        
        assert message.federation_id == "fed-123"
        assert len(message.member_cells) == 2
        assert message.coordinator_cell == "cell-1"
        assert "version" in message.terms


class TestHandshakeSessionModel:
    """Test handshake session model"""
    
    def test_handshake_session_creation(self):
        """Test handshake session creation"""
        session = HandshakeSession(
            session_id="session-123",
            session_nonce="nonce456",
            initiator_cell_id="cell-1",
            responder_cell_id="cell-2"
        )
        
        assert session.session_id == "session-123"
        assert session.session_nonce == "nonce456"
        assert session.initiator_cell_id == "cell-1"
        assert session.responder_cell_id == "cell-2"
        assert session.current_state == HandshakeState.UNINITIALIZED
        assert session.step_index == 0
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_handshake_state_enum(self):
        """Test handshake state enumeration"""
        states = [
            HandshakeState.UNINITIALIZED,
            HandshakeState.IDENTITY_EXCHANGE,
            HandshakeState.CAPABILITY_NEGOTIATION,
            HandshakeState.TRUST_ESTABLISHMENT,
            HandshakeState.CONFIRMED,
            HandshakeState.ACTIVE,
            HandshakeState.FAILED_IDENTITY,
            HandshakeState.FAILED_CAPABILITIES,
            HandshakeState.FAILED_TRUST,
            HandshakeState.SUSPENDED,
        ]
        
        assert len(states) == 10
        assert all(isinstance(state, str) for state in states)


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_cell_identity_serialization(self):
        """Test CellIdentity JSON serialization"""
        identity = CellIdentity(
            cell_id="cell-us-east-1-cluster-01-node-01",
            cell_public_key="key",
            cell_certificate_chain=["cert"],
            capabilities=[CapabilityType.BELIEF_AGGREGATION],
            trust_score=0.8
        )
        
        # Serialize to JSON
        json_str = identity.model_dump_json()
        assert isinstance(json_str, str)
        assert "cell-us-east-1-cluster-01-node-01" in json_str
        
        # Deserialize from JSON
        restored = CellIdentity.model_validate_json(json_str)
        assert restored.cell_id == identity.cell_id
        assert restored.trust_score == identity.trust_score
        assert restored.capabilities == identity.capabilities
    
    def test_message_serialization_with_timestamps(self):
        """Test message serialization preserves timestamps"""
        identity = CellIdentity(
            cell_id="cell-us-east-1-cluster-01-node-01",
            cell_public_key="key",
            cell_certificate_chain=["cert"],
            capabilities=[CapabilityType.BELIEF_AGGREGATION]
        )
        
        message = IdentityExchangeMessage(
            cell_identity=identity,
            signature="sig",
            nonce="nonce"
        )
        
        json_str = message.model_dump_json()
        restored = IdentityExchangeMessage.model_validate_json(json_str)
        
        assert restored.timestamp.isoformat() == message.timestamp.isoformat()


class TestFeatureFlagIsolation:
    """Test that models work independently of feature flags"""
    
    def test_models_work_without_feature_flags(self):
        """Test models can be created and used without feature flag system"""
        # Models should work independently
        identity = CellIdentity(
            cell_id="cell-us-east-1-cluster-01-node-01",
            cell_public_key="key",
            cell_certificate_chain=["cert"],
            capabilities=[CapabilityType.BELIEF_AGGREGATION]
        )
        
        session = HandshakeSession(
            session_id="test-session",
            session_nonce="test-nonce",
            initiator_cell_id="cell-1",
            responder_cell_id="cell-2"
        )
        
        # Should not raise any errors
        assert identity.cell_id == "cell-us-east-1-cluster-01-node-01"
        assert session.session_id == "test-session"
