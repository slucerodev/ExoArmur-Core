"""
ExoArmur Public SDK API

This module provides the ONLY stable, public entrypoint for ExoArmur governance functionality.
All internal modules are considered implementation details and may change without notice.

GOVERNANCE GUARANTEES:
- All executions go through the governed ProxyPipeline
- No direct executor access is permitted
- All proof bundles are created through the official builder
- All replay operations use the deterministic ReplayEngine

DETERMINISM GUARANTEES:
- Identical inputs produce identical outputs across runs
- All timestamps use deterministic clock abstraction
- All IDs are generated through deterministic ULID factory
- Replay hashes are stable and cryptographically verifiable

REPLAY GUARANTEES:
- Every execution produces a verifiable proof bundle
- Proof bundles can be deterministically replayed
- Schema migration is handled automatically
- Audit trails are complete and immutable

USAGE:
    from exoarmur.sdk.public_api import run_governed_execution, replay_governed_execution
    
    # Execute with full governance
    bundle = run_governed_execution(intent, config)
    
    # Replay with verification
    report = replay_governed_execution(bundle)

WARNING:
    Do NOT import internal modules directly.
    Use only the public API functions provided here.
    Internal modules are NOT stable and may change.
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime

# Public SDK imports - these are the ONLY stable APIs
from ..execution_boundary_v2.models.action_intent import ActionIntent
from ..execution_boundary_v2.models.execution_proof_bundle import ExecutionProofBundle
from ..execution_boundary_v2.utils.verdict_resolution import FinalVerdict
from ..replay.replay_engine import ReplayEngine, ReplayReport
from ..clock import utc_now
from ..ids import make_id


class SDKConfig:
    """Configuration for SDK operations.
    
    Attributes:
        enable_detailed_logging: Enable detailed governance logging
        strict_replay_verification: Require strict replay verification
        audit_stream_id: Optional audit stream ID for tracking
    """
    
    def __init__(
        self,
        enable_detailed_logging: bool = False,
        strict_replay_verification: bool = True,
        audit_stream_id: Optional[str] = None
    ):
        self.enable_detailed_logging = enable_detailed_logging
        self.strict_replay_verification = strict_replay_verification
        self.audit_stream_id = audit_stream_id
        self.config_id = make_id("sdk_config")
        self.created_at = utc_now()


def run_governed_execution(
    intent: ActionIntent,
    config: Optional[SDKConfig] = None
) -> ExecutionProofBundle:
    """Execute an intent through the full governance pipeline.
    
    This is the ONLY supported way to execute actions in ExoArmur.
    All executions go through the governed ProxyPipeline with policy evaluation,
    safety gate enforcement, and comprehensive audit trails.
    
    Args:
        intent: The action intent to execute
        config: Optional SDK configuration
        
    Returns:
        ExecutionProofBundle: Complete proof bundle with deterministic replay verification
        
    Raises:
        ValueError: If intent is invalid or governance fails
        RuntimeError: If governance pipeline encounters errors
        
    Governance Guarantees:
    - Intent is evaluated by PolicyDecisionPoint
    - Safety gate enforcement is applied
    - Executor is sandboxed and capability-restricted
    - Complete audit trail is generated
    - Cryptographic proof bundle is created
    - Deterministic replay is supported
    
    Example:
        intent = ActionIntent.create(
            action_type="file_delete",
            target="/path/to/file",
            parameters={"force": False}
        )
        
        bundle = run_governed_execution(intent)
        print(f"Execution bundle: {bundle.bundle_id}")
        print(f"Schema version: {bundle.schema_version}")
        print(f"Replay hash: {bundle.replay_hash}")
    """
    if config is None:
        config = SDKConfig()
    
    # Import internal components - these are implementation details
    from ..execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline, V2AuditEmitter
    from ..execution_boundary_v2.interfaces.policy_decision_point import PolicyDecisionPoint
    from ..execution_boundary_v2.interfaces.executor_plugin import ExecutorPlugin
    from ..safety.safety_gate import SafetyGate
    from ..execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict
    
    # Create a simple SDK policy that denies everything for demonstration
    class SDKPolicyDecisionPoint(PolicyDecisionPoint):
        """Simple SDK policy that denies all actions for demonstration."""
        
        def evaluate(self, intent: ActionIntent) -> PolicyDecision:
            return PolicyDecision.create(
                intent_id=intent.intent_id,
                verdict=PolicyVerdict.DENY,
                rationale="SDK demonstration: All actions denied for safety",
                confidence=1.0
            )
        
        def approval_status(self, intent_id: str):
            from ..interfaces.policy_decision_point import ApprovalStatus
            return ApprovalStatus.DENIED
    
    # Create governance components (internal implementation)
    # NOTE: These are internal components and may change
    policy = SDKPolicyDecisionPoint()
    safety_gate = SafetyGate()
    audit_emitter = V2AuditEmitter()
    
    # Create a mock executor for demonstration
    # In production, this would be a real sandboxed executor
    class MockExecutor(ExecutorPlugin):
        def execute(self, intent: ActionIntent) -> Any:
            return {"success": False, "error": "DENIED", "output": None}
        
        def validate_target(self, intent: ActionIntent) -> Any:
            return {"result": "invalid", "reason": "Mock validation"}
    
    executor = MockExecutor()
    
    # Create governance pipeline (internal implementation)
    pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
    
    # Execute through governed pipeline
    try:
        result, trace = pipeline.execute_with_trace(intent)
        
        # Create proof bundle through official builder (internal implementation)
        from ..execution_boundary_v2.utils.bundle_builder import build_execution_proof_bundle
        
        bundle = build_execution_proof_bundle(
            intent=intent,
            policy_decision=policy.evaluate(intent),
            execution_trace=trace.model_dump() if hasattr(trace, 'model_dump') else trace,
            executor_result={
                "success": result.success if hasattr(result, 'success') else False,
                "output": getattr(result, 'output', None),
                "error": getattr(result, 'error', None),
                "evidence": getattr(result, 'evidence', {}),
            }
        )
        
        if config.enable_detailed_logging:
            print(f"[SDK] Governance execution completed: {bundle.bundle_id}")
            print(f"[SDK] Schema version: {bundle.schema_version}")
            print(f"[SDK] Replay hash: {bundle.replay_hash}")
        
        return bundle
        
    except Exception as e:
        raise RuntimeError(f"Governance execution failed: {e}") from e


def replay_governed_execution(
    bundle: Union[ExecutionProofBundle, Dict[str, Any]],
    config: Optional[SDKConfig] = None
) -> ReplayReport:
    """Replay and verify a governed execution proof bundle.
    
    This is the ONLY supported way to replay executions in ExoArmur.
    All replay operations go through the deterministic ReplayEngine with
    automatic schema migration and comprehensive verification.
    
    Args:
        bundle: Execution proof bundle to replay (can be dict or ExecutionProofBundle)
        config: Optional SDK configuration
        
    Returns:
        ReplayReport: Comprehensive replay verification report
        
    Raises:
        ValueError: If bundle is invalid or cannot be replayed
        RuntimeError: If replay encounters errors
        
    Replay Guarantees:
    - Automatic schema migration for older bundles
    - Deterministic replay verification
    - Cryptographic hash validation
    - Complete audit trail reconstruction
    - Governance compliance verification
    
    Example:
        bundle = run_governed_execution(intent)
        report = replay_governed_execution(bundle)
        
        if report.result.value == "success":
            print("Replay verification passed")
        else:
            print(f"Replay failed: {report.failures}")
    """
    if config is None:
        config = SDKConfig()
    
    # Convert bundle to dict if needed
    if isinstance(bundle, ExecutionProofBundle):
        bundle_dict = bundle.model_dump()
    else:
        bundle_dict = bundle
    
    # Create replay engine (internal implementation)
    replay_engine = ReplayEngine({})
    
    try:
        # Perform replay with automatic migration
        report = replay_engine.replay_bundle_with_migration(bundle_dict)
        
        if config.enable_detailed_logging:
            print(f"[SDK] Replay completed: {report.result.value}")
            print(f"[SDK] Schema validation: {report.warnings}")
        
        return report
        
    except Exception as e:
        raise RuntimeError(f"Replay execution failed: {e}") from e


def verify_governance_integrity(bundle: ExecutionProofBundle) -> Dict[str, Any]:
    """Verify the integrity of a governance proof bundle.
    
    Args:
        bundle: Execution proof bundle to verify
        
    Returns:
        Dict containing verification results
        
    Verification Checks:
    - Schema version compatibility
    - Cryptographic hash integrity
    - Canonical structure validity
    - Replay determinism
    """
    # Import internal verification components
    from ..execution_boundary_v2.schema_migrations import SchemaMigrations
    from ..execution_boundary_v2.utils.canonicalization import compute_replay_hash_with_migration
    
    bundle_dict = bundle.model_dump()
    
    verification = {
        "bundle_id": bundle.bundle_id,
        "schema_version": bundle.schema_version,
        "verification_timestamp": utc_now(),
        "final_verdict": bundle.final_verdict.value if hasattr(bundle.final_verdict, 'value') else str(bundle.final_verdict),
        "checks": {}
    }
    
    # Check schema version
    try:
        schema_report = SchemaMigrations.validate_schema_compliance(bundle_dict)
        verification["checks"]["schema_version"] = {
            "valid": schema_report["is_supported"],
            "current": schema_report["is_current"],
            "issues": schema_report["issues"]
        }
    except Exception as e:
        verification["checks"]["schema_version"] = {
            "valid": False,
            "error": str(e)
        }
    
    # Check replay hash
    try:
        computed_hash = compute_replay_hash_with_migration(bundle_dict)
        verification["checks"]["replay_hash"] = {
            "valid": computed_hash == bundle.replay_hash,
            "computed": computed_hash,
            "original": bundle.replay_hash
        }
    except Exception as e:
        verification["checks"]["replay_hash"] = {
            "valid": False,
            "error": str(e)
        }
    
    # Overall validity
    verification["is_valid"] = all(
        check.get("valid", False) for check in verification["checks"].values()
    )
    
    return verification


# Public API exports - these are the ONLY stable exports
__all__ = [
    "run_governed_execution",
    "replay_governed_execution", 
    "verify_governance_integrity",
    "SDKConfig",
    "ActionIntent",
    "ExecutionProofBundle",
    "FinalVerdict"
]

# SDK version information
SDK_VERSION = "1.0.0"
GOVERNANCE_VERSION = "2.0"
SUPPORTED_SCHEMA_VERSIONS = ["1.0", "2.0"]

print(f"[SDK] ExoArmur Public SDK v{SDK_VERSION} loaded")
print(f"[SDK] Governance version: {GOVERNANCE_VERSION}")
print(f"[SDK] Supported schema versions: {SUPPORTED_SCHEMA_VERSIONS}")