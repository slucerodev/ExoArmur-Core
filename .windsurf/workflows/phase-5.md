---
auto_execution_mode: 2
---
EXOARMUR — WORKFLOW 5 (PHASE 5) OPERATIONAL SAFETY HARDENING
TARGET MILESTONE: GATE 5 GREEN + GATE 6 GREEN
EVIDENCE BUNDLE: artifacts/reality_run_007/ (suggested)

PRECONDITIONS (MUST HOLD TRUE):
- Gates 1–4 remain GREEN
- V1 contracts are immutable (no modifications)
- Golden Demo still passes unchanged
- No silent skips, no weakened assertions, no masking failures

============================================================
WORKFLOW 5A — SAFETY SURFACE INVENTORY (NO CODE CHANGES YET)
============================================================

1) Enumerate ALL “execution paths” (places where the system can cause side effects):
   - action executors
   - background workers
   - control API endpoints triggering execution
   - replay driver execution mode
   - any integrations that write/send/modify external state

2) For each execution path, classify:
   - READ-ONLY (safe)
   - WRITE/SIDE-EFFECT (unsafe)
   - UNKNOWN (treat as unsafe until proven)

3) Emit: artifacts/reality_run_007/00_execution_surface.md
   - list of paths + classification + file/line references

ACCEPTANCE:
- Cold reviewer can point to every side-effect path and agree nothing is missed.

============================================================
WORKFLOW 5B — GLOBAL + TENANT KILL SWITCH (ENFORCEMENT, NOT “FLAGS”)
============================================================

IMPLEMENTATION REQUIREMENTS:
- Single authoritative gate function used by every execution path
- Evaluated BEFORE any side effect attempt
- Default behavior must be SAFE (deny execution)
- Must emit audit event when blocking occurs

Minimum design:
- Global kill switch: system-wide disable
- Tenant kill switch: disable per tenant/workspace
- Evaluation source must be durable (JetStream KV or equivalent durable config)

TESTS (MANDATORY):
- Unit tests: kill switch blocks each execution path
- Integration test: docker-compose environment shows kill switch blocks execution
- Replay test: blocked execution is deterministic and reproduces

ACCEPTANCE GATE (GATE 5):
- “Kill switches demonstrably prevent all execution paths”
- Proof includes: test logs + deterministic replay artifacts

Emit:
- artifacts/reality_run_007/01_kill_switch_design.md
- artifacts/reality_run_007/02_gate5_test_outputs.txt (or equivalent)

============================================================
WORKFLOW 5C — TENANCY ISOLATION (HARD GUARANTEE)
============================================================

IMPLEMENTATION REQUIREMENTS:
- Tenant context required for all state reads/writes
- No global shared mutable state without explicit, audited exemption
- Any missing tenant context must fail closed

Mechanics:
- Introduce TenantContext propagated through call graph
- Enforce tenant scoping in:
  - JetStream subjects/streams naming (or metadata)
  - KV keys / buckets / prefixes
  - ledger entries
  - audit events

TESTS (MANDATORY):
- Negative tests: tenant A cannot read tenant B state
- Contract-shape tests: tenant fields required where applicable
- Integration: two tenants in docker-compose, isolation enforced

ACCEPTANCE GATE (GATE 6):
- “Tenant isolation is enforced and provable”
- Evidence includes tests + logs + replay determinism preserved

Emit:
- artifacts/reality_run_007/03_tenancy_isolation_design.md
- artifacts/reality_run_007/04_gate6_test_outputs.txt

============================================================
WORKFLOW 5D — OPERATOR APPROVAL GATE (A3) WIRED AS REAL CONTROL POINT
============================================================

IMPLEMENTATION REQUIREMENTS:
- For any SIDE-EFFECT action class:
  - default = DENY unless explicit approval exists
- Approval must be:
  - durable (persisted)
  - replayable (replay yields same decision)
  - auditable (who/what/when/why)
- “Propose” is allowed without approval; “Execute” requires approval

TESTS (MANDATORY):
- Deny by default tests
- Approval allows execution tests
- Replay reproduces identical approval outcome

Emit:
- artifacts/reality_run_007/05_a3_approval_design.md
- artifacts/reality_run_007/06_a3_test_outputs.txt

============================================================
WORKFLOW 5E — AUTHN/Z MINIMUM VIABLE (BOUNDARY PROTECTION)
============================================================

Pick ONE minimal auth mechanism and implement it correctly:
- API key (fastest) OR mTLS (stronger) OR OIDC (heavier)

REQUIREMENTS:
- All execution-triggering endpoints require authentication
- Authorization checks map principal -> allowed action classes/tenants
- Fail closed

TESTS:
- Unauthed calls rejected
- Authenticated but unauthorized rejected
- Authorized permitted

Emit:
- artifacts/reality_run_007/07_auth_design.md
- artifacts/reality_run_007/08_auth_test_outputs.txt

============================================================
WORKFLOW 5F — FINAL PHASE 5 REALITY RUN (COLD REVIEWER REPRODUCIBLE)
============================================================

1) Run full verification suite:
   - Golden Demo
   - all unit/integration tests
   - replay equivalence checks

2) Run docker-compose “cold reviewer” flow:
   - spin up stack
   - run one command to execute and produce artifacts
   - run one command to replay and verify identical outcome

3) Bundle evidence:
   artifacts/reality_run_007/
     - execution surface inventory
     - designs (kill switch / tenancy / approval / auth)
     - logs + test outputs
     - exact commands used (copy/paste runnable)
     - checksums if appropriate

SUCCESS CRITERIA:
- Gates 1–4 remain GREEN
- Gate 5 becomes GREEN
- Gate 6 becomes GREEN
- Approval enforcement and authn/z are proven (even if not formal “gates” yet)
- Cold reviewer can reproduce with docker-compose + single command

END WORKFLOW 5
