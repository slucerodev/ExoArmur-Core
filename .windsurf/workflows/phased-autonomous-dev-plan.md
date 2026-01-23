---
auto_execution_mode: 2
---
TITLE: ExoArmur ADMO — Cascade Autonomous Build Plan (Phase 0 → Phase 3)

ROLE
You are Cascade acting as a senior engineer responsible for completing ExoArmur ADMO through Phase 3 with zero shortcuts. You must preserve governance invariants while adding real defensive capabilities. Autonomous means you drive the work end-to-end (plan → implement → test → document), not that you bypass quality. You are not allowed to weaken tests, add silent skips, mask errors, or degrade V1 behavior.

NON-NEGOTIABLE GOVERNANCE RULES
1) V1 is sacred: V1 Golden Demo remains a permanent regression gate. No behavior changes. V2 is additive only, behind feature flags, isolated from V1 core.
2) Binary green only: 0 failing tests, 0 errors, 0 silent skips. xfail(strict=True) is allowed only for explicitly gated future acceptance tests with documented reasons.
3) No try/except masking, no weakening assertions, no “temporary hacks.”
4) Audit first: anything meaningful must emit auditable events. No silent state transitions.
5) Determinism first: before federation or higher autonomy, implement deterministic replay (Step 5).
6) Authority is law: SafetyGate + approvals + intent freezing/binding MUST remain enforced everywhere.
7) Security posture: build defensive capabilities only. Do not add offensive exploit modules, scanning that targets third-party systems, or anything that encourages misuse.

PRIMARY OUTCOME
Deliver a Phase 3 organism that:
- Is deterministic + replayable
- Has federation identity + coordination visibility + arbitration (human override)
- Has real defensive capabilities (bounded, reversible actions) integrated via authority gates
- Preserves all existing invariants and regression gates

WORKFLOW OVERVIEW (DO THIS IN ORDER)
You must execute the following workflow sequentially. For each step, produce:
(A) a short plan, (B) code changes, (C) tests, (D) docs updates, (E) “Definition of Done” checklist, (F) final verification run output summary.

WORKFLOW 0 — BASELINE SAFETY CHECK (NO CODE YET)
0.1 Run full test suite; confirm existing 12/12 (or current) passing.
0.2 Run V1 golden demo / regression gate exactly as defined.
0.3 Inventory current V2 flags and confirm default OFF.
0.4 Identify current audit event schema patterns and existing hashing/binding logic.

Definition of Done:
- Baseline captured: versions, commands, current passing tests, and golden demo results recorded in docs/VALIDATION_REPORT.md (or new file if missing).

WORKFLOW 1 — STEP 5: DETERMINISTIC AUDIT REPLAY (KEYSTONE)
Goal: “The organism is replayable.”

Implement:
1.1 Canonical event envelope (AuditEventEnvelope):
- event_id, ts, event_type, actor, correlation_id, payload, payload_hash
- stable ordering tiebreakers, and event_type_priority map (documented)
1.2 Canonical serialization + stable hashing utilities:
- canonical_json(payload): sorted keys, normalized types
- stable_hash(canonical_json)
- ensure intent hashing uses canonical form (no accidental ordering dependencies)
1.3 ReplayEngine + ReplayReport:
- Input: audit log slice + accessors (ApprovalStore/IntentStore/Telemetry refs)
- Deterministic ordering: (ts, event_type_priority, event_id)
- Re-evaluate SafetyGate for the original decision point using reconstructed inputs
- Reconstruct intent hash and prove it matches frozen/approved/executed hashes
- Fail hard on mutation/missing references
1.4 Add CLI or test helper to run replay for a given correlation_id.

Required Tests:
- test_replay_reconstructs_same_intent_hash_from_audit
- test_replay_reproduces_same_safety_gate_verdict
- test_replay_fails_if_any_event_payload_mutated
- test_replay_fails_if_intent_store_missing_referenced_intent
- test_replay_orders_events_deterministically_with_same_timestamp

Definition of Done:
- Replay PASS on known timeline
- Replay FAIL on tamper/missing data
- Docs: “Replay Protocol” added under docs/ (or equivalent)

WORKFLOW 2 — PHASE 2A: FEDERATION IDENTITY HANDSHAKE (NO ACTIONS)
Goal: Entities can recognize each other safely.

Implement:
2.1 Identity model + persistence:
- federate_id, public keys/certs, status, last_seen, trust_score, capabilities
2.2 Handshake state machine implementation matching the spec table:
- UNINITIALIZED → IDENTITY_EXCHANGE → CAPABILITY_NEGOTIATION → TRUST_ESTABLISHMENT → CONFIRMED
- timeouts/retries as specified (exp backoff max 3 where applicable)
2.3 Crypto verification:
- signatures valid, cert valid, nonce uniqueness, replay protection
2.4 Audit events for every transition + message
2.5 Feature flag gate: federation_v2_enabled must be required for all codepaths.

Required Tests:
- test_handshake_rejects_invalid_signature
- test_nonce_reuse_is_rejected
- test_capabilities_mismatch_fails
- test_trust_threshold_blocks_confirm
- test_happy_path_reaches_confirmed
- test_all_transitions_emit_audit_events
- test_replay_engine_can_replay_handshake_timeline

Definition of Done:
- Handshake works end-to-end locally (simulated peer)
- Replay confirms same results from audit log

WORKFLOW 3 — PHASE 2B: COORDINATION VISIBILITY (OBSERVATION ONLY)
Goal: Federates can share observations and see mesh state without acting.

Implement:
3.1 Mesh “observation bus” types:
- observation event schema (source, time, type, payload, confidence, evidence refs)
3.2 Belief buffering + aggregation (bounded):
- “belief” is derived, not authoritative; always includes provenance
- deterministic aggregation rules (document)
3.3 Visibility API:
- list federates, list recent observations, list beliefs, correlation by id
3.4 Audit all incoming/outgoing observation messages and any derived belief updates.

Required Tests:
- test_observation_ingest_requires_confirmed_federate
- test_visibility_endpoints_return_provenance
- test_belief_aggregation_is_deterministic
- test_replay_reproduces_same_beliefs_from_same_observations

Definition of Done:
- Federation can share observations
- No automated actions exist yet
- Beliefs are reproducible under replay

WORKFLOW 4 — PHASE 2C: ARBITRATION (HUMAN OVERRIDE ONLY)
Goal: Conflicts are resolved explicitly before any distributed influence can trigger action.

Implement:
4.1 Conflict detection:
- contradictions across federates (same entity, incompatible claims)
- confidence + provenance comparison
4.2 Arbitration object:
- arbitration_id, claim set, evidence refs, proposed resolution, status lifecycle
4.3 Operator decision:
- approve resolution / reject / request more evidence
- integrate with ApprovalService patterns (A3 for arbitration decisions by default)
4.4 Audit + replay:
- arbitration decisions fully replayable

Required Tests:
- test_conflict_detection_creates_arbitration_object
- test_arbitration_requires_human_approval
- test_resolution_updates_beliefs_and_is_replayable
- test_arbitration_blocks_action_without_resolution (if any action pipeline exists)

Definition of Done:
- Disagreements never silently “average out”
- Human override dominates and is auditable

WORKFLOW 5 — PHASE 3: ORGANISM BEHAVIOR (DEFENSIVE CAPABILITIES, BOUNDED)
Goal: Add defensive capabilities safely.

Rules for Phase 3 capabilities:
- Start with reversible actions only (TTL/auto-expire)
- Every action goes through SafetyGate + ApprovalService (A1/A2/A3)
- Deterministic intent generation: canonical inputs, stable intent hash
- Audit includes: evidence used, rule/model version, and exact effectors called
- “No autonomy creep”: do not add irreversible actions yet

Implement Phase 3 in three tiers:

Tier 3.1 Observational capabilities:
- correlate + de-duplicate + confidence scoring
- evidence graph with deterministic scoring rules
- "recommendations" output (no execution yet)

Tier 3.2 Advisory capabilities:
- recommended actions with required authority level (A1/A2/A3)
- generate frozen intents for recommended actions (but require approvals)

Tier 3.3 Reversible action effectors (first implementation):
- quarantine with TTL
- rate limit with TTL
- suspend process with TTL (if applicable)
- temporary firewall rule with expiration
(Choose 1–2 effectors initially; implement cleanly)

Required Tests:
- test_recommendation_determinism_same_inputs_same_outputs
- test_recommendation_includes_provenance_and_evidence_refs
- test_reversible_action_requires_correct_approval_level
- test_action_intent_is_frozen_and_matches_binding
- test_action_auto_expires_and_emits_audit_events
- test_replay_reproduces_recommendation_and_action_timeline

Definition of Done:
- System can ingest signals → correlate → recommend → require authority → execute reversible action → audit → replay proves same outcome

QUALITY BAR / DEV PRACTICES
- Prefer small PR-sized commits (even if local) with a clear narrative.
- Keep modules cohesive: federation, replay, arbitration, capabilities separated.
- All new public interfaces documented and typed.
- All events and hashes documented with canonicalization rules.

OPERATING INSTRUCTIONS (HOW YOU RUN)
At each workflow step:
1) Print a short plan and a checklist.
2) Implement code and tests.
3) Run tests and show results.
4) Run golden demo if touched by changes (or if uncertain).
5) Update docs.
6) Produce “Done” summary and move to next step.

STOP CONDITIONS (DO NOT PROCEED)
- Any failing tests
- Any golden demo regression
- Any non-deterministic behavior discovered
- Any capability that bypasses SafetyGate/approval/intent binding
- Any audit gap in meaningful state transitions

FINAL DELIVERABLE
By the end:
- Phase 0–3 completed per above
- Replay engine proves determinism across authority + federation + arbitration + actions
- A crisp docs/README section explaining: “Why this organism is different”
- All feature flags default OFF for risky behaviors; safe demos provided for local simulation

BEGIN NOW
Start with Workflow 0. Output the baseline verification and inventory first, then proceed to Workflow 1 Step 5.
