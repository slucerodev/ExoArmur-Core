# ExoArmur Core Failure Taxonomy

This document defines the failure types that ExoArmur Core can encounter. Each failure type has defined semantics, audit expectations, replay behavior, retryability, and operator action requirements. This taxonomy enables precise incident classification and response.

## Failure Types

### DENIED_BY_POLICY

**Meaning**: Action was denied by policy evaluation or safety gate before execution.

**Execution occurred?**: NO - Action did not execute on target system.

**Audit expectation**: 
- Audit record shows denial reason
- Safety gate verdict is DENIED
- No executor side effects
- Policy bundle reference included

**Replay behavior**: 
- Replay reproduces denial
- Hash stable across replays
- No executor state reconstruction needed

**Retryable?**: NO - Denial is intentional based on policy/safety evaluation.

**Operator action needed?**: MAYBE - If denial is unexpected, operator may need to:
- Review policy bundle
- Adjust safety gate configuration
- Approve action if appropriate
- Investigate why action was denied

**Example**: Delete action outside authorized path denied by safety gate.

**Test coverage**: `demos/canonical_truth_reconstruction_demo.py`, `tests/test_execution_boundary_v2_policy_engine.py`

---

### EXECUTOR_FAILED

**Meaning**: Executor attempted to execute approved action but failed due to executor error (e.g., network failure, resource unavailable, permission error).

**Execution occurred?**: PARTIAL - Executor attempted execution but did not complete successfully.

**Audit expectation**:
- Audit record shows executor failure
- Execution intent was APPROVED
- Executor error details captured
- Side effects may have occurred (partial execution)

**Replay behavior**:
- Replay reproduces executor failure if same error condition exists
- Hash may differ if executor error is nondeterministic
- Requires executor state reconstruction

**Retryable?**: YES - If executor error is transient (network, resource).

**Operator action needed?**: YES - Operator must:
- Investigate executor error
- Fix underlying issue (network, resource, permission)
- Retry action if appropriate
- Assess partial execution impact

**Example**: Approved delete action failed due to file permission error.

**Test coverage**: `tests/test_execution_boundary_v2_filesystem_executor_integration.py`

---

### REPLAY_MISMATCH

**Meaning**: Replay hash does not match original execution hash, indicating potential tampering, nondeterminism, or state divergence.

**Execution occurred?**: UNKNOWN - Original execution may or may not have occurred as claimed.

**Audit expectation**:
- Audit records exist but may be tampered
- Replay hash mismatch detected
- Original hash available for comparison
- Potential evidence of tampering

**Replay behavior**:
- Replay fails with hash mismatch error
- System refuses to accept replay result
- Requires investigation before trust re-establishment

**Retryable?**: NO - Hash mismatch indicates fundamental issue requiring investigation.

**Operator action needed?**: YES - Operator must:
- Investigate cause of hash mismatch
- Verify audit record integrity
- Check for nondeterminism in execution
- Restore trusted state if tampering confirmed

**Example**: Replay of audit bundle produces different hash than original execution.

**Test coverage**: `tests/test_replay_determinism.py`, `tests/test_replay_bundle.py`

---

### STALE_CORE_VERSION

**Meaning**: Core version is outdated and does not include latest security patches, contract updates, or invariant fixes.

**Execution occurred?**: UNKNOWN - Execution may succeed but with known vulnerabilities or bugs.

**Audit expectation**:
- Audit records valid but from outdated version
- May lack security fixes
- May have known bugs
- Replay may not be stable

**Replay behavior**:
- Replay may succeed or fail depending on compatibility
- Hash may not be stable across versions
- May require version upgrade for reliable replay

**Retryable?**: YES - After Core version upgrade.

**Operator action needed?**: YES - Operator must:
- Upgrade Core to latest version
- Re-run affected actions if needed
- Validate audit records from old version
- Assess security impact of delay

**Example**: Core version 2.0.0 has known security vulnerability fixed in 2.1.0.

**Test coverage**: Version compatibility tests (planned)

---

### PROOF_TAMPERED

**Meaning**: Audit records or proof bundle have been modified, deleted, or corrupted, invalidating the execution proof.

**Execution occurred?**: UNKNOWN - Original execution cannot be verified due to tampered evidence.

**Audit expectation**:
- Audit records missing or corrupted
- Proof bundle invalid
- Tampering detected through integrity checks
- No reliable audit trail available

**Replay behavior**:
- Replay fails due to missing or invalid audit records
- Hash cannot be computed
- System refuses to accept tampered evidence

**Retryable?**: NO - Tampered evidence cannot be recovered.

**Operator action needed?**: YES - Operator must:
- Investigate tampering source
- Restore audit records from backup if available
- Identify responsible party if malicious
- Implement stronger audit protection

**Example**: Audit record deleted from NATS JetStream storage.

**Test coverage**: Audit integrity tests (planned)

---

### NONDETERMINISTIC_TRACE

**Meaning**: Execution produced nondeterministic trace, causing hash instability across runs without external tampering.

**Execution occurred?**: YES - Action executed, but trace is nondeterministic.

**Audit expectation**:
- Audit records exist but may vary across runs
- Hash not stable
- May indicate code issue or environmental factor
- Replay may produce different results

**Replay behavior**:
- Replay may succeed but with different hash
- Hash instability detected
- Requires investigation of nondeterminism source

**Retryable?**: NO - Nondeterminism indicates code or environment issue requiring fix.

**Operator action needed?**: YES - Operator must:
- Investigate source of nondeterminism
- Fix code issue if found
- Stabilize environment if environmental factor
- Re-run action after fix

**Example**: Action includes timestamp in execution context causing hash variation.

**Test coverage**: `tests/test_determinism_proof_harness.py`, `tests/test_adversarial_determinism.py`

---

### INVALID_BUNDLE

**Meaning**: Policy bundle, intent freeze, or other signed bundle is invalid (wrong signature, expired, malformed).

**Execution occurred?**: NO - Bundle validation failed before execution.

**Audit expectation**:
- Audit record shows bundle validation failure
- Bundle signature verification failed
- Bundle metadata invalid
- No execution attempted

**Replay behavior**:
- Replay reproduces bundle validation failure
- Hash stable
- No execution state reconstruction needed

**Retryable?**: YES - After providing valid bundle.

**Operator action needed?**: YES - Operator must:
- Provide valid signed bundle
- Verify bundle signature
- Check bundle expiration
- Re-submit action with valid bundle

**Example**: Policy bundle signature verification failed due to expired signing key.

**Test coverage**: `tests/test_intent_freeze_binding.py`, bundle validation tests

---

### UNKNOWN_EXECUTION_STATE

**Meaning**: System cannot determine execution state due to missing audit records, incomplete logs, or system failure during execution.

**Execution occurred?**: UNKNOWN - Execution state cannot be determined.

**Audit expectation**:
- Audit records missing or incomplete
- Logs may be unavailable
- System failure during execution
- No definitive execution status

**Replay behavior**:
- Replay fails due to missing audit records
- Cannot reconstruct execution path
- Hash cannot be computed

**Retryable?**: NO - Cannot retry without knowing execution state.

**Operator action needed?**: YES - Operator must:
- Investigate missing audit records
- Check system logs for execution evidence
- Assess impact of unknown state
- Implement stronger audit retention

**Example**: System crashed during execution, audit records not written.

**Test coverage**: Fault injection tests (planned)

---

## Failure Classification Matrix

| Failure Type | Execution | Audit | Replay | Retryable | Operator Action |
|--------------|-----------|-------|--------|----------|----------------|
| DENIED_BY_POLICY | NO | Complete | Stable | NO | Maybe (review policy) |
| EXECUTOR_FAILED | PARTIAL | Complete | Variable | YES | YES (fix executor) |
| REPLAY_MISMATCH | UNKNOWN | Suspect | Fail | NO | YES (investigate) |
| STALE_CORE_VERSION | UNKNOWN | Valid | Variable | YES | YES (upgrade) |
| PROOF_TAMPERED | UNKNOWN | Missing/Invalid | Fail | NO | YES (investigate) |
| NONDETERMINISTIC_TRACE | YES | Variable | Variable | NO | YES (fix code) |
| INVALID_BUNDLE | NO | Complete | Stable | YES | YES (provide valid bundle) |
| UNKNOWN_EXECUTION_STATE | UNKNOWN | Missing | Fail | NO | YES (investigate) |

## Failure Response Workflow

### Immediate Response
1. Classify failure using this taxonomy
2. Check audit record availability and integrity
3. Determine if execution occurred
4. Assess retryability
5. Notify operator if action required

### Investigation
1. Review audit records for failure details
2. Check logs for additional context
3. Validate bundle signatures if applicable
4. Replay execution if audit records available
5. Compare hashes to detect tampering

### Resolution
1. Fix underlying issue if fixable
2. Retry action if appropriate
3. Restore audit records if tampered
4. Upgrade Core if version stale
5. Document incident for future reference

## Failure Prevention

### DENIED_BY_POLICY Prevention
- Clear policy documentation
- Safety gate configuration review
- Operator training on policy evaluation

### EXECUTOR_FAILED Prevention
- Executor health monitoring
- Resource availability checks
- Permission validation before execution
- Network connectivity monitoring

### REPLAY_MISMATCH Prevention
- Determinism enforcement
- Pre-commit determinism scanner
- Regular replay validation
- Audit record integrity checks

### STALE_CORE_VERSION Prevention
- Automated version checking
- Security patch notifications
- Upgrade automation
- Version compatibility testing

### PROOF_TAMPERED Prevention
- Immutable audit storage
- Audit record integrity monitoring
- Access control on audit storage
- Regular audit backup

### NONDETERMINISTIC_TRACE Prevention
- Pre-commit determinism scanner
- Environmental stability
- Code review for nondeterminism
- Determinism testing

### INVALID_BUNDLE Prevention
- Bundle signature validation
- Bundle expiration monitoring
- Bundle format validation
- Key management

### UNKNOWN_EXECUTION_STATE Prevention
- Robust error handling
- Audit record durability
- System health monitoring
- Fault-tolerant execution

## Failure Metrics

Track the following metrics to identify patterns and improve system reliability:
- Failure type frequency
- Time to resolution per failure type
- Operator intervention frequency
- Replay success rate
- Audit record integrity incidents

## Future Work

- Add automated failure classification
- Implement failure response automation
- Create failure response runbooks
- Develop failure prediction models
- Integrate with incident management systems
