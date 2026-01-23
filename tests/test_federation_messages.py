"""
Tests for Federation Signed Message Schemas
Tests V2 federation message models with deterministic canonicalization
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from src.federation.messages import (
    IdentityExchangeMessage,
    CapabilityNegotiateMessage, 
    TrustEstablishMessage,
    SignatureAlgorithm,
    MessageType,
    MessageVersion,
    SignatureInfo,
    IdentityExchangePayload,
    CapabilityNegotiatePayload,
    TrustEstablishPayload,
    create_identity_exchange_message,
    create_capability_negotiate_message,
    create_trust_establish_message
)
from src.replay.canonical_utils import canonical_json, stable_hash


class TestMessageModels:
    """Test federation message models"""
    
    @pytest.fixture
    def sample_timestamp(self):
        """Sample timestamp for testing"""
        return datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    @pytest.fixture
    def sample_signature_info(self):
        """Sample signature info"""
        return SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id="key-123",
            cert_fingerprint=None,
            sig_b64="base64_signature_here"
        )
    
    @pytest.fixture
    def identity_payload(self):
        """Sample identity exchange payload"""
        return IdentityExchangePayload(
            cell_public_key="base64_public_key",
            certificate_chain=["-----BEGIN CERTIFICATE-----\n..."],
            federation_role="member",
            capabilities=["belief_aggregation", "audit_consolidation"],
            trust_score=0.8,
            cell_metadata={"region": "us-east-1"}
        )
    
    @pytest.fixture
    def capability_payload(self):
        """Sample capability negotiation payload"""
        return CapabilityNegotiatePayload(
            supported_capabilities=["belief_aggregation", "policy_distribution"],
            required_capabilities=["audit_consolidation"],
            priority=2,
            capability_constraints={"max_beliefs": 1000},
            negotiation_metadata={"version": "2.0"}
        )
    
    @pytest.fixture
    def trust_payload(self):
        """Sample trust establishment payload"""
        return TrustEstablishPayload(
            trust_score=0.9,
            trust_reasons=["successful_interactions", "certificate_valid"],
            expiration=datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            trust_policies=["policy_1", "policy_2"],
            trust_metadata={"verification_method": "certificate_chain"}
        )
    
    def test_identity_exchange_message_creation(self, sample_timestamp, sample_signature_info, identity_payload):
        """Test creating identity exchange message"""
        message = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=MessageVersion.IDENTITY_EXCHANGE,
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="nonce_123",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=identity_payload,
            signature=sample_signature_info
        )
        
        # Verify core fields
        assert message.msg_type == MessageType.IDENTITY_EXCHANGE
        assert message.msg_version == 1
        assert message.federate_id == "cell-us-east-1-cluster-01-node-01"
        assert message.nonce == "nonce_123"
        assert message.correlation_id == "corr-456"
        assert message.signature.alg == SignatureAlgorithm.ED25519
        assert message.signature.key_id == "key-123"
        assert message.signature.sig_b64 == "base64_signature_here"
        
        # Verify payload
        assert message.payload.cell_public_key == "base64_public_key"
        assert message.payload.capabilities == ["belief_aggregation", "audit_consolidation"]
        assert message.payload.trust_score == 0.8
    
    def test_capability_negotiate_message_creation(self, sample_timestamp, sample_signature_info, capability_payload):
        """Test creating capability negotiation message"""
        message = CapabilityNegotiateMessage(
            msg_type=MessageType.CAPABILITY_NEGOTIATE,
            msg_version=MessageVersion.CAPABILITY_NEGOTIATE,
            federate_id="cell-us-west-1-cluster-01-node-01",
            nonce="nonce_789",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=capability_payload,
            signature=sample_signature_info
        )
        
        assert message.msg_type == MessageType.CAPABILITY_NEGOTIATE
        assert message.payload.supported_capabilities == ["belief_aggregation", "policy_distribution"]
        assert message.payload.required_capabilities == ["audit_consolidation"]
        assert message.payload.priority == 2
    
    def test_trust_establish_message_creation(self, sample_timestamp, sample_signature_info, trust_payload):
        """Test creating trust establishment message"""
        message = TrustEstablishMessage(
            msg_type=MessageType.TRUST_ESTABLISH,
            msg_version=MessageVersion.TRUST_ESTABLISH,
            federate_id="cell-us-central-1-cluster-01-node-01",
            nonce="nonce_999",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=trust_payload,
            signature=sample_signature_info
        )
        
        assert message.msg_type == MessageType.TRUST_ESTABLISH
        assert message.payload.trust_score == 0.9
        assert message.payload.trust_reasons == ["successful_interactions", "certificate_valid"]
        assert len(message.payload.trust_policies) == 2
    
    def test_message_requires_nonce_federate_id_timestamp(self, identity_payload, sample_signature_info):
        """Test that messages require nonce, federate_id, and timestamp"""
        # Test missing federate_id
        with pytest.raises(Exception):
            IdentityExchangeMessage(
                msg_type=MessageType.IDENTITY_EXCHANGE,
                msg_version=1,
                federate_id="",  # Empty should fail validation
                nonce="nonce_123",
                timestamp_utc=datetime.now(timezone.utc),
                correlation_id="corr-456",
                payload=identity_payload,
                signature=sample_signature_info
            )
        
        # Test missing nonce
        with pytest.raises(Exception):
            IdentityExchangeMessage(
                msg_type=MessageType.IDENTITY_EXCHANGE,
                msg_version=1,
                federate_id="cell-us-east-1-cluster-01-node-01",
                nonce="",  # Empty should fail validation
                timestamp_utc=datetime.now(timezone.utc),
                correlation_id="corr-456",
                payload=identity_payload,
                signature=sample_signature_info
            )
    
    def test_message_type_version_constants(self):
        """Test message type and version constants"""
        assert MessageType.IDENTITY_EXCHANGE == "identity_exchange"
        assert MessageType.CAPABILITY_NEGOTIATE == "capability_negotiate"
        assert MessageType.TRUST_ESTABLISH == "trust_establish"
        
        assert MessageVersion.CURRENT == 1
        assert MessageVersion.IDENTITY_EXCHANGE == 1
        assert MessageVersion.CAPABILITY_NEGOTIATE == 1
        assert MessageVersion.TRUST_ESTABLISH == 1
    
    def test_signed_payload_excludes_signature_fields(self, sample_timestamp, identity_payload):
        """Test that signed payload excludes signature fields"""
        signature_info = SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id="key-123",
            cert_fingerprint=None,
            sig_b64="base64_signature_here"
        )
        
        message = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="nonce_123",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=identity_payload,
            signature=signature_info
        )
        
        signed_payload = message.signed_payload_dict()
        
        # Should include core fields
        assert 'msg_type' in signed_payload
        assert 'msg_version' in signed_payload
        assert 'federate_id' in signed_payload
        assert 'nonce' in signed_payload
        assert 'timestamp_utc' in signed_payload
        assert 'correlation_id' in signed_payload
        assert 'payload' in signed_payload
        
        # Should NOT include signature fields
        assert 'signature' not in signed_payload
        assert 'sig_b64' not in signed_payload
        assert 'key_id' not in signed_payload
        assert 'alg' not in signed_payload
        
        # Verify payload structure
        payload = signed_payload['payload']
        assert 'cell_public_key' in payload
        assert 'certificate_chain' in payload
        assert 'federation_role' in payload
        assert 'capabilities' in payload
        assert 'trust_score' in payload
        assert 'cell_metadata' in payload
    
    def test_correlation_id_propagates(self, sample_timestamp, identity_payload, sample_signature_info):
        """Test that correlation_id propagates through all message types"""
        correlation_id = "test-correlation-123"
        
        identity_msg = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-1",
            nonce="nonce-1",
            timestamp_utc=sample_timestamp,
            correlation_id=correlation_id,
            payload=identity_payload,
            signature=sample_signature_info
        )
        
        capability_msg = CapabilityNegotiateMessage(
            msg_type=MessageType.CAPABILITY_NEGOTIATE,
            msg_version=1,
            federate_id="cell-2",
            nonce="nonce-2",
            timestamp_utc=sample_timestamp,
            correlation_id=correlation_id,
            payload=CapabilityNegotiatePayload(
                supported_capabilities=["test"],
                required_capabilities=["test"],
                priority=1
            ),
            signature=sample_signature_info
        )
        
        trust_msg = TrustEstablishMessage(
            msg_type=MessageType.TRUST_ESTABLISH,
            msg_version=1,
            federate_id="cell-3",
            nonce="nonce-3",
            timestamp_utc=sample_timestamp,
            correlation_id=correlation_id,
            payload=TrustEstablishPayload(
                trust_score=0.8,
                trust_reasons=["test"],
                expiration=datetime.now(timezone.utc) + timedelta(days=1)
            ),
            signature=sample_signature_info
        )
        
        # All should have the same correlation_id
        assert identity_msg.correlation_id == correlation_id
        assert capability_msg.correlation_id == correlation_id
        assert trust_msg.correlation_id == correlation_id
    
    def test_message_models_roundtrip_json_is_stable(self, sample_timestamp, identity_payload, sample_signature_info):
        """Test that message models roundtrip through JSON stably"""
        message = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="nonce_123",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=identity_payload,
            signature=sample_signature_info
        )
        
        # Serialize to JSON
        json_str1 = message.model_dump_json()
        
        # Parse back from JSON
        parsed_message = IdentityExchangeMessage.model_validate_json(json_str1)
        
        # Serialize again
        json_str2 = parsed_message.model_dump_json()
        
        # Should be identical (deterministic)
        assert json_str1 == json_str2
        
        # Verify all fields are preserved
        assert parsed_message.msg_type == message.msg_type
        assert parsed_message.federate_id == message.federate_id
        assert parsed_message.nonce == message.nonce
        assert parsed_message.correlation_id == message.correlation_id
        assert parsed_message.payload.cell_public_key == message.payload.cell_public_key
        assert parsed_message.signature.alg == message.signature.alg
    
    def test_canonical_bytes_deterministic(self, sample_timestamp, identity_payload):
        """Test that canonical_bytes produces deterministic output"""
        signature_info = SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id="key-123",
            cert_fingerprint=None,
            sig_b64="base64_signature_here"
        )
        
        message = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="nonce_123",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=identity_payload,
            signature=signature_info
        )
        
        # Generate canonical bytes multiple times
        bytes1 = message.canonical_bytes()
        bytes2 = message.canonical_bytes()
        bytes3 = message.canonical_bytes()
        
        # Should be identical
        assert bytes1 == bytes2 == bytes3
        
        # Should be valid UTF-8 JSON
        json_str = bytes1.decode('utf-8')
        parsed = json.loads(json_str)
        
        # Verify structure
        assert parsed['msg_type'] == 'identity_exchange'
        assert parsed['msg_version'] == 1
        assert parsed['federate_id'] == 'cell-us-east-1-cluster-01-node-01'
        assert parsed['nonce'] == 'nonce_123'
        assert parsed['correlation_id'] == 'corr-456'
        assert 'payload' in parsed
        assert 'signature' not in parsed  # Should not be in signed payload
    
    def test_payload_hash_stability(self, sample_timestamp, identity_payload):
        """Test that payload hash is stable and deterministic"""
        signature_info = SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id="key-123",
            cert_fingerprint=None,
            sig_b64="base64_signature_here"
        )
        
        message = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-us-east-1-cluster-01-node-01",
            nonce="nonce_123",
            timestamp_utc=sample_timestamp,
            correlation_id="corr-456",
            payload=identity_payload,
            signature=signature_info
        )
        
        # Generate hash multiple times
        hash1 = message.payload_hash()
        hash2 = message.payload_hash()
        hash3 = message.payload_hash()
        
        # Should be identical
        assert hash1 == hash2 == hash3
        
        # Should be SHA-256 (64 hex characters)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1.lower())
    
    def test_timestamp_utc_normalization(self, identity_payload, sample_signature_info):
        """Test UTC timestamp normalization"""
        # Test with naive datetime (should be assumed UTC)
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        message1 = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-1",
            nonce="nonce-1",
            timestamp_utc=naive_time,
            correlation_id="corr-1",
            payload=identity_payload,
            signature=sample_signature_info
        )
        
        # Test with explicit UTC datetime
        utc_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        message2 = IdentityExchangeMessage(
            msg_type=MessageType.IDENTITY_EXCHANGE,
            msg_version=1,
            federate_id="cell-1",
            nonce="nonce-1",
            timestamp_utc=utc_time,
            correlation_id="corr-1",
            payload=identity_payload,
            signature=sample_signature_info
        )
        
        # Should normalize to the same UTC time
        assert message1.timestamp_utc == message2.timestamp_utc
        assert message1.timestamp_utc.tzinfo == timezone.utc
        assert message2.timestamp_utc.tzinfo == timezone.utc
    
    def test_signature_info_validation(self):
        """Test signature info validation"""
        # Should work with key_id
        sig1 = SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id="key-123",
            cert_fingerprint=None,
            sig_b64="signature"
        )
        assert sig1.key_id == "key-123"
        assert sig1.cert_fingerprint is None
        
        # Should work with cert_fingerprint
        sig2 = SignatureInfo(
            alg=SignatureAlgorithm.ED25519,
            key_id=None,
            cert_fingerprint="fp-456",
            sig_b64="signature"
        )
        assert sig2.cert_fingerprint == "fp-456"
        assert sig2.key_id is None
        
        # Should fail with neither key_id nor cert_fingerprint
        with pytest.raises(Exception):
            SignatureInfo(
                alg=SignatureAlgorithm.ED25519,
                key_id=None,
                cert_fingerprint=None,
                sig_b64="signature"
                # Missing both key_id and cert_fingerprint
            )
    
    def test_factory_functions(self, sample_timestamp):
        """Test factory functions for creating messages"""
        # Test identity exchange factory
        identity_msg = create_identity_exchange_message(
            federate_id="cell-1",
            nonce="nonce-1",
            correlation_id="corr-1",
            cell_public_key="public_key",
            certificate_chain=["cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8,
            timestamp=sample_timestamp
        )
        
        assert identity_msg.msg_type == MessageType.IDENTITY_EXCHANGE
        assert identity_msg.payload.cell_public_key == "public_key"
        assert identity_msg.payload.capabilities == ["belief_aggregation"]
        
        # Test capability negotiate factory
        capability_msg = create_capability_negotiate_message(
            federate_id="cell-2",
            nonce="nonce-2",
            correlation_id="corr-1",
            supported_capabilities=["belief_aggregation"],
            required_capabilities=["audit_consolidation"],
            priority=3,
            timestamp=sample_timestamp
        )
        
        assert capability_msg.msg_type == MessageType.CAPABILITY_NEGOTIATE
        assert capability_msg.payload.priority == 3
        
        # Test trust establish factory
        trust_msg = create_trust_establish_message(
            federate_id="cell-3",
            nonce="nonce-3",
            correlation_id="corr-1",
            trust_score=0.9,
            trust_reasons=["valid_cert"],
            expiration=sample_timestamp + timedelta(days=30),
            timestamp=sample_timestamp
        )
        
        assert trust_msg.msg_type == MessageType.TRUST_ESTABLISH
        assert trust_msg.payload.trust_score == 0.9
        assert len(trust_msg.payload.trust_reasons) == 1
    
    def test_payload_immutability(self):
        """Test that payload sub-models are immutable"""
        payload = IdentityExchangePayload(
            cell_public_key="public_key",
            certificate_chain=["cert"],
            federation_role="member",
            capabilities=["belief_aggregation"],
            trust_score=0.8
        )
        
        # Should be frozen
        assert payload.model_config.get('frozen', False) is True
        
        # Attempting to modify should fail
        with pytest.raises(Exception):
            payload.cell_public_key = "modified"
    
    def test_message_field_validation(self):
        """Test message field validation"""
        # Test invalid trust score
        with pytest.raises(Exception):
            TrustEstablishPayload(
                trust_score=1.5,  # Invalid: > 1.0
                trust_reasons=["test"],
                expiration=datetime.now(timezone.utc)
            )
        
        # Test invalid priority
        with pytest.raises(Exception):
            CapabilityNegotiatePayload(
                supported_capabilities=["test"],
                required_capabilities=["test"],
                priority=15  # Invalid: > 10
            )
        
        # Test invalid algorithm
        with pytest.raises(Exception):
            SignatureInfo(
                alg="invalid_algorithm",  # Should be enum value
                key_id="key-123",
                sig_b64="signature"
            )
