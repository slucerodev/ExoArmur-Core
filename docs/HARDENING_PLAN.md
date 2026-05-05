# ExoArmur Core Hardening Plan

This document defines the hardening roadmap for ExoArmur Core. The plan is structured in phases (H1-H8) that progressively strengthen the system's invariants, claims, and evidence. Each phase has specific goals, success criteria, and dependencies.

## Phase Overview

| Phase | Goal | Success Criteria | Dependencies |
|-------|------|------------------|--------------|
| H1 | Document invariants and claims | INVARIANTS.md and CLAIM_EVIDENCE_MATRIX.md created | None |
| H2 | Implement claim lint | Automated claim linting enforced in CI/CD | H1 |
| H3 | Adversarial replay mutation tests | Replay detects tampering mutations | H1 |
| H4 | Malicious executor tests | System rejects malicious executor behavior | H1 |
| H5 | Evidence export bundle | Audit export format and validation | H1, INV-004 |
| H6 | Module manifest contract | Module boundaries formally specified | H1, INV-008 |
| H7 | Canonicalization audit | Canonicalization process validated | H1, INV-001 |
| H8 | Threat model | Comprehensive threat model documented | H1-H7 |

---

## H1: Invariants and Claims Documentation

**Goal**: Explicitly define system invariants and map all claims to supporting evidence.

### Tasks
- ✅ Create INVARIANTS.md with 8 core invariants
- ✅ Create CLAIM_EVIDENCE_MATRIX.md with claim-to-evidence mapping
- ✅ Document invariant enforcement mechanisms
- ✅ Map claims to specific tests and demonstrations

### Success Criteria
- [x] All 8 invariants defined with ID, statement, enforcement, evidence
- [x] All claims mapped to evidence with confidence levels
- [x] Forbidden claims documented
- [x] Claim discipline rules established

### Dependencies
- None (foundational phase)

### Status
✅ COMPLETED - See docs/INVARIANTS.md and docs/CLAIM_EVIDENCE_MATRIX.md

---

## H2: Claim Lint Implementation

**Goal**: Implement automated claim linting to prevent overclaiming and ensure all claims are evidence-backed.

### Tasks
- Implement claim_lint tool to scan documentation
- Define forbidden claim patterns (see Forbidden Claims section below)
- Integrate claim_lint into pre-commit hooks
- Integrate claim_lint into CI/CD pipeline
- Add claim_lint to documentation validation

### Success Criteria
- Claim_lint scans all .md files in docs/
- Forbidden claims trigger build failure
- Claims without evidence trigger warnings
- Claim_lint passes in CI/CD on every commit
- Documentation updates require claim_lint pass

### Dependencies
- H1 (invariants and claims documentation)

### Implementation Approach
1. Create scripts/claim_lint.py
2. Define forbidden claim patterns in config file
3. Add to .pre-commit-config.yaml
4. Add to CI/CD workflow
5. Document claim_lint usage in CONTRIBUTING.md

### Forbidden Claims
The following claims are FORBIDDEN and must trigger claim_lint failure:

**Production Readiness Claims**
- "production-ready"
- "production-grade" (except when referring to specific components like "production-grade deterministic governance runtime")
- "ready for production deployment"
- "production deployment"

**Audit/Certification Claims**
- "externally audited"
- "third-party audited"
- "security audit completed"
- "penetration tested" (without specifying scope)
- "SOC 2 compliant"
- "ISO 27001 certified"
- "GDPR compliant"
- "HIPAA compliant"

**Advanced Capabilities (Not in Core)**
- "BFT" (Byzantine Fault Tolerance)
- "Byzantine fault tolerance"
- "post-quantum"
- "PQC"
- "quantum-resistant"
- "causal inference"
- "counterfactual reasoning"
- "digital antibody"
- "moving target defense"
- "adversary twin"
- "sovereign federation"

**Security Claims**
- "zero CVEs"
- "no vulnerabilities"
- "unhackable"
- "100% secure"
- "impossible to compromise"
- "cannot be hacked"

**Licensing Claims**
- "open source"
- "MIT licensed"
- "BSD licensed"
- "GPL licensed"
- "free software"

**Absolute Claims**
- "never fails"
- "always works"
- "guaranteed"
- "impossible to fail"
- "zero downtime"
- "100% uptime"

**Comparative Claims**
- "better than X" (without objective evidence)
- "superior to X" (without objective evidence)
- "best in class" (without objective evidence)
- "industry leading" (without objective evidence)

### Allowed Claim Patterns
The following claim patterns are ALLOWED when properly qualified:

**Qualified Production Claims**
- "production-grade deterministic governance runtime" (referring to Core engine quality)
- "not production-ready" (when explicitly stating not ready)
- "private evaluation" (current posture)

**Qualified Security Claims**
- "deterministic enforcement" (proven by tests)
- "execution boundary enforcement" (proven by Golden Demo)
- "audit trail" (proven by audit tests)
- "replay verification" (proven by replay tests)

**Qualified Licensing Claims**
- "proprietary evaluation license"
- "private evaluation repository"
- "not open source"

**Evidence-Backed Claims**
- "1166 passing tests" (with pytest output)
- "Golden Demo passes" (with hash)
- "V1 contracts stable" (with schema snapshot tests)

### Claim Lint Rules

1. **Forbidden Pattern Rule**: Any forbidden claim pattern triggers failure
2. **Evidence Rule**: Claims must reference evidence in CLAIM_EVIDENCE_MATRIX.md
3. **Confidence Rule**: Claims must have assigned confidence level
4. **Limitation Rule**: Claims must state what they do NOT prove
5. **Absolute Rule**: Absolute claims ("never", "always", "impossible") trigger failure
6. **Future Rule**: Future capability claims trigger failure (use "reserved extension surfaces" instead)

### Status
🚧 PENDING - Implementation required

---

## H3: Adversarial Replay Mutation Tests

**Goal**: Implement tests that verify replay detects tampering through intentional mutation of audit records.

### Tasks
- Create adversarial replay mutation test suite
- Define mutation vectors (audit record modification, hash tampering, bundle corruption)
- Implement mutation injection framework
- Validate replay detects all mutations
- Add mutation tests to CI/CD

### Success Criteria
- Replay detects all defined mutation vectors
- Mutation tests pass with 100% detection rate
- Mutation tests run in CI/CD on every commit
- Mutation coverage documented

### Dependencies
- H1 (INV-005: Replay Integrity)

### Mutation Vectors
1. **Audit Record Deletion**: Remove audit record from bundle
2. **Audit Record Modification**: Change field value in audit record
3. **Audit Record Reordering**: Change order of audit records
4. **Hash Tampering**: Modify replay hash in bundle
5. **Bundle Corruption**: Corrupt bundle metadata
6. **Signature Forgery**: Attempt to forge bundle signature
7. **Timestamp Manipulation**: Modify execution timestamps
8. **Executor State Tampering**: Modify executor state in bundle

### Test Coverage
- `tests/test_adversarial_replay_mutation.py` (new)
- Mutation detection rate: 100%
- False positive rate: 0%

### Status
🚧 PENDING - Implementation required

---

## H4: Malicious Executor Tests

**Goal**: Implement tests that verify system rejects malicious executor behavior (bypassing safety gates, executing denied actions).

### Tasks
- Create malicious executor test suite
- Define malicious executor behaviors
- Implement malicious executor simulation
- Validate system rejects all malicious behaviors
- Add malicious executor tests to CI/CD

### Success Criteria
- System rejects all defined malicious behaviors
- Malicious executor tests pass with 100% rejection rate
- Malicious executor tests run in CI/CD on every commit
- Malicious behavior catalog documented

### Dependencies
- H1 (INV-002: Execution Boundary Integrity, INV-003: Policy Precedence)

### Malicious Behaviors
1. **Safety Gate Bypass**: Attempt to execute without safety gate approval
2. **Policy Override**: Attempt to override policy denial
3. **Side Channel Execution**: Attempt to execute through non-approved path
4. **Executor Spoofing**: Attempt to spoof executor identity
5. **Intent Forgery**: Attempt to forge approved intent
6. **Approval Spoofing**: Attempt to spoof operator approval
7. **Bundle Tampering**: Attempt to use tampered policy bundle
8. **State Manipulation**: Attempt to manipulate executor state to bypass checks

### Test Coverage
- `tests/test_malicious_executor.py` (new)
- Rejection rate: 100%
- False positive rate: 0%

### Status
🚧 PENDING - Implementation required

---

## H5: Evidence Export Bundle

**Goal**: Define and implement audit export bundle format for external audit and compliance verification.

### Tasks
- Define evidence export bundle schema
- Implement evidence export tool
- Validate export bundle completeness
- Add export bundle tests
- Document export process

### Success Criteria
- Evidence export bundle schema defined
- Export tool generates complete bundles
- Export bundles validate successfully
- Export tests pass in CI/CD
- Export process documented

### Dependencies
- H1 (INV-004: Audit/Proof Integrity)

### Export Bundle Contents
1. **Audit Records**: Complete audit trail for execution
2. **Policy Bundles**: All policy bundles used in execution
3. **Safety Gate Configuration**: Safety gate rules and verdicts
4. **Execution Intents**: All approved execution intents
5. **Replay Hashes**: Replay hashes for verification
6. **System Metadata**: Core version, configuration, environment
7. **Evidence Signatures**: Cryptographic signatures for verification

### Export Format
- JSON format with schema validation
- Compressed bundle for large exports
- Signature verification capability
- Version compatibility tracking

### Test Coverage
- `tests/test_evidence_export.py` (new)
- Export completeness tests
- Export validation tests
- Signature verification tests

### Status
🚧 PENDING - Implementation required

---

## H6: Module Manifest Contract

**Goal**: Formally specify module boundaries and contracts to ensure modules extend Core without modification.

### Tasks
- Define module manifest schema
- Implement module manifest validation
- Add module boundary tests
- Document module contract requirements
- Validate module isolation

### Success Criteria
- Module manifest schema defined
- Manifest validation tool implemented
- Module boundary tests pass
- Module contract documented
- Module isolation validated

### Dependencies
- H1 (INV-008: Module Isolation)

### Module Manifest Contents
1. **Module Identity**: Name, version, author
2. **Entry Points**: Plugin entry points provided
3. **Contract Dependencies**: V1/V2 contracts used
4. **Feature Flags**: Feature flags required
5. **Extension Points**: Core extension points used
6. **Isolation Guarantees**: Module isolation commitments
7. **Testing Requirements**: Module testing requirements

### Manifest Schema
- JSON schema with validation
- Version compatibility matrix
- Dependency constraints
- Extension point contracts

### Test Coverage
- `tests/test_module_manifest.py` (new)
- Manifest validation tests
- Module boundary tests
- Isolation verification tests

### Status
🚧 PENDING - Implementation required

---

## H7: Canonicalization Audit

**Goal**: Validate the canonicalization process to ensure deterministic ID and timestamp generation.

### Tasks
- Document canonicalization process
- Implement canonicalization audit tests
- Validate ID generation determinism
- Validate timestamp generation determinism
- Add canonicalization tests to CI/CD

### Success Criteria
- Canonicalization process documented
- Canonicalization tests pass
- ID generation deterministic across runs
- Timestamp generation deterministic across runs
- Canonicalization tests in CI/CD

### Dependencies
- H1 (INV-001: Determinism)

### Canonicalization Process
1. **Intent ID Generation**: Deterministic ULID from action parameters
2. **Timestamp Generation**: UTC timestamp with nanosecond precision
3. **Correlation ID Generation**: Deterministic correlation from telemetry
4. **Bundle Hash Generation**: Deterministic hash from bundle contents
5. **Replay Hash Generation**: Deterministic hash from audit records

### Test Coverage
- `tests/test_canonicalization_audit.py` (new)
- ID generation determinism tests
- Timestamp generation determinism tests
- Hash generation determinism tests
- Canonicalization process tests

### Status
🚧 PENDING - Implementation required

---

## H8: Threat Model

**Goal**: Document comprehensive threat model covering all attack vectors and mitigations.

### Tasks
- Identify threat actors and motivations
- Document attack vectors
- Map threats to invariants
- Document mitigation strategies
- Validate threat model against tests

### Success Criteria
- Threat model documented
- Attack vectors cataloged
- Threat-to-invariant mapping complete
- Mitigation strategies defined
- Threat model validated against tests

### Dependencies
- H1-H7 (all invariants and hardening phases)

### Threat Actors
1. **Internal Operator**: Authorized operator with malicious intent
2. **External Attacker**: Unauthorized external attacker
3. **Compromised Module**: Malicious module attempting to violate boundaries
4. **Supply Chain Attacker**: Attacker compromising dependencies
5. **Infrastructure Attacker**: Attacker compromising infrastructure

### Attack Vectors
1. **Policy Tampering**: Modifying policy bundles
2. **Safety Gate Bypass**: Attempting to bypass safety gates
3. **Audit Tampering**: Modifying or deleting audit records
4. **Executor Compromise**: Compromising executor implementation
5. **Module Boundary Violation**: Module attempting to modify Core
6. **Replay Attack**: Attempting to forge replay results
7. **Determinism Break**: Introducing nondeterminism
8. **Signature Forgery**: Forging bundle signatures

### Mitigation Strategies
1. **Policy Tampering**: Bundle signing, signature verification
2. **Safety Gate Bypass**: Contract enforcement, precedence rules
3. **Audit Tampering**: Immutable storage, integrity checks
4. **Executor Compromise**: Executor validation, sandboxing
5. **Module Boundary Violation**: Plugin architecture, manifest validation
6. **Replay Attack**: Hash verification, tampering detection
7. **Determinism Break**: Pre-commit scanner, determinism tests
8. **Signature Forgery**: Cryptographic signatures, key management

### Test Coverage
- Threat model validated against existing tests
- Gaps identified for future test development
- Mitigation strategies mapped to specific tests

### Status
🚧 PENDING - Implementation required

---

## Hardening Progress Summary

| Phase | Status | Completion |
|-------|--------|------------|
| H1: Invariants and Claims | ✅ COMPLETED | 100% |
| H2: Claim Lint | 🚧 PENDING | 0% |
| H3: Adversarial Replay Tests | 🚧 PENDING | 0% |
| H4: Malicious Executor Tests | 🚧 PENDING | 0% |
| H5: Evidence Export Bundle | 🚧 PENDING | 0% |
| H6: Module Manifest Contract | 🚧 PENDING | 0% |
| H7: Canonicalization Audit | 🚧 PENDING | 0% |
| H8: Threat Model | 🚧 PENDING | 0% |

**Overall Progress**: 12.5% (1/8 phases completed)

## Next Recommended Step

Implement H2: Claim Lint as the next hardening phase. Claim linting provides immediate value by preventing overclaiming in documentation and ensuring all claims remain evidence-backed.

### H2 Implementation Priority
- High impact, low effort
- Prevents future overclaiming incidents
- Integrates with existing CI/CD
- Builds on H1 foundation

### H2 Success Metrics
- Zero forbidden claims in documentation
- All claims mapped to evidence
- Claim lint passes in CI/CD
- Documentation quality improved
