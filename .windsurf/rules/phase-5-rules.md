---
trigger: model_decision
---
PHASE 5 — NEW RULES (OPERATIONAL SAFETY GOVERNANCE)

R0 — OLD RULES STILL APPLY
- V1 contracts immutable
- Golden Demo permanent, unchanged
- Binary green only (no silent skips, no weakened assertions, no masking)
- Replay equivalence must remain intact

========================================
R1 — FAIL CLOSED ON EXECUTION
========================================
- Any path that can cause side effects must default to DENY.
- Missing context, missing auth, missing tenant, unknown action class, unknown policy => DENY.
- No “best effort” execution.

========================================
R2 — SINGLE AUTHORITATIVE ENFORCEMENT POINT
========================================
- Kill switch + approval + authz checks must route through one authoritative gate function/module.
- No scattered “if kill_switch:” checks in random files.
- Every execution path must call the same gate before any side effect.

========================================
R3 — TENANT CONTEXT IS MANDATORY
========================================
- TenantContext must be present for:
  - any state read/write
  - any audit/ledger write
  - any action execution/proposal linkage
- Absence of tenant context => DENY (or error) before touching durable state.
- Tenant-scoping must be structural (keys/subjects/prefixes), not convention.

========================================
R4 — SIDE EFFECTS REQUIRE OPERATOR APPROVAL BY DEFAULT
========================================
- SIDE-EFFECT actions are DENY unless explicit approval exists.
- “Propose” may occur without approval; “Execute” may not.
- Approval is durable, auditable, and replayable.

========================================
R5 — AUTHN/Z REQUIRED FOR EXECUTION TRIGGERS
========================================
- Any endpoint or interface that can cause SIDE-EFFECT execution must require authentication.
- Authorization must bind:
  - principal -> tenant(s)
  - principal -> allowed action classes
- Unauth/unauthorized => DENY.

========================================
R6 — EVERY DENIAL MUST BE AUDITED
========================================
- When execution is blocked (kill switch, no approval, no auth, wrong tenant), emit:
  - who/tenant
  - what action class
  - which policy denied
  - deterministic reason code
- Denial must be replay-stable.

========================================
R7 — NO NEW CAPABILITIES UNTIL GATE 5 & 6 ARE GREEN
========================================
- Phase 5 work is strictly safety substrate.
- Do not add new sensors, integrations, or “smart behavior” until:
  - GATE 5 (kill switch proof) is GREEN
  - GATE 6 (tenancy isolation proof) is GREEN

========================================
R8 — “UNKNOWN” IS A HARD ERROR, NOT A TODO
========================================
- Any unclassified execution path is treated as SIDE-EFFECT until proven otherwise.
- Unknown action types cannot execute.
- Unknown policy states cannot execute.

END PHASE 5 RULESET

