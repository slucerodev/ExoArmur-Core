---
trigger: always_on
---
# EXOARMUR — REALITY-FIRST DEVELOPMENT RULESET
# PURPOSE: Permanently eliminate hollow, symbolic, or illusion-based progress.

MISSION
You are developing a fully functioning real-world application.
Architectural shape, mockups, prototypes, and skeletons are insufficient.
Work is valid only if it increases operational truth under real conditions.

DEFINITION OF REAL
A component is REAL only if all of the following are true:

1. It persists data outside the Python process.
2. It survives full process termination and restart.
3. Its outputs can be externally verified.
4. Its behavior can be replayed or audited from durable artifacts.
5. Evidence exists on disk proving the above.

If any condition is unmet, the component is HOLLOW.

NO EXCEPTIONS.

---------------------------------------------------------------------

NON-NEGOTIABLE CONSTRAINTS

- No new features.
- No redesign of architecture shape.
- No speculative work.
- No “this should work.”
- No optimism.
- No assumptions.

Only enforcement and grounding of what already exists is permitted.

---------------------------------------------------------------------

REALITY GATES (SINGLE SOURCE OF TRUTH)

GATE 1 — DURABLE PERSISTENCE EXISTS
PASS ONLY IF:
- Audit records and beliefs are persisted outside process memory.
- Persistence is real (JetStream file-backed streams and/or real database).
- Data remains accessible after application shutdown.

If persistence disappears on exit → FAIL.

---------------------------------------------------------------------

GATE 2 — RESTART SURVIVAL
PASS ONLY IF:
- Application is terminated.
- Broker/storage is terminated.
- Both restart cleanly.
- System continues without manual intervention.
- No silent loss of records.

Verifier must confirm expected counts.

---------------------------------------------------------------------

GATE 3 — REPLAY EQUIVALENCE
PASS ONLY IF:
- A completed run is replayed from durable storage.
- Replay produces identical or explicitly-declared outcomes:
  - intent hash (or equivalent)
  - safety verdict
  - approval requirement
  - audit trace structure

If replay diverges without explanation → FAIL.

---------------------------------------------------------------------

GATE 4 — MINIMAL DEPLOYMENT PROOF
PASS ONLY IF:
- docker-compose up brings up the full system.
- A single command executes a known scenario.
- An evidence bundle is produced consumable by a cold reviewer.

---------------------------------------------------------------------

REALITY HARNESS (MANDATORY)

A single command must exist:
- make reality
  OR
- scripts/reality.sh

This command MUST:
- Use real components only (no mocks).
- Start JetStream with file-backed storage (or real DB).
- Start ExoArmur service.
- Inject known telemetry.
- Verify persistence.
- Run replay.
- Emit evidence artifacts.

---------------------------------------------------------------------

MANDATORY EVIDENCE BUNDLE

Each reality run MUST output:

artifacts/<run_id>/
- audit_export.jsonl
- jetstream_state.json (streams, consumers, counts)
- replay_report.json
- service.log
- PASS_FAIL.txt

If evidence is missing → gate cannot pass.

---------------------------------------------------------------------

HARD PROHIBITIONS (AUTOMATIC FAILURES)

The following are architectural lies:

- TODO or FIXME in any I/O path.
- In-memory storage used as persistence.
- Mocked JetStream or DB in reality harness.
- Hard-coded identifiers.
- “Looks correct” statements.
- Passing tests without external proof.

If found:
1. Mark as LIE.
2. Add failing gate or verifier.
3. Remove or make real.

---------------------------------------------------------------------

IDENTITY AND TRACE TRUTH

All core identifiers MUST be real and unique:
- audit_id
- belief_id
- intent_id
- correlation_id

Hard-coded or reused identifiers are forbidden.

ULID or equivalent required.

---------------------------------------------------------------------

CASCADE BEHAVIOR REQUIREMENTS

Before implementing anything, Cascade MUST:

1. Declare which Reality Gate (1–4) is being addressed.
2. Identify the minimal change required to flip that gate to GREEN.
3. Implement verifier BEFORE or WITH the change.
4. Produce or describe evidence artifacts.
5. Refuse scope drift.

“No while I’m here.”
“No cleanup.”
“No refactors unless required to eliminate a lie.

---------------------------------------------------------------------

ACCEPTANCE STANDARD

Cascade may claim completion ONLY when:
- The current gate is GREEN.
- Evidence bundle exists.
- A cold external reviewer can reproduce results.

If proof cannot be shown, output MUST state:

UNPROVEN.

---------------------------------------------------------------------

CORE PRINCIPLE

If the system cannot survive reality,
it does not exist.

Truth overrides elegance.
Evidence overrides belief.
Reality overrides architecture.

