# ExoArmur Architecture Overview

## Execution Pipeline Diagram

```
Gateway
  ↓
ActionIntent  
  ↓
ProxyPipeline.execute_with_trace()  
  ↓
PolicyDecisionPoint  
  ↓
SafetyGate  
  ↓
Approval Workflow  
  ↓
ExecutorPlugin (untrusted capability module)  
  ↓
ExecutionTrace  
  ↓
ExecutionProofBundle
```

## Component Explanations

### Gateway
Entry point for all actions entering the governance system.
Validates incoming requests and creates ActionIntent objects.

### ActionIntent
Structured representation of an action to be executed.
Contains action type, parameters, and execution context.

### ProxyPipeline.execute_with_trace()
**The sole execution boundary** - all actions must pass through this governance boundary.
Enforces policy rules, safety checks, and creates audit trails.
Coordinates with approval workflows when required.

### PolicyDecisionPoint
Evaluates actions against ordered policy rules.
The first matching rule determines whether the action is allowed, denied, or requires approval.

### SafetyGate
Deterministic safety enforcement with arbitration precedence.
Can block actions that violate safety constraints regardless of policy decisions.

### Approval Workflow
Human-in-the-loop interfaces for critical actions.
Provides operator approval, denial, and escalation capabilities.

### ExecutorPlugin
**Untrusted capability modules** - treated as external, sandboxed components.
Receive only ActionIntent objects and return only ExecutorResult objects.
Cannot access governance components or modify traces.

### ExecutionTrace
Complete audit trail of the decision and execution process.
Contains all events, decisions, and outcomes in deterministic order.

### ExecutionProofBundle
Cryptographic proof bundle containing the complete execution evidence.
Supports deterministic replay and verification of recorded decision chains.

## Key Architectural Principles

1. **ProxyPipeline is the sole execution boundary** - All actions must pass through this governance boundary
2. **Executors are untrusted capability modules** - Treated as external, sandboxed components
3. **Execution must remain deterministic** - Same inputs always produce identical outputs
4. **Evidence artifacts must be replayable** - Audit trails support reconstruction of recorded decisions
5. **CI invariant gates enforce integrity** - Automated checks preserve architectural guarantees

This architecture ensures that autonomous systems remain accountable, auditable, and enforceable while maintaining clear separation between intelligence and governance.
