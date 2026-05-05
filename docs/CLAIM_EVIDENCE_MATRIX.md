# ExoArmur Core Claim Evidence Matrix

This document maps claims about ExoArmur Core to their supporting evidence. All claims must be test-proven and tied to specific tests or demonstrations. This matrix prevents overclaiming and enables independent verification.

## Claim Evidence Table

| Claim | Status | Evidence | What it proves | What it does NOT prove | Confidence |
|-------|--------|----------|----------------|------------------------|------------|
| Denied actions do not execute | ✅ PROVEN | Golden Demo (`demos/canonical_truth_reconstruction_demo.py`) | Actions denied by policy/safety gate do not execute on target system | System is secure against all attacks, executor is bug-free | HIGH |
| Deterministic replay hash stability | ✅ PROVEN | `tests/test_determinism_proof_harness.py` (100+ runs), `tests/test_replay_determinism.py` | Replay produces identical hash across multiple runs | System is deterministic in all contexts, no edge cases | HIGH |
| V1 contracts are stable | ✅ PROVEN | `tests/test_schema_snapshots.py`, 1386 passing tests | V1 data models and API contracts have not changed | Contracts are bug-free, optimal for all use cases | HIGH |
| System is not externally audited | ✅ PROVEN | Repository history, documentation | No external audit reports exist | System is unauditable, internal validation is insufficient | CERTAIN |
| System is not production certified | ✅ PROVEN | Repository history, documentation | No production certifications exist | System cannot be used in production, lacks production readiness | CERTAIN |
| Replay detects tampering | ⚠️ PARTIAL | `tests/test_replay_bundle.py`, replay hash validation | Replay detects hash mismatches indicating tampering or nondeterminism | Replay detects all tampering vectors, tampering detection is comprehensive | MEDIUM |
| Feature flags isolate V2 | ✅ PROVEN | `tests/test_v2_feature_flag_isolation.py`, `tests/test_phase_gate_matrix_enforcement.py` | V2 functionality is inert when disabled, requires explicit opt-in | V2 cannot be accidentally enabled through any mechanism | HIGH |
| Module boundaries are enforced | ✅ PROVEN | Plugin architecture, module separation documentation | Core is standalone, modules extend but do not modify Core | Modules cannot violate contracts through side channels | HIGH |
| Safety gates override policy | ✅ PROVEN | `tests/test_arbitration.py`, `src/spec/contracts/arbitration_precedence_v1.yaml` | Safety gate verdict is final, cannot be bypassed by policy | Safety gates are bug-free, all unsafe actions are caught | HIGH |
| Audit records are tamper-evident | ✅ PROVEN | NATS JetStream immutable storage, `tests/test_audit_normalizer_integration.py` | Audit records written to immutable storage, tampering causes detection | Audit records are impossible to tamper with, storage is infallible | HIGH |
| Golden Demo is mandatory regression gate | ✅ PROVEN | Repository policy, CI/CD configuration | All changes must pass Golden Demo before merge | Golden Demo covers all failure modes, no edge cases | HIGH |
| System has 1386 passing tests | ✅ PROVEN | pytest output, CI/CD logs | Test suite passes with 1386 tests | Tests cover all code paths, no bugs exist | HIGH |
| Zero skipped tests in verify_core suite | ✅ PROVEN | pytest output, test classification | Core constitutional tests have zero skips | All test suites have zero skips, no deferred work | HIGH |

## Claim Definitions

### Denied actions do not execute
- **Evidence**: Golden Demo demonstrates that a delete action outside the authorized path is denied before any filesystem side effect occurs.
- **Test**: `demos/canonical_truth_reconstruction_demo.py`
- **Golden Demo Hash**: `7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b`
- **Limitation**: Only proves denial for the specific tested scenario. Does not prove denial for all possible attack vectors or executor bugs.

### Deterministic replay hash stability
- **Evidence**: `tests/test_determinism_proof_harness.py` runs 100+ iterations and validates hash stability. `tests/test_replay_determinism.py` validates replay across different runs.
- **Tests**: 100+ deterministic proof harness iterations, replay determinism tests
- **Limitation**: Proves determinism for tested scenarios. Does not guarantee determinism for untested edge cases or environmental variations.

### V1 contracts are stable
- **Evidence**: `tests/test_schema_snapshots.py` validates V1 schema stability. All 1386 tests pass without V1 modifications.
- **Tests**: Schema snapshot tests, full test suite
- **Limitation**: Proves contracts have not changed in the tested version. Does not prove contracts are optimal or bug-free.

### System is not externally audited
- **Evidence**: Repository history shows no external audit reports. Documentation does not claim external audit.
- **Evidence Type**: Negative evidence (absence of audit reports)
- **Confidence**: CERTAIN - absence of evidence is evidence of absence for external audits

### System is not production certified
- **Evidence**: Repository history shows no production certifications. Documentation states "private evaluation" posture.
- **Evidence Type**: Negative evidence (absence of certifications)
- **Confidence**: CERTAIN - absence of evidence is evidence of absence for certifications

### Replay detects tampering
- **Evidence**: `tests/test_replay_bundle.py` validates replay bundle integrity. Replay hash mismatch indicates tampering or nondeterminism.
- **Tests**: Replay bundle tests, hash validation
- **Limitation**: Only proves tampering detection through hash mismatches. Does not prove detection of sophisticated tampering that preserves hash.

### Feature flags isolate V2
- **Evidence**: `tests/test_v2_feature_flag_isolation.py` validates V2 is inert when disabled. `tests/test_phase_gate_matrix_enforcement.py` validates phase gate enforcement.
- **Tests**: Feature flag isolation tests, phase gate tests
- **Limitation**: Proves isolation for tested flag configurations. Does not guarantee isolation for all possible flag combinations.

### Module boundaries are enforced
- **Evidence**: Plugin architecture with entry point discovery. Module separation documented in `docs/MODULE_SEPARATION.md`.
- **Documentation**: Module separation strategy
- **Limitation**: Proves architectural separation. Does not guarantee runtime isolation from side channels.

### Safety gates override policy
- **Evidence**: `tests/test_arbitration.py` validates precedence rules. `src/spec/contracts/arbitration_precedence_v1.yaml` defines safety gate as highest precedence.
- **Tests**: Arbitration tests
- **Contract**: Arbitration precedence contract
- **Limitation**: Proves contract enforcement. Does not guarantee safety gates are bug-free or catch all unsafe actions.

### Audit records are tamper-evident
- **Evidence**: NATS JetStream provides immutable storage. `tests/test_audit_normalizer_integration.py` validates audit normalization.
- **Tests**: Audit normalization tests
- **Storage**: NATS JetStream immutable storage
- **Limitation**: Proves tamper-evidence through storage mechanism. Does not guarantee storage is infallible or tampering is impossible.

### Golden Demo is mandatory regression gate
- **Evidence**: Repository policy requires Golden Demo pass. CI/CD configuration enforces this gate.
- **Policy**: Repository governance policy
- **CI/CD**: Regression gate configuration
- **Limitation**: Proves gate is enforced in CI/CD. Does not guarantee gate covers all failure modes.

### System has 1166 passing tests
- **Evidence**: pytest output shows 1386 passed, 13 skipped, 3 xfailed.
- **Test Output**: pytest summary
- **Limitation**: Proves test count. Does not prove test coverage is complete or tests are comprehensive.

### Zero skipped tests in verify_core suite
- **Evidence**: Test classification shows verify_core suite has zero skips.
- **Test Classification**: `docs/TEST_CLASSIFICATION.md`
- **Limitation**: Proves zero skips in verify_core suite. Does not prove zero skips in all suites.

## Confidence Levels

- **CERTAIN**: Negative evidence (absence of proof is proof of absence)
- **HIGH**: Strong test evidence with comprehensive coverage
- **MEDIUM**: Test evidence with known limitations or partial coverage
- **LOW**: Limited test evidence or indirect proof

## Claim Discipline Rules

1. **No overclaiming**: Claims must not exceed what evidence proves
2. **Evidence required**: Every claim must map to specific tests or documentation
3. **Limitations stated**: Each claim must state what it does NOT prove
4. **Confidence assigned**: Each claim must have a confidence level based on evidence strength
5. **No future claims**: Claims must be about current state, not future capabilities
6. **No comparative claims**: Avoid "better than X" claims without objective evidence
7. **No absolute claims**: Avoid "impossible", "never", "always" without comprehensive proof

## Forbidden Claims (Not Proven)

The following claims are NOT supported by current evidence and MUST NOT be made:

- "Production-ready" - Not proven by current tests or certifications
- "Externally audited" - No external audit reports exist
- "BFT" - No Byzantine fault tolerance implementation in Core
- "Causal inference" - No causal inference capabilities in Core
- "Zero CVEs" - No security audit or vulnerability assessment
- "Unhackable" - No system is unhackable
- "100% secure" - No system is 100% secure
- "No bugs" - 1386 passing tests does not prove zero bugs

## Claim Lint Recommendations

Implement automated claim linting to:
1. Scan documentation for forbidden claims
2. Validate claims against evidence matrix
3. Flag claims without supporting evidence
4. Enforce confidence level assignment
5. Prevent overclaiming in documentation

See `docs/HARDENING_PLAN.md` for claim lint implementation roadmap.
