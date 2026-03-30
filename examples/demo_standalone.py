from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from exoarmur.execution_boundary_v2.interfaces.executor_plugin import (
    ExecutorPlugin,
    ExecutorResult,
)
from exoarmur.execution_boundary_v2.interfaces.policy_decision_point import (
    ApprovalStatus,
    PolicyDecisionPoint,
)
from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
from exoarmur.execution_boundary_v2.models.policy_decision import (
    PolicyDecision,
    PolicyVerdict,
)
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import AuditEmitter, ProxyPipeline
from exoarmur.execution_boundary_v2.utils.bundle_builder import build_execution_proof_bundle
from exoarmur.safety.safety_gate import SafetyGate


logging.basicConfig(level=logging.WARNING, format="%(message)s")

AUTHORIZED_ROOT = Path("/tmp/exoarmur-demo-authorized")
UNAUTHORIZED_TARGET = Path("/tmp/exoarmur-demo-private/secret-exports/customer-records.csv")
PROOF_BUNDLE_PATH = Path(__file__).with_name("demo_standalone_proof_bundle.json")
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
INTENT_ID = "demo-standalone-delete-outside-authorized-path"


class PathBoundaryPolicyDecisionPoint(PolicyDecisionPoint):
    def __init__(self, authorized_root: Path):
        self.authorized_root = authorized_root.resolve(strict=False)

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        requested_path = Path(intent.target).expanduser().resolve(strict=False)
        try:
            requested_path.relative_to(self.authorized_root)
        except ValueError:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                rationale=(
                    f"Denied delete request for {requested_path} outside authorized root "
                    f"{self.authorized_root}"
                ),
                evidence={
                    "action_type": intent.action_type,
                    "requested_path": str(requested_path),
                    "authorized_root": str(self.authorized_root),
                    "requested_operation": intent.parameters.get("operation"),
                },
                confidence=1.0,
                approval_required=False,
                policy_version="demo-standalone-v1",
            )

        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            rationale=f"Delete request allowed under {self.authorized_root}",
            evidence={
                "action_type": intent.action_type,
                "requested_path": str(requested_path),
                "authorized_root": str(self.authorized_root),
            },
            confidence=1.0,
            approval_required=False,
            policy_version="demo-standalone-v1",
        )

    def approval_status(self, intent_id: str) -> str:
        return ApprovalStatus.NOT_REQUIRED.value


class GuardedFilesystemExecutor(ExecutorPlugin):
    def name(self) -> str:
        return "guarded-filesystem-executor"

    def capabilities(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "capabilities": ["filesystem.delete"],
            "constraints": {
                "authorized_root": str(AUTHORIZED_ROOT),
                "mode": "demo-deny-only",
            },
        }

    def execute(self, intent: ActionIntent) -> ExecutorResult:
        raise RuntimeError("GuardedFilesystemExecutor must never run for the denied standalone demo")


def build_demo_intent() -> ActionIntent:
    return ActionIntent(
        intent_id=INTENT_ID,
        actor_id="demo-agent-001",
        actor_type="agent",
        action_type="filesystem_delete",
        target=str(UNAUTHORIZED_TARGET),
        parameters={
            "operation": "delete",
            "path": str(UNAUTHORIZED_TARGET),
            "authorized_root": str(AUTHORIZED_ROOT),
        },
        safety_context={
            "scenario": "unauthorized_filesystem_delete",
            "reason": "attempted deletion outside authorized root",
        },
        timestamp=FIXED_TIMESTAMP,
        tenant_id="demo-tenant",
        cell_id="demo-cell",
    )


def write_proof_bundle(
    proof_bundle,
    audit_records,
    audit_stream_id: str,
    action_executed: bool,
    output_path: Path,
) -> Path:
    payload = {
        "audit_stream_id": audit_stream_id,
        "action_executed": action_executed,
        "proof_bundle": proof_bundle.model_dump(mode="json"),
        "audit_records": [record.model_dump(mode="json") for record in audit_records],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return output_path


def main() -> None:
    print("ExoArmur Standalone Execution Boundary Demo")
    print("Simulated AI agent action: delete a file outside the authorized path")
    print(f"Authorized root: {AUTHORIZED_ROOT}")
    print(f"Requested delete target: {UNAUTHORIZED_TARGET}")
    print()

    intent = build_demo_intent()
    policy = PathBoundaryPolicyDecisionPoint(AUTHORIZED_ROOT)
    safety_gate = SafetyGate()
    executor = GuardedFilesystemExecutor()
    audit_emitter = AuditEmitter()
    pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)

    policy_decision = policy.evaluate(intent)
    result, trace = pipeline.execute_with_trace(intent)

    if not isinstance(result, ExecutorResult):
        raise RuntimeError(f"Expected a denied ExecutorResult, got {type(result).__name__}")
    if result.success or result.error != "DENIED" or trace.final_status != "DENIED":
        raise RuntimeError(
            f"Expected denied pipeline outcome, got success={result.success}, error={result.error}, status={trace.final_status}"
        )

    proof_bundle = build_execution_proof_bundle(
        intent=intent,
        policy_decision=policy_decision,
        approval_records=[],
        execution_trace=trace,
        executor_result={
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "evidence": result.evidence,
        },
    )

    audit_stream_id = intent.intent_id
    bundle_path = write_proof_bundle(
        proof_bundle=proof_bundle,
        audit_records=audit_emitter.audit_records,
        audit_stream_id=audit_stream_id,
        action_executed=result.success,
        output_path=PROOF_BUNDLE_PATH,
    )

    print("Execution boundary result: policy denied before any filesystem side effect")
    print(f"Proof bundle written: {bundle_path}")
    print(f"Proof bundle replay hash: {proof_bundle.replay_hash}")
    print("DEMO_RESULT=DENIED")
    print("ACTION_EXECUTED=false")
    print(f"AUDIT_STREAM_ID={audit_stream_id}")


if __name__ == "__main__":
    main()
