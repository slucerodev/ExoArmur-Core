# Phase 2B Exit Checklist

## A) Preconditions
- Clean git tree; on branch `phase-2b`.
- Tooling available: Python 3.12, pytest, no local NATS required for hermetic lane.
- Environment defaults: `EXOARMUR_PHASE=1` (Phase 1), transport guard enabled.

## B) Required Commands + Expected Outcomes
- `python3 -m pytest -q`
  - Expected: green; xfail allowed; 0 xpass.
- `python3 -m pytest -q -m "not live_nats"`
  - Expected: green hermetic lane; no network usage.
- `EXOARMUR_TEST_ALLOW_LIVE_NATS=1 python3 -m pytest -q -m live_nats`
  - Expected: live_nats lane passes; opt-in transport only.
- `EXOARMUR_LIVE_DEMO=1 EXOARMUR_TEST_ALLOW_LIVE_NATS=1 python3 -m pytest -q tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream`
  - Expected: live Golden Demo passes; explicit opt-in required.

## C) Go/No-Go Criteria
| Check | Go | No-Go |
| --- | --- | --- |
| git status clean | Yes | Any dirty files not in scope |
| Branch | `phase-2b` | Any other branch |
| pytest -q | Green, 0 xpass | Failures or xpass |
| pytest -q -m "not live_nats" | Green | Any failure/side-effect |
| live_nats lane | Green when opt-in | Failures; unexpected transport when not opt-in |
| Golden Demo live | Pass when explicitly opt-in | Failures or skipped without explicit rationale |

## D) Authorization Rule (PoD → BFT → Counterfactual)
- Execution beyond Phase 2B requires explicit authorization to elevate to Phase 2 and enable module capabilities (PoD, BFT, Counterfactual). No Phase 2 execution without that approval.

## E) Rollback Instructions
- To return to baseline: `git checkout phase2a-green-85067d6`
- If branch exists: `git checkout phase2a-green-85067d6` in detached mode, or create a new branch from that tag if needed.
- Ensure working tree clean before switching; stash or commit local changes first.
