# ExoArmur Core Invariants

This document defines the core invariants that ExoArmur Core must maintain. These invariants are non-negotiable properties of the system that enable deterministic governance, auditability, and safe execution.

## INV-001: Determinism

**Statement**: Given identical inputs (telemetry events, policy bundles, safety gate configuration), the system produces identical execution decisions, audit records, and replay hashes across multiple runs.

**Why it matters**: Determinism is the foundation of reproducible audits, incident reconstruction, and trust verification. Without determinism, audit records cannot be independently verified, and replay cannot prove execution integrity.

**Enforcement mechanism**:
- Pre-commit determinism scanner checks source code for nondeterministic patterns
- Golden Demo enforces deterministic replay across multiple runs
- Replay engine validates hash stability

**Evidence (tests/demo)**:
- `tests/test_determinism_proof_harness.py` - Proves determinism across 100+ runs
- `tests/test_replay_determinism.py` - Validates replay hash stability
- `demos/canonical_truth_reconstruction_demo.py` - Demonstrates deterministic boundary enforcement
- Golden Demo hash: `7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b`

**Failure mode**: Nondeterministic trace, replay hash mismatch, divergent audit records

**Status**: ✅ ENFORCED - 1166 passing tests, Golden Demo stable

---

## INV-002: Execution Boundary Integrity

**Statement**: Actions denied by policy or safety gates never execute on the target system. No side effects occur before denial.

**Why it matters**: Prevents unauthorized or unsafe actions from executing. The boundary must reject before any filesystem, network, or system state modification occurs.

**Enforcement mechanism**:
- V2EntryGate enforces all domain logic passes through boundary
- Safety gate evaluates before executor dispatch
- Executor only receives approved intents

**Evidence (tests/demo)**:
- `tests/test_execution_boundary_v2_policy_engine.py` - Boundary enforcement tests
- `tests/test_boundary_contract_enforcement.py` - Contract boundary validation
- `demos/canonical_truth_reconstruction_demo.py` - Demonstrates denial before filesystem side effect
- Golden Demo proves denied actions do not execute

**Failure mode**: Action executes before denial, side effect occurs despite denial

**Status**: ✅ ENFORCED - Golden Demo proves denial occurs before execution

---

## INV-003: Policy Precedence

**Statement**: Safety gates override all other decision logic. Safety gate verdict is final and cannot be bypassed by policy, operator approval, or executor.

**Why it matters**: Prevents unsafe actions from being approved through lower-level mechanisms. Safety gates are the last line of defense.

**Enforcement mechanism**:
- Arbitration precedence contract defines safety gate as highest precedence
- Safety gate evaluation occurs after policy but before executor
- Executor checks safety verdict before dispatch

**Evidence (tests/demo)**:
- `tests/test_arbitration.py` - Precedence rule enforcement
- `tests/test_gate5_kill_switch_simple.py` - Kill switch overrides
- `src/spec/contracts/arbitration_precedence_v1.yaml` - Precedence contract

**Failure mode**: Policy or operator approval bypasses safety gate, unsafe action executes

**Status**: ✅ ENFORCED - Contract and tests prove precedence

---

## INV-004: Audit/Proof Integrity

**Statement**: Audit records are immutable, tamper-evident, and sufficient for independent reconstruction of the governance decision path.

**Why it matters**: Enables post-incident investigation, compliance verification, and trust establishment. Audit must prove what happened, not just claim it.

**Enforcement mechanism**:
- Audit records written to immutable storage (NATS JetStream)
- Audit emitter enforces required fields
- Replay validates audit completeness

**Evidence (tests/demo)**:
- `tests/test_audit_normalizer_integration.py` - Audit normalization tests
- `tests/test_replay_bundle.py` - Audit bundle validation
- Golden Demo proves audit sufficiency for reconstruction

**Failure mode**: Audit records missing, tampered, or insufficient for reconstruction

**Status**: ✅ ENFORCED - Audit normalization and replay tests pass

---

## INV-005: Replay Integrity

**Statement**: Replay reconstructs the exact governance decision path from audit records and supporting stores. Replay hash mismatch indicates tampering or nondeterminism.

**Why it matters**: Enables independent verification of execution without trusting the original runtime. Replay is the proof mechanism for execution integrity.

**Enforcement mechanism**:
- Replay engine validates hash stability
- Replay requires immutable audit storage
- Replay failure blocks acceptance

**Evidence (tests/demo)**:
- `tests/test_replay_engine.py` - Replay engine tests
- `tests/test_replay_determinism.py` - Replay hash stability
- `examples/quickstart_replay.py` - Replay demonstration
- Golden Demo replay hash: `7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b`

**Failure mode**: Replay hash mismatch, replay fails to reconstruct, replay diverges

**Status**: ✅ ENFORCED - Replay tests pass, Golden Demo replay stable

---

## INV-006: V1 Immutability

**Statement**: V1 contracts, cognition loop, and Golden Demo are locked. No changes to V1 behavior, data models, or API contracts are permitted.

**Why it matters**: V1 is the production-grade foundation. Changes would break reproducibility, invalidate audit trails, and require re-validation.

**Enforcement mechanism**:
- Contract tests validate V1 schema stability
- Golden Demo regression gate blocks V1 changes
- Repository policy prohibits V1 modifications

**Evidence (tests/demo)**:
- `tests/test_schema_snapshots.py` - V1 schema snapshot tests
- Golden Demo enforces V1 functional requirements
- All 1166 tests pass without V1 modifications

**Failure mode**: V1 contract change, Golden Demo regression, test failure

**Status**: ✅ ENFORCED - Contract tests and Golden Demo protect V1

---

## INV-007: Feature-Flag Isolation

**Statement**: V2 functionality is disabled by default and inert when disabled. Feature flags cannot accidentally enable V2 without explicit opt-in.

**Why it matters**: Prevents accidental activation of incomplete or experimental V2 features. Ensures V1 remains the default safe state.

**Enforcement mechanism**:
- All V2 flags default to False
- Feature flag isolation tests validate inertness
- Phase gate requires explicit environment variable for V2

**Evidence (tests/demo)**:
- `tests/test_v2_feature_flag_isolation.py` - Feature flag isolation tests
- `tests/test_phase_gate_matrix_enforcement.py` - Phase gate enforcement
- V2 acceptance tests marked xfail(strict=True) until Phase 2

**Failure mode**: V2 activates without opt-in, V1 behavior modified by V2

**Status**: ✅ ENFORCED - Feature flag isolation tests pass

---

## INV-008: Module Isolation

**Statement**: Core and proprietary modules are strictly separated. Core is standalone and does not depend on proprietary modules. Modules extend Core but never modify it.

**Why it matters**: Enables open-source Core while preserving proprietary value. Prevents module changes from breaking Core guarantees.

**Enforcement mechanism**:
- Plugin architecture with entry point discovery
- Module contracts are additive-only
- Module boundary tests validate isolation

**Evidence (tests/demo)**:
- `docs/MODULE_SEPARATION.md` - Module separation strategy
- Plugin registry tests validate zero-provider behavior
- Module integration tests validate additive-only behavior

**Failure mode**: Module modifies Core behavior, Core depends on module

**Status**: ✅ ENFORCED - Plugin architecture and module separation documented

---

## Invariant Status Summary

| Invariant | Status | Enforcement | Evidence |
|-----------|--------|-------------|----------|
| INV-001: Determinism | ✅ ENFORCED | Pre-commit scanner, Golden Demo | 1166 tests pass, replay stable |
| INV-002: Execution Boundary Integrity | ✅ ENFORCED | V2EntryGate, Safety Gate | Golden Demo proves denial |
| INV-003: Policy Precedence | ✅ ENFORCED | Arbitration contract | Precedence tests pass |
| INV-004: Audit/Proof Integrity | ✅ ENFORCED | Immutable storage, validation | Audit normalization tests pass |
| INV-005: Replay Integrity | ✅ ENFORCED | Replay engine validation | Replay tests pass, hash stable |
| INV-006: V1 Immutability | ✅ ENFORCED | Contract tests, Golden Demo | Schema snapshot tests pass |
| INV-007: Feature-Flag Isolation | ✅ ENFORCED | Default False, Phase gate | Isolation tests pass |
| INV-008: Module Isolation | ✅ ENFORCED | Plugin architecture, contracts | Module separation documented |

All invariants are currently enforced through tests, contracts, and the Golden Demo regression gate.
