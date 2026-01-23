# Phase -0.5 Identity Audit Emitter - Remaining Failure Signatures

## Summary
4 failing tests in Identity Audit Emitter bucket requiring fixes to achieve 10/10 passing.

## Failure Signatures

### 1. test_emit_diagnostic_event_when_disabled
- **Exact assertion**: `Expected 'log_event' to have been called once. Called 0 times.`
- **Expected audit call**: `mock_audit_logger.log_event.assert_called_once()`
- **Actual calls**: 0 calls to log_event
- **Feature flag state**: `mock_feature_checker = Mock(return_value=False)` (V2 federation disabled)
- **Test expectation**: When V2 federation is disabled, should emit diagnostic event "federation.identity.disabled"

### 2. test_create_event_handler  
- **Exact assertion**: `Expected 'log_event' to have been called once. Called 0 times.`
- **Expected audit call**: `mock_audit_logger.log_event.assert_called_once()`
- **Actual calls**: 0 calls to log_event
- **Feature flag state**: Not explicitly set (defaults to disabled)
- **Test expectation**: Event handler creation should trigger audit logging

### 3. test_emit_event_error_handling
- **Test status**: ERROR - test method not found/missing
- **Expected behavior**: Test error handling during event emission
- **Feature flag state**: `mock_feature_checker = Mock(return_value=True)` (V2 federation enabled)
- **Test expectation**: Should handle audit interface errors gracefully and emit failure events

### 4. test_audit_emitter_respects_feature_flags
- **Exact assertion**: `assert 0 == 1`
- **Expected audit call**: `assert mock_audit_logger_disabled.log_event.call_count == 1`
- **Actual calls**: 0 calls when feature flag disabled
- **Feature flag state**: Two test cases - disabled (`lambda: False`) and enabled (`lambda: True`)
- **Test expectation**: 
  - When disabled: emit 1 diagnostic event
  - When enabled: emit 1 functional event
  - Different event types between disabled/enabled states

## Root Cause Analysis

All failures share the same root cause: **tests are using `mock_audit_logger` but passing `NoOpAuditInterface()` to the emitter**. The tests expect to mock audit calls but the emitter is using a no-op interface that doesn't track calls.

## Required Fixes

1. **Fix test mocking patterns**: Tests should mock the actual audit interface passed to emitter
2. **Implement diagnostic event emission**: When feature flags are disabled, emit diagnostic events
3. **Add error handling**: Implement proper error handling for audit interface failures
4. **Ensure feature flag gating**: Functional vs diagnostic events based on flag state

## Test Pattern Issues

The tests follow this incorrect pattern:
```python
mock_audit_logger = Mock()
emitter = IdentityAuditEmitter(
    audit_interface=NoOpAuditInterface(),  # ❌ Should use mock_audit_logger
    feature_flag_checker=mock_feature_checker
)
```

Should be:
```python
mock_audit_interface = Mock()
emitter = IdentityAuditEmitter(
    audit_interface=mock_audit_interface,  # ✅ Use the mock
    feature_flag_checker=mock_feature_checker
)
```
