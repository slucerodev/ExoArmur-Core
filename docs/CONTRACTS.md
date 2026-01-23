# ExoArmur ADMO Contracts

## Contract Index

### V1 Contracts (Immutable)

V1 contracts are locked and must never change. They define the core autonomous defense mesh functionality.

| Contract | Purpose | Status |
|----------|---------|--------|
| `models_v1.py` | Pydantic v2 data models for all ADMO data types | ✅ Immutable |
| `nats_jetstream_v1.yaml` | NATS JetStream configuration for mesh communication | ✅ Immutable |
| `policy_bundle_v1.yaml` | Signed tenant policy bundle format and enforcement | ✅ Immutable |
| `safety_gate_v1.yaml` | Deterministic safety gate rules and verdict contract | ✅ Immutable |
| `arbitration_precedence_v1.yaml` | Deterministic precedence rules for conflict resolution | ✅ Immutable |
| `golden_demo_flow_v1.yaml` | End-to-end demo scenario proving V1 functional requirements | ✅ Immutable |
| `operational_defaults_v1.yaml` | V1 operational defaults for bootstrap and parameters | ✅ Immutable |

### V2 Contracts (Additive)

V2 contracts are additive-only and define external layers that coordinate but never modify V1 core behavior.

| Contract | Purpose | Status |
|----------|---------|--------|
| `federation_v2.yaml` | Multi-cell federation protocol and coordination | 🚧 Scaffolding |
| `federation_identity_v2.yaml` | Multi-cell federation identity, authentication, authorization | 🚧 Scaffolding |
| `control_plane_v2.yaml` | Operator control plane API endpoints and workflows | 🚧 Scaffolding |
| `operator_approval_v2.yaml` | Human operator approval workflows and decision factors | 🚧 Scaffolding |
| `feature_flags_v2.yaml` | V2 feature flag system for controlled rollout | 🚧 Scaffolding |
| `audit_federation_v2.yaml` | Cross-cell audit trail consolidation and correlation | 🚧 Scaffolding |

## V2 Contracts Added

### federation_v2.yaml
**Purpose**: Multi-cell federation protocol and coordination
**Key Features**:
- Federation topology and membership
- Cross-cell belief aggregation protocols
- Quorum computation and consensus
- Message types and NATS subjects
- Partition tolerance and recovery
- Lifecycle events and error handling

**Status**: Contract defined, implementation scaffolding only
**Feature Flag**: `v2_federation_enabled` (defaults to False)

### federation_identity_v2.yaml
**Purpose**: Multi-cell federation identity, authentication, and authorization
**Key Features**:
- Cell and operator identity management
- Authentication protocols and certificates
- Authorization framework and permissions
- NATS subjects for identity operations
- Security requirements and compliance
- Lifecycle events and audit trails

**Status**: Contract defined, implementation scaffolding only
**Feature Flag**: `v2_federation_identity_enabled` (defaults to False)

### control_plane_v2.yaml
**Purpose**: Operator control plane for human oversight and intervention
**Key Features**:
- API endpoints for federation management
- Operator approval workflow states
- Authentication and session management
- UI components and interfaces
- NATS subjects for control operations
- Emergency response coordination procedures

**Status**: Contract defined, implementation scaffolding only
**Feature Flag**: `v2_control_plane_enabled` (defaults to False)

### operator_approval_v2.yaml
**Purpose**: Human operator approval workflows and decision factors
**Key Features**:
- Approval request types (A3, policy change, emergency)
- Workflow states and transitions
- Operator roles and permissions
- Decision factors and confidence scoring
- Notification and escalation procedures
- Audit requirements and compliance

**Status**: Contract defined, implementation scaffolding only
**Feature Flag**: `v2_operator_approval_required` (defaults to False)

### feature_flags_v2.yaml
**Purpose**: V2 feature flag system for controlled rollout and safety
**Key Features**:
- Flag definitions and metadata
- Configuration schema and loading
- Rollout strategies and dependencies
- Evaluation logic and context
- Management operations and monitoring
- Persistence and caching mechanisms

**Status**: Contract defined, implementation scaffolding only
**Implementation**: Basic feature flag system implemented

### audit_federation_v2.yaml
**Purpose**: Cross-cell audit trail consolidation and correlation
**Key Features**:
- Audit aggregation across multiple cells
- Cross-cell event correlation
- Federation event tracking
- Consolidation protocols and formats
- Storage requirements and retention
- Query capabilities and security

**Status**: Contract defined, implementation scaffolding only
**Feature Flag**: `v2_audit_federation_enabled` (defaults to False)

## Versioning Rules

### V1 Contracts
- **LOCKED**: No changes permitted
- **Purpose**: Define immutable core behavior
- **Validation**: Must pass all existing tests
- **Backward Compatibility**: Not applicable (locked)

### V2 Contracts
- **ADDITIVE ONLY**: New fields and features only
- **Purpose**: Define external layer capabilities
- **Validation**: Must pass isolation tests
- **Backward Compatibility**: Required for all changes

### Feature Flag Integration
All V2 contracts are controlled by feature flags:
- **Default State**: All V2 flags default to False
- **Activation**: Requires explicit enablement
- **Isolation**: V2 contracts inert when disabled
- **Safety**: Feature flags provide emergency disable

## Contract Usage

### V1 Contract Usage
```python
# Import V1 models (immutable)
from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, ExecutionIntentV1

# Use V1 contracts in core cognition
telemetry = TelemetryEventV1(...)
belief = BeliefV1(...)
intent = ExecutionIntentV1(...)
```

### V2 Contract Usage
```python
# Import V2 contracts (additive, feature-flagged)
from spec.contracts.federation_v2 import FederationConfig
from spec.contracts.control_plane_v2 import ControlPlaneConfig

# Check feature flags before use
from src.feature_flags import get_feature_flags
flags = get_feature_flags()

if flags.is_v2_federation_enabled():
    # Use V2 federation contracts
    config = FederationConfig(...)
```

## Validation

### Contract Syntax Validation
```bash
# Validate YAML contracts
python -c "import yaml; yaml.safe_load(open('spec/contracts/federation_v2.yaml'))"

# Validate Python contracts
python -c "import spec.contracts.models_v1"
```

### Reference Validation
```bash
# Validate all contract references
python scripts/validate_spec_refs.py
```

### Integration Validation
```bash
# Validate V2 isolation
pytest tests/test_v2_feature_flag_isolation.py -v

# Validate V2 acceptance (xfail expected)
pytest tests/test_federation_v2_acceptance.py -v
pytest tests/test_operator_approval_v2_acceptance.py -v
```

## Contract Evolution

### V1 Evolution
**PROHIBITED**: V1 contracts are locked for all time.

### V2 Evolution
**ALLOWED**: Additive changes only
- New optional fields
- New optional capabilities
- New feature flags
- Enhanced documentation

**PROCESS**:
1. Update contract with additive changes
2. Update implementation scaffolding
3. Ensure isolation tests pass
4. Update acceptance tests as needed
5. Maintain feature flag controls

## Contract Relationships

### V1 Contract Dependencies
V1 contracts have no external dependencies and define the complete autonomous defense mesh.

### V2 Contract Dependencies
V2 contracts depend on:
- V1 contracts (read-only)
- Feature flag system
- External coordination interfaces
- NATS JetStream messaging

### Cross-Contract Validation
All contracts must pass:
- Syntax validation
- Reference validation
- Integration validation
- Governance compliance

This contract system ensures ExoArmur maintains core immutability while enabling controlled evolution through external layers.
