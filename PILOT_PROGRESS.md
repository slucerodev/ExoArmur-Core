# Pilot Progress — Governed Workflow (2.2.0 baseline)

- **Baseline:** `baseline-2.2.0-alignment` @ `80cb2d9` (docs alignment on `26cd75d`)
- **Branch:** `pilot/governed-workflow`
- **Worktree:** `/home/oem/ExoArmur-Core-main` (old worktree/branch preserved untouched)
- **Test DB:** local PostgreSQL `exoarmur_pilot_test` @ localhost:54322

## Milestones

| # | Milestone | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Trusted policy + safety inputs | implemented, focused tests pass | `kernel/boundary.py` `SafetyInputs`/`SafetyContextProvider`, fail-closed default; `api/policy_source.py` digest-pinned operator policy |
| 2 | Authentication & authorization | implemented, focused tests pass | `api/auth.py` API-key principals (hash-only store), CSRF on cookie sessions, per-route permission checks |
| 3 | Real governed action + approval resume | implemented, focused tests pass | `api/pilot_service.py` + `executors/file_system_executor.py` via `ProxyPipeline`; exact-param approval binding, deny/expiry, idempotent resume |
| 4 | Durable pause + evidence | implemented, focused tests pass | `api/migrations/002_pilot.sql` (actions, pauses, evidence); pause re-check before dispatch; payload-hash verification endpoint |
| 5 | Operator GUI | implemented | `api/gui/index.html` server-served, real API state, no stored master keys |
| 6 | Docs + handover | done | `docs/PILOT.md` runbook; KNOWN_LIMITATIONS/README/docs index updated |

## Current task
Complete — final report.

## Blockers
(none)

## Validation evidence
- `tests/api/test_pilot.py`: 19 passed against real PostgreSQL (auth, tenant isolation, policy deny/allow, approval flow, deny, expiry, idempotency, pause global/tenant, traversal rejection, evidence verify+tamper, restart durability, GUI serving).
- Full suite: 398 passed, 17 skipped.
- Live demo (uvicorn + real DB + FileSystemExecutor): submit→PENDING_APPROVAL (no file), approve→EXECUTED + file written, evidence VERIFIED, global pause→BLOCKED no file, missing key→401, GUI served.

## Remaining work
- Legacy routes (`/v1/*`, `/api/v2/*`, `/api/cli/*`) remain unauthenticated — out of pilot scope, documented.
- Pilot branch not merged to main (per instructions).
