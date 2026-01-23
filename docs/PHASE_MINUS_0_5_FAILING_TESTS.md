# Phase -0.5 Failing Tests Inventory

## Summary
- **Total Tests**: 360
- **Passing**: 307  
- **Failing**: 45
- **Skipped**: 31
- **Pass Rate**: 85.3%

## Failing Test Inventory

| Test Node ID | File | Subsystem | Invariant Protected | Failure Signature | Root Cause Bucket |
|-------------|------|-----------|-------------------|------------------|------------------|
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_emit_diagnostic_event_when_disabled` | test_identity_audit_emitter.py | Identity Audit Emitter | Diagnostic event emission when V2 disabled | `Expected 'log_event' to have been called once. Called 0 times.` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_create_event_handler` | test_identity_audit_emitter.py | Identity Audit Emitter | Event handler creation | `Expected 'log_event' to have been called once. Called 0 times.` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_get_audit_trail_enabled` | test_identity_audit_emitter.py | Identity Audit Emitter | Audit trail retrieval when enabled | `assert trail is not None` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_get_audit_trail_without_audit_logger` | test_identity_audit_emitter.py | Identity Audit Emitter | Audit trail fallback without logger | `'NoOpAuditInterface' object has no attribute 'get_events'` | A) API signature mismatch |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_validate_audit_integrity_success` | test_identity_audit_emitter.py | Identity Audit Emitter | Audit integrity validation | `'NoOpAuditInterface' object has no attribute 'get_events'` | A) API signature mismatch |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_validate_audit_integrity_step_count_mismatch` | test_identity_audit_emitter.py | Identity Audit Emitter | Step count validation | `KeyError: 'step_count_valid'` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_validate_audit_integrity_duplicate_idempotency_keys` | test_identity_audit_emitter.py | Identity Audit Emitter | Idempotency key validation | `KeyError: 'idempotency_valid'` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_validate_audit_integrity_chronological_violation` | test_identity_audit_emitter.py | Identity Audit Emitter | Chronological validation | `KeyError: 'chronological_valid'` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestIdentityAuditEmitter::test_emit_event_error_handling` | test_identity_audit_emitter.py | Identity Audit Emitter | Error handling in audit emission | `assert True is False` | C) Audit envelope incompatibility |
| `tests/test_identity_audit_emitter.py::TestFeatureFlagIsolation::test_audit_emitter_respects_feature_flags` | test_identity_audit_emitter.py | Identity Audit Emitter | Feature flag enforcement | `assert 0 == 1` | F) Feature flag gating incorrect |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_correlation_id_locking` | test_handshake_state_machine.py | Handshake State Machine | Correlation ID locking after completion | `assert False` | H) Real bug (logic incorrect) |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_terminal_state_transition_rejection` | test_handshake_state_machine.py | Handshake State Machine | Terminal state transition rejection | `assert not True` | H) Real bug (logic incorrect) |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_failure_handshake` | test_handshake_state_machine.py | Handshake State Machine | Failure handshake state management | `TypeError: HandshakeStateMachine.fail_handshake() missing 1 required positional argument: 'audit_event'` | A) API signature mismatch |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_retry_count_increment` | test_handshake_state_machine.py | Handshake State Machine | Retry count tracking | `TypeError: HandshakeStateMachine.fail_handshake() missing 1 required positional argument: 'audit_event'` | A) API signature mismatch |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_retry_delay_calculation` | test_handshake_state_machine.py | Handshake State Machine | Retry delay calculation | `TypeError: HandshakeStateMachine.fail_handshake() missing 1 required positional argument: 'audit_event'` | A) API signature mismatch |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_cleanup_expired_sessions` | test_handshake_state_machine.py | Handshake State Machine | Expired session cleanup | `assert 3 == 1` | H) Real bug (logic incorrect) |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_get_active_sessions` | test_handshake_state_machine.py | Handshake State Machine | Active session tracking | `TypeError: HandshakeStateMachine.fail_handshake() missing 1 required positional argument: 'audit_event'` | A) API signature mismatch |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_get_session_statistics` | test_handshake_state_machine.py | Handshake State Machine | Session statistics | `TypeError: HandshakeStateMachine.fail_handshake() missing 1 required positional argument: 'audit_event'` | A) API signature mismatch |
| `tests/test_handshake_state_machine.py::TestHandshakeStateMachine::test_federate_to_correlation_mapping` | test_handshake_state_machine.py | Handshake State Machine | Federate-to-correlation mapping | `assert 'corr-12345' is None` | H) Real bug (logic incorrect) |
| `tests/test_coordination_models_v2.py::TestCoordinationModels::test_coordination_observation_confidence_validation` | test_coordination_models_v2.py | Coordination Models | Confidence validation | `AssertionError: Regex pattern did not match` | B) Contract model mismatch |
| `tests/test_coordination_models_v2.py::TestCoordinationModels::test_coordination_session_expiration` | test_coordination_models_v2.py | Coordination Models | Session expiration | `pydantic_core._pydantic_core.ValidationError: 1 validation error for CoordinationSession` | B) Contract model mismatch |
| `tests/test_coordination_models_v2.py::TestCoordinationModels::test_coordination_event_idempotency_key` | test_coordination_models_v2.py | Coordination Models | Event idempotency | `AssertionError: assert '3d90a5ca087b...5aa19c5868618' == '2a8c30c21a09...7ab9b9c3e07a4'` | G) Ordering/canonicalization/hash mismatch |
| `tests/test_coordination_state_machine.py::TestCoordinationStateMachine::test_create_announcement_invalid_expiration` | test_coordination_state_machine.py | Coordination State Machine | Invalid expiration rejection | `pydantic_core._pydantic_core.ValidationError: 1 validation error for CoordinationAnnouncement` | B) Contract model mismatch |
| `tests/test_coordination_state_machine.py::TestCoordinationStateMachine::test_add_observation_success` | test_coordination_state_machine.py | Coordination State Machine | Observation addition | `AssertionError: assert 'cell-2' in []` | H) Real bug (logic incorrect) |
| `tests/test_coordination_state_machine.py::TestCoordinationStateMachine::test_get_active_coordinations` | test_coordination_state_machine.py | Coordination State Machine | Active coordination tracking | `assert 0 == 1` | H) Real bug (logic incorrect) |
| `tests/test_federate_identity_store_old.py::TestFederateIdentityStore::test_store_and_retrieve_identity` | test_federate_identity_store_old.py | Legacy Federation | Identity persistence | `assert None is not None` | H) Real bug (logic incorrect) |
| `tests/test_federate_identity_store_old.py::TestFederateIdentityStore::test_list_identities` | test_federate_identity_store_old.py | Legacy Federation | Identity enumeration | `assert 0 == 3` | H) Real bug (logic incorrect) |
| `tests/test_federate_identity_store_old.py::TestFederateIdentityStore::test_update_identity` | test_federate_identity_store_old.py | Legacy Federation | Identity updates | `assert None is not None` | H) Real bug (logic incorrect) |
| `tests/test_federate_identity_store_old.py::TestFederateIdentityStore::test_delete_identity` | test_federate_identity_store_old.py | Legacy Federation | Identity deletion | `AssertionError: assert None is not None` | H) Real bug (logic incorrect) |
| `tests/test_federate_identity_store_old.py::TestFederateIdentityStore::test_get_statistics` | test_federate_identity_store_old.py | Legacy Federation | Statistics tracking | `AttributeError: 'FederateIdentityStore' object has no attribute 'get_statistics'` | A) API signature mismatch |
| `tests/test_federation_crypto_tightened.py::TestProtocolEnforcement::test_valid_message_passes_enforcement` | test_federation_crypto_tightened.py | Federation Crypto | Tightened enforcement | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestProtocolEnforcement::test_invalid_signature_is_rejected` | test_federation_crypto_tightened.py | Federation Crypto | Tightened enforcement | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestProtocolEnforcement::test_nonce_reuse_is_rejected` | test_federation_crypto_tightened.py | Federation Crypto | Tightened enforcement | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestProtocolEnforcement::test_timestamp_skew_is_rejected` | test_federation_crypto_tightened.py | Federation Crypto | Tightened enforcement | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestProtocolEnforcement::test_future_timestamp_skew_is_rejected` | test_federation_crypto_tightened.py | Federation Crypto | Tightened enforcement | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestFeatureFlagIsolation::test_no_import_time_flag_evaluation` | test_federation_crypto_tightened.py | Federation Crypto | Feature flag isolation | Various failures | F) Feature flag gating incorrect |
| `tests/test_federation_crypto_tightened.py::TestFeatureFlagIsolation::test_nonce_store_isolated_between_tests` | test_federation_crypto_tightened.py | Federation Crypto | Test isolation | Various failures | E) Store state leakage |
| `tests/test_federation_crypto_tightened.py::TestDeterministicTime::test_timestamp_validation_uses_injected_clock` | test_federation_crypto_tightened.py | Federation Crypto | Deterministic time | Various failures | D) Clock/deterministic time violations |
| `tests/test_handshake_controller.py::TestHandshakeController::test_handshake_fails_without_signature` | test_handshake_controller.py | Handshake Controller | Signature validation | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_handshake_fails_on_nonce_reuse` | test_handshake_controller.py | Handshake Controller | Nonce reuse protection | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_handshake_reaches_confirmed_on_valid_sequence` | test_handshake_controller.py | Handshake Controller | Valid sequence completion | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_handshake_stops_after_failed_identity` | test_handshake_controller.py | Handshake Controller | Failure state handling | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_handshake_retry_backoff_enforced` | test_handshake_controller.py | Handshake Controller | Retry backoff | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_replay_reproduces_handshake_state_transitions` | test_handshake_controller.py | Handshake Controller | Replay determinism | Various failures | A) API signature mismatch |
| `tests/test_handshake_controller.py::TestHandshakeController::test_protocol_error_handling` | test_handshake_controller.py | Handshake Controller | Protocol error handling | Various failures | A) API signature mismatch |

## Root Cause Bucket Summary

### A) API Signature Mismatch (15 tests)
- Missing `audit_event` parameter in `fail_handshake()` method
- Missing `get_events()` method in `NoOpAuditInterface`
- Various controller API signature issues

### B) Contract Model Mismatch (3 tests)
- Pydantic validation errors in coordination models
- Confidence validation regex pattern failures

### C) Audit Envelope Incompatibility (7 tests)
- Missing audit envelope fields (`step_count_valid`, `idempotency_valid`, `chronological_valid`)
- Wrong event types/payload shapes
- Diagnostic events not emitted properly

### D) Clock/Deterministic Time Violations (1 test)
- Timestamp validation not using injected clock

### E) Store State Leakage (1 test)
- Nonce store not isolated between tests

### F) Feature Flag Gating Incorrect (7 tests)
- V2 federation not properly enabled in tightened crypto tests
- Import-time flag evaluation issues

### G) Ordering/Canonicalization/Hash Mismatch (1 test)
- Idempotency key hash differences

### H) Real Bug (Logic Incorrect) (10 tests)
- Correlation ID locking logic errors
- Terminal state transition logic errors
- Session cleanup logic errors
- Legacy federate store implementation gaps

## Fix Order Priority

1. **IDENTITY AUDIT EMITTER** (10 tests) - Buckets A, C, F
2. **HANDSHAKE STATE MACHINE** (10 tests) - Buckets A, H  
3. **COORDINATION VALIDATION** (6 tests) - Buckets B, H, G
4. **AUTHORITY ENFORCEMENT + APPROVAL BINDING** (19 tests) - Buckets A, D, E, F, H
