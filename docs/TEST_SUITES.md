# ExoArmur Test Suites

This document defines the explicit test suites for ExoArmur ADMO V2.

## Test Suite Definitions

### verify_core
**Purpose**: Constitutional + always-run suite  
**Scope**: Core constitutional tests that must always pass  
**Command**: `python3 -m pytest tests/ -m "not integration and not slow"`  
**Gates**: All core functionality, basic invariants, and constitutional boundaries  
**Excludes**: Integration tests, slow tests, external dependencies  

### verify_all  
**Purpose**: Full suite, no ignores  
**Scope**: All tests including integration and slow tests  
**Command**: `python3 -m pytest tests/`  
**Gates**: Complete system functionality including external integrations  
**Includes**: All test categories, no exclusions  

### verify_integration
**Purpose**: External deps only  
**Scope**: Tests requiring external systems, network calls, or services  
**Command**: `python3 -m pytest tests/ -m integration`  
**Gates**: External system integrations, API endpoints, database connections  
**Markers**: `@pytest.mark.integration`  

## Test Categories

### Constitutional Tests (verify_core)
- Authority boundaries
- Approval binding
- Audit integrity  
- Replay determinism
- Federation crypto
- Handshake protocols
- Arbitration precedence
- Safety gate enforcement

### Integration Tests (verify_integration)
- API endpoints
- External service calls
- Database operations
- Network communications
- Third-party integrations

### Slow Tests
- Performance benchmarks
- Load testing
- End-to-end workflows
- Large dataset processing

## CI/Gating Usage

### Primary Gate: verify_all
- Used in main CI pipeline
- Must pass for all PRs
- Binary green requirement

### Fast Feedback: verify_core
- Used for quick PR validation
- Runs on every commit
- Constitutional invariants only

### Integration Gate: verify_integration
- Runs after verify_core passes
- External dependency validation
- Staging environment testing

## Markers Reference

```python
@pytest.mark.integration  # Requires external systems
@pytest.mark.slow         # Takes >10 seconds
@pytest.mark.unit          # Fast unit test (default)
```

## Execution Requirements

- All suites must run from any working directory
- Clean venv installation must work: `pip install -e .`
- No PYTHONPATH or cwd dependencies
- Deterministic test ordering and results
