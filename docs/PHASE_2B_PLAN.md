# ExoArmur — Phase 2B Plan (Planning Only)

## Baseline
- Phase 2A green commit: 85067d6
- Test status at baseline: 577 passed, 7 skipped, 11 xfailed, 0 failed, 0 xpass

## Objectives (Phase 2B)
1. Define V2 activation architecture (schema-first, capability-aligned).
2. Specify governance-grade PhaseGate behavior (phase matrix + tests).
3. Define module boundaries for open-core + 3 paid modules.
4. Build deterministic harness + fixtures for future V2 execution (NO live V2 logic).

## Non-goals (explicit)
- No V2 live logic implementation.
- No V1 contract modifications.
- No Golden Demo semantic changes.
- No weakening assertions or relaxing governance invariants.

## Capability Map (Core vs 3 Paid Modules)
### Core (Open)
- Deterministic audit/replay substrate
- Safety/phase gates + invariant enforcement
- Transport isolation and hermetic default testing
- Plugin boundary + registry contracts

### Paid Module 1 — PoD (Cryptographic Proof-of-Defense)
- Capability:
  - Proof artifacts, verification pipeline, deterministic receipts
- Contracts:
  - PoD artifact schema + verification result schema
- Non-goals (2B):
  - No live PoD enforcement—planning + contracts + tests only

### Paid Module 2 — BFT (Consensus / Quorum Authority)
- Capability:
  - Quorum-based approvals, signed decision lineage
- Contracts:
  - BFT vote envelope, quorum certificate schema
- Non-goals (2B):
  - No live consensus engine wiring—planning + contracts + tests only

### Paid Module 3 — Counterfactual (Causal / Policy Simulation)
- Capability:
  - Counterfactual reasoning outputs + explainability artifacts
- Contracts:
  - Counterfactual query/response envelope, traceability schema
- Non-goals (2B):
  - No live simulation execution—planning + contracts + tests only

## V2 Gating Model
### Phase Matrix (Example)
- Phase 1:
  - V2 components may exist as scaffolding only
  - Any enabled=True path must raise NotImplementedError (or explicit PhaseGate error) before transport/storage
- Phase 2+ (future, requires explicit authorization):
  - V2 modules allowed to execute behind explicit capability flags + operator approval where applicable

## Contract Pack (Phase 2B Deliverable)
Define schema-first contracts for:
1) Federation identity handshake envelope
2) Operator approval request/decision envelope
3) Durable storage boundary (KV semantics) + in-memory reference spec
4) Audit emission envelope confirmation (no live transport required in default run)

## Test Strategy
- Hermetic by default: no NATS, no docker required
- live_nats lane: explicitly marked; opt-in only
- Required tests in 2B:
  - schema round-trip tests
  - PhaseGate deny tests for Phase 1
  - “enabled=True cannot escape PhaseGate” tests
  - determinism / no-side-effects tests (imports, globals, env)

## Risks + Mitigations
- Risk: env/flag leakage → Mitigation: strict autouse reset + singleton reset
- Risk: accidental transport dependence → Mitigation: default-deny transport guard + live_nats marker lane
- Risk: scope sprawl → Mitigation: explicit non-goals + capability boundaries

## Exit Criteria (Phase 2B Planning Complete)
- Plan doc merged
- Contract pack defined (schemas + examples)
- Hermetic tests for contracts + PhaseGate behavior in place and green
- No V2 live logic implemented
- Explicit go/no-go checklist ready for PoD → BFT → Counterfactual execution (Phase 2C+)
