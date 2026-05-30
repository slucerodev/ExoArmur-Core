# ExoArmur Kernel Formal Invariants

**Version:** 1.0  
**Date:** May 28, 2026  
**Purpose:** Formal specification of kernel invariants for formal verification

---

## Overview

This document specifies the formal invariants that must be verified for the ExoArmur kernel to achieve DACT Level 6 (Formal Verification) compliance. These invariants are expressed in a verification-ready format suitable for model checkers and theorem provers.

---

## Invariant Categories

### 1. Determinism Invariants

#### INV-DET-001: Canonical JSON Determinism
**Property:** For any input data, canonical JSON encoding produces identical output across all executions.

**Formal Specification:**
```
∀ input_data, execution1, execution2:
  canonical_json(input_data, execution1) = canonical_json(input_data, execution2)
```

**Implementation:** `canonical_json()` in kernel modules uses:
- Sorted keys
- No whitespace variation
- Consistent separators (",", ":")
- Deterministic type conversion

**Verification Method:** Property-based testing with QuickCheck/property-based testing

---

#### INV-DET-002: Clock Determinism
**Property:** DeterministicClock produces identical time sequences for identical advance sequences.

**Formal Specification:**
```
∀ initial_time, advance_sequence1, advance_sequence2:
  advance_sequence1 = advance_sequence2 ⇒
    execute_clock(initial_time, advance_sequence1) = execute_clock(initial_time, advance_sequence2)
```

**Implementation:** `DeterministicClock` in `clock.py`
- Fixed initial time
- Deterministic advance operations
- No wall-clock dependencies

**Verification Method:** Model checking of clock state machine

---

#### INV-DET-003: ID Generation Determinism
**Property:** ID generation produces identical outputs for identical inputs.

**Formal Specification:**
```
∀ seed, kind, payload:
  make_id(seed, kind, payload) = make_id(seed, kind, payload)
```

**Implementation:** `IDFactory` in `ids.py`
- Canonical JSON input
- SHA-256 hashing
- ULID generation from hash bytes

**Verification Method:** Algebraic specification and testing

---

### 2. Isolation Invariants

#### INV-ISO-001: Kernel Network Isolation
**Property:** Kernel modules have zero network dependencies.

**Formal Specification:**
```
∀ module ∈ kernel_modules:
  ¬has_network_import(module)
```

**Implementation:** Verified by dependency audit
- No `import urllib`, `import requests`, `import socket`, `import nats`
- No network calls in execution path

**Verification Method:** Static analysis and dependency graph verification

---

#### INV-ISO-002: Kernel ML Isolation
**Property:** Kernel modules have zero ML dependencies in authority path.

**Formal Specification:**
```
∀ module ∈ kernel_modules:
  ¬has_ml_import(module)
```

**Implementation:** Verified by dependency audit
- No `import torch`, `import transformers`, `import sklearn`, `import tensorflow`
- All policy/safety decisions are rule-based

**Verification Method:** Static analysis and dependency graph verification

---

#### INV-ISO-003: Executor Isolation
**Property:** Executors cannot access governance internals directly.

**Formal Specification:**
```
∀ executor, governance_internal:
  ¬can_access(executor, governance_internal)
```

**Implementation:** Executor interface design
- Executors receive only governed action input
- Executors return only execution result
- No direct access to policy, safety, or audit internals

**Verification Method:** Capability safety analysis

---

### 3. Integrity Invariants

#### INV-INT-001: Audit Trail Immutability
**Property:** Audit records cannot be modified after creation.

**Formal Specification:**
```
∀ audit_record, time1, time2:
  time1 < time2 ⇒ audit_record.state(time1) = audit_record.state(time2)
```

**Implementation:** Cryptographic audit trail
- Hash-linked decision chain
- Tamper-evident storage
- External anchoring capability

**Verification Method:** Cryptographic proof and state machine analysis

---

#### INV-INT-002: Execution Boundary Enforcement
**Property:** All actions must pass through the single execution boundary.

**Formal Specification:**
```
∀ action:
  executed(action) ⇒ passed_through_boundary(action)
```

**Implementation:** `ProxyPipeline` in boundary.py
- Single mandatory execution entry point
- No bypass mechanisms
- Boundary validation on all actions

**Verification Method:** Control flow analysis and reachability verification

---

#### INV-INT-003: Rollback Consistency
**Property:** Rollback operations return system to pre-action state within defined bounds.

**Formal Specification:**
```
∀ action, rollback(action):
  distance(state(pre_action), state(post_rollback)) ≤ rollback_bound(action)
```

**Implementation:** Executor rollback capabilities
- Precomputed reversal plans
- Bounded rollback window
- Post-action verification

**Verification Method:** State transition analysis and distance metrics

---

### 4. Security Invariants

#### INV-SEC-001: Cryptographic Attestation
**Property:** Execution proof bundles provide verifiable cryptographic evidence.

**Formal Specification:**
```
∀ bundle, verifier:
  verify(bundle, verifier) ⇒ integrity_guaranteed(bundle)
```

**Implementation:** ExecutionProofBundle
- SHA-256 hashes of all artifacts
- Ed25519 signature support
- External verifier CLI

**Verification Method:** Cryptographic protocol verification

---

#### INV-SEC-002: Policy Enforcement
**Property:** All actions are evaluated against policy before execution.

**Formal Specification:**
```
∀ action:
  executed(action) ⇒ policy_evaluated(action) ∧ policy_passed(action)
```

**Implementation:** Policy evaluation in boundary.py
- Pre-execution policy check
- Policy gate enforcement
- Action classification for reversibility

**Verification Method:** Protocol verification and state machine analysis

---

#### INV-SEC-003: Safety Gate Enforcement
**Property:** All actions are evaluated against safety constraints before execution.

**Formal Specification:**
```
∀ action:
  executed(action) ⇒ safety_evaluated(action) ∧ safety_passed(action)
```

**Implementation:** Safety evaluation in boundary.py
- Pre-execution safety check
- Safety gate enforcement
- Risk assessment integration

**Verification Method:** Protocol verification and state machine analysis

---

## Verification Methodology

### Verification Tools

1. **TLA+** - For temporal logic properties and state machine verification
2. **Coq** - For theorem proving of algebraic properties
3. **Isabelle/HOL** - For higher-order logic verification
4. **Model Checkers** - For finite state verification
5. **Property-Based Testing** - For runtime invariant checking

### Verification Strategy

1. **Phase 1: Specification** - Express invariants in formal language
2. **Phase 2: Modeling** - Create formal models of kernel components
3. **Phase 3: Verification** - Apply verification tools to models
4. **Phase 4: Validation** - Map verification results to implementation
5. **Phase 5: Documentation** - Publish verification artifacts

### Verification Artifacts

- Formal specification files (TLA+, Coq, Isabelle)
- Verification tool outputs and proofs
- Model checking results
- Property-based test suites
- Verification methodology documentation

---

## Compliance Mapping

### DACT Level 6 Requirements

| Requirement | Invariant | Status |
|------------|-----------|--------|
| Formal specification of invariants | All invariants documented | ✅ Complete |
| Model checking or theorem proving | Verification methodology defined | ⏳ Pending execution |
| Independent third-party audit | Partnership sought | ⏳ Pending |

---

## Next Steps

1. **Select verification tool** based on invariant characteristics
2. **Create formal models** of kernel components
3. **Execute verification** using selected tools
4. **Document results** and publish artifacts
5. **Seek third-party review** for independent validation

---

## References

- DACT Standard v0.2: `docs/DACT_STANDARD_v0.2.md`
- Kernel Architecture: `ARCHITECTURE.md`
- Stripping Rules: `.windsurf/rules/stripping-rules.md`
