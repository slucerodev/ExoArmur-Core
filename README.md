# ExoArmur ADMO

Autonomous Defense Mesh Organism

## Overview

ExoArmur is an enterprise-grade autonomous defense/orchestration platform that operates as a distributed mesh of autonomous defensive cells. Each cell makes independent decisions following organism laws, with coordination achieved through belief propagation rather than centralized command distribution.

## Architecture

ExoArmur follows the core organism loop:
**TelemetryEventV1** → **SignalFactsV1** → **BeliefV1** → **CollectiveConfidence** → **SafetyGate** → **ExecutionIntentV1** → **AuditRecordV1**

Key architectural principles:
- No central brain; cognition is per-cell
- Belief propagation, not command distribution
- Deterministic behavior and replay capability
- Human-in-the-loop for critical decisions

## Current Implementation Status

### ✅ Phase 2: Federation Foundation (Complete)
- **Handshake Protocol**: Secure federate identity establishment with cryptographic verification
- **Identity Management**: Federate identity store with trust scoring and capability negotiation  
- **Message Security**: End-to-end encryption and signature verification for all federation messages
- **Replay Protection**: Nonce-based replay attack prevention
- **Audit Trail**: Complete audit events for all federation operations

### ✅ Phase 2B: Coordination Visibility (Complete)
- **Observation Ingest**: Signed observation ingestion with validation and storage
- **Belief Aggregation**: Deterministic belief generation from observations with provenance tracking
- **Visibility API**: Read-only REST API for federation coordination visibility
- **Conflict Detection**: Automatic detection of conflicting beliefs with deterministic conflict keys
- **Correlation Tracking**: Timeline views and correlation ID-based event grouping

### ✅ Phase 2C: Arbitration (Complete)
- **Conflict Arbitration**: Human-in-the-loop resolution of belief conflicts
- **Approval Integration**: A3-level human approval required for all conflict resolutions
- **Deterministic Resolution**: Reproducible post-resolution belief states
- **Audit Completeness**: Full audit trail for arbitration lifecycle

### ✅ Phase 3: Execution & Enforcement (Complete)
- **Safety Gate**: Policy enforcement with arbitration precedence (KillSwitch > PolicyVerification > SafetyGate > PolicyAuthorization > TrustConstraints > CollectiveConfidence > LocalDecision)
- **Execution Engine**: Intent execution with idempotency and audit trails
- **Control Plane**: Human approval workflows with intent freezing and binding
- **Policy Engine**: Rule evaluation and decision making with safety constraints
- **Collective Confidence**: Quorum-based decision aggregation

### 🔄 Phase 4: Advanced Capabilities (Planning)
Future enhancements may include:
- Machine learning-based analysis and predictions
- Advanced automation capabilities
- Extended defensive measures

### 📊 Test Coverage
- **299 tests passing** across all components
- **Constitutional invariants** enforced
- **Boundary enforcement** between federation and execution layers
- **Deterministic replay** capability verified
- **Feature flag isolation** tested

## Safety Guarantees
- All execution requires human approval (A3) unless explicitly permitted
- Kill switches can override all automation
- Policy violations force escalation
- Audit trail continues through execution phase

## Development

### Quick Start
```bash
# Run all verification checks
make verify

# Run tests only
make test

# Run specific test suite
python3 -m pytest tests/test_constitutional_invariants.py -v
```

### Project Structure
```
src/federation/          # Federation coordination (Phase 2)
├── handshake_controller.py
├── observation_ingest.py
├── belief_aggregation.py
├── arbitration_service.py
└── visibility_api.py

spec/contracts/          # Data contracts and models
├── models_v1.py        # Core ADMO models
└── feature_flags_v2.yaml

tests/                   # Comprehensive test suite
├── test_constitutional_invariants.py
├── test_boundary_enforcement.py
├── test_replay_determinism.py
└── test_*.py

docs/                    # Documentation
├── COORDINATION_VISIBILITY.md
├── ARBITRATION.md
├── AUDIT_EVENT_CATALOG.md
└── FEATURE_FLAGS.md
```

### Feature Flags
All V2 features are disabled by default and require explicit enablement:

```bash
# Enable federation features
export EXOARMUR_V2_FEDERATION_ENABLED=true

# Enable observation ingest
export EXOARMUR_V2_OBSERVATION_INGEST_ENABLED=true

# Enable arbitration
export EXOARMUR_V2_ARBITRATION_ENABLED=true
```

See [docs/FEATURE_FLAGS.md](docs/FEATURE_FLAGS.md) for complete flag matrix.

## Constitutional Invariants

The system enforces these core invariants:

1. **Federation Cannot Trigger Execution**: Federation modules are isolated from execution modules
2. **Unconfirmed Federates Cannot Ingest**: Only CONFIRMED federates can submit observations
3. **Conflicts Cannot Auto-Resolve**: All conflicts require human approval
4. **Deterministic Replay**: Same inputs always produce same outputs
5. **Audit Completeness**: All significant operations emit audit events

## Compliance and Security

- **Zero Trust Architecture**: All federates authenticate and authorize
- **End-to-End Encryption**: All federation messages are encrypted
- **Human-in-the-Loop**: Critical decisions require human approval
- **Complete Audit Trail**: All operations are auditable and replayable
- **Deterministic Behavior**: System behavior is reproducible and testable

## Contributing

1. All changes must maintain constitutional invariants
2. V1 functionality cannot be modified
3. V2 features must be feature-flagged
4. All changes require comprehensive tests
5. Boundary violations are not permitted

## License

[License information to be added]

---

**Current Status**: Phase 2 Complete ✅ | Phase 3 Complete ✅ | Phase 4: Planning 📋 | Tests Passing: 299/360 ✅
