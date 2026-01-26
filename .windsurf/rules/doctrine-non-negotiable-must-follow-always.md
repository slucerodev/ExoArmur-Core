---
trigger: model_decision
---
EXOARMUR — REALITY-FIRST RULESET (v2: Production-Grade Truth)

MISSION
Build a fully functioning real-world application.
Work is valid ONLY if it increases operational truth under real conditions.

DEFINITION OF REAL
A component is REAL only if ALL are true:
1) Persists outside the Python process
2) Survives full process termination and restart
3) Produces externally verifiable outputs
4) Can be replayed/audited from durable artifacts
5) Evidence exists on disk proving the above

If any condition is unmet → HOLLOW.
If proof cannot be shown → UNPROVEN.

────────────────────────────────────────────────────────

NON-NEGOTIABLE CONSTRAINTS
- No new product features.
- No architecture redesign.
- No speculative work.
- No “this should work.”
- No optimism. No assumptions.
- No mocks in any reality path.
- No in-memory persistence used as “storage.”
- Refactors ONLY when required to eliminate a lie or to enable a verifier/evidence artifact.

────────────────────────────────────────────────────────

TRUTH AXIOMS (PRODUCTION LANDMINES)
A) TIME IS NOT TRUTH
- Wall-clock time (now()) is forbidden in any decision path unless the time basis is recorded into artifacts.
- Artifacts must distinguish event_time (source) vs process_time (system).
- Replay must not depend on current time.

B) DELIVERY IS AT-LEAST-ONCE
- Duplicates are expected.
- The system MUST be idempotent at the ingest/commit boundary.
- Duplicate input must not duplicate durable outcomes.

C) CONFIG DRIFT IS A LIE
- Effective runtime config (flags/env/config files influencing behavior) MUST be snapshotted and hashed per run.
- Replay must use recorded config; if config differs and is not declared, replay equivalence fails.

D) HUMANS ARE NON-DETERMINISTIC
- Any operator/human action that influences outcomes MUST be captured as a durable event:
  actor_id, action, event_time, process_time, correlation_id.
- Replay consumes recorded decisions, not “what a human would do.”

────────────────────────────────────────────────────────

REALITY GATES (SOURCE OF TRUTH)
Gate 1 — Durable Persistence Exists
Gate 2 — Restart Survival
Gate 3 — Replay Equivalence
Gate 4 — Minimal Deployment Proof
Gate 5 — Time Truth (replay clock safety)
Gate 6 — Duplicate/Idempotency Truth (at-least-once safety)
Gate 7 — Config + Human Action Truth (reproducibility boundaries)

A gate is GREEN only with durable evidence artifacts on disk.
Otherwise: RED or UNPROVEN.

────────────────────────────────────────────────────────

MANDATORY EVIDENCE BUNDLE (PER RUN)
artifacts/<run_id>/
- audit_export.jsonl
- storage_state.json
- replay_report.json
- service.log
- config_snapshot.json
- config_hash.txt
- time_model.json
- idempotency_report.json        (when Gate 6 is targeted)
- operator_actions.jsonl         (when operator actions exist)
- PASS_FAIL.txt                  (includes per-gate status)

Missing required artifacts → FAIL.

────────────────────────────────────────────────────────

AUTOMATIC FAILURES (ARCHITECTURAL LIES)
- TODO/FIXME in any I/O, persistence, or replay path
- in-memory used as persistence in reality harness
- mocked JetStream/DB in reality harness
- hard-coded or reused identifiers
- “looks correct” reasoning / passing tests without disk proof
- decision logic using now() without recorded time basis

On detection:
1) Mark as LIE
2) Add failing verifier and/or artifact requirement
3) Do not proceed until resolved

────────────────────────────────────────────────────────

IDENTITY AND TRACE TRUTH
All core IDs must be unique and real:
audit_id, belief_id, intent_id, correlation_id, idempotency_key
ULID (or equivalent) required. Hard-coded IDs forbidden.

────────────────────────────────────────────────────────

ACCEPTANCE STANDARD
Completion may be claimed ONLY when:
- Target gate is GREEN
- Evidence bundle exists
- Cold reviewer can reproduce via docker-compose + single command

Otherwise output MUST state: UNPROVEN
