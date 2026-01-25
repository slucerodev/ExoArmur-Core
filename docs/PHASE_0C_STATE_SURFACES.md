# Phase 0C State Surface Inventory

This document identifies all mutable/shared state across src/ and tests/ that could cause cross-test leakage.

## Critical State Surfaces

### 1. FederateIdentityStore
**File**: `src/federation/federate_identity_store.py`
**State Held**:
- `_identities: Dict[str, FederateIdentityV1]` - federate_id -> identity
- `_nonces: Dict[str, NonceRecord]` - nonce -> NonceRecord  
- `_active_sessions: Dict[str, HandshakeSessionV1]` - session_id -> session
**Current Lifecycle**: Instance-level (created per use)
**Recommended Lifecycle**: Function-scoped fixture `fresh_identity_store` ✅ ALREADY IMPLEMENTED

### 2. HandshakeStateMachine
**File**: `src/federation/handshake_state_machine.py`
**State Held**:
- `_sessions: Dict[str, HandshakeSessionV1]` - correlation_id -> session
- `_correlation_ids: Dict[str, str]` - federate_id -> correlation_id
- `_transitions: List[HandshakeTransition]` - transition history
- `_locked_correlation_ids: Dict[str, datetime]` - correlation_id -> lock expiry
**Current Lifecycle**: Instance-level (created per use)
**Recommended Lifecycle**: Function-scoped fixture (needs implementation)

### 3. ObservationStore
**File**: `src/federation/observation_store.py`
**State Held**: In-memory observation cache
**Current Lifecycle**: Unknown (needs investigation)
**Recommended Lifecycle**: Function-scoped fixture

### 4. ArbitrationStore
**File**: `src/federation/arbitration_store.py`
**State Held**: Arbitration records and state
**Current Lifecycle**: Unknown (needs investigation)
**Recommended Lifecycle**: Function-scoped fixture

### 5. FeatureFlags
**File**: `src/feature_flags/feature_flags.py`
**State Held**: Global feature flag state
**Current Lifecycle**: Module-level singleton (⚠️ RISK)
**Recommended Lifecycle**: Injected instance via constructor

## Lower Risk State Surfaces

### 6. ReplayEngine
**File**: `src/replay/replay_engine.py`
**State Held**: Replay cache and state
**Current Lifecycle**: Instance-level
**Recommended Lifecycle**: Function-scoped fixture if used in tests

### 7. SafetyGate
**File**: `src/safety/safety_gate.py`
**State Held**: Safety policy cache
**Current Lifecycle**: Instance-level
**Recommended Lifecycle**: Function-scoped fixture if used in tests

### 8. Audit Emitters
**Files**: 
- `src/federation/identity_audit_emitter.py`
- `src/federation/coordination/coordination_audit_emitter.py`
**State Held**: Audit event buffers
**Current Lifecycle**: Instance-level
**Recommended Lifecycle**: Function-scoped fixture if stateful

## Test Fixture Analysis

### Already Properly Isolated ✅
- `fresh_identity_store` - Function-scoped, fresh per test
- `fresh_protocol_enforcer` - Function-scoped, fresh per test
- `fixed_clock` - Function-scoped, deterministic time
- `mock_feature_flags_enabled/disabled` - Function-scoped

### Need Investigation ⚠️
- HandshakeStateMachine usage in tests
- ObservationStore fixtures
- ArbitrationStore fixtures
- Any module-level instantiations

## Leakage Risk Assessment

### HIGH RISK
1. **FeatureFlags singleton** - Global state affects all tests
2. **HandshakeStateMachine** - Session state could leak between tests
3. **Store classes without function fixtures** - In-memory state persistence

### MEDIUM RISK
1. **Audit emitters** - Event buffers might accumulate
2. **ReplayEngine** - Cache persistence across tests

### LOW RISK
1. **Configuration objects** - Typically immutable
2. **Utility classes** - Usually stateless

## Action Items

### Immediate (Phase 0C)
1. **Audit HandshakeStateMachine usage** - Ensure function-scoped fixtures
2. **Check FeatureFlags usage** - Convert to dependency injection
3. **Verify store fixtures** - Ensure all stores use function scope

### Future (Phase 0D+)
1. **Consider store interface abstraction** - For better testability
2. **Implement state leak detection** - Diagnostic helpers for tests
3. **Add deterministic reset methods** - Where shared state is unavoidable
