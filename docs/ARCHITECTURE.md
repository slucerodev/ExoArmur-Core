# ExoArmur Core Architecture

## Overview

ExoArmur is a minimal deterministic governance kernel that provides a governance boundary for autonomous execution. The kernel enforces policy gates, produces cryptographic audit trails, and enables deterministic replay verification.

## Kernel Architecture

The kernel consists of a single execution boundary pipeline:

```
ActionIntent → ProxyPipeline → PolicyDecisionPoint → SafetyGate → Executor → ExecutionTrace → Audit
```

**Kernel Components:**
- **Boundary** (`kernel/boundary.py`): Minimal routing for Intent → Policy → Safety → Executor → Audit
- **Clock** (`kernel/clock.py`): Clock abstraction with deterministic time for replay
- **IDs** (`kernel/ids.py`): Deterministic ULID generation for governance entities
- **Trust Evaluator** (`kernel/trust_evaluator.py`): Formal interface (raises NotImplementedError)

**Executors:**
- **FileSystemExecutor** (`executors/file_system_executor.py`): File operations with rollback
- **DatabaseExecutor** (`executors/database_executor.py`): SQLite operations with transaction rollback

## Determinism Architecture

### Clock Abstraction

The kernel uses a controlled clock abstraction to separate wall-clock time from replay time:

```python
# Deterministic clock for core replay
def utc_now() -> datetime:
    """Get current UTC time using global clock"""
    return get_clock().utc_now()

# Clock implementations
class SystemClock:
    """Production clock using system time"""
    def utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

class DeterministicClock:
    """Deterministic clock for testing/replay"""
    def utc_now(self) -> datetime:
        return self._current_time  # Fixed or sequenced
```

### Canonical JSON

All state serialization uses canonical JSON (sorted keys, no whitespace) to ensure hash consistency:

```python
canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
hash = hashlib.sha256(canonical.encode()).hexdigest()
```

## ML Isolation

The kernel has **zero ML in the authority path**. All decision-making is deterministic and rule-based.

| Component | ML Status | Reason |
|-----------|-----------|--------|
| `PolicyDecisionPoint.evaluate()` | ❌ Prohibited | Binding decisions must be deterministic |
| `SafetyGate.evaluate_safety()` | ❌ Prohibited | Safety gate uses deterministic state machine |
| `ProxyPipeline.execute_with_trace()` | ❌ Prohibited | Execution path must be deterministic |
| `AuditEmitter.emit_audit_event()` | ❌ Prohibited | Audit chain requires cryptographic integrity |

## Air-Gap Integrity

The **kernel** (`kernel/` + `executors/` packages) has **zero network dependencies**:

- No network calls in the kernel execution path
- No external dependencies for core decisions
- Importable as a pure Python library
- Verified via dependency audit

Scope note: the optional `exoarmur.api` FastAPI layer and `scripts/` utilities are
separate from the kernel and do use web frameworks; the air-gap claim applies to
the kernel packages only.

## ASCII Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │         External Systems            │
                    │                                     │
                    │  ┌─────────────┐  ┌───────────────┐ │
                    │  │   Agents    │  │   Automation  │ │
                    │  └─────────────┘  └───────────────┘ │
                    └─────────────────────────────────────┘
                                ↕
                    ┌─────────────────────────────────────┐
                    │      ExoArmur Kernel (~1,800 lines)  │
                    │                                     │
                    │  ┌─────────────────────────────────┐ │
                    │  │      ProxyPipeline             │ │
                    │  │                                 │ │
                    │  │  ActionIntent                   │ │
                    │  │       ↓                         │ │
                    │  │  PolicyDecisionPoint            │ │
                    │  │       ↓                         │ │
                    │  │  SafetyGate                     │ │
                    │  │       ↓                         │ │
                    │  │  Executor                       │ │
                    │  │       ↓                         │ │
                    │  │  ExecutionTrace                │ │
                    │  │       ↓                         │ │
                    │  │  Audit                          │ │
                    │  └─────────────────────────────────┘ │
                    │                                     │
                    │  ┌─────────────────────────────────┐ │
                    │  │     Executors                  │ │
                    │  │                                 │ │
                    │  │  • FileSystemExecutor            │ │
                    │  │  • DatabaseExecutor             │ │
                    │  └─────────────────────────────────┘ │
                    └─────────────────────────────────────┘
                                ↕
                    ┌─────────────────────────────────────┐
                    │         Target Systems              │
                    │                                     │
                    │  ┌─────────────┐  ┌───────────────┐ │
                    │  │  File System│  │   Databases   │ │
                    │  └─────────────┘  └───────────────┘ │
                    └─────────────────────────────────────┘
```

## Component Interactions

### Execution Flow
1. **Intent Creation**: External system creates ActionIntent
2. **Policy Evaluation**: PolicyDecisionPoint evaluates against rules
3. **Safety Check**: SafetyGate enforces deterministic constraints
4. **Executor Dispatch**: Executor performs the operation
5. **Trace Recording**: ExecutionTrace records all events
6. **Audit Emission**: Audit event emitted with canonical record

> **Current limitation (2.2.0 baseline):** `ProxyPipeline.execute_with_trace()`
> currently constructs its safety-evaluation state (`policy_verified`, trust
> score, kill switches, required approval) from hardcoded placeholder values,
> and no durable kill-switch store exists. These inputs are scheduled to be
> replaced by trusted application configuration — see
> [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

### Rollback Flow
1. **Pre-execution**: Rollback plan computed for reversible actions
2. **Execution**: Operation performed
3. **Failure Detection**: If execution fails, rollback triggered
4. **State Restoration**: Original state restored via rollback plan
5. **Hash Verification**: Restored state hash verified against original

## Data Flow Boundaries

### Kernel Internal Data
- Remains within kernel boundary
- Never exposed to external systems
- Protected by cryptographic hashing

### Executor Data
- Flows through ProxyPipeline only
- Executors are untrusted capability modules
- Cannot access governance components

## Safety and Reliability

### Kernel Safety Guarantees
- Deterministic policy evaluation
- Zero external dependencies for core decisions
- Immediate response capability
- Complete audit trail with cryptographic proof

### Executor Constraints
- Cannot bypass policy/safety checks
- Cannot modify governance state
- Must declare capabilities via standardized schema
- Strictly sandboxed within ProxyPipeline

This architecture ensures ExoArmur maintains deterministic governance capabilities with minimal complexity and zero external dependencies.

