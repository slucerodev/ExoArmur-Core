#!/usr/bin/env python3
"""
Visibility & Arbitration Demo Script

Demonstrates observation ingest, belief aggregation, conflict detection, and arbitration.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from federation.observation_ingest import ObservationIngestService
from federation.belief_aggregation import BeliefAggregationService
from federation.arbitration_service import ArbitrationService
from federation.conflict_detection import ConflictDetectionService
from federation.observation_store import ObservationStore
from federation.arbitration_store import ArbitrationStore
from federation.federate_identity_store import FederateIdentityStore
from federation.clock import FixedClock
from federation.audit import AuditService
from federation.crypto import FederateKeyPair
from spec.contracts.models_v1 import (
    ObservationType,
    TelemetrySummaryPayloadV1,
    ThreatIntelPayloadV1,
    FederationRole,
    CellStatus
)
from datetime import datetime, timezone


def main():
    """Run visibility and arbitration demo"""
    print("👁️ ExoArmur Visibility & Arbitration Demo")
    print("=" * 60)
    
    # Setup
    clock = FixedClock()
    observation_store = ObservationStore(clock)
    arbitration_store = ArbitrationStore(clock)
    identity_store = FederateIdentityStore(clock)
    audit_service = AuditService()
    
    # Create services
    print("\n🔧 Initializing services...")
    
    ingest_service = ObservationIngestService(
        observation_store=observation_store,
        identity_store=identity_store,
        clock=clock,
        feature_flag_enabled=True
    )
    
    belief_service = BeliefAggregationService(
        observation_store=observation_store,
        clock=clock,
        feature_flag_enabled=True
    )
    
    conflict_service = ConflictDetectionService(
        arbitration_store=arbitration_store,
        audit_service=audit_service,
        clock=clock,
        feature_flag_enabled=True
    )
    
    # Wire conflict detection into belief aggregation
    belief_service.conflict_detection_service = conflict_service
    
    arbitration_service = ArbitrationService(
        arbitration_store=arbitration_store,
        audit_service=audit_service,
        clock=clock,
        observation_store=observation_store,
        feature_flag_enabled=True
    )
    
    print("✅ Services initialized")
    
    # Create confirmed federates
    print("\n👥 Creating confirmed federates...")
    
    federates = []
    for i, name in enumerate(["alpha", "beta", "gamma"]):
        keypair = FederateKeyPair()
        identity = keypair.create_identity(
            federate_id=f"federate-{name}",
            role=FederationRole.MEMBER,
            capabilities=["observation_ingest", "belief_aggregation"],
            trust_score=0.8 + (i * 0.05)
        )
        # Set status to CONFIRMED
        identity.status = CellStatus.CONFIRMED
        identity_store.store_identity(identity)
        federates.append((identity, keypair))
        print(f"✅ Created federate-{name} (trust: {identity.trust_score})")
    
    # Create conflicting observations
    print("\n📊 Creating conflicting observations...")
    
    base_time = clock.now()
    
    # Federate Alpha sees malware
    obs1 = belief_service.observation_store.create_observation(
        observation_id="obs-malware-1",
        source_federate_id="federate-alpha",
        timestamp_utc=base_time,
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.9,
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=5,
            threat_types=["malware"],
            confidence_score=0.9,
            sources=["threat_feed_1"]
        ),
        correlation_id="conflict-demo-123"
    )
    
    # Federate Beta sees benign activity
    obs2 = belief_service.observation_store.create_observation(
        observation_id="obs-benign-1",
        source_federate_id="federate-beta",
        timestamp_utc=base_time,
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.8,
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=3,
            threat_types=["benign"],
            confidence_score=0.8,
            sources["threat_feed_2"]
        ),
        correlation_id="conflict-demo-123"
    )
    
    # Federate Gamma sees suspicious but not malware
    obs3 = belief_service.observation_store.create_observation(
        observation_id="obs-suspicious-1",
        source_federate_id="federate-gamma",
        timestamp_utc=base_time,
        observation_type=ObservationType.THREAT_INTEL,
        confidence=0.7,
        payload=ThreatIntelPayloadV1(
            payload_type="threat_intel",
            data={},
            ioc_count=2,
            threat_types=["suspicious"],
            confidence_score=0.7,
            sources=["threat_feed_3"]
        ),
        correlation_id="conflict-demo-123"
    )
    
    print(f"✅ Created 3 conflicting observations")
    
    # Aggregate beliefs (should detect conflicts)
    print("\n🧠 Aggregating beliefs...")
    beliefs = belief_service.aggregate_observations()
    
    print(f"📊 Generated {len(beliefs)} beliefs:")
    for belief in beliefs:
        print(f"   {belief.belief_id}: {belief.belief_type} (confidence: {belief.confidence})")
    
    # Check for arbitrations
    print("\n⚖️ Checking for arbitrations...")
    arbitrations = arbitration_service.list_arbitrations()
    
    if arbitrations:
        print(f"📋 Found {len(arbitrations)} arbitration(s):")
        for arb in arbitrations:
            print(f"   {arb.arbitration_id}: {arb.conflict_type.value} - {arb.status.value}")
            print(f"      Subject: {arb.subject_key}")
            print(f"      Claims: {len(arb.claims)}")
            print(f"      Approval ID: {arb.approval_id}")
    else:
        print("📋 No arbitrations found")
    
    # Demo arbitration resolution
    if arbitrations:
        print("\n🔧 Demonstrating arbitration resolution...")
        
        arbitration = arbitrations[0]
        
        # Propose resolution
        resolution = {
            "resolved_threat_type": "trojan",
            "type": "threat_classification_update",
            "proposed_by": "security_analyst"
        }
        
        success = arbitration_service.propose_resolution(arbitration.arbitration_id, resolution)
        if success:
            print(f"✅ Resolution proposed: {resolution['resolved_threat_type']}")
            
            # Apply resolution (mock approval)
            success = arbitration_service.apply_resolution(
                arbitration.arbitration_id, 
                "resolver-federate"
            )
            
            if success:
                print("✅ Resolution applied successfully")
                
                # Check updated beliefs
                updated_arb = arbitration_service.get_arbitration(arbitration.arbitration_id)
                print(f"📊 Arbitration status: {updated_arb.status.value}")
                print(f"📊 Resolver: {updated_arb.resolver_federate_id}")
                
            else:
                print("❌ Failed to apply resolution")
        else:
            print("❌ Failed to propose resolution")
    
    # Show final state
    print("\n📈 Final system state:")
    print(f"   Observations: {len(observation_store.list_observations())}")
    print(f"   Beliefs: {len(observation_store.list_beliefs())}")
    print(f"   Arbitrations: {len(arbitration_store.list_arbitrations())}")
    
    # Show statistics
    print("\n📊 Service statistics:")
    ingest_stats = ingest_service.get_ingest_statistics()
    belief_stats = belief_service.get_aggregation_statistics()
    arb_stats = arbitration_service.get_statistics()
    
    print(f"   Ingest - Feature enabled: {ingest_stats['feature_enabled']}")
    print(f"   Ingest - Total observations: {ingest_stats['store_statistics']['total_observations']}")
    print(f"   Belief - Feature enabled: {belief_stats['feature_enabled']}")
    print(f"   Belief - Total beliefs: {belief_stats['store_statistics']['total_beliefs']}")
    print(f"   Arbitration - Feature enabled: {arb_stats['feature_enabled']}")
    print(f"   Arbitration - Pending approvals: {arb_stats['pending_approvals']}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
