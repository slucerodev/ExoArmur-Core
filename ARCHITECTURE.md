# ExoArmur Architecture

## Overview

ExoArmur is a deterministic governance runtime system with strict architectural separation between execution, safety, audit, replay, telemetry, causal logging, and environment state planes.

## Architecture Model

### Execution Plane (V1/V2 Runtime)

The execution plane contains the core runtime system with two major versions:

#### V1 Core (Immutable)
- **Purpose**: Deterministic execution engine with proven governance
- **Characteristics**: 
  - Immutable contracts and behavior
  - Golden Demo compliance required
  - No architectural modifications allowed
  - Core business logic and decision execution

#### V2 Entry Gate (Additive)
- **Purpose**: Governance boundary enforcement and routing
- **Characteristics**:
  - Single mandatory execution entry point
  - Strict validation and deterministic routing
  - V2 governance activation with feature flags
  - Additive-only modifications to V1

### Observability Separation Model

ExoArmur implements strict physical isolation between all observability systems:

#### Physical Isolation Architecture
```
EXECUTION PLANE
├── V1 Core Runtime (isolated)
├── V2 Entry Gate (isolated)
└── No direct observability access

TELEMETRY PLANE (Thread/Process Isolated)
├── V2TelemetryHandler (isolated)
├── Memory sinks (isolated)
├── Async file sinks (isolated)
└── No access to other planes

CAUSAL PLANE (Thread/Process Isolated)
├── CausalContextLogger (isolated)
├── Memory causal sinks (isolated)
├── Causal chain tracking (isolated)
└── No access to other planes

AUDIT/REPLAY PLANE (Thread/Process Isolated)
├── Audit normalizer (isolated)
├── Replay engine (isolated)
├── Audit record storage (isolated)
└── No access to live observability streams

SAFETY DECISION PLANE (Thread/Process Isolated)
├── Safety gates (isolated)
├── Policy evaluators (isolated)
├── Trust evaluators (isolated)
└── No access to observability planes
```

#### Serialized Event Bridge
All cross-plane communication occurs through serialized events:
- **JSON serialization**: All data converted to JSON before transport
- **No object references**: Direct object sharing prohibited
- **Deep copy boundary**: Data is deep copied across planes
- **Event routing**: Deterministic routing to target planes

### Safety + Decision Isolation Model

The safety and decision systems operate in complete isolation:

#### Safety Decision Plane
- **Purpose**: Safety gates, policy evaluation, trust assessment
- **Isolation**: Thread/process isolation from all other planes
- **Communication**: Only through serialized events
- **No Runtime Access**: Cannot access live observability streams

#### Decision Flow
```
EXECUTION → SAFETY DECISION (via serialized events)
SAFETY DECISION → EXECUTION (via serialized decisions)
SAFETY DECISION × OBSERVABILITY (forbidden)
```

### Boundary Enforcement Layer (Step 8)

The boundary enforcement layer provides structural guardrails:

#### Contract Domain Separation
```
EXECUTION_DOMAIN: Core execution modules and engines
TELEMETRY_DOMAIN: Telemetry handlers and monitoring
CAUSAL_DOMAIN: Causal context logging and lineage tracking
AUDIT_REPLAY_DOMAIN: Audit normalization and replay engines
SAFETY_DECISION_DOMAIN: Safety gates, policy evaluators, trust systems
ENVIRONMENT_DOMAIN: Environment state and configuration
```

#### Forbidden Dependencies
- TELEMETRY_DOMAIN → CAUSAL_DOMAIN (forbidden)
- CAUSAL_DOMAIN → TELEMETRY_DOMAIN (forbidden)
- SAFETY_DECISION_DOMAIN → OBSERVABILITY_LAYERS (forbidden)
- AUDIT_REPLAY_DOMAIN → LIVE_OBSERVABILITY_STREAMS (forbidden)

#### Schema Fingerprinting
- **Structural fingerprints**: Hash-based schema detection
- **Drift detection**: Cross-domain schema reuse prevention
- **Immutable contracts**: No retroactive schema modifications

### Physical Isolation Layer (Step 9)

The physical isolation layer enforces runtime separation:

#### Isolation Strategies
- **Thread Isolation**: Independent threads with separate memory
- **Process Isolation**: Separate processes with complete memory isolation
- **Queue Systems**: Independent event queues per plane
- **Serialization Boundaries**: All cross-plane data serialized

#### Failure Isolation Guarantees
- **Plane crash isolation**: Failures don't propagate to other planes
- **Backpressure isolation**: No cross-plane performance impact
- **Resource isolation**: Resource exhaustion contained within planes
- **Error isolation**: Errors are contained within planes

#### Stress Validation Results
- **Telemetry flood**: 1000+ events processed without degradation
- **Causal chains**: Deep ancestry graphs handled without memory explosion
- **Concurrent load**: Multiple planes operating simultaneously
- **Corruption handling**: Malformed events safely discarded

## Key Architectural Principles

### 1. Strict Domain Separation
- No cross-domain imports allowed
- Each domain has isolated memory space
- Communication only through serialized events

### 2. Physical Isolation
- Thread or process isolation for each plane
- No shared memory between planes
- Independent execution contexts

### 3. Deterministic Execution
- V1 core behavior is immutable
- All execution paths are reproducible
- No non-deterministic elements in critical paths

### 4. Failure Safety
- Fail-open for execution plane
- Fail-closed for contract violations
- No cascading failures across planes

### 5. Observational Purity
- Observability planes are strictly observational
- No influence on execution flow or decisions
- No feedback loops into core systems

## Module Boundaries

### Single Entry Points
Each subsystem has exactly one entry point:
- **Execution**: V2EntryGate
- **Telemetry**: V2TelemetryHandler
- **Causal**: CausalContextLogger
- **Boundary**: BoundaryContractRegistry
- **Isolation**: ObservabilityPlaneManager

### Isolated Adapter Layers
Each plane has an isolated adapter:
- **TelemetryAdapter**: Handles V2TelemetryHandler in isolation
- **CausalAdapter**: Handles CausalContextLogger in isolation
- **AuditAdapter**: Handles audit/replay systems in isolation
- **SafetyAdapter**: Handles safety/decision systems in isolation

### No Direct Cross-Domain Imports
All cross-domain communication must go through:
- Serialized events
- Bridge interfaces
- Contract validation

## Implementation Status

### Completed Components
- ✅ V2 Entry Gate with governance enforcement
- ✅ V2 Telemetry Handler with isolated sinks
- ✅ Causal Context Logger with lineage tracking
- ✅ Boundary Contract Enforcement Layer
- ✅ Physical Isolation Layer with stress validation

### Validation Results
- ✅ All isolation guarantees verified
- ✅ Stress testing completed
- ✅ Failure isolation confirmed
- ✅ Zero execution impact maintained

## Architecture Evolution

The architecture follows a strict evolution model:

1. **V1 Core** (Immutable): Proven deterministic execution
2. **V2 Governance** (Additive): Enhanced governance and routing
3. **Observability** (Isolated): Complete physical separation
4. **Boundaries** (Structural): Contract enforcement and validation
5. **Isolation** (Physical): Runtime separation and failure isolation

Each layer builds upon the previous without modifying core behavior, ensuring system integrity while adding new capabilities.

## Future Considerations

The architecture is designed for future extensibility:

- **New Planes**: Additional observability planes can be added
- **Enhanced Isolation**: Process isolation can be upgraded to container isolation
- **Advanced Routing**: More sophisticated event routing can be implemented
- **Performance Optimization**: Queue sizes and processing can be tuned

All future changes must maintain the strict separation principles and isolation guarantees established in RC1.
