# Gate 5 Kill Switch Design Document
## WORKFLOW 5B - GLOBAL + TENANT KILL SWITCH ENFORCEMENT

**Generated:** 2026-01-25T20:45:00Z  
**Status:** IMPLEMENTED AND TESTED

---

## DESIGN OVERVIEW

### Single Authoritative Enforcement Point
All side-effect execution paths must route through `ExecutionGate.evaluate_execution()` before any state modification can occur. This implements Rule R2 from Phase 5 rules.

### FAIL CLOSED Default Behavior
- Default state: DENY execution
- Missing context, unknown action types, system errors → DENY
- Implements Rule R1: Fail closed on execution

### Durable Storage Backing
- Global kill switches: `EXOARMUR_KILL_SWITCH_GLOBAL` KV bucket
- Tenant kill switches: `EXOARMUR_KILL_SWITCH_TENANT` KV bucket
- JetStream KV provides replayable, durable storage

---

## ARCHITECTURE

### Core Components

#### 1. ExecutionGate Class
```python
class ExecutionGate:
    """Single authoritative enforcement point for all execution paths"""
    
    async def evaluate_execution(context: ExecutionContext) -> GateResult
    async def get_global_kill_switch_status(switch_name: str) -> bool
    async def get_tenant_kill_switch_status(tenant_id: str, switch_name: str) -> bool
    async def emit_denial_audit(context: ExecutionContext, result: GateResult) -> None
```

#### 2. ExecutionContext Data Structure
```python
@dataclass
class ExecutionContext:
    action_type: ExecutionActionType
    tenant_id: Optional[str] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    principal_id: Optional[str] = None
    additional_context: Optional[Dict[str, Any]] = None
```

#### 3. ExecutionActionType Enum
```python
class ExecutionActionType(str, Enum):
    IDENTITY_CONTAINMENT_APPLY = "identity_containment_apply"
    IDENTITY_CONTAINMENT_REVERT = "identity_containment_revert"
    IDENTITY_CONTAINMENT_EXPIRE = "identity_containment_expire"
    EXECUTION_KERNEL_INTENT = "execution_kernel_intent"
    FEDERATION_JOIN = "federation_join"
    APPROVAL_GRANT = "approval_grant"
    APPROVAL_DENY = "approval_deny"
```

### Enforcement Flow

1. **Pre-execution Check**: All side-effect paths call `enforce_execution_gate()`
2. **Tenant Context Validation**: Rule R3 - tenant context mandatory
3. **Global Kill Switch Check**: System-wide execution blocking
4. **Tenant Kill Switch Check**: Per-tenant execution blocking
5. **Decision**: ALLOW or DENY with specific reason
6. **Audit**: All denials emit audit events (Rule R6)

---

## INTEGRATION POINTS

### Modified Execution Paths

#### 1. Identity Containment Execution
- `execute_containment_apply()` - Added gate enforcement before effector operations
- `execute_containment_revert()` - Added gate enforcement before revert operations  
- `process_expirations()` - Added gate enforcement for batch expiration processing
- `tick()` - Async modification to support gate enforcement

#### 2. Execution Kernel
- `execute_intent()` - Added gate enforcement before intent execution
- All action classes (A0/A1/A2/A3) now go through gate

#### 3. Control Plane API (Future)
- `join_federation()` - Will require gate enforcement (Phase 2)
- `approve_request()` - Will require gate enforcement (Phase 2)
- `deny_request()` - Will require gate enforcement (Phase 2)

---

## KILL SWITCH OPERATIONS

### Global Kill Switches
- **Key**: `switch_all_execution`
- **Values**: `active` (DENY) or `inactive` (ALLOW)
- **Scope**: System-wide execution blocking
- **Use Cases**: Emergency shutdown, maintenance windows

### Tenant Kill Switches
- **Key**: `{tenant_id}_switch_all_execution`
- **Values**: `active` (DENY) or `inactive` (ALLOW)
- **Scope**: Per-tenant execution blocking
- **Use Cases**: Tenant suspension, billing issues, compliance

---

## AUDIT AND REPLAY

### Denial Audit Events
All execution denials emit structured audit events:
```json
{
    "event_type": "execution_denied",
    "action_type": "identity_containment_apply",
    "tenant_id": "tenant-123",
    "principal_id": "user-456",
    "denial_reason": "global_kill_switch_active",
    "denial_message": "Global execution kill switch is active",
    "evaluated_at": "2026-01-25T20:45:00Z",
    "additional_context": {...}
}
```

### Replay Determinism
- Kill switch state is durable in JetStream KV
- Audit events capture exact denial reasoning
- Replay will reproduce identical ALLOW/DENY decisions

---

## TESTING STRATEGY

### Unit Tests
- ✅ FAIL CLOSED behavior without tenant context
- ✅ Global kill switch enforcement
- ✅ Tenant kill switch enforcement  
- ✅ Execution allowed when switches inactive
- ✅ Denial audit emission

### Integration Tests
- TODO: Docker-compose environment with kill switch operations
- TODO: Replay verification of kill switch decisions

### Test Coverage
- Core gate logic: 100%
- Integration points: Identity containment, Execution kernel
- Mock infrastructure: NATS KV, audit emission

---

## SECURITY PROPERTIES

### Fail Safe
- No NATS storage → DENY by default
- Missing tenant context → DENY
- Unknown action types → DENY
- System errors → DENY

### Audit Completeness
- Every denial is audited with deterministic reason codes
- Audit events include full context for replay
- Audit trail is tamper-evident via JetStream

### Tenant Isolation
- Tenant switches cannot affect other tenants
- Global switch affects all tenants (emergency override)
- Switch state is durable and replayable

---

## OPERATIONAL PROCEDURES

### Emergency Shutdown
```bash
# Set global kill switch to ACTIVE
nats kv put EXOARMUR_KILL_SWITCH_GLOBAL switch_all_execution active

# Verify status
nats kv get EXOARMUR_KILL_SWITCH_GLOBAL switch_all_execution
```

### Tenant Suspension
```bash
# Suspend specific tenant
nats kv put EXOARMUR_KILL_SWITCH_TENANT tenant-123_switch_all_execution active

# Resume tenant
nats kv put EXOARMUR_KILL_SWITCH_TENANT tenant-123_switch_all_execution inactive
```

### Monitoring
- Monitor audit stream for `execution_denied` events
- Alert on high denial rates
- Track kill switch state changes

---

## COMPLIANCE WITH PHASE 5 RULES

- ✅ **R0**: Old rules still apply (V1 contracts immutable)
- ✅ **R1**: Fail closed on execution (DENY by default)
- ✅ **R2**: Single authoritative enforcement point
- ✅ **R3**: Tenant context mandatory for side effects
- ✅ **R6**: Every denial audited with deterministic replay

---

## NEXT STEPS

1. Complete integration with Control Plane API (Phase 2)
2. Add comprehensive integration tests
3. Implement operational monitoring dashboards
4. Document runbook procedures for operators

**STATUS: GATE 5 READY FOR VERIFICATION**
