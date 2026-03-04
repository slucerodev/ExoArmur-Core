# ExoArmur Execution Governance Architecture

## Overview

This document defines the formal architecture for introducing an "Execution Governance Boundary" as V2 scaffolding without modifying any V1 contracts or runtime behavior. The execution governance layer transforms ExoArmur into an execution firewall for AI agents and autonomous workflows while preserving all V1 invariants.

## Architecture Diagram

```
Agents / automation / humans
        ↓
ExoArmur Governance Boundary
        ↓
Executor Modules
        ↓
External Systems
```

## V1 Primitive Analysis

### Existing V1 Primitives That Support Execution Governance

1. **Intent Creation & Canonicalization**
   - `ExecutionIntentV1` - Idempotent execution request produced after policy + safety gating
   - ULID-based `intent_id` with deterministic validation
   - `idempotency_key` for safe retries
   - `action_class` (A0_observe, A1_soft_containment, A2_hard_containment, A3_irreversible)

2. **Deterministic ID Generation**
   - ULID validation in `ExecutionIntentV1.validate_ulid()`
   - Stable hash generation via `canonical_utils.stable_hash()`
   - Correlation and trace IDs for end-to-end tracking

3. **Safety Gate Evaluation**
   - `SafetyGate` class with arbitration precedence enforcement
   - `SafetyVerdict` dataclass (allow/deny/require_quorum/require_human)
   - `PolicyState`, `TrustState`, `EnvironmentState` for comprehensive evaluation
   - Kill switch enforcement with highest precedence

4. **Audit Evidence Emission**
   - `AuditRecordV1` - Append-only audit evidence record for replay and compliance
   - `AuditLogger` for structured evidence emission
   - NATS JetStream integration for persistent audit trails

5. **Replay Verification**
   - `ReplayEngine` for deterministic audit replay
   - `ReplayReport` with comprehensive verification results
   - Intent hash verification, safety gate verification, audit integrity verification

## V2 Package Structure

### New Namespace: `execution_boundary_v2/`

```
src/exoarmur/execution_boundary_v2/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── action_intent.py      # ActionIntent schema
│   ├── policy_decision.py    # PolicyDecision schema
│   └── execution_dispatch.py # ExecutionDispatch schema
├── interfaces/
│   ├── __init__.py
│   ├── policy_decision_point.py  # PolicyDecisionPoint interface
│   ├── executor_plugin.py        # ExecutorPlugin interface
│   └── execution_dispatch.py      # ExecutionDispatch interface
├── pipeline/
│   ├── __init__.py
│   ├── proxy_pipeline.py     # Proxy pipeline implementation
│   └── intent_canonicalizer.py # ActionIntent canonicalization
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_interfaces.py
    └── test_pipeline.py
```

## Schema Definitions

### ActionIntent Schema

```python
class ActionIntent(BaseModel):
    """Canonical action intent envelope for execution governance"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    # Core identification
    intent_id: str = Field(description="ULID intent identifier")
    actor: Dict[str, Any] = Field(
        description="Actor information",
        examples=[{
            "actor_type": "agent",
            "actor_id": "agent-123",
            "actor_version": "1.0.0"
        }]
    )
    
    # Action specification
    action_type: str = Field(description="Type of action to execute")
    target: Dict[str, Any] = Field(
        description="Target specification",
        examples=[{
            "target_type": "http_endpoint",
            "target_id": "api.example.com",
            "target_resource": "/v1/containers"
        }]
    )
    parameters: Dict[str, Any] = Field(
        description="Action parameters",
        examples=[{
            "method": "POST",
            "payload": {"name": "test-container"},
            "headers": {"Authorization": "Bearer token"}
        }]
    )
    
    # Governance context
    safety_context: Dict[str, Any] = Field(
        description="Safety evaluation context",
        examples=[{
            "risk_level": "medium",
            "required_approvals": ["human"],
            "ttl_seconds": 3600
        }]
    )
    
    # Metadata
    timestamp: datetime = Field(description="Intent creation timestamp")
    correlation_id: str = Field(description="Correlation identifier")
    trace_id: str = Field(description="Trace identifier")
    
    @field_validator('intent_id')
    @classmethod
    def validate_ulid(cls, v: str) -> str:
        """Validate ULID format."""
        if not re.match(r'^[0123456789ABCDEFGHJKMNPQRSTVWXYZ]{26}$', v):
            raise ValueError('intent_id must be a valid ULID')
        return v
```

### PolicyDecision Schema

```python
class PolicyDecision(BaseModel):
    """Policy decision result for intent evaluation"""
    
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    
    decision_id: str = Field(description="ULID decision identifier")
    intent_id: str = Field(description="Associated intent identifier")
    verdict: Literal["allow", "deny", "require_approval", "escalate"] = Field(
        description="Policy verdict"
    )
    rationale: str = Field(description="Decision rationale")
    rule_ids: List[str] = Field(description="Applied rule identifiers")
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence")
    requires_human_approval: bool = Field(default=False, description="Human approval required")
    approval_requirements: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Specific approval requirements"
    )
    timestamp: datetime = Field(description="Decision timestamp")
```

## Interface Contracts

### PolicyDecisionPoint Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PolicyDecisionPoint(ABC):
    """Interface for policy decision evaluation"""
    
    @abstractmethod
    async def evaluate_intent(
        self,
        intent: ActionIntent,
        context: Optional[Dict[str, Any]] = None
    ) -> PolicyDecision:
        """
        Evaluate an intent against policy rules
        
        Args:
            intent: The action intent to evaluate
            context: Additional evaluation context
            
        Returns:
            Policy decision with verdict and rationale
        """
        pass
    
    @abstractmethod
    async def check_approval_status(
        self,
        intent_id: str,
        decision_id: str
    ) -> Dict[str, Any]:
        """
        Check approval status for a pending decision
        
        Args:
            intent_id: Intent identifier
            decision_id: Decision identifier
            
        Returns:
            Approval status information
        """
        pass
```

### ExecutorPlugin Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ExecutorPlugin(ABC):
    """Interface for executor modules"""
    
    @abstractmethod
    def get_executor_type(self) -> str:
        """Return the executor type identifier"""
        pass
    
    @abstractmethod
    def get_supported_actions(self) -> List[str]:
        """Return list of supported action types"""
        pass
    
    @abstractmethod
    async def execute_action(
        self,
        intent: ActionIntent,
        decision: PolicyDecision,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute an action with proper authorization
        
        Args:
            intent: The action intent to execute
            decision: The policy decision authorizing execution
            context: Additional execution context
            
        Returns:
            Execution result with metadata
        """
        pass
    
    @abstractmethod
    async def validate_target(
        self,
        target: Dict[str, Any],
        action_type: str
    ) -> ValidationResult:
        """
        Validate target specification
        
        Args:
            target: Target specification
            action_type: Type of action to perform
            
        Returns:
            Validation result
        """
        pass
```

### ExecutionDispatch Interface

```python
class ExecutionDispatch(ABC):
    """Interface for execution dispatch coordination"""
    
    @abstractmethod
    async def submit_intent(
        self,
        intent: ActionIntent,
        actor_context: Dict[str, Any]
    ) -> SubmissionResult:
        """
        Submit an intent for execution
        
        Args:
            intent: The action intent to submit
            actor_context: Actor authentication and context
            
        Returns:
            Submission result with tracking information
        """
        pass
    
    @abstractmethod
    async def get_execution_status(
        self,
        intent_id: str
    ) -> ExecutionStatus:
        """
        Get execution status for an intent
        
        Args:
            intent_id: Intent identifier
            
        Returns:
            Current execution status
        """
        pass
    
    @abstractmethod
    async def cancel_execution(
        self,
        intent_id: str,
        reason: str
    ) -> CancellationResult:
        """
        Cancel a pending or running execution
        
        Args:
            intent_id: Intent identifier
            reason: Cancellation reason
            
        Returns:
            Cancellation result
        """
        pass
```

## Proxy Pipeline Design

### Pipeline Flow Using Existing V1 Primitives

```
1. Intent Submission
   Actor → ActionIntent (V2 canonicalization)
   ↓
2. Policy Evaluation
   PolicyDecisionPoint.evaluate_intent() → PolicyDecision
   ↓
3. Safety Gate Enforcement
   SafetyGate.evaluate_safety() using V1 SafetyGate
   ↓
4. Executor Dispatch
   ExecutionDispatch.submit_intent() → ExecutorPlugin.execute_action()
   ↓
5. Evidence Emission
   AuditLogger.emit() using V1 AuditRecordV1
   ↓
6. Replay Verification
   ReplayEngine.replay() using V1 ReplayEngine
```

### Integration with V1 Primitives

1. **Intent Canonicalization**
   - Wrap V1 `ExecutionIntentV1` with V2 `ActionIntent`
   - Preserve V1 ULID validation and deterministic ID generation
   - Add actor and target context while maintaining V1 compatibility

2. **Safety Gate Integration**
   - Use existing V1 `SafetyGate.evaluate_safety()`
   - Map V2 `PolicyDecision` to V1 `LocalDecisionV1` format
   - Preserve V1 arbitration precedence and kill switch behavior

3. **Audit Evidence Emission**
   - Emit V1 `AuditRecordV1` for all execution events
   - Include V2 context in audit record attributes
   - Maintain V1 replay compatibility

4. **Replay Verification**
   - Use existing V1 `ReplayEngine` for deterministic replay
   - Extend replay report with V2 execution metadata
   - Preserve V1 replay invariants

## Risk Register

### Determinism Leaks

1. **Non-deterministic Executor Behavior**
   - Risk: Executor plugins introduce non-deterministic side effects
   - Mitigation: Require deterministic execution contracts and replay verification
   - Impact: High

2. **Timestamp Drift**
   - Risk: Distributed execution introduces timing variations
   - Mitigation: Use logical timestamps and causal ordering
   - Impact: Medium

### Bypass Vectors

1. **Direct Executor Access**
   - Risk: Actors bypass governance boundary by calling executors directly
   - Mitigation: Enforce authentication at executor plugin level
   - Impact: High

2. **Intent Spoofing**
   - Risk: Malicious actors forge intents with fake actor context
   - Mitigation: Strong actor authentication and intent signing
   - Impact: High

### Executor Plugin Security Risks

1. **Privilege Escalation**
   - Risk: Executor plugins escalate privileges beyond policy limits
   - Mitigation: Principle of least privilege and capability-based security
   - Impact: High

2. **Resource Exhaustion**
   - Risk: Executor plugins consume excessive resources
   - Mitigation: Resource quotas and monitoring
   - Impact: Medium

### Evidence Integrity Concerns

1. **Audit Record Tampering**
   - Risk: Compromise of audit trail integrity
   - Mitigation: Cryptographic evidence chaining and tamper-evident storage
   - Impact: High

2. **Replay Consistency**
   - Risk: Replay results diverge from actual execution
   - Mitigation: Deterministic execution contracts and evidence verification
   - Impact: Medium

## Implementation Constraints

### V1 Invariant Preservation

1. **No V1 Contract Modifications**
   - All V1 models and interfaces remain unchanged
   - V2 functionality is additive only
   - Backward compatibility maintained

2. **Golden Demo Semantics**
   - Golden Demo behavior remains unchanged
   - V2 features are feature-gated and disabled by default
   - No impact on V1 test invariants

3. **Phase Gating**
   - All V2 functionality requires explicit feature flags
   - Progressive rollout with safety boundaries
   - Rollback capability at each phase

### Security Boundaries

1. **Execution Isolation**
   - Executor plugins run in isolated contexts
   - No direct access to Core internals
   - Capability-based security model

2. **Authentication & Authorization**
   - Strong actor authentication required
   - Policy-based authorization enforcement
   - Audit trail for all access decisions

## Next Steps

1. **Phase 0: Architecture Baseline**
   - Review and approve this architecture specification
   - Create detailed interface documentation
   - Establish risk mitigation strategies

2. **Phase 1: Boundary Contracts**
   - Implement V2 models and interfaces
   - Add feature flags for V2 functionality
   - Create comprehensive test suites

3. **Phase 2: Proxy Pipeline**
   - Implement minimal proxy pipeline
   - Integrate with V1 primitives
   - Add mock executor for testing

4. **Phase 3: Executor Modules**
   - Develop executor plugin framework
   - Implement reference executors
   - Add executor registry

5. **Phase 4: Replay Hardening**
   - Extend replay engine for V2 execution
   - Add forensic analysis capabilities
   - Implement evidence verification

6. **Phase 5: Developer Platform**
   - Create developer documentation
   - Build quickstart workflows
   - Add agent adapter examples
