---
auto_execution_mode: 2
---
EXOARMUR — DOMINANCE ROADMAP (CASCADE EXECUTION PLAN)
GOAL: “INEVITABILITY INSIDE THE DOMAIN” (no exploits, no hack-back). ExoArmur detects early, constrains movement, collapses options, and ends threat capability via deterministic, policy-governed containment choreography.

────────────────────────────────────────────────────────────
GLOBAL GOVERNANCE (APPLIES TO EVERY PHASE / PR / COMMIT)

G0 — V1 IMMUTABLE
- No changes that alter V1 contract shapes, semantics, or Golden Demo behavior.

G1 — BINARY GREEN + PROVABLE PROGRESS
- Repo must remain green at each step.
- No skipped tests. No “temporary red.” No weakening assertions.

G2 — ADDITIVE ONLY
- New capability lives in V2/new modules. Feature flags default OFF.

G3 — DETERMINISM + REPLAY
- No wall-clock dependence (inject clocks).
- Randomness must be seeded and logged.
- Replay must reproduce identical decisions/hashes/markers.

G4 — “DOMINANCE IS CHOREOGRAPHY, NOT AGGRESSION”
- Dominance is implemented as deterministic containment plans + rapid domain controls.
- No exploit tooling. No external targeting. No retaliatory actions.

G5 — QUALITY BARS
- Overall test coverage must remain ≥ 90% (enforced in CI and verify_all).
- Lint/type checks must pass.
- Keep repo organized: no new doc files unless explicitly required; update existing docs.

G6 — EVIDENCE-BASED GATES
- Each phase gate requires: tests green + coverage pass + demo markers + replay verification.
- If any gate fails: stop and fix before advancing.

────────────────────────────────────────────────────────────
PHASE 0 — FOUNDATION LOCK (YOU MAY ALREADY BE HERE)
Objective: cement a stable engineering substrate for autonomous work.

Deliverables
0.1 exoarmur CLI contract finalized
- exoarmur health
- exoarmur verify_all
- exoarmur demo <scenario>
- exoarmur replay verify --audit-stream-id <id>

0.2 verify_all is source of truth
- Runs full pytest suite
- Enforces coverage ≥ 90%
- Runs boundary/determinism gate (random order + sensitive repeats)
- Runs demo smoke (deny default) with stable markers
- Runs replay verification

0.3 CI enforcement
- Required checks include: verify_all + coverage threshold + lint/type checks
- No merges when any check fails

Gate 0
- clean venv install proof script passes (if applicable)
- exoarmur verify_all exits 0
- pytest: 0 failed / 0 errors / 0 skipped
- coverage ≥ 90%

────────────────────────────────────────────────────────────
PHASE 1 — DOMINANCE PRIMITIVES (THE “MUSCLES”, SAFE + REVERSIBLE)
Objective: build the reversible “weapons” (authority-bounded effectors) and prove idempotent execution.

Deliverables
1.1 DominanceAction interface (V2)
- action_name, scope, ttl, idempotency_key, safety_class (A1/A2/A3), required_evidence
- deterministic serialization for audit/replay

1.2 Deterministic clock + TTL engine
- tick-based expiration for any containment window
- deterministic expiry events in audit

1.3 Safe simulated effectors (first-class)
- revoke_sessions(sim)
- isolate_endpoint(sim)
- freeze_identity(sim)
- rate_limit(sim)
- disable_workload(sim)
All must be:
- idempotent
- TTL-bound where applicable
- auditable
- replay-verifiable

1.4 Demo scenarios (deny by default)
- exoarmur demo primitives --deny/--approve
Stable markers:
- DEMO_RESULT
- ACTIONS_PLANNED=<n>
- ACTIONS_EXECUTED=<n>
- AUDIT_STREAM_ID
- REPLAY_VERIFIED

Gate 1
- verify_all green + coverage ≥ 90%
- demos produce stable markers
- replay verification returns true

────────────────────────────────────────────────────────────
PHASE 2 — CONTAINMENT PLANS (INEVITABILITY VIA CHOREOGRAPHY)
Objective: create “meet it at every door” behavior using deterministic multi-step plans.

Deliverables
2.1 ContainmentPlanIntent (V2)
- contains ordered sub-intents (DominanceActions)
- deterministic ordering
- transactional semantics:
  - either full execute OR deterministic rollback/compensation
- plan_hash included in audit

2.2 Plan executor
- deterministic execution order
- strict idempotency across restarts (within the demo/store scope)
- partial failure compensation (simulated) with proof in audit

2.3 “Door Net” plan preset
- a plan designed to close avenues fast:
  - revoke sessions → isolate endpoint → rate limit → disable workload (all simulated)
- configurable TTL windows
- approval required for A2/A3

2.4 Demo
- exoarmur demo dominance_plan
Outputs:
- PLAN_HASH
- ACTION_SEQUENCE=[...]
- ACTIONS_EXECUTED
- COMPENSATION_APPLIED=true/false
- AUDIT_STREAM_ID
- REPLAY_VERIFIED=true

Gate 2
- verify_all green + coverage ≥ 90%
- plan demo works in deny + approve modes
- replay reproduces identical PLAN_HASH and ACTION_SEQUENCE

────────────────────────────────────────────────────────────
PHASE 3 — IDENTITY SHADOWING (STANDING BEHIND IT)
Objective: once suspicious, the entity is continuously tracked and constrained deterministically.

Deliverables
3.1 IdentityShadow state (V2)
- deterministic correlation keys across observations/intents
- “shadow lifecycle” in audit
- no wall-clock; use injected time

3.2 Shadow-driven plan selection (INFLUENCE ONLY)
- Shadow increases evidence requirements and response readiness
- Must not bypass approvals
- Must not grant execution permission

3.3 Demo
- exoarmur demo identity_shadow
Shows:
- SHADOW_CREATED=true
- SHADOW_KEY=<stable>
- PLAN_SELECTED=<name>
- AUDIT_STREAM_ID / REPLAY_VERIFIED

Gate 3
- tests prove shadow cannot bypass approval or safety gate
- replay reproduces SHADOW_KEY and selection outputs

────────────────────────────────────────────────────────────
PHASE 4 — ENVIRONMENT SHAPING (THE WORLD IS ALREADY EXOARMUR)
Objective: “the environment collapses” without deception/honeypots; this is policy-driven tightening of allowed behavior.

Deliverables
4.1 Deterministic “Policy Posture Modes” (advisory → enforced)
- Normal / Heightened / Lockdown
- Posture changes are auditable and TTL-bound
- Posture changes only adjust allowed actions within domain (no external action)

4.2 Posture-driven network/service constraints (simulated first)
- when heightened: stricter rate limits, stricter isolation windows, stricter protected principal rules

4.3 Demo
- exoarmur demo posture_lockdown
Outputs:
- POSTURE=<mode>
- POSTURE_TTL
- POLICY_HASH_IN_EFFECT=<hash>
- AUDIT_STREAM_ID / REPLAY_VERIFIED

Gate 4
- tests prove posture changes influence only allowed action bounds, never approvals
- replay reproduces POLICY_HASH_IN_EFFECT

────────────────────────────────────────────────────────────
PHASE 5 — EVIDENCE PACKS (PROVABLE HUMILIATION)
Objective: every decisive action produces a complete, stable, reproducible proof artifact.

Deliverables
5.1 EvidencePackV1 (canonical JSON + stable hash)
- provenance chain: observations → beliefs → shadow → posture → approvals → plan → actions → outcomes
- includes plan_hash, policy_hash, evidence_hash

5.2 Evidence export
- exoarmur evidence export --audit-stream-id <id>
- yields deterministic artifact and stable hash

5.3 Demo
- exoarmur demo evidence_pack
Outputs:
- EVIDENCE_HASH=<stable>
- ARTIFACT_PATH=<path>
- REPLAY_VERIFIED=true

Gate 5
- replay reproduces identical EVIDENCE_HASH and artifact bytes (or canonical hash)

────────────────────────────────────────────────────────────
PHASE 6 — DEFENSIVE MEMORY (IT REMEMBERS AND GETS FASTER)
Objective: institutional memory that is deterministic and replay-stable.

Deliverables
6.1 MemorySnapshotV1 (stable hash)
- outcome rates, reversal rates, approval latency, posture drift indicators
- deterministic snapshotting under replay

6.2 Advisory recommendations (never execution)
- e.g. “suggest heightened posture” or “suggest wider TTL”
- never auto-apply without approval/explicit command

6.3 Demo
- exoarmur demo memory_snapshot
Outputs:
- MEMORY_HASH=<stable>
- REPLAY_VERIFIED=true

Gate 6
- replay reproduces identical MEMORY_HASH
- tests prove no execution path influence

────────────────────────────────────────────────────────────
PHASE 7 — TRUST & RELIABILITY (INFLUENCE ONLY, NEVER PERMISSION)
Objective: reliability scoring that can’t become a backdoor.

Deliverables
7.1 ReliabilityScore model + computation
- signal quality scoring
- federate reliability scoring (if applicable)
- strictly advisory influence on evidence requirements/escalation only

7.2 Proof tests
- explicit tests proving:
  - trust cannot trigger execution
  - trust cannot bypass approvals
  - trust cannot lower required evidence below policy minimum

7.3 Demo
- exoarmur demo trust_influence
Outputs:
- TRUST_SCORE=<value>
- REQUIRED_EVIDENCE_LEVEL=<level>
- EXECUTION_ALLOWED=false (unless separately approved)
- REPLAY_VERIFIED=true

Gate 7
- tests prove “no execution path influence”
- replay stable

────────────────────────────────────────────────────────────
PHASE 8 — POLICY COMPILER + HARDENING (THE MOAT + SURVIVABILITY)
Objective: policies become compiled guardrails; system resists abuse.

Deliverables
8.1 Policy DSL + compiler
- TTL bounds, authority mapping, protected principals, evidence requirements, escalation ladders
- compiled validators for SafetyGate
- policy versions auditable; policy hash stamped everywhere

8.2 Abuse resistance
- kill switches (global + tenant)
- rate limits for approvals/actions
- quorum escalation option for high-risk actions
- adversarial replay tests + fuzzing for schema/order

8.3 Final “WOW” demo
- exoarmur demo wow
Scenario:
- suspicious telemetry → belief → shadow → posture tighten → approval → dominance plan executes (sim) → evidence export → memory snapshot → replay verify
Outputs:
- PLAN_HASH
- POLICY_HASH_IN_EFFECT
- EVIDENCE_HASH
- MEMORY_HASH
- REPLAY_VERIFIED=true

FINAL GATE
- verify_all green + coverage ≥ 90%
- 0 failed / 0 errors / 0 skipped
- boundary gate green
- wow demo passes with stable markers
- replay reproduces identical hashes for plan/policy/evidence/memory
