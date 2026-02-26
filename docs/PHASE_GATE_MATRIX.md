# Phase Gate Matrix (Phase 1 vs Phase 2+)

Governance: Phase 1 must deny all V2 execution paths before any transport/storage side effect. Phase 2+ remains explicitly gated.

## Phases
- **Phase 1 (default)**: `EXOARMUR_PHASE=1` — V2 surfaces must raise `NotImplementedError` with explicit PhaseGate message before transport/storage.
- **Phase 2+ (future)**: `EXOARMUR_PHASE=2` — V2 surfaces may execute when explicitly elevated; additional capability flags still apply.

## V2 Surfaces
| Surface | Phase 1 Behavior | Expected Failure | Must Occur Before Transport/Storage |
| --- | --- | --- | --- |
| Federation (FederationManager.initialize) | Denied | `NotImplementedError` from `PhaseGate.check_phase_2_eligibility("FederationManager")` | Yes — gate triggers before any NATS connect/JetStream setup |
| Operator Approval (ApprovalService enabled=True paths) | Denied (Phase 2 scaffolding only) | `NotImplementedError` from PhaseGate/feature flag checks when enabled paths are invoked | Yes — gate/flag check before any external call |
| Control Plane (ControlAPI.startup/shutdown/is_running) | Denied | `NotImplementedError` with PhaseGate message | Yes — gate triggers before runtime wiring |
| Durable Storage (V2 KV boundary) | Denied | `NotImplementedError` via PhaseGate for any enabled V2 storage activation | Yes — gate must fire before any storage/transport |

## Failure Mode Notes
- Failure MUST be `NotImplementedError` with explicit PhaseGate rationale: "Phase 2 behavior requires EXOARMUR_PHASE=2" (or equivalent message including current phase).
- Denial must precede any attempt to connect transport (e.g., `nats.connect`) or durable storage.
- Transport guard failures (e.g., test default-deny NATS) must not be the first failure for PhaseGate violations.

## Enforcement Expectations
- When `enabled=True` for any V2 surface in Phase 1, the call must raise immediately via PhaseGate.
- No side effects: no background tasks, network connections, or storage mutations when Phase 1 denial occurs.
- Phase 2 enablement requires explicit phase elevation plus feature-flag controls where applicable.
