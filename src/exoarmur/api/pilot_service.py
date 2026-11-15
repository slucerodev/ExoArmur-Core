"""
Pilot governed-action service (2.2.0).

One real, restricted workflow: an authenticated principal proposes a
narrowly-scoped file write inside an operator-configured workspace. The
proposal is evaluated by the digest-verified operator policy, durably
stored, and — when the policy requires it — held for human approval bound
to the exact stored parameters. Execution resumes only from the stored
action, re-checking authorization, policy, and durable execution pauses
immediately before dispatch.

Honesty notes:
- File effects are real but local; there is no exactly-once guarantee —
  a crash between executor success and evidence persistence can leave an
  action EXECUTING. Resume of an EXECUTING action reports the ambiguity
  rather than blindly re-executing.
- Evidence integrity is payload-hash consistency recorded at write time;
  it is not signer verification or proof against a compromised store.
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from exoarmur.api.auth import Principal
from exoarmur.api.db import get_pool
from exoarmur.api.policy_source import OperatorPolicyDecisionPoint
from exoarmur.executors.file_system_executor import FileSystemExecutor
from exoarmur.kernel.boundary import (
    ActionIntent,
    ExecutionDispatch,
    ExecutorResult,
    PolicyDecisionPoint,
    ProxyPipeline,
    SafetyGate,
    SafetyInputs,
    V2AuditEmitter,
    V2EnvironmentState,
    V2PolicyState,
    V2TrustState,
)
from exoarmur.kernel.canonicalization import canonical_hash
from exoarmur.kernel.clock import utc_now
from exoarmur.kernel.ids import make_audit_id

SUPPORTED_OPERATIONS = {"create_file", "modify_file"}
_EXECUTOR_OP = {"create_file": "create", "modify_file": "modify"}


class PilotUnavailableError(Exception):
    """Pilot path cannot run (missing config or durable store)."""


class PilotStoreError(Exception):
    """Durable state unreadable — must block execution."""


@dataclass
class ActionRecord:
    action_id: str
    tenant_id: str
    principal_id: str
    operation: str
    target_path: str
    parameters: Dict[str, Any]
    params_sha256: str
    action_class: str
    policy_version: Optional[str]
    status: str
    approval_id: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[str]
    expires_at: Optional[str]
    result: Optional[Dict[str, Any]]
    evidence: Optional[Dict[str, Any]]
    evidence_sha256: Optional[str]
    idempotency_key: str
    created_at: str
    updated_at: str


def _row_to_action(r: Any) -> ActionRecord:
    return ActionRecord(
        action_id=r["action_id"],
        tenant_id=r["tenant_id"],
        principal_id=r["principal_id"],
        operation=r["operation"],
        target_path=r["target_path"],
        parameters=dict(r["parameters"] or {}),
        params_sha256=r["params_sha256"],
        action_class=r["action_class"],
        policy_version=r["policy_version"],
        status=r["status"],
        approval_id=r["approval_id"],
        approved_by=r["approved_by"],
        approved_at=str(r["approved_at"]) if r["approved_at"] else None,
        expires_at=str(r["expires_at"]) if r["expires_at"] else None,
        result=dict(r["result"]) if r["result"] else None,
        evidence=dict(r["evidence"]) if r["evidence"] else None,
        evidence_sha256=r["evidence_sha256"],
        idempotency_key=r["idempotency_key"],
        created_at=str(r["created_at"]),
        updated_at=str(r["updated_at"]),
    )


_SELECT = """
    SELECT action_id, tenant_id, principal_id, operation, target_path,
           parameters, params_sha256, action_class, policy_version, status,
           approval_id, approved_by, approved_at, expires_at, result,
           evidence, evidence_sha256, idempotency_key, created_at, updated_at
    FROM governed_actions
"""


class PilotService:
    """Composes policy, safety inputs, pauses, executor, and evidence."""

    def __init__(
        self,
        workspace_root: str,
        policy: OperatorPolicyDecisionPoint,
        approval_ttl_hours: int = 24,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.policy = policy
        self.approval_ttl_hours = approval_ttl_hours
        self.executor = FileSystemExecutor(authorized_root=str(self.workspace_root))

    # ------------------------------------------------------------------
    # Configuration / availability
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "PilotService":
        root = os.getenv("EXOARMUR_WORKSPACE_ROOT")
        policy_file = os.getenv("EXOARMUR_POLICY_FILE")
        policy_sha = os.getenv("EXOARMUR_POLICY_SHA256")
        if not root or not policy_file or not policy_sha:
            raise PilotUnavailableError(
                "Pilot requires EXOARMUR_WORKSPACE_ROOT, EXOARMUR_POLICY_FILE, "
                "and EXOARMUR_POLICY_SHA256"
            )
        from exoarmur.api.policy_source import load_operator_policy

        try:
            op = load_operator_policy(policy_file, policy_sha)
        except Exception as e:
            # Fail closed: unavailable policy => PDP denies everything.
            pdp = OperatorPolicyDecisionPoint(None)
            service = cls(root, pdp)
            service.policy_load_error = str(e)
            return service
        return cls(root, OperatorPolicyDecisionPoint(op))

    async def _pool(self):
        pool = await get_pool()
        if pool is None:
            raise PilotStoreError("Durable store unavailable")
        return pool

    # ------------------------------------------------------------------
    # Pauses (durable global + tenant)
    # ------------------------------------------------------------------

    async def pause_state(self, tenant_id: str) -> Dict[str, Any]:
        """Read durable pause rows. Unreadable store => PilotStoreError."""
        pool = await self._pool()
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT scope, scope_key, paused, updated_by, updated_at "
                    "FROM execution_pauses WHERE scope='global' "
                    "OR (scope='tenant' AND scope_key=$1)",
                    tenant_id,
                )
        except Exception as e:
            raise PilotStoreError(f"Cannot read pause state: {e}") from e
        state = {"global": False, "tenant": False, "detail": {}}
        for r in rows:
            key = "global" if r["scope"] == "global" else "tenant"
            state[key] = bool(r["paused"])
            state["detail"][key] = {
                "paused": bool(r["paused"]),
                "updated_by": r["updated_by"],
                "updated_at": str(r["updated_at"]),
            }
        return state

    async def set_pause(
        self, scope: str, scope_key: str, paused: bool, actor: str
    ) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO execution_pauses (scope, scope_key, paused, updated_by)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (scope, scope_key) DO UPDATE SET
                    paused = EXCLUDED.paused,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
                """,
                scope,
                scope_key,
                paused,
                actor,
            )

    # ------------------------------------------------------------------
    # Action submission
    # ------------------------------------------------------------------

    def _resolve_target(self, rel_path: str) -> Path:
        """Resolve a workspace-relative path; reject escapes."""
        if not rel_path or rel_path.startswith("/") or "\x00" in rel_path:
            raise ValueError("path must be a non-empty relative path")
        candidate = (self.workspace_root / rel_path).resolve()
        try:
            candidate.relative_to(self.workspace_root)
        except ValueError:
            raise ValueError("path escapes the configured workspace")
        return candidate

    def _params_hash(self, tenant_id, principal_id, operation, rel_path, content):
        return canonical_hash(
            {
                "tenant_id": tenant_id,
                "principal_id": principal_id,
                "operation": operation,
                "path": rel_path,
                "content": content,
            }
        )

    async def submit(
        self,
        principal: Principal,
        operation: str,
        rel_path: str,
        content: str,
        tenant_id: Optional[str] = None,
    ) -> Tuple[ActionRecord, bool]:
        """Propose an action. Returns (record, created)."""
        if operation not in SUPPORTED_OPERATIONS:
            raise ValueError(f"Unsupported operation: {operation}")

        target = self._resolve_target(rel_path)
        tenant_id = tenant_id or (
            principal.tenant_ids[0] if len(principal.tenant_ids) == 1 else None
        )
        if tenant_id is None or not principal.allows_tenant(tenant_id):
            raise PermissionError("Principal not authorized for requested tenant")

        params_hash = self._params_hash(
            tenant_id, principal.principal_id, operation, rel_path, content
        )
        idempotency_key = params_hash

        pool = await self._pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                _SELECT + " WHERE idempotency_key = $1", idempotency_key
            )
            if existing is not None:
                return _row_to_action(existing), False

            intent = self._build_intent(
                principal, operation, str(target), rel_path, content, tenant_id
            )
            decision = self.policy.evaluate(intent)

            action_class = self._action_class_for(intent)
            action_id = canonical_hash(
                {"idem": idempotency_key, "tenant": tenant_id}
            )[:32]
            now = utc_now()
            from datetime import timedelta

            expires = now + timedelta(hours=self.approval_ttl_hours)

            status = {
                "allow": "APPROVED",
                "require_approval": "PENDING_APPROVAL",
                "deny": "DENIED",
            }.get(decision.verdict.value, "BLOCKED")

            await conn.execute(
                """
                INSERT INTO governed_actions (
                    action_id, tenant_id, principal_id, operation, target_path,
                    parameters, params_sha256, action_class, policy_version,
                    status, approval_id, expires_at, idempotency_key
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                """,
                action_id,
                tenant_id,
                principal.principal_id,
                operation,
                str(target),
                {
                    "operation": _EXECUTOR_OP[operation],
                    "payload": {"content": content},
                    "path": rel_path,
                },
                params_hash,
                action_class or "unknown",
                decision.policy_version,
                status,
                action_id if status == "PENDING_APPROVAL" else None,
                expires,
                idempotency_key,
            )

        await self._audit(
            action_id,
            tenant_id,
            "action_proposed",
            {
                "operation": operation,
                "path": rel_path,
                "status": status,
                "policy_verdict": decision.verdict.value,
                "principal_id": principal.principal_id,
            },
        )

        record = await self.get_action(action_id)
        assert record is not None
        if record.status == "APPROVED":
            # Policy allowed without approval — dispatch immediately.
            dispatched = await self.resume(action_id, principal)
            return dispatched, True
        return record, True

    def _build_intent(
        self,
        principal: Principal,
        operation: str,
        target: str,
        rel_path: str,
        content: str,
        tenant_id: str,
    ) -> ActionIntent:
        return ActionIntent.create(
            actor_id=principal.principal_id,
            actor_type="operator",
            action_type=f"fs.{operation}",
            target=target,
            parameters={
                "operation": _EXECUTOR_OP[operation],
                "payload": {"content": content},
                "path": rel_path,
            },
            tenant_id=tenant_id,
            cell_id="pilot",
        )

    def _action_class_for(self, intent: ActionIntent) -> Optional[str]:
        """Resolve action class from the matched policy rule only."""
        pol = getattr(self.policy, "policy", None)
        if pol is None:
            return None
        rule = pol.matching_rule(intent)
        return rule.action_class_for(intent.action_type) if rule else None

    def _rule_for(self, intent: ActionIntent):
        pol = getattr(self.policy, "policy", None)
        return pol.matching_rule(intent) if pol else None

    # ------------------------------------------------------------------
    # Approval / resume
    # ------------------------------------------------------------------

    async def get_action(self, action_id: str) -> Optional[ActionRecord]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_SELECT + " WHERE action_id = $1", action_id)
        return _row_to_action(row) if row else None

    async def list_actions(
        self, tenant_id: str, status: Optional[str] = None, limit: int = 100
    ) -> List[ActionRecord]:
        pool = await self._pool()
        async with pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    _SELECT
                    + " WHERE tenant_id = $1 AND status = $2 "
                    + "ORDER BY created_at DESC LIMIT $3",
                    tenant_id, status, limit,
                )
            else:
                rows = await conn.fetch(
                    _SELECT
                    + " WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2",
                    tenant_id, limit,
                )
        return [_row_to_action(r) for r in rows]

    async def approve(
        self, action_id: str, approver: Principal
    ) -> ActionRecord:
        """Approve the exact stored action, then resume it."""
        record = await self.get_action(action_id)
        if record is None:
            raise KeyError("Action not found")
        if not approver.allows_tenant(record.tenant_id):
            raise PermissionError("Approver not authorized for action tenant")
        if record.status == "EXECUTED":
            return record  # idempotent: already done, no re-dispatch
        if record.status == "DENIED":
            raise ValueError("Action was denied")

        pool = await self._pool()
        async with pool.acquire() as conn:
            # Atomic claim: only PENDING_APPROVAL -> APPROVED transitions.
            row = await conn.fetchrow(
                """
                UPDATE governed_actions
                SET status='APPROVED', approved_by=$2, approved_at=NOW(),
                    updated_at=NOW()
                WHERE action_id=$1 AND status='PENDING_APPROVAL'
                RETURNING action_id
                """,
                action_id, approver.principal_id,
            )
            if row is None:
                current = await self.get_action(action_id)
                if current and current.status == "EXECUTED":
                    return current
                raise ValueError(f"Action not approvable in state {record.status}")

        await self._audit(
            action_id, record.tenant_id, "approval_granted",
            {"approver": approver.principal_id},
        )
        return await self.resume(action_id, approver)

    async def deny(
        self, action_id: str, denier: Principal, reason: str
    ) -> ActionRecord:
        record = await self.get_action(action_id)
        if record is None:
            raise KeyError("Action not found")
        if not denier.allows_tenant(record.tenant_id):
            raise PermissionError("Denier not authorized for action tenant")

        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE governed_actions
                SET status='DENIED', approved_by=$2, approved_at=NOW(),
                    result = COALESCE(result,'{}'::jsonb) || $3::jsonb,
                    updated_at=NOW()
                WHERE action_id=$1 AND status='PENDING_APPROVAL'
                RETURNING action_id
                """,
                action_id, denier.principal_id,
                {"denial_reason": reason},
            )
            if row is None:
                raise ValueError(f"Action not deniable in state {record.status}")

        await self._audit(
            action_id, record.tenant_id, "approval_denied",
            {"denier": denier.principal_id, "reason": reason},
        )
        updated = await self.get_action(action_id)
        assert updated is not None
        return updated

    async def resume(self, action_id: str, actor: Principal) -> ActionRecord:
        """Dispatch a stored APPROVED action after fresh checks."""
        record = await self.get_action(action_id)
        if record is None:
            raise KeyError("Action not found")
        if record.status == "EXECUTED":
            return record
        if record.status in ("DENIED", "EXPIRED", "FAILED"):
            raise ValueError(f"Action cannot resume from state {record.status}")
        if not actor.allows_tenant(record.tenant_id):
            raise PermissionError("Actor not authorized for action tenant")

        # Expiry check
        if record.expires_at:
            from datetime import datetime, timezone

            exp = datetime.fromisoformat(record.expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < utc_now():
                await self._set_status(action_id, "EXPIRED")
                raise ValueError("Approval expired")

        # Atomic claim APPROVED -> EXECUTING (or PENDING->EXECUTING for
        # policy-allowed actions submitted directly).
        pool = await self._pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE governed_actions SET status='EXECUTING', updated_at=NOW()
                WHERE action_id=$1 AND status IN ('APPROVED','PENDING_APPROVAL')
                RETURNING action_id
                """,
                action_id,
            )
            if row is None:
                current = await self.get_action(action_id)
                if current and current.status == "EXECUTED":
                    return current
                if current and current.status == "EXECUTING":
                    raise ValueError(
                        "Action dispatch already in progress or outcome ambiguous; "
                        "not retrying to avoid duplicate effects"
                    )
                raise ValueError(f"Action not resumable in state {record.status}")

        return await self._dispatch(record)

    # ------------------------------------------------------------------
    # Dispatch: pause -> safety inputs -> pipeline -> evidence
    # ------------------------------------------------------------------

    async def _set_status(self, action_id: str, status: str) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE governed_actions SET status=$2, updated_at=NOW() "
                "WHERE action_id=$1",
                action_id, status,
            )

    async def _dispatch(self, record: ActionRecord) -> ActionRecord:
        intent = self._build_intent(
            Principal(
                principal_id=record.principal_id,
                tenant_ids=(record.tenant_id,),
                permissions=frozenset(),
            ),
            record.operation,
            record.target_path,
            record.parameters.get("path", ""),
            record.parameters.get("payload", {}).get("content", ""),
            record.tenant_id,
        )
        # Deterministic intent id is reproduced identically at dispatch.

        # --- Durable pause check, immediately before dispatch ---
        try:
            pauses = await self.pause_state(record.tenant_id)
        except PilotStoreError as e:
            await self._finish(record.action_id, "BLOCKED",
                               {"result": {"reason": f"pause_state_unavailable: {e}"}})
            raise
        if pauses["global"] or pauses["tenant"]:
            await self._finish(
                record.action_id, "BLOCKED",
                {"result": {"reason": "execution_paused",
                 "pause": {k: v for k, v in pauses["detail"].items() if v["paused"]}}},
            )
            updated = await self.get_action(record.action_id)
            assert updated is not None
            return updated

        # --- Safety inputs from trusted config (never request data) ---
        rule = self._rule_for(intent)
        trust = rule.trust_score if rule else None
        if trust is None:
            await self._finish(
                record.action_id, "BLOCKED",
                {"result": {"reason": "trusted_trust_score_unavailable"}},
            )
            updated = await self.get_action(record.action_id)
            assert updated is not None
            return updated

        safety_inputs = SafetyInputs(
            policy_state=V2PolicyState(
                policy_verified=self.policy.policy is not None,
                kill_switch_global=pauses["global"],
                kill_switch_tenant=pauses["tenant"],
                required_approval=(rule.required_approval if rule else "none"),
            ),
            trust_state=V2TrustState(emitter_trust_score=trust),
            environment_state=V2EnvironmentState(
                degraded_mode=os.getenv("EXOARMUR_DEGRADED_MODE", "false").lower()
                == "true"
            ),
            source="operator_config",
        )

        # Approved resumes bypass REQUIRE_APPROVAL only with a recorded
        # approver; unmatched rules still deny inside evaluate_approved.
        pdp = self.policy
        approval_valid = record.approved_by is not None
        if approval_valid and hasattr(pdp, "evaluate_approved"):
            decision = pdp.evaluate_approved(intent, approval_valid=True)
        else:
            decision = pdp.evaluate(intent)

        pipeline = ProxyPipeline(
            policy=_ResumePolicy(pdp, decision),
            safety_gate=SafetyGate(),
            executor=self.executor,
            audit_emitter=V2AuditEmitter(),
            safety_context_provider=lambda _i: safety_inputs,
        )

        result, trace = pipeline.execute_with_trace(intent)

        # --- Persist outcome + evidence ---
        trace_payload = [
            {
                "stage": ev.stage.value if hasattr(ev.stage, "value") else str(ev.stage),
                "ok": ev.ok,
                "code": ev.code,
                "details": ev.details,
            }
            for ev in trace.events
        ]
        if isinstance(result, ExecutorResult):
            status = "EXECUTED" if result.success else "FAILED"
            evidence = {
                "execution_id": result.execution_id,
                "output": result.output,
                "executor_evidence": result.evidence,
                "error": result.error,
                "trace": trace_payload,
                "final_verdict": trace.final_verdict,
                "policy_version": decision.policy_version,
            }
        else:
            status = "BLOCKED"
            evidence = {
                "dispatch_status": result.status.value
                if hasattr(result.status, "value") else str(result.status),
                "trace": trace_payload,
                "final_verdict": trace.final_verdict,
                "policy_version": decision.policy_version,
            }

        evidence["params_sha256"] = record.params_sha256
        evidence_sha = canonical_hash(evidence)

        await self._finish(
            record.action_id,
            status,
            {
                "result": {
                    "success": getattr(result, "success", False),
                    "execution_id": getattr(result, "execution_id", None),
                    "error": getattr(result, "error", None),
                },
                "evidence": evidence,
                "evidence_sha256": evidence_sha,
            },
        )
        await self._audit(
            record.action_id, record.tenant_id,
            "action_dispatched",
            {"status": status, "final_verdict": trace.final_verdict,
             "evidence_sha256": evidence_sha},
        )
        updated = await self.get_action(record.action_id)
        assert updated is not None
        return updated

    async def _finish(self, action_id: str, status: str, extra: Dict[str, Any]) -> None:
        pool = await self._pool()
        async with pool.acquire() as conn:
            sets = ["status=$2", "updated_at=NOW()"]
            params: List[Any] = [action_id, status]
            if "result" in extra:
                params.append(extra["result"])
                sets.append(f"result=${len(params)}::jsonb")
            if "evidence" in extra:
                params.append(extra["evidence"])
                sets.append(f"evidence=${len(params)}::jsonb")
            if "evidence_sha256" in extra:
                params.append(extra["evidence_sha256"])
                sets.append(f"evidence_sha256=${len(params)}")
            await conn.execute(
                f"UPDATE governed_actions SET {', '.join(sets)} WHERE action_id=$1",
                *params,
            )

    async def _audit(
        self, action_id: str, tenant_id: str, kind: str, payload: Dict[str, Any]
    ) -> None:
        try:
            from exoarmur.api.stores import audit_store
            from exoarmur.api.models import AuditRecord

            await audit_store.append(
                AuditRecord(
                    audit_id=make_audit_id(action_id, "pilot", kind),
                    event_kind=f"pilot_{kind}",
                    payload_ref={"action_id": action_id, **payload},
                    correlation_id=action_id,
                    trace_id="",
                    tenant_id=tenant_id,
                    cell_id="pilot",
                    idempotency_key=f"{action_id}-{kind}",
                    created_at=utc_now().isoformat(),
                )
            )
        except Exception:
            # Audit persistence failure must not silently pass; surface it.
            raise

    # ------------------------------------------------------------------
    # Evidence verification
    # ------------------------------------------------------------------

    async def verify_action(self, action_id: str) -> Dict[str, Any]:
        """Recompute stored hashes and compare to values recorded at write."""
        record = await self.get_action(action_id)
        if record is None:
            raise KeyError("Action not found")

        # parameters store the executor op name; the submit-time hash used
        # the pilot operation name, so recompute with record.operation.
        recomputed_params = self._params_hash(
            record.tenant_id,
            record.principal_id,
            record.operation,
            record.parameters.get("path", ""),
            record.parameters.get("payload", {}).get("content", ""),
        )
        params_ok = recomputed_params == record.params_sha256
        checks = [{"check": "params_sha256", "status": "VERIFIED" if params_ok else "MISMATCH"}]

        ev_ok = None
        if record.evidence is not None and record.evidence_sha256:
            recomputed_ev = canonical_hash(record.evidence)
            ev_ok = recomputed_ev == record.evidence_sha256
            checks.append({"check": "evidence_sha256", "status": "VERIFIED" if ev_ok else "MISMATCH"})
        else:
            checks.append({"check": "evidence_sha256", "status": "NOT_CHECKED",
                           "reason": "no evidence recorded"})

        overall = "VERIFIED" if params_ok and all(
            c["status"] in ("VERIFIED", "NOT_CHECKED") for c in checks
        ) else "MISMATCH"
        return {
            "action_id": action_id,
            "status": record.status,
            "checks": checks,
            "overall": overall,
            "verified_at": utc_now().isoformat(),
        }


class _ResumePolicy:
    """Wraps the PDP so the pipeline sees the precomputed resume decision."""

    def __init__(self, inner: PolicyDecisionPoint, decision):
        self._inner = inner
        self._decision = decision

    def evaluate(self, intent: ActionIntent):
        return self._decision

    def approval_status(self, intent_id: str):
        return self._inner.approval_status(intent_id)
