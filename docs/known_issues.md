# Known Issues - ExoArmur Core

## initialize_components() Structural Problem

### Issue Description
The `initialize_components()` function in `src/exoarmur/main.py` has been eliminated to enforce V2EntryGate governance boundaries. Direct component instantiation now bypasses V2EntryGate enforcement and is blocked.

### Exact Error Message
```
RuntimeError: VIOLATION: initialize_components() bypasses V2EntryGate governance.
This function has been eliminated to prevent unauthorized domain logic access.

SOLUTION:
• For system startup: Use FastAPI lifespan() (V2-compliant)
• For domain logic: Route through V2EntryGate.execute_module()
• For testing: Use V2EntryGate for component access
• For CLI: Commands must use V2EntryGate, not direct initialization

All domain logic MUST pass through V2EntryGate. No exceptions.
```

### Affected Tests
The following integration-style tests are affected:
- `tests/test_integration.py` (9 tests)
  - `TestThinVerticalSlice::test_health_endpoint`
  - `TestThinVerticalSlice::test_telemetry_ingest_endpoint`
  - `TestThinVerticalSlice::test_audit_retrieval_endpoint`
  - `TestThinVerticalSlice::test_admo_flow_audit_chain`
  - `TestThinVerticalSlice::test_telemetry_validation_error_handling`
  - `TestThinVerticalSlice::test_different_severity_levels`
  - `TestThinVerticalSlice::test_idempotency_in_integration`
  - `TestThinVerticalSlice::test_audit_for_nonexistent_correlation`
  - `TestAsyncIntegration::test_async_client_integration`

- `tests/test_intent_freeze_binding.py` (4 tests)
  - `TestIntentFreezeBinding::test_require_human_freezes_intent_and_binds_approval`
  - `TestIntentFreezeBinding::test_execution_blocked_until_approved`
  - `TestIntentFreezeBinding::test_execution_allowed_after_approved_and_matches_binding`
  - `TestIntentFreezeBinding::test_execution_blocked_on_binding_mismatch`

- `tests/test_approval_wiring.py` (8 tests)
  - `TestApprovalWiring::test_ingest_returns_pending_when_require_human`
  - `TestApprovalWiring::test_ingest_returns_pending_when_require_quorum`
  - `TestApprovalWiring::test_approve_endpoint_changes_status_to_approved`
  - `TestApprovalWiring::test_deny_endpoint_changes_status_to_denied`
  - `TestApprovalWiring::test_deny_endpoint_requires_reason`
  - `TestApprovalWiring::test_get_approval_status_endpoint`
  - `TestApprovalWiring::test_execution_kernel_blocks_without_approval`
  - `TestApprovalWiring::test_execution_kernel_allows_a0_without_approval`

**Total affected tests: 21 integration tests**

### First Appearance
**Commit**: `7b40899` - "[ARCH] Phase 5: V2 Execution Enforcement + Bootstrap + Bypass Elimination"
**Date**: During Phase 5 implementation
**Message**: "Elimination of initialize_components() bypass"

### Why initialize_components() Violates V2EntryGate Governance

The `initialize_components()` function represents a **structural bypass** of ExoArmur's execution governance boundary:

#### Architectural Context
ExoArmur enforces that **all domain logic must pass through V2EntryGate** for:
- **Auditability**: Every execution decision must be recorded
- **Policy Enforcement**: Safety and policy checks must occur
- **Determinism**: Execution must be replayable and verifiable
- **Security**: No unauthorized side effects outside governance

#### The Problem
`initialize_components()` directly instantiates core components:
```python
# BEFORE (bypass):
def initialize_components():
    global nats_client, telemetry_validator, facts_deriver, local_decider
    global belief_generator, collective_aggregator, safety_gate, execution_kernel, audit_logger
    
    # Direct instantiation - bypasses V2EntryGate
    telemetry_validator = TelemetryValidator()
    facts_deriver = FactsDeriver()
    local_decider = LocalDecider()
    # ... more direct instantiation
```

This creates **unaudited, ungoverned execution** that:
- Bypasses policy and safety checks
- Avoids audit trail recording
- Enables unauthorized side effects
- Violates the core architectural invariant

#### The Solution
All system initialization now occurs through **V2-governed bootstrap**:
```python
# AFTER (compliant):
async def lifespan(app: FastAPI):
    # Bootstrap system through V2EntryGate
    bootstrap_success = bootstrap_system_via_v2_entry_gate(nats_config_dict)
    if not bootstrap_success:
        raise RuntimeError("System bootstrap failed through V2EntryGate")
```

### Impact on Testing

Integration tests that previously called `initialize_components()` directly must now:
1. **Use V2EntryGate**: Create proper `ExecutionRequest` objects for component access
2. **Mock appropriately**: Use V2-compliant test fixtures
3. **Follow governance**: Route all test setup through the same boundaries as production

### Current Status
- **Structural enforcement**: Active - direct instantiation blocked
- **Test impact**: 21 integration tests affected
- **Production impact**: None - production uses FastAPI lifespan (V2-compliant)
- **Resolution needed**: Tests must be updated to use V2EntryGate

### Related Documentation
- `ARCHITECTURE.md` - V2EntryGate governance model
- `BOUNDARY_MODEL.md` - Execution boundary enforcement
- `ISOLATION_GUARANTEES.md` - Structural bypass elimination
