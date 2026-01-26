---
auto_execution_mode: 2
---
NAME: ExoArmur Reality Enforcement Workflow (v2 — Production Landmine Coverage)

TRIGGER: always_on

OBJECTIVE:
Convert ExoArmur from hollow symbolic code into a REAL, PROVABLE, USABLE production system.
Progress is valid ONLY when durable evidence exists on disk AND is reproducible by a cold reviewer.

────────────────────────────────────────────────────────
GLOBAL RULES (NON-NEGOTIABLE)

- No new product features.
- No architecture redesign.
- No speculative work.
- No refactors unless required to eliminate a lie OR to enable a verifier/evidence artifact.
- No mocks in any reality path.
- No in-memory used as persistence in reality paths.
- No optimism. No assumptions.

If proof cannot be produced, output MUST state:
UNPROVEN

────────────────────────────────────────────────────────
DEFINITION OF REAL

A component is REAL only if ALL are true:
1) Persists outside the Python process
2) Survives full process termination and restart
3) Produces externally verifiable outputs
4) Can be replayed/audited from durable artifacts
5) Evidence exists on disk proving the above

If any condition fails → HOLLOW

────────────────────────────────────────────────────────
MANDATORY RESPONSE HEADER

Every response MUST begin with:

TARGET GATE: <1–7>
CURRENT STATUS: RED | YELLOW | GREEN
MINIMAL TRUTH OBJECTIVE: <single sentence>
EVIDENCE TO EMIT: <explicit artifact list>

If this cannot be stated, halt.

────────────────────────────────────────────────────────
REALITY GATES (SINGLE SOURCE OF TRUTH)

GATE 1 — DURABLE PERSISTENCE EXISTS
PASS ONLY IF:
- Audit OR belief data persists outside process memory
- Storage is real (JetStream file-backed and/or real DB)
- Data survives service shutdown

GATE 2 — RESTART SURVIVAL
PASS ONLY IF:
- Service terminated
- Broker/storage terminated
- Both restart cleanly
- System continues without manual intervention
- No silent loss of records; counts verified

GATE 3 — REPLAY EQUIVALENCE
PASS ONLY IF:
- A completed run is replayed solely from durable artifacts (no runtime memory)
- Replay produces identical OR explicitly-declared outcomes:
  - intent hash (or equivalent)
  - safety verdict
  - approval requirement
  - audit trace structure

GATE 4 — MINIMAL DEPLOYMENT PROOF
PASS ONLY IF:
- docker-compose up brings up the full system
- A single command executes a known scenario
- An evidence bundle is produced consumable by a cold reviewer

────────────────────────────────────────────────────────
PRODUCTION LANDMINE GATES (ADDED)

GATE 5 — TIME TRUTH (REPLAY CLOCK SAFETY)
PASS ONLY IF:
- Artifacts explicitly record BOTH:
  - event_time (source timestamp as carried by input)
  - process_time (when system processed it)
- Replay uses recorded event ordering/time, not wall-clock now()
- Any time-based logic is deterministic under replay

If any decision depends on unrecorded wall-clock time → FAIL

GATE 6 — DUPLICATE & IDEMPOTENCY TRUTH (AT-LEAST-ONCE SAFETY)
PASS ONLY IF:
- The system treats input delivery as at-least-once (duplicates expected)
- Duplicate deliveries do not duplicate durable outcomes
- Idempotency keys are persisted and enforced at ingest/commit boundary
- Verifier proves “double-inject” does NOT double counts or change verdicts

If duplicates create divergent or duplicated artifacts → FAIL

GATE 7 — CONFIG + HUMAN ACTION TRUTH (REPRODUCIBILITY BOUNDARIES)
PASS ONLY IF:
- Effective runtime configuration is captured and hashed in artifacts
- Feature flags, env, config files that influence behavior are recorded
- Any operator/human action is captured as a durable event with:
  - who/what (actor id)
  - what (decision/action)
  - when (event_time + process_time)
  - correlation_id
- Replay consumes these recorded decisions deterministically

If replay depends on “what the operator would do” or missing config → FAIL

────────────────────────────────────────────────────────
MANDATORY REALITY HARNESS

A single command MUST exist:
- make reality
OR
- scripts/reality.sh

This command MUST:
- Start real storage (JetStream file-backed and/or real DB)
- Start ExoArmur service
- Inject known telemetry (and include a duplicate-inject test once Gate 6 is targeted)
- Verify persistence + restart survival + replay
- Emit evidence artifacts

────────────────────────────────────────────────────────
MANDATORY EVIDENCE BUNDLE (EXPANDED)

Each reality run MUST output:

artifacts/<run_id>/
- audit_export.jsonl
- storage_state.json             (JetStream streams/consumers + counts OR DB schema + counts)
- replay_report.json
- service.log
- config_snapshot.json           (effective config/flags/env subset)
- config_hash.txt                (hash of config snapshot)
- time_model.json                (event_time vs process_time summary; ordering proof)
- idempotency_report.json        (only when Gate 6 is targeted; includes duplicate-inject results)
- operator_actions.jsonl         (only when operator/human actions exist)
- PASS_FAIL.txt                  (includes per-gate status)

If any required artifact is missing for the targeted gate → FAIL

────────────────────────────────────────────────────────
AUTOMATIC FAILURE CONDITIONS

- TODO or FIXME in any I/O / persistence / replay path
- In-memory used as persistence in reality harness
- Mocked JetStream/DB in reality harness
- Hard-coded identifiers OR reused identifiers
- “Looks correct” or “should work” statements
- Tests passing without durable artifact proof
- Any use of wall-clock time (now()) in a decision path without recording time basis into artifacts

On detection:
1) Mark as LIE
2) Add failing verifier and/or artifact requirement
3) Do not proceed until resolved

────────────────────────────────────────────────────────
IDENTITY AND TRACE TRUTH

All core identifiers MUST be real and unique:
- audit_id
- belief_id
- intent_id
- correlation_id
- idempotency_key

ULID (or equivalent) required.
Hard-coded or reused identifiers are forbidden.

────────────────────────────────────────────────────────
CASCADE EXECUTION ORDER (STRICT)

1) Inventory reality claims (no code)
2) Classify each as REAL / HOLLOW / UNPROVEN (with file/line references)
3) Select ONE gate
4) Identify the minimal change to flip that gate from RED→GREEN
5) Implement verifier BEFORE or WITH the change
6) Run reality harness and emit artifacts
7) Stop immediately after the gate is GREEN

No “while I’m here.”
No cleanup.
No expansion.

────────────────────────────────────────────────────────
ACCEPTANCE STANDARD

Cascade may claim completion ONLY when:
- Targeted gate is GREEN
- Evidence bundle exists on disk
- Cold reviewer can reproduce results with docker-compose + single command

Otherwise output MUST be:
UNPROVEN

STATUS RULE:
- GREEN requires a reality run evidence bundle under artifacts/<run_id>/PASS_FAIL.txt.
- YELLOW is allowed ONLY when a verifier exists and is runnable, but the gate has not yet passed.
- If no artifacts exist for the current cycle, status MUST be RED and output MUST be UNPROVEN.
