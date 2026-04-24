"""
Tests for Federate Identity Store
Tests V2 federation identity persistence with feature flag isolation
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock

from exoarmur.federation.federate_identity_store import FederateIdentityStore
from spec.contracts.models_v1 import FederateIdentityV1, FederationRole, CellStatus
from exoarmur.federation.clock import FixedClock
from tests.federation_fixtures import MockFeatureFlags


class TestFederateIdentityStore:
    """Test federate identity store functionality"""
    
    @pytest.fixture
    def fixed_clock(self):
        """Fixed clock for deterministic testing"""
        return FixedClock()
    
    @pytest.fixture
    def identity_store(self):
        """Identity store for testing with V2 federation enabled"""
        mock_flags = MockFeatureFlags(v2_federation_enabled=True)
        return FederateIdentityStore(feature_flags=mock_flags)
    
    def test_store_and_retrieve_identity(self, identity_store):
        """Test storing and retrieving federate identity"""
        # Create identity
        identity = FederateIdentityV1(
            schema_version="2.0.0",
            federate_id="cell-us-east-1-cluster-01-node-01",
            public_key="test-public-key",
            key_id="test-key-id",
            certificate_chain=["cert-1", "cert-2"],
            federation_role=FederationRole.MEMBER,
            capabilities=["observation_ingest", "belief_aggregation"],
            trust_score=0.85,
            last_seen=datetime.now(timezone.utc),
            status=CellStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store identity
        identity_store.store_identity(identity)
        
        # Retrieve identity
        retrieved = identity_store.get_identity("cell-us-east-1-cluster-01-node-01")
        
        assert retrieved is not None
        assert retrieved.federate_id == identity.federate_id
        assert retrieved.public_key == identity.public_key
        assert retrieved.federation_role == identity.federation_role
        assert retrieved.trust_score == identity.trust_score
        assert retrieved.status == identity.status
    
    def test_list_identities(self, identity_store):
        """Test listing all identities"""
        # Create multiple identities
        identities = [
            FederateIdentityV1(
                schema_version="2.0.0",
                federate_id=f"cell-us-east-1-cluster-01-node-{i:02d}",
                public_key=f"test-key-{i}",
                key_id=f"test-key-id-{i}",
                certificate_chain=[f"cert-{i}"],
                federation_role=FederationRole.MEMBER,
                capabilities=["observation_ingest"],
                trust_score=0.8 + (i * 0.05),
                last_seen=datetime.now(timezone.utc),
                status=CellStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            for i in range(3)
        ]
        
        # Store identities
        for identity in identities:
            identity_store.store_identity(identity)
        
        # List all identities
        all_identities = identity_store.list_identities()
        
        assert len(all_identities) == 3
        federate_ids = [id.federate_id for id in all_identities]
        assert "cell-us-east-1-cluster-01-node-00" in federate_ids
        assert "cell-us-east-1-cluster-01-node-01" in federate_ids
        assert "cell-us-east-1-cluster-01-node-02" in federate_ids
    
    def test_update_identity(self, identity_store):
        """Test updating existing identity"""
        # Create initial identity
        identity = FederateIdentityV1(
            schema_version="2.0.0",
            federate_id="cell-us-east-1-cluster-01-node-01",
            public_key="test-public-key",
            key_id="test-key-id",
            certificate_chain=["cert-1"],
            federation_role=FederationRole.MEMBER,
            capabilities=["observation_ingest"],
            trust_score=0.8,
            last_seen=datetime.now(timezone.utc),
            status=CellStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Store initial identity
        identity_store.store_identity(identity)
        
        # Update identity
        updated_identity = FederateIdentityV1(
            schema_version="2.0.0",
            federate_id="cell-us-east-1-cluster-01-node-01",
            public_key="updated-public-key",
            key_id="test-key-id",
            certificate_chain=["cert-1", "cert-2"],
            federation_role=FederationRole.COORDINATOR,
            capabilities=["observation_ingest", "belief_aggregation"],
            trust_score=0.9,
            last_seen=datetime.now(timezone.utc),
            status=CellStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        identity_store.store_identity(updated_identity)
        
        # Retrieve updated identity
        retrieved = identity_store.get_identity("cell-us-east-1-cluster-01-node-01")
        
        assert retrieved is not None
        assert retrieved.public_key == "updated-public-key"
        assert retrieved.federation_role == FederationRole.COORDINATOR
        assert retrieved.trust_score == 0.9
        assert len(retrieved.capabilities) == 2
    
    def test_delete_identity(self, identity_store):
        """Test deleting identity"""
        # Create and store identity
        identity = FederateIdentityV1(
            schema_version="2.0.0",
            federate_id="cell-us-east-1-cluster-01-node-01",
            public_key="test-public-key",
            key_id="test-key-id",
            certificate_chain=["cert-1"],
            federation_role=FederationRole.MEMBER,
            capabilities=["observation_ingest"],
            trust_score=0.8,
            last_seen=datetime.now(timezone.utc),
            status=CellStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        identity_store.store_identity(identity)
        
        # Verify identity exists
        assert identity_store.get_identity("cell-us-east-1-cluster-01-node-01") is not None
        
        # Delete identity
        identity_store.delete_identity("cell-us-east-1-cluster-01-node-01")
        
        # Verify identity is deleted
        assert identity_store.get_identity("cell-us-east-1-cluster-01-node-01") is None
    
    def test_get_statistics(self, identity_store):
        """Test getting store statistics"""
        # Store some identities
        for i in range(3):
            identity = FederateIdentityV1(
                schema_version="2.0.0",
                federate_id=f"cell-us-east-1-cluster-01-node-{i:02d}",
                public_key=f"test-key-{i}",
                key_id=f"test-key-id-{i}",
                certificate_chain=[f"cert-{i}"],
                federation_role=FederationRole.MEMBER,
                capabilities=["observation_ingest"],
                trust_score=0.8,
                last_seen=datetime.now(timezone.utc),
                status=CellStatus.ACTIVE,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            identity_store.store_identity(identity)
        
        # Get statistics
        stats = identity_store.get_statistics()
        
        assert stats["total_identities"] == 3
        assert "federate_ids" in stats
        assert "roles" in stats
        assert "status_counts" in stats
        assert len(stats["federate_ids"]) == 3
