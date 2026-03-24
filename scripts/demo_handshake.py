#!/usr/bin/env python3
"""
Handshake Demo Script

Demonstrates the ExoArmur federation handshake protocol.
"""

import sys
import os
from pathlib import Path

# Add src to path

from exoarmur.federation.handshake_controller import HandshakeController
from exoarmur.federation.federate_identity_store import FederateIdentityStore
from exoarmur.federation.clock import FixedClock
from exoarmur.federation.crypto import FederateKeyPair
from exoarmur.spec.contracts.models_v1 import FederationRole, CellStatus
from datetime import datetime, timezone


def main():
    """Run handshake demo"""
    print("🤝 ExoArmur Handshake Demo")
    print("=" * 50)
    
    # Setup
    clock = FixedClock()
    identity_store = FederateIdentityStore(clock)
    
    # Create federates
    print("\n📝 Creating federates...")
    
    # Federate Alpha
    alpha_keypair = FederateKeyPair()
    alpha_identity = alpha_keypair.create_identity(
        federate_id="federate-alpha",
        role=FederationRole.MEMBER,
        capabilities=["handshake", "observation_ingest"],
        trust_score=0.9
    )
    identity_store.store_identity(alpha_identity)
    print(f"✅ Created federate-alpha (trust: {alpha_identity.trust_score})")
    
    # Federate Beta
    beta_keypair = FederateKeyPair()
    beta_identity = beta_keypair.create_identity(
        federate_id="federate-beta", 
        role=FederationRole.MEMBER,
        capabilities=["handshake", "belief_aggregation"],
        trust_score=0.85
    )
    identity_store.store_identity(beta_identity)
    print(f"✅ Created federate-beta (trust: {beta_identity.trust_score})")
    
    # Create handshake controllers
    print("\n🔧 Initializing handshake controllers...")
    alpha_controller = HandshakeController(
        identity_store=identity_store,
        clock=clock,
        key_pair=alpha_keypair,
        feature_flag_enabled=True
    )
    
    beta_controller = HandshakeController(
        identity_store=identity_store,
        clock=clock,
        key_pair=beta_keypair,
        feature_flag_enabled=True
    )
    
    print("✅ Controllers initialized")
    
    # Initiate handshake
    print("\n🤝 Initiating handshake...")
    
    # Alpha initiates handshake with Beta
    result = alpha_controller.initiate_handshake("federate-beta")
    
    print(f"📊 Handshake result: {result['result']}")
    print(f"📋 Session ID: {result['session_id']}")
    print(f"🔐 Trust established: {result['trust_established']}")
    
    if result['result'] == 'confirmed':
        print("\n🎉 Handshake successful!")
        print(f"   Alpha trust score: {result['alpha_trust_score']}")
        print(f"   Beta trust score: {result['beta_trust_score']}")
        print(f"   Shared capabilities: {result['shared_capabilities']}")
    else:
        print(f"\n❌ Handshake failed: {result.get('failure_reason', 'Unknown')}")
    
    # Show final state
    print("\n📈 Final federate states:")
    for federate_id in ["federate-alpha", "federate-beta"]:
        identity = identity_store.get_identity(federate_id)
        print(f"   {federate_id}: {identity.status.value} (trust: {identity.trust_score})")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
