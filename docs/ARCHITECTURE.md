# ExoArmur ADMO Architecture

## Boundary Definition

### V1 Core (Immutable Cognition Loop)
The V1 core is the autonomous decision-making pipeline that must never change:

```
TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGateV1 → ExecutionIntentV1 → AuditRecordV1
```

**V1 Core Components:**
- **Perception**: Telemetry ingestion and signal extraction
- **Analysis**: Threat correlation and belief generation  
- **Decision**: Collective confidence and local decision making
- **Safety**: Deterministic safety gate with arbitration precedence
- **Execution**: Intent generation with audit trail
- **Persistence**: Audit logging and event storage

### V2 External Layers (Additive Only)
V2 provides external capabilities that coordinate but never modify V1 core behavior:

```
┌─────────────────────────────────────────────────────────────┐
│                    V2 External Layers                      │
├─────────────────────┬───────────────────────────────────────┤
│  Federation Layer   │         Control Plane Layer           │
│                     │                                       │
│ • Multi-cell        │ • Operator approval workflows        │
│ • Cross-cell        │ • Human-in-the-loop interfaces        │
│ • Aggregation       │ • External coordination procedures     │
│ • Quorum            │ • Emergency response coordination     │
└─────────────────────┴───────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    V1 Core (Immutable)                     │
│                                                             │
│  Telemetry → SignalFacts → Belief → CollectiveConfidence   │
│                ↓                                           │
│            SafetyGate → ExecutionIntent → Audit            │
└─────────────────────────────────────────────────────────────┘
```

## Must Never List

**V2 must NEVER:**
- Modify V1 cognition pipeline behavior
- Change V1 data models or contracts
- Interfere with V1 safety gate precedence
- Alter V1 Golden Demo execution
- Block or delay V1 decision making
- Modify V1 audit trail generation
- Directly execute actions inside V1 cognition pipeline
- Mutate signed V1 policy bundles

**V2 must ALWAYS:**
- Remain inert when feature flags are disabled
- Use only external coordination interfaces
- Respect V1 safety gate decisions
- Preserve V1 audit trail integrity
- Operate through message boundaries only

## Message and Bus Boundaries

### V1 Internal Messaging
V1 uses internal function calls and in-memory data structures:
- Direct function calls between pipeline stages
- In-memory data flow (TelemetryEventV1 → ExecutionIntentV1)
- Local audit logging
- Internal safety gate evaluation

### V2 External Coordination
V2 uses message-based coordination through NATS JetStream:
- Cross-cell federation messages
- Operator approval requests/responses
- Policy bundle distribution
- Audit trail consolidation

### Boundary Enforcement
```
V1 Core ←→ NATS JetStream ←→ V2 External Layers
```

**Key Principles:**
- V1 never directly calls V2 code
- V2 never modifies V1 internal state
- All V2→V1 communication goes through message interfaces
- Feature flags control V2 activation independently

**V1/V2 Boundary Pattern:**
V2 modules must not directly import V1 systems. All V1 access goes through explicit interfaces:

```python
# V2 module uses boundary interface (NOT direct V1 import)
from federation.audit_interface import AuditInterface, V1AuditAdapter

class V2Module:
    def __init__(self, audit_interface: AuditInterface):
        self.audit_interface = audit_interface  # Boundary-safe
```

**AuditInterface Adapter Pattern:**
- `AuditInterface`: Abstract contract for V1 audit access
- `V1AuditAdapter`: Wraps V1 audit logger, implements boundary interface
- `NoOpAuditInterface`: Testing/disabled scenario implementation
- V2 modules receive interface via dependency injection, never import V1 directly

## ASCII Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │         External Interfaces          │
                    │                                     │
                    │  ┌─────────────┐  ┌───────────────┐ │
                    │  │   Web UI    │  │   REST API    │ │
                    │  │ (Operators) │  │ (Automation)  │ │
                    │  └─────────────┘  └───────────────┘ │
                    └─────────────────────────────────────┘
                                ↕
                    ┌─────────────────────────────────────┐
                    │         V2 Control Plane             │
                    │                                     │
                    │  ┌─────────────┐  ┌───────────────┐ │
                    │  │   Approval  │  │   Operator    │ │
                    │  │   Service   │  │   Interface   │ │
                    │  └─────────────┘  └───────────────┘ │
                    │           ↕           ↕              │
                    │  ┌─────────────────────────────────┐ │
                    │  │        Control API              │ │
                    │  └─────────────────────────────────┘ │
                    └─────────────────────────────────────┘
                                ↕ (NATS JetStream)
                    ┌─────────────────────────────────────┐
                    │         V2 Federation                │
                    │                                     │
                    │  ┌─────────────┐  ┌───────────────┐ │
                    │  │ Federation   │  │ Cross-Cell    │ │
                    │  │  Manager     │  │ Aggregator    │ │
                    │  └─────────────┘  └───────────────┘ │
                    └─────────────────────────────────────┘
                                ↕ (NATS JetStream)
                    ┌─────────────────────────────────────┐
                    │           V1 Core (Immutable)       │
                    │                                     │
                    │  ┌─────────────────────────────────┐ │
                    │  │      Cognition Pipeline         │ │
                    │  │                                 │ │
                    │  │  Telemetry → SignalFacts        │ │
                    │  │       ↓                         │ │
                    │  │    Belief → CollectiveConfidence │ │
                    │  │       ↓                         │ │
                    │  │    SafetyGate → ExecutionIntent  │ │
                    │  │       ↓                         │ │
                    │  │         AuditRecord              │ │
                    │  └─────────────────────────────────┘ │
                    │                                     │
                    │  ┌─────────────────────────────────┐ │
                    │  │     Safety & Arbitration        │ │
                    │  │                                 │ │
                    │  │  KillSwitch > PolicyVerification │ │
                    │  │  > SafetyGate > TrustConstraints │ │
                    │  │  > CollectiveConfidence         │ │
                    │  │  > LocalDecision                │ │
                    │  └─────────────────────────────────┘ │
                    └─────────────────────────────────────┘
```

## Component Interactions

### V1 Core Flow
1. **Telemetry Ingestion**: External systems send telemetry
2. **Signal Extraction**: Telemetry → SignalFacts transformation
3. **Belief Generation**: SignalFacts → Belief correlation
4. **Decision Making**: Belief → CollectiveConfidence evaluation
5. **Safety Validation**: SafetyGate with deterministic precedence
6. **Intent Generation**: SafetyGate → ExecutionIntent creation
7. **Audit Recording**: All steps logged to AuditRecord

### V2 Coordination Flow
1. **Feature Flag Check**: V2 components check if enabled
2. **External Coordination**: V2 layers coordinate via NATS
3. **Policy Distribution**: V2 distributes policy bundles
4. **Operator Approval**: V2 handles human approval workflows
5. **Federation**: V2 aggregates across multiple cells
6. **Audit Consolidation**: V2 consolidates audit trails

## Data Flow Boundaries

### V1 Internal Data
- Remains within V1 core
- Never exposed to V2 layers
- Protected by immutability guarantees

### V2 External Data
- Flows through NATS JetStream
- Never modifies V1 internal state
- Subject to feature flag controls

## Safety and Reliability

### V1 Safety Guarantees
- Deterministic safety gate precedence
- No external dependencies for core decisions
- Immediate response capability
- Complete audit trail

### V2 Safety Constraints
- Cannot block V1 decision making
- Must respect V1 safety gate decisions
- Feature flags provide emergency disable
- External coordination only

This architecture ensures ExoArmur maintains autonomous defense capabilities while enabling controlled evolution through external layers that never compromise core safety or reliability.
