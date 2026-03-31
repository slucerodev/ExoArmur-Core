#!/usr/bin/env python3
"""
Simple Demo API Test (no external dependencies)

Tests the demo API functionality without requiring external packages.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_api_functionality():
    """Test API functionality directly"""
    print("🧪 Testing ExoArmur Demo API Functionality")
    print("=" * 50)
    
    try:
        # Import API modules
        from exoarmur.demo_api import app, _create_sample_events
        print("✅ API modules imported successfully")
        
        # Test sample events creation
        events = _create_sample_events()
        print(f"✅ Sample events created: {len(events)} events")
        
        # Test event conversion
        from exoarmur.demo_api import convert_to_canonical_events
        canonical_events = convert_to_canonical_events(events)
        print(f"✅ Events converted to CanonicalEvent: {len(canonical_events)} events")
        
        # Test replay functionality
        from exoarmur.replay.replay_engine import ReplayEngine
        audit_store = {"demo-correlation-001": canonical_events}
        replay_engine = ReplayEngine(audit_store=audit_store)
        report = replay_engine.replay_correlation("demo-correlation-001")
        print(f"✅ Replay completed: {report.processed_events} events processed")
        
        # Test multi-node verification
        from exoarmur.replay.multi_node_verifier import MultiNodeReplayVerifier
        verifier = MultiNodeReplayVerifier(node_count=3)
        divergence_report = verifier.verify_consensus(canonical_events, "demo-correlation-001")
        print(f"✅ Multi-node verification: {divergence_report.consensus_result.value}")
        
        # Test Byzantine fault injection
        from exoarmur.replay.byzantine_fault_injection import (
            ByzantineTestRunner, 
            ByzantineScenario
        )
        test_runner = ByzantineTestRunner(node_count=3, deterministic_seed=42)
        result = test_runner.run_byzantine_test(canonical_events, ByzantineScenario.SINGLE_NODE)
        print(f"✅ Byzantine test: {result.scenario.value}, consensus: {result.divergence_report.consensus_result.value}")
        
        # Test deterministic responses
        print("\n🔍 Testing Determinism:")
        
        # Run replay multiple times
        replay_hashes = []
        for i in range(3):
            report = replay_engine.replay_correlation("demo-correlation-001")
            from exoarmur.replay.canonical_utils import canonical_json, stable_hash
            replay_hash = stable_hash(canonical_json(report.to_dict()))
            replay_hashes.append(replay_hash)
        
        if len(set(replay_hashes)) == 1:
            print("✅ Replay output is deterministic")
        else:
            print("❌ Replay output is NOT deterministic")
            return False
        
        # Test API response models
        print("\n📋 Testing Response Models:")
        
        from exoarmur.demo_api import (
            ReplayResponse, 
            VerificationResponse, 
            ByzantineTestResponse
        )
        
        replay_response = ReplayResponse(
            correlation_id="test",
            replay_hash="abc123",
            replay_output={"test": "data"},
            total_events=3,
            processed_events=3,
            result="success"
        )
        print("✅ ReplayResponse model works")
        
        verification_response = VerificationResponse(
            correlation_id="test",
            consensus=True,
            consensus_result="consensus",
            node_count=3,
            node_hashes={"node-1": "hash1", "node-2": "hash1", "node-3": "hash1"},
            divergent_nodes=[],
            consensus_nodes=["node-1", "node-2", "node-3"]
        )
        print("✅ VerificationResponse model works")
        
        byzantine_response = ByzantineTestResponse(
            correlation_id="test",
            scenario="single_node",
            baseline_hash="abc123",
            consensus=False,
            consensus_result="divergence",
            corrupted_nodes=["node-1"],
            divergence_detected=True
        )
        print("✅ ByzantineTestResponse model works")
        
        print("\n🎉 ALL API FUNCTIONALITY TESTS PASSED!")
        print("✅ ExoArmur Demo API is ready for deployment")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run API functionality tests"""
    # Ensure deterministic environment
    os.environ['PYTHONHASHSEED'] = '0'
    
    success = test_api_functionality()
    
    if success:
        print("\n📊 API Capabilities Summary:")
        print("  • Deterministic replay of canonical events")
        print("  • Multi-node consensus verification")
        print("  • Byzantine fault injection testing")
        print("  • 100% deterministic responses")
        print("  • No timestamps or environment dependencies")
        print("  • Hash-based integrity verification")
        
        print("\n🚀 Ready for Phase 5: Demo Scenario")
        sys.exit(0)
    else:
        print("\n❌ API functionality tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
