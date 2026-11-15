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
| 6 | Docs + handover | pending | |

## Current task
M6 — documentation/handover, then final integration validation.

## Blockers
(none)

## Remaining work
- M6 docs (setup/demo path, limitations).
- Final full-suite run + end-to-end demonstration (real DB + executor + GUI).
- Known gap to verify in final pass: expired-approval path test coverage.
