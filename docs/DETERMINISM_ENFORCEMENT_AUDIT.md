# Determinism Enforcement Audit

## Mission
Eliminate or strictly control all nondeterministic behavior in critical execution paths and enforce deterministic guarantees at the system level.

## Critical Execution Paths
- ReplayEngine - deterministic audit replay
- Policy evaluation - policy decision computation
- Safety gates - safety verdict computation
- Intent execution - execution kernel
- State transitions - intent store, state management
- Audit records - audit logger

## datetime.now() Usage Classification

### CRITICAL - Must be replaced with DeterministicClock
These usages affect execution decisions, state, or audit trails and MUST be deterministic.

1. **src/exoarmur/federation/clock.py:27**
   - `SystemClock.now()` - Main federation clock
   - Impact: Federation coordination, identity management
   - Action: Replace with DeterministicClock

2. **src/exoarmur/clock.py:28,32**
   - `utc_now()` - Core clock utility
   - Impact: Used throughout core for timestamps
   - Action: Replace with DeterministicClock

3. **src/exoarmur/federation/crypto.py:298**
   - Timestamp for crypto operations
   - Impact: Cryptographic signatures, federation security
   - Action: Replace with DeterministicClock

4. **src/exoarmur/audit/audit_logger.py:322,342**
   - Audit record timestamps
   - Impact: Audit trail integrity
   - Action: Replace with DeterministicClock

5. **src/exoarmur/safety/execution_gate.py:63**
   - Evaluation timestamp
   - Impact: Safety gate evaluation
   - Action: Replace with DeterministicClock

6. **src/exoarmur/causal/causal_context_logger.py:361,423,487,550**
   - Causal logging timestamps
   - Impact: Causal chain tracking
   - Action: Replace with DeterministicClock

7. **src/exoarmur/federation/federate_identity_store.py:83,107,258,303,332,374,403,449,466**
   - Identity management timestamps
   - Impact: Federation identity state
   - Action: Replace with DeterministicClock

8. **src/exoarmur/federation/identity_handshake_state_machine.py:91,391,408,411**
   - Handshake state machine timestamps
   - Impact: Federation handshakes
   - Action: Replace with DeterministicClock

9. **src/exoarmur/federation/coordination/coordination_state_machine.py:165,217,279,335,402,415,448,486**
   - Coordination state machine timestamps
   - Impact: Federation coordination
   - Action: Replace with DeterministicClock

10. **src/exoarmur/federation/coordination/coordination_models_v2.py:78,81,105,108,170,173,225,237**
    - Coordination model timestamps and validation
    - Impact: Federation coordination logic
    - Action: Replace with DeterministicClock

### NON-CRITICAL - Can use wall-clock for observability only
These usages are for logging, telemetry, or observability and do NOT affect execution decisions.

1. **src/exoarmur/stability/deterministic_clock.py:91**
   - `WallClock.now()` - Explicitly for non-critical operations
   - Impact: None - designed for logging/metrics
   - Action: Keep as-is (already documented as non-critical)

2. **src/exoarmur/observability/plane_manager.py:162,532,537**
   - Observability timestamps
   - Impact: Metrics and monitoring only
   - Action: Keep as-is (non-critical)

3. **src/exoarmur/observability/integration_bridge.py:75,80,81,93,124,134,165,178,215,229,267,282,311,319,353,361**
   - Integration bridge timestamps for observability
   - Impact: Observability only
   - Action: Keep as-is (non-critical)

4. **src/exoarmur/collective_confidence/aggregator.py:105,121**
   - Collective confidence aggregation timestamps
   - Impact: Logging/telemetry only
   - Action: Keep as-is (non-critical)

5. **src/exoarmur/telemetry/v2_telemetry_handler.py:306,365**
   - Telemetry handler timestamps
   - Impact: Telemetry only
   - Action: Keep as-is (non-critical)

### UNCERTAIN - Requires manual review
These usages need manual inspection to determine if they affect critical paths.

1. **src/exoarmur/boundary/boundary_contract_registry.py:88,200,242,276,291,388**
   - Boundary contract registry timestamps
   - Action: Manual review required

2. **src/exoarmur/tenancy/tenant_context.py:22**
   - Tenant context creation timestamp
   - Action: Manual review required

3. **src/exoarmur/approval/approval_gate.py:43,57,339,386**
   - Approval gate timestamps
   - Action: Manual review required

4. **src/exoarmur/federation/identity_audit_emitter.py:164,172,198,233**
   - Identity audit emitter timestamps
   - Action: Manual review required

5. **src/exoarmur/auth/auth_service.py:48,66,80,150**
   - Auth service timestamps
   - Action: Manual review required

6. **src/exoarmur/federation/cross_cell_aggregator.py:205**
   - Cross-cell aggregation timestamp
   - Action: Manual review required

7. **src/exoarmur/federation/federation_identity_manager.py:190,198**
   - Federation identity manager timestamps
   - Action: Manual review required

8. **src/exoarmur/federation/identity_transcript_builder.py:86,255**
   - Identity transcript builder timestamps
   - Action: Manual review required

9. **src/exoarmur/federation/models/federation_identity_v2.py:60,79,88,98,109,122,123**
   - Federation identity model timestamps
   - Action: Manual review required

10. **src/exoarmur/federation/coordination/federation_coordination_manager.py:110,171,348,432,477,485,506**
    - Federation coordination manager timestamps
    - Action: Manual review required

11. **src/exoarmur/federation/federation_manager.py:208,231,256,279,312,325,367,402,412,424**
    - Federation manager timestamps
    - Action: Manual review required

12. **src/exoarmur/federation/messages.py:306,353,399**
    - Federation message timestamps
    - Action: Manual review required

13. **src/exoarmur/identity_containment/icw_api.py:316,414**
    - ICW API timestamps
    - Action: Manual review required

14. **src/exoarmur/v2_restrained_autonomy/mock_executor.py:44,78,104**
    - Mock executor timestamps
    - Action: Manual review required

## Enforcement Priority

### Phase 1: Core Clock Replacement (HIGH PRIORITY)
1. Replace `src/exoarmur/clock.py` clock functions with DeterministicClock
2. Replace `src/exoarmur/federation/clock.py` SystemClock with DeterministicClock
3. Update all critical usages to use the new deterministic clock

### Phase 2: Critical Path Refactoring (HIGH PRIORITY)
1. Replace datetime.now() in audit logger
2. Replace datetime.now() in safety gate
3. Replace datetime.now() in causal logger
4. Replace datetime.now() in federation identity management

### Phase 3: Manual Review and Classification (MEDIUM PRIORITY)
1. Review uncertain usages
2. Classify as critical or non-critical
3. Refactor critical usages
4. Document non-critical usages

## Hash Safety Enforcement
Identify all uses of Python hash() in critical paths and replace with stable_hash.

## Ordering Guarantees
Audit unordered collections (set, dict) in critical paths to ensure they don't affect outputs.

## Regression Safeguards
Add tests that fail if:
- datetime.now() is used in critical paths
- nondeterministic ordering affects outputs
- hash instability affects results
