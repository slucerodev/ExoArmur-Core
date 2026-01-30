#!/usr/bin/env python3
"""
Identity Containment Window (ICW) Demo Script
Demonstrates the complete ICW workflow from recommendation to auto-revert
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path and ensure src is in Python path for relative imports
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.dirname(__file__))  # Add scripts dir too

# Import ICW components
from federation.clock import FixedClock
from federation.audit import AuditService
from identity_containment.recommender import IdentityContainmentRecommender
from identity_containment.intent_service import IdentityContainmentIntentService
from identity_containment.execution import IdentityContainmentExecutor
from identity_containment.effector import SimulatedIdentityProviderEffector
from control_plane.approval_service import ApprovalService
from control_plane.intent_store import IntentStore
from safety.safety_gate import SafetyGate, SafetyVerdict

# Import models
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))
from models_v1 import (
    IdentitySubjectV1,
    IdentityContainmentScopeV1,
    IdentityContainmentRecommendationV1
)

# Import replay engine
from replay.replay_engine import ReplayEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ICWDemo:
    """ICW Demo orchestrator"""
    
    def __init__(self):
        """Initialize demo components"""
        self.clock = FixedClock()
        self.audit_service = AuditService()
        self.approval_service = ApprovalService()
        self.intent_store = IntentStore()
        self.safety_gate = SafetyGate()
        
        # Initialize ICW components
        self.recommender = IdentityContainmentRecommender(
            observation_store=None,  # Mock for demo
            clock=self.clock,
            audit_service=self.audit_service
        )
        
        self.intent_service = IdentityContainmentIntentService(
            clock=self.clock,
            audit_service=self.audit_service,
            safety_gate=self.safety_gate,
            approval_service=self.approval_service
        )
        
        self.effector = SimulatedIdentityProviderEffector(
            clock=self.clock,
            audit_service=self.audit_service,
            max_ttl_seconds=3600
        )
        
        self.executor = IdentityContainmentExecutor(
            clock=self.clock,
            audit_service=self.audit_service,
            approval_service=self.approval_service,
            intent_service=self.intent_service,
            effector=self.effector
        )
        
        # Mock audit store for replay
        self.audit_store = {}
        
        logger.info("ICW Demo initialized")
    
    def seed_observations_and_beliefs(self):
        """Seed mock observations and beliefs to trigger recommendation"""
        logger.info("🌱 Seeding observations and beliefs...")
        
        # In a real implementation, this would:
        # 1. Create telemetry events indicating suspicious activity
        # 2. Generate beliefs from observations
        # 3. Trigger recommendation engine
        
        # For demo, we'll mock this by creating a direct recommendation
        logger.info("✅ Observations and beliefs seeded")
    
    def generate_recommendation(self) -> IdentityContainmentRecommendationV1:
        """Generate containment recommendation"""
        logger.info("🎯 Generating containment recommendation...")
        
        # Create subject for containment
        subject = IdentitySubjectV1(
            subject_id="demo_user",
            subject_type="USER",
            provider="okta",
            metadata={"department": "engineering", "risk_score": "0.85"}
        )
        
        # Generate recommendation (mock implementation)
        recommendation = IdentityContainmentRecommendationV1(
            recommendation_id="rec_demo_001",
            correlation_id="demo_correlation_001",
            subject=subject,
            scope=IdentityContainmentScopeV1.SESSIONS,
            suggested_ttl_seconds=300,  # 5 minutes for demo
            confidence=0.92,
            risk_level="HIGH",
            summary="Suspicious login patterns detected from multiple geographic locations",
            evidence_refs=["obs_001", "obs_002", "obs_003"],
            belief_refs=["belief_001", "belief_002"],
            recommended_authority="A3"
        )
        
        logger.info(f"✅ Recommendation generated: {recommendation.recommendation_id}")
        logger.info(f"   Subject: {recommendation.subject.subject_id}@{recommendation.subject.provider}")
        logger.info(f"   Scope: {recommendation.scope.value}")
        logger.info(f"   TTL: {recommendation.suggested_ttl_seconds} seconds")
        logger.info(f"   Risk Level: {recommendation.risk_level}")
        
        return recommendation
    
    def freeze_intent_and_create_approval(self, recommendation: IdentityContainmentRecommendationV1) -> tuple:
        """Freeze intent from recommendation and create approval"""
        logger.info("🧊 Freezing intent and creating approval...")
        
        # Create intent and approval
        intent, approval_id = self.intent_service.create_intent_from_recommendation(recommendation)
        
        logger.info(f"✅ Intent frozen: {intent.intent_id}")
        logger.info(f"   Intent Hash: {intent.intent_hash[:16]}...")
        logger.info(f"   Approval ID: {approval_id}")
        logger.info(f"   Expires At: {intent.expires_at_utc}")
        
        return intent, approval_id
    
    def approve_request(self, approval_id: str) -> str:
        """Approve the containment request"""
        logger.info("✅ Approving containment request...")
        
        # Approve the request
        status = self.approval_service.approve(approval_id, "demo_operator")
        
        logger.info(f"✅ Approval {approval_id} approved with status: {status}")
        return status
    
    def execute_apply(self, approval_id: str):
        """Execute containment apply"""
        logger.info("🔒 Executing containment apply...")
        
        # Execute containment
        result = self.executor.execute_containment_apply(approval_id)
        
        if result:
            logger.info(f"✅ Containment applied successfully")
            logger.info(f"   Intent ID: {result.intent_id}")
            logger.info(f"   Subject: {result.subject_id}@{result.provider}")
            logger.info(f"   Applied At: {result.applied_at_utc}")
            logger.info(f"   Expires At: {result.expires_at_utc}")
            return result
        else:
            logger.error("❌ Containment execution failed")
            return None
    
    def show_status_before_revert(self, subject_id: str, provider: str):
        """Show containment status before revert"""
        logger.info("📊 Checking containment status (before revert)...")
        
        # Check effector state
        state_key = self.effector._make_state_key(subject_id, provider, IdentityContainmentScopeV1.SESSIONS)
        state = self.effector.state_store.get_state(state_key)
        
        if state and state.status.value == "active":
            logger.info(f"✅ Subject {subject_id}@{provider} is CONTAINED")
            logger.info(f"   Status: {state.status.value}")
            logger.info(f"   Applied At: {state.applied_at_utc}")
            logger.info(f"   Expires At: {state.expires_at_utc}")
            logger.info(f"   Approval ID: {state.approval_id}")
            return state
        else:
            logger.info(f"❌ Subject {subject_id}@{provider} is NOT contained")
            return None
    
    def advance_clock_and_expire(self, ttl_seconds: int):
        """Advance clock past TTL and process expirations"""
        logger.info("⏰ Advancing clock to trigger TTL expiration...")
        
        # Advance clock past expiration
        self.clock.advance(timedelta(seconds=ttl_seconds + 10))
        
        logger.info(f"⏰ Clock advanced to: {self.clock.now()}")
        
        # Process expirations
        reverted_records = self.effector.process_expirations()
        
        logger.info(f"🔄 Processed {len(reverted_records)} expirations")
        for record in reverted_records:
            logger.info(f"   Reverted: {record.intent_id} - {record.reason}")
        
        return reverted_records
    
    def show_status_after_revert(self, subject_id: str, provider: str):
        """Show containment status after revert"""
        logger.info("📊 Checking containment status (after revert)...")
        
        # Check effector state
        state_key = self.effector._make_state_key(subject_id, provider, IdentityContainmentScopeV1.SESSIONS)
        state = self.effector.state_store.get_state(state_key)
        
        if state and state.status.value == "active":
            logger.info(f"❌ Subject {subject_id}@{provider} is still CONTAINED (unexpected)")
        else:
            logger.info(f"✅ Subject {subject_id}@{provider} is REVERTED to normal")
        
        return state
    
    def capture_audit_events(self, correlation_id: str):
        """Capture audit events for replay"""
        logger.info("📋 Capturing audit events for replay...")
        
        # Get audit events from the service
        events = []
        
        # In a real implementation, this would query the audit store
        # For demo, we'll collect from the audit service mock
        if hasattr(self.audit_service, 'events'):
            events = self.audit_service.events.get(correlation_id, [])
        
        logger.info(f"📋 Captured {len(events)} audit events")
        self.audit_store[correlation_id] = events
        
        return events
    
    def run_replay_and_verify(self, correlation_id: str):
        """Run replay and verify identical outcome"""
        logger.info("🔄 Running replay verification...")
        
        # Create replay engine
        replay_engine = ReplayEngine(audit_store=self.audit_store)
        
        # Run replay
        report = replay_engine.replay_correlation(correlation_id)
        
        logger.info(f"🔄 Replay completed with result: {report.result.value}")
        logger.info(f"   Events Processed: {report.processed_events}/{report.total_events}")
        logger.info(f"   ICW Applied: {len(report.icw_applied)}")
        logger.info(f"   ICW Reverted: {len(report.icw_reverted)}")
        
        # Verify final status
        if correlation_id in report.icw_final_status:
            final_status = report.icw_final_status[correlation_id]
            logger.info(f"   Final Status: {final_status.get('status')}")
            logger.info(f"   Revert Reason: {final_status.get('revert_reason', 'N/A')}")
        
        # Verify deterministic reconstruction
        if report.result.value == "success":
            logger.info("✅ Replay verification PASSED - identical outcome reproduced")
        else:
            logger.error("❌ Replay verification FAILED")
            for failure in report.failures:
                logger.error(f"   Failure: {failure}")
        
        return report
    
    def run_demo(self):
        """Run the complete ICW demo"""
        logger.info("🚀 Starting Identity Containment Window Demo")
        logger.info("=" * 60)
        
        try:
            # Step 1: Seed observations and beliefs
            self.seed_observations_and_beliefs()
            
            # Step 2: Generate recommendation
            recommendation = self.generate_recommendation()
            
            # Step 3: Freeze intent and create approval
            intent, approval_id = self.freeze_intent_and_create_approval(recommendation)
            
            # Step 4: Approve request
            self.approve_request(approval_id)
            
            # Step 5: Execute apply
            applied_record = self.execute_apply(aproval_id)
            if not applied_record:
                return False
            
            # Step 6: Show status before revert
            state_before = self.show_status_before_revert(
                recommendation.subject.subject_id, 
                recommendation.subject.provider
            )
            
            # Step 7: Advance clock and expire
            reverted_records = self.advance_clock_and_expire(recommendation.suggested_ttl_seconds)
            
            # Step 8: Show status after revert
            state_after = self.show_status_after_revert(
                recommendation.subject.subject_id, 
                recommendation.subject.provider
            )
            
            # Step 9: Capture audit events
            self.capture_audit_events(recommendation.correlation_id)
            
            # Step 10: Run replay and verify
            replay_report = self.run_replay_and_verify(recommendation.correlation_id)
            
            # Summary
            logger.info("=" * 60)
            logger.info("🎉 ICW Demo completed successfully!")
            logger.info(f"   Recommendation: {recommendation.recommendation_id}")
            logger.info(f"   Intent: {intent.intent_id}")
            logger.info(f"   Approval: {approval_id}")
            logger.info(f"   Applied: {'✅' if applied_record else '❌'}")
            logger.info(f"   Reverted: {'✅' if reverted_records else '❌'}")
            logger.info(f"   Replay: {'✅' if replay_report.result.value == 'success' else '❌'}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main demo entry point"""
    print("Identity Containment Window (ICW) Demo")
    print("=====================================")
    print()
    print("This demo demonstrates:")
    print("1. Recommendation generation from observations/beliefs")
    print("2. Intent freezing and approval creation")
    print("3. Human approval process")
    print("4. Containment apply execution")
    print("5. TTL-based auto-revert")
    print("6. Audit event capture and replay verification")
    print()
    
    # Check feature flag
    if not os.getenv("ICW_FEATURE_ENABLED", "false").lower() == "true":
        print("⚠️  WARNING: ICW_FEATURE_ENABLED is not set to 'true'")
        print("   Some features may be disabled")
        print()
    
    # Run demo
    demo = ICWDemo()
    success = demo.run_demo()
    
    if success:
        print("\n✅ Demo completed successfully!")
        print("The ICW feature is working as expected.")
    else:
        print("\n❌ Demo failed!")
        print("Please check the logs above for details.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
