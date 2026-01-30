# ExoArmur Build and Test Guide

This guide covers how to build, test, and validate ExoArmur ADMO V2.

## Quick Start

```bash
# Install in development mode (pip 24.0 required due to known pip 25.x regression)
pip install --upgrade pip -c constraints.txt
pip install -e .

# Run all tests
python -m pytest tests/

# Run verification script
python scripts/verify_all.py
```

## Phase 0E Complete: Protocol Enforcer Green

**Status: ✅ COMPLETE**
- All 8 protocol enforcer tests now pass (0 failures)
- Bounded failing quarantine removed
- Full green status achieved for protocol enforcement

### What Was Fixed
1. **API Signature Mismatches**: Fixed `FederateIdentityStore.update_handshake_session()` calls to use correct parameters
2. **Feature Flag Integration**: Added mock feature flags to enable V2 federation in tests
3. **Session Management**: Fixed session creation and state advancement logic
4. **Contract Compliance**: Added missing `step_index` field to `HandshakeSessionV1` model
5. **Test Expectations**: Corrected failure reason expectations to match actual behavior

## Phase 0D Boundary Enforcement

ExoArmur uses strict boundary enforcement to ensure determinism and prevent state leakage.

### Running Boundary Gates Locally

#### 1. Boundary Gate (Determinism + Fixture Scopes)
```bash
# Run the full boundary gate
python scripts/boundary_gate.py

# This runs:
# - Sensitive tests with randomized ordering (3 runs)
# - Fixture scope violation detection
# - Determinism verification
# - Identical result comparison
```

#### 2. Protocol Enforcer Boundary Check
```bash
# Check protocol enforcer failing set is bounded
python scripts/protocol_enforcer_boundary.py

# This verifies:
# - No new failures beyond known failing set
# - No silent behavior drift
# - Exact bounded failure enforcement
# Note: Now passes with 0 failures (all green)
```

#### 3. Test Collection Stability
```bash
# Verify test collection count is stable
python -m pytest --collect-only -q | tail -1
# Should show: "417 tests collected"
```

### Sensitive Test Markers

Tests that must be deterministic are marked with `@pytest.mark.sensitive`:

```python
import pytest

pytestmark = pytest.mark.sensitive

class TestMySensitiveComponent:
    def test_deterministic_behavior(self):
        # This test will be included in boundary gate
        pass
```

### Fixture Scope Rules

**Sensitive tests must use function-scoped fixtures** unless explicitly whitelisted:

```python
@pytest.fixture  # Function scope (default) - ✅ OK
def my_fixture():
    return SomeObject()

@pytest.fixture(scope="class")  # ❌ NOT ALLOWED in sensitive tests
def class_scoped_fixture():
    return SomeObject()
```

### Adding New Sensitive Tests

1. Mark the test class or module with `@pytest.mark.sensitive`
2. Use only function-scoped fixtures
3. Ensure deterministic behavior (no random values, fixed time)
4. Test passes boundary gate locally

### Updating Known Failing Lists

**No longer needed for protocol enforcer** - all tests now pass.

For other components with bounded failures:
1. Run the boundary check: `python scripts/protocol_enforcer_boundary.py`
2. If it reports "TESTS FIXED", update the known failing list
3. Remove fixed tests from the known failing list

### CI Integration

The CI pipeline includes:
- **Boundary Gate**: Runs on every PR and push
- **Protocol Enforcer Boundary**: Ensures 0 failures (all green)
- **Test Collection Stability**: Verifies 417 tests collected
- **Full Test Suite**: Runs on main branch pushes

### Troubleshooting

#### Boundary Gate Failures

**Fixture Scope Violation:**
```
FIXTURE SCOPE VIOLATION in test_module.py::TestClass::test_method:
Fixture 'my_fixture' has scope='class' but sensitive tests require scope='function'
```

**Fix:** Change fixture to function scope or add to whitelist in `conftest.py`.

**Determinism Failure:**
```
Results differ between runs
Only in run 2: test_module.py::TestClass::test_method
```

**Fix:** Check for non-deterministic behavior (random values, time dependencies, etc.).

#### Protocol Enforcer Failures

**New Failures:**
```
❌ NEW FAILURES DETECTED:
  test_protocol_enforcer.py::TestProtocolEnforcer::new_test_method
```

**Fix:** Investigate the new failure and either:
1. Fix the underlying issue, or
2. Add to known failing list with justification

**Tests Fixed:**
```
✅ TESTS FIXED:
  test_protocol_enforcer.py::TestProtocolEnforcer::old_test_method
```

**Fix:** Update known failing list to remove fixed tests.

## Development Workflow

1. Make changes
2. Run boundary gate locally: `python scripts/boundary_gate.py`
3. Run protocol enforcer check: `python scripts/protocol_enforcer_boundary.py`
4. If both pass, commit and push
5. CI will run the same checks automatically

## Test Categories

### Sensitive Tests (Must Be Deterministic)
- Federation crypto operations
- Handshake controller flows
- Identity audit emission
- Protocol enforcement ✅ **NOW GREEN**
- Any stateful component tests

### Boundary Tests
- Verify boundary enforcement rules
- Test fixture scope compliance
- Validate isolation mechanisms

### Integration Tests
- External system dependencies
- Full workflow tests
- Performance benchmarks

## Dependencies

Required for Phase 0D boundary enforcement:
- `pytest-randomly>=3.15.0` - Test randomization
- `pytest-timeout>=2.2.1` - Per-test timeouts
- `pytest-json-report>=1.5.0` - JSON reporting for analysis

## Strict Settings

Boundary gate uses these strict settings:
- `-W error` - Warnings as errors
- `--strict-markers` - Fail on unregistered markers
- `--timeout=300` - 5 minute per-test timeout
- `--randomly-seed` - Deterministic randomization

## Protocol Enforcer Status

- **Tests**: 8 total, 8 passing, 0 failing ✅
- **Status**: FULL GREEN
- **Bounded Quarantine**: REMOVED (no longer needed)
- **Last Updated**: Phase 0E complete
