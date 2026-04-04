# ExoArmur System Positioning

## System Identity

ExoArmur is a deterministic execution safety substrate that provides byte-for-byte reproducible execution guarantees for AI agent systems through causal traceability and safety gate enforcement.

## What It Is

- **Deterministic Execution Layer**: Ensures identical outputs across runs and environments
- **Causal Traceability System**: Maintains complete audit trails with cryptographic evidence
- **Safety Gate Framework**: Enforces allow/deny/require_human decisions before execution
- **Replay Verification Engine**: Provides byte-for-byte execution reconstruction
- **Audit Evidence Chain**: Cryptographically verifiable records of all system actions

## What It Is Not

- **Autonomous Decision System**: Does not make security decisions or detect threats
- **AI Agent Platform**: Does not host or run AI agents directly
- **Regulatory Compliance Tool**: Not certified for any regulatory frameworks
- **Production-Ready System**: Currently in development with experimental components
- **Market-Dominant Solution**: Engineering-focused substrate, not commercial product

## System Architecture

### Core Engine (Production-Grade)
```
src/exoarmur/
├── replay/           # Deterministic replay engine
├── safety/           # Safety gate enforcement
├── audit/            # Audit evidence chain
├── execution/        # Execution kernel
└── clock/            # Deterministic time handling
```

**Core Guarantees**:
- ✅ Byte-for-byte deterministic execution
- ✅ Complete audit traceability
- ✅ Safety gate enforcement
- ✅ Replay verification
- ✅ Cryptographic evidence integrity

### Experimental V2 Layer (Development)
```
src/exoarmur/execution_boundary_v2/
├── interfaces/       # Plugin interfaces
├── models/          # Action intent models
├── pipeline/        # Proxy pipeline
└── utils/           # Utility functions
```

**Experimental Status**:
- 🧪 Feature-flagged by default
- 🧪 Operator approval workflows
- 🧪 Mock executor implementations
- 🧪 Plugin architecture development

## Safety Gate Model

### Decision Types
- **ALLOW**: Action proceeds with full audit trail
- **DENY**: Action blocked before any side effects
- **REQUIRE_HUMAN**: Action paused pending operator approval

### Enforcement Points
- **Pre-Execution**: All actions evaluated before side effects
- **Tenant Isolation**: Multi-tenant safety boundaries
- **Audit Binding**: All decisions cryptographically bound to evidence

## Deterministic Guarantees

### What Is Guaranteed
- **Same Inputs → Same Outputs**: Identical byte-for-byte execution across environments
- **Replay Consistency**: Audit trails reproduce identical execution results
- **Hash Stability**: SHA-256 hashes remain constant across runs
- **Temporal Determinism**: No wall-clock dependencies in core execution

### What Is Not Guaranteed
- **External System Behavior**: Depends on external integrations
- **Experimental Features**: V2 components behind feature flags
- **Performance Characteristics**: Varies with workload and environment
- **Regulatory Compliance**: Not certified for any frameworks

## Current System State

### Production-Ready Components
- **Core Replay Engine**: 100% reproducible execution
- **Safety Gate Framework**: Deterministic allow/deny enforcement
- **Audit Evidence Chain**: Complete traceability with cryptographic proofs
- **Deterministic Clock**: Fixed timestamp generation for reproducibility

### Development Components
- **V2 Execution Boundary**: Plugin architecture in development
- **Operator Approval Workflows**: Human-in-the-loop decision gates
- **Mock Executors**: Test implementations for development
- **Federation Layer**: Multi-node coordination (experimental)

## Trust Primitives

### Proof Mode
```bash
exoarmur proof
```
Provides deterministic system validation with structured output:
- Decision: ALLOWED/DENIED
- Action Executed: true/false
- Replay Hash: stable cryptographic hash
- Correlation ID: unique execution identifier

### Canonical Demo
```bash
exoarmur demo --scenario canonical
```
Demonstrates full system capabilities with policy enforcement and replay verification.

## System Boundaries

### In Scope
- Deterministic execution enforcement
- Safety gate policy application
- Audit evidence generation and verification
- Replay-based system validation
- Cryptographic proof generation

### Out of Scope
- AI agent decision making
- Threat detection and analysis
- External system integration
- Regulatory compliance certification
- Market-ready product features

## Engineering Principles

### Determinism First
- All core execution paths are deterministic
- No wall-clock dependencies in critical paths
- Stable hash generation across environments
- Reproducible test results

### Safety by Default
- All actions require explicit allow/deny decisions
- Human approval required for high-risk operations
- Complete audit trails for all system actions
- Cryptographic evidence integrity

### Explicit Boundaries
- Clear separation between core and experimental
- Feature flags control experimental access
- No hidden capabilities or backdoors
- Conservative external claims

## Development Status

### Current Phase
- **Core Engine**: Production-ready with deterministic guarantees
- **V2 Experimental**: Development phase with feature flags
- **Documentation**: Truth-aligned positioning established
- **Testing**: Comprehensive deterministic test coverage

### Next Steps
- Complete V2 plugin architecture
- Expand safety gate policy options
- Enhance operator approval workflows
- Strengthen federation capabilities

## Usage Guidelines

### For System Integration
- Use Proof Mode for deterministic validation
- Implement safety gates for all external actions
- Maintain audit trails for compliance verification
- Test replay scenarios for system validation

### For Development
- Enable V2 features behind explicit flags
- Use mock executors for testing
- Verify deterministic behavior across environments
- Maintain conservative external claims

---

**Note**: This positioning document reflects the current implemented state of ExoArmur. Claims are limited to verified, testable capabilities of the core engine. Experimental components are clearly marked and feature-flagged.
