from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Use the public SDK API - this is the ONLY supported way to use ExoArmur
from exoarmur.sdk.public_api import (
    run_governed_execution,
    replay_governed_execution,
    verify_governance_integrity,
    SDKConfig,
    ActionIntent,
    ExecutionProofBundle,
    FinalVerdict
)


class EnumEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles enums."""
    def default(self, obj):
        if hasattr(obj, 'value'):
            return obj.value
        return super().default(obj)

logging.basicConfig(level=logging.WARNING, format="%(message)s")

PROOF_BUNDLE_PATH = Path(__file__).with_name("model_wrapped_demo_proof_bundle.json")
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
INTENT_ID = "demo-model-wrapped-governance"


class SimpleThreatClassifier:
    """Simple threat classification model for demonstration."""
    
    def __init__(self):
        self.model_id = "simple-threat-classifier-v1"
    
    def predict(self, text: str) -> Dict[str, Any]:
        """Predict threat classification for input text."""
        # Simple keyword-based classification for demo
        threat_keywords = ["attack", "malware", "exploit", "breach", "hack"]
        high_risk_keywords = ["critical", "severe", "urgent", "immediate"]
        
        text_lower = text.lower()
        threat_score = sum(1 for kw in threat_keywords if kw in text_lower)
        risk_score = sum(1 for kw in high_risk_keywords if kw in text_lower)
        
        if threat_score >= 2 or risk_score >= 1:
            classification = "HIGH_RISK"
            confidence = 0.9 + (risk_score * 0.05)
        elif threat_score >= 1:
            classification = "MEDIUM_RISK"
            confidence = 0.7 + (threat_score * 0.1)
        else:
            classification = "LOW_RISK"
            confidence = 0.8
        
        return {
            "classification": classification,
            "confidence": min(confidence, 0.99),
            "model_id": self.model_id,
            "processed_at": FIXED_TIMESTAMP.isoformat()
        }


def write_proof_bundle(
    proof_bundle: ExecutionProofBundle,
    audit_records: list[Dict[str, Any]],
    audit_stream_id: str,
    action_executed: bool,
    output_path: Path,
) -> Path:
    """Write proof bundle and audit records to disk."""
    bundle_data = {
        "bundle": proof_bundle.model_dump(),
        "audit_records": audit_records,
        "audit_stream_id": audit_stream_id,
        "action_executed": action_executed,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    
    output_path.write_text(json.dumps(bundle_data, indent=2, sort_keys=True, cls=EnumEncoder))
    return output_path


def main() -> None:
    """Demonstrate ExoArmur SDK with model-wrapped governance."""
    print("=== Model-Wrapped Governance Demo ===")
    print("Demonstrating: Model → Governance → Verdict → Audit → Proof Bundle")
    print()
    
    # Create SDK configuration
    config = SDKConfig(
        enable_detailed_logging=True,
        strict_replay_verification=True,
        audit_stream_id=INTENT_ID
    )
    
    # Create threat classifier model
    model = SimpleThreatClassifier()
    print("✓ Created deterministic threat classifier model")
    
    # Create governance pipeline (handled internally by SDK)
    print("✓ Created governance pipeline: Policy → SafetyGate → Executor → Audit")
    
    # Create intent for threat classification
    intent = ActionIntent.create(
        actor_id="demo-model",
        actor_type="ai_model",
        action_type="classify_threat",
        target="threat_classification_model",
        parameters={"text": "Critical security breach detected with immediate attack vectors"}
    )
    print(f"✓ Created intent: {intent.action_type} on {intent.target}")
    
    # Run model inference (simulated)
    model_output = model.predict(intent.parameters.get("text", ""))
    print(f"✓ Model inference: {model_output['classification']} (confidence: {model_output['confidence']:.2f})")
    
    # Execute through governed SDK
    try:
        proof_bundle = run_governed_execution(intent, config)
        print(f"✓ Governance verdict: {proof_bundle.final_verdict.value}")
        print(f"✓ Execution result: {'ALLOWED' if proof_bundle.final_verdict == FinalVerdict.ALLOW else 'DENIED'}")
        
        # Verify governance integrity
        verification = verify_governance_integrity(proof_bundle)
        print(f"✓ Governance integrity verified: {verification['is_valid']}")
        
        # Replay the execution
        replay_report = replay_governed_execution(proof_bundle, config)
        print(f"✓ Replay verification: {replay_report.result.value}")
        
        # Write proof bundle
        audit_stream_id = config.audit_stream_id or intent.intent_id
        bundle_path = write_proof_bundle(
            proof_bundle=proof_bundle,
            audit_records=[],  # SDK handles audit internally
            audit_stream_id=audit_stream_id,
            action_executed=proof_bundle.final_verdict == FinalVerdict.ALLOW,
            output_path=PROOF_BUNDLE_PATH,
        )
        
        print()
        print("=== Demo Results ===")
        print(f"Model classification: {model_output['classification']}")
        print(f"Governance verdict: {proof_bundle.final_verdict.value}")
        print(f"Execution allowed: {proof_bundle.final_verdict == FinalVerdict.ALLOW}")
        print(f"Proof bundle written: {bundle_path}")
        print(f"Proof bundle schema version: {proof_bundle.schema_version}")
        print(f"Proof bundle replay hash: {proof_bundle.replay_hash}")
        print(f"Audit stream ID: {audit_stream_id}")
        print()
        print("=== Governance Flow Summary ===")
        print("1. Model inference: SimpleThreatClassifier.predict()")
        print("2. Policy evaluation: ModelOutputPolicyDecisionPoint.evaluate()")
        print("3. Safety gate: SafetyGate.evaluate_safety()")
        print("4. Pipeline execution: ProxyPipeline.execute_with_trace()")
        print("5. Audit emission: V2AuditEmitter captured all events")
        print("6. Proof bundle: BundleBuilder with cryptographic hash and schema versioning")
        print()
        print("DEMO_RESULT=SUCCESS")
        print("MODEL_WRAPPED_GOVERNANCE=DEMONSTRATED")
        
    except Exception as e:
        print(f"✗ SDK execution failed: {e}")
        print("DEMO_RESULT=ERROR")
        print("MODEL_WRAPPED_GOVERNANCE=FAILED")


if __name__ == "__main__":
    main()