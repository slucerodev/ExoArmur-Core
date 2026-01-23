# ExoArmur ADMO Testing

## Test Taxonomy

### Unit Tests
**Purpose**: Test individual components in isolation
**Location**: `tests/test_*.py` (unit-specific files)
**Characteristics**:
- Fast execution
- No external dependencies
- Mock external services
- Test specific functionality

### Integration Tests
**Purpose**: Test component interactions
**Location**: `tests/test_integration.py`, `tests/test_idempotency.py`
**Characteristics**:
- Multiple components
- Real data flow
- External service dependencies
- End-to-end scenarios

### Acceptance Tests
**Purpose**: Validate functional requirements
**Location**: `tests/test_federation_v2_acceptance.py`, `tests/test_operator_approval_v2_acceptance.py`
**Characteristics**:
- Business requirement validation
- Future implementation gates
- Strict xfail marking
- Comprehensive scenarios

### Golden Demo Tests
**Purpose**: Validate V1 core functionality end-to-end
**Location**: `tests/test_golden_demo_live.py`, `tests/test_golden_demo_flow.py`
**Characteristics**:
- Live NATS JetStream required
- V1 immutability validation
- Mandatory regression gate
- Production-like conditions

## V2 Acceptance Tests

### Current State: Strict XFAIL

All V2 acceptance tests are marked with `xfail(strict=True)` because Phase 2 implementation is not complete.

**Files and Gates:**

#### `tests/test_federation_v2_acceptance.py`
**Purpose**: Validate multi-cell federation capabilities
**Test Count**: 6 tests
**Xfail Reason**: "V2 federation not yet implemented (Phase 2). This is a future acceptance gate."

**Tests:**
1. `test_federation_formation` - Federation topology formation
2. `test_cross_cell_belief_aggregation` - Cross-cell belief correlation
3. `test_federation_quorum_computation` - Quorum and consensus algorithms
4. `test_federation_partition_tolerance` - Network partition handling
5. `test_federation_identity_and_trust` - Cell identity and trust management
6. `test_federation_audit_trail` - Federation audit consolidation

#### `tests/test_operator_approval_v2_acceptance.py`
**Purpose**: Validate operator control plane capabilities
**Test Count**: 8 tests
**Xfail Reason**: "V2 operator approval not yet implemented (Phase 2). This is a future acceptance gate."

**Tests:**
1. `test_operator_authentication` - Operator authentication and authorization
2. `test_a3_approval_workflow` - A3 threat response approval
3. `test_operator_authorization_levels` - Role-based access control
4. `test_emergency_response_procedure` - Emergency response coordination procedures
5. `test_control_plane_api_functionality` - Control plane API endpoints
6. `test_federation_approval_coordination` - Multi-cell approval coordination
7. `test_v1_compatibility_with_v2_disabled` - V1 compatibility validation
8. `test_control_plane_startup_shutdown` - Lifecycle management

### Phase 2 Transition

**When Phase 2 implementation begins:**
1. Implement V2 functionality according to contracts
2. Remove `xfail` markers as tests pass
3. Convert to real passing acceptance gates
4. Ensure strict governance compliance

**Process:**
```bash
# Run V2 acceptance tests
pytest tests/test_federation_v2_acceptance.py -v

# When tests pass (XPASS), remove xfail markers:
# 1. Edit test file
# 2. Remove @pytest.mark.xfail decorator
# 3. Commit change
# 4. Verify tests still pass
```

## Isolation Testing

### `tests/test_v2_feature_flag_isolation.py`

**Purpose**: Prove V2 modules cause zero side effects when disabled
**Test Count**: 7 tests
**Status**: ✅ All passing

**Invariants Protected:**
- V1 core behavior unchanged
- V2 imports cause no side effects
- V2 object instantiation is inert
- V2 method calls are no-op when disabled
- Memory cleanup works correctly
- Feature flags default to disabled
- enabled=True triggers NotImplementedError as expected

**Tests:**
1. `test_v2_imports_no_side_effects` - Import safety validation
2. `test_v2_objects_instantiation_no_side_effects` - Object creation safety
3. `test_v2_methods_no_side_effects` - Method call safety
4. `test_v2_feature_flags_all_disabled` - Default flag state validation
5. `test_v2_objects_shutdown_no_side_effects` - Cleanup safety
6. `test_v2_memory_cleanup` - Memory management validation
7. `test_v2_enabled_triggers_notimplementederror` - Proper error handling

**Running Isolation Tests:**
```bash
pytest tests/test_v2_feature_flag_isolation.py -v
# Expected: 7 passed, 0 failed
```

## Test Execution

### Full Test Suite
```bash
pytest -q
# Expected: 59 passed, 15 xfailed, 155 warnings
```

### V1 Core Tests
```bash
# Run V1 tests only (exclude V2 acceptance)
pytest -q --ignore=tests/test_federation_v2_acceptance.py --ignore=tests/test_operator_approval_v2_acceptance.py
# Expected: 51 passed, 2 xfailed, 0 failed, 0 errors, 0 skipped
```

### V2 Tests Only
```bash
# Run V2 acceptance tests (expected xfail)
pytest tests/test_federation_v2_acceptance.py tests/test_operator_approval_v2_acceptance.py -v
# Expected: 0 passed, 14 xfailed, 0 failed, 0 errors, 0 skipped

# Run V2 isolation tests (expected pass)
pytest tests/test_v2_feature_flag_isolation.py -v
# Expected: 7 passed, 0 failed
```

### Golden Demo Tests
```bash
# Live Golden Demo (mandatory gate)
pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
# Expected: 1 passed, 0 failed

# Mock Golden Demo (xfail - not acceptance)
pytest tests/test_golden_demo_flow.py::test_golden_demo_flow_mock -v
# Expected: 1 xfailed
```

## Test Data and Fixtures

### Test Fixtures Location
- **V1 Fixtures**: Defined in individual test files
- **V2 Fixtures**: Defined in acceptance test files
- **Golden Demo Fixtures**: Live NATS JetStream setup

### Test Data Management
- **Static Test Data**: `tests/fixtures/` (if exists)
- **Generated Test Data**: Created in test fixtures
- **External Dependencies**: Mocked or containerized

## Test Environment Setup

### Local Development
```bash
# Setup test environment
source venv/bin/activate
pip install -r requirements.txt

# Start NATS JetStream (required for Golden Demo)
docker-compose up -d

# Run tests
pytest -q
```

### CI/CD Environment
```bash
# CI test execution
pytest -q --tb=short
python scripts/validate_spec_refs.py
python scripts/audit_integrity.py
```

## Test Governance

### Binary Green Definition
**Green means exactly:**
- 0 failed tests
- 0 errors
- 0 skipped tests

### Test Writing Guidelines

#### Unit Tests
- Test single responsibility
- Use descriptive test names
- Mock external dependencies
- Assert specific behavior

#### Integration Tests
- Test component interactions
- Use real data flow
- Test error conditions
- Validate end-to-end scenarios

#### Acceptance Tests
- Test business requirements
- Use realistic scenarios
- Test edge cases
- Document expected behavior

#### Isolation Tests
- Test side-effect prevention
- Validate feature flag isolation
- Test memory management
- Ensure V1 immutability

### Test Maintenance

#### When Adding Features
1. Write unit tests for new components
2. Write integration tests for interactions
3. Update acceptance tests if V2 functionality
4. Verify isolation tests still pass
5. Ensure Golden Demo still passes

#### When Fixing Bugs
1. Write failing test reproducing bug
2. Fix implementation
3. Verify test passes
4. Run full test suite
5. Check for regressions

## Test Troubleshooting

### Common Issues

#### Test Failures
```bash
# Run with verbose output
pytest -v --tb=short

# Run specific failing test
pytest tests/path/to/test.py::test_name -v --tb=long
```

#### Golden Demo Failures
```bash
# Check NATS JetStream status
docker-compose ps

# Restart NATS if needed
docker-compose restart

# Run Golden Demo with debug output
pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v -s
```

#### V2 Isolation Failures
```bash
# Check feature flag state
python -c "from src.feature_flags import get_feature_flags; print(get_feature_flags().is_v2_federation_enabled())"

# Run isolation tests with detailed output
pytest tests/test_v2_feature_flag_isolation.py -v -s
```

This testing strategy ensures ExoArmur maintains reliability and safety while enabling controlled evolution through comprehensive test coverage and strict governance.
