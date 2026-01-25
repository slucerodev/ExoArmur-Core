---
auto_execution_mode: 2
---
RECOMMENDED WORKFLOW — CASCADE (EXOARMUR ADMO)

PRIORITY:
Achieve constitutional test stability before any roadmap or feature development.

OBJECTIVE:
Restore binary-green truth across the repository and lock Phase -0.5 before proceeding.

────────────────────────────────────────────
WORKFLOW STEPS
────────────────────────────────────────────

PHASE 1 — STABILIZATION SPRINT (MANDATORY)

Goal:
Reduce failing tests from 35 → 0 with provable, deterministic fixes.

Inputs:
- FAILING_SET_NOW.txt (authoritative failing list)

Rules:
- NO skipped tests
- NO weakened assertions
- NO contract shape changes to V1
- ALL time-dependent logic must use injected clocks
- ALL randomness must be seeded

Execution:
1. Fix failures by ROOT-CAUSE BUCKET only:
   - Priority 1: Identity Audit Emitter (10 tests)
   - Priority 2: Handshake State Machine (9 tests)
   - Priority 3: Coordination Models (6 tests)
   - Priority 4: Federation Crypto Tightening (10 tests)

2. After each subsystem:
   - Run `make verify`
   - Confirm failing count decreases
   - Update FAILING_SET_NOW.txt
   - Ensure no new failures introduced
   - Working tree must be reviewed for unrelated drift

Subsystem considered COMPLETE only when:
- Bucket tests pass
- Global verify passes
- No regression introduced

────────────────────────────────────────────
PHASE 2 — COMMIT HYGIENE (STRICT)

Goal:
Ensure clean historical truth and reviewable progress.

Commit Strategy:
- Commit A (MANDATORY):
  - Contains ONLY changes required to restore tests to green
  - No new features
  - No speculative refactors
  - No untracked feature files

  Commit message:
  "Phase -0.5: constitutional restoration — all tests GREEN"

- Commit B (OPTIONAL, GATED):
  - Stage new feature files ONLY if:
      • strictly additive
      • behind feature flags
      • does not alter V1 contracts
      • does not widen interfaces
  - Otherwise defer entirely

────────────────────────────────────────────
PHASE 3 — SYNC ORIGIN

- Push commits to origin/main
- Confirm GitHub reflects binary-green state
- Confirm CI parity with local verification

────────────────────────────────────────────
PHASE 4 — ROADMAP RESUMPTION

Only after Phase -0.5 is locked:

- Resume work per:
  .windsurf/workflows/exoarmur-max-build-roadmap.md

- Feature development permitted ONLY under:
  - additive-only rule
  - explicit feature flags
  - preserved Golden Demo invariants

────────────────────────────────────────────
INVARIANT TRUTH

Red code invalidates all future work.
Green code is the only foundation permitted.
