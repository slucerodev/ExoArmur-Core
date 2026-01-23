"""
Test fixtures for federation components
Provides fresh contexts and deterministic time for testing
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Optional

from src.federation.clock import Clock, FixedClock
from src.federation.federate_identity_store import FederateIdentityStore
from src.federation.protocol_enforcer import ProtocolEnforcer
from src.federation.handshake_context import HandshakeContext
from src.federation.crypto import FederateKeyPair
from src.feature_flags.feature_flags import FeatureFlags
from spec.contracts.models_v1 import FederateIdentityV1, FederationRole, CellStatus


class MockFeatureFlags:
    """Mock feature flags for testing"""
    
    def __init__(self, v2_federation_identity_enabled: bool = False):
        self._flags = {
            'v2_federation_identity_enabled': v2_federation_identity_enabled
        }
    
    def is_enabled(self, flag_key: str) -> bool:
        return self._flags.get(flag_key, False)


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Fixed clock starting at 2023-01-01 12:00:00 UTC"""
    return FixedClock(datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def mock_feature_flags_enabled() -> MockFeatureFlags:
    """Mock feature flags with V2 federation identity enabled"""
    return MockFeatureFlags(v2_federation_identity_enabled=True)


@pytest.fixture
def mock_feature_flags_disabled() -> MockFeatureFlags:
    """Mock feature flags with V2 federation identity disabled"""
    return MockFeatureFlags(v2_federation_identity_enabled=False)


@pytest.fixture
def fresh_identity_store(mock_feature_flags_enabled) -> FederateIdentityStore:
    """Fresh identity store for each test"""
    return FederateIdentityStore(feature_flags=mock_feature_flags_enabled)


@pytest.fixture
def fresh_protocol_enforcer(fresh_identity_store, fixed_clock) -> ProtocolEnforcer:
    """Fresh protocol enforcer for each test"""
    return ProtocolEnforcer(fresh_identity_store, fixed_clock)


@pytest.fixture
def handshake_context(mock_feature_flags_enabled, fixed_clock) -> HandshakeContext:
    """Fresh handshake context for each test"""
    from src.federation.protocol_enforcer import ProtocolEnforcer
    identity_store = FederateIdentityStore(feature_flags=mock_feature_flags_enabled)
    protocol_enforcer = ProtocolEnforcer(identity_store, fixed_clock)
    return HandshakeContext(
        identity_store=identity_store,
        clock=fixed_clock,
        protocol_enforcer=protocol_enforcer
    )


@pytest.fixture
def test_key_pair() -> FederateKeyPair:
    """Test key pair for cryptographic operations"""
    return FederateKeyPair()


@pytest.fixture
def test_federate_identity(test_key_pair, fixed_clock) -> FederateIdentityV1:
    """Test federate identity for cryptographic tests"""
    now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return FederateIdentityV1(
        schema_version="2.0.0",
        federate_id="cell-us-east-1-cluster-01-node-01",
        public_key=test_key_pair.public_key_b64,
        key_id=test_key_pair.key_id,
        certificate_chain=["test-cert"],
        federation_role=FederationRole.MEMBER,
        status=CellStatus.ACTIVE,
        capabilities=["belief_aggregation"],
        trust_score=0.8,
        last_seen=now,
        created_at=now,
        updated_at=now
    )


@pytest.fixture
def old_timestamp(fixed_clock) -> datetime:
    """Old timestamp for timestamp skew tests"""
    return fixed_clock.now() - timedelta(hours=1)


@pytest.fixture
def future_timestamp(fixed_clock) -> datetime:
    """Future timestamp for timestamp skew tests"""
    return fixed_clock.now() + timedelta(hours=1)
