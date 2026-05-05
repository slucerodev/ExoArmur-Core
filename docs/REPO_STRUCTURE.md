# ExoArmur Repository Structure

## Directory Overview

This document describes the repository structure for ExoArmur Core (v2.1.0), distributed as a private evaluation repository.

```
ExoArmur/
├── .github/                       # GitHub workflows and issue templates
│   ├── workflows/                # CI/CD workflows
│   │   ├── github-release.yml
│   │   ├── security-scan.yml
│   │   └── [additional workflows]
│   └── ISSUE_TEMPLATE/           # Issue templates
├── .windsurf/                     # IDE configuration
│   └── workflows/               # Cascade workflows
├── artifacts/                     # Generated artifacts and schemas
│   ├── openapi_v1.json          # OpenAPI specification (canonical)
│   └── schemas/                 # JSON schema definitions
├── dashboard/                     # Dashboard UI (separate repository, ignored)
├── demos/                        # Canonical governance demos
│   └── canonical_truth_reconstruction_demo.py  # Golden Demo (CI-verified)
├── docs/                         # Documentation (source of truth)
│   ├── ARCHITECTURE.md          # System architecture
│   ├── INSTALLATION.md          # Installation guide (private evaluation)
│   ├── PHASE_STATUS.md          # Implementation phase status
│   ├── REPO_STRUCTURE.md        # This file
│   ├── governance/              # Governance documentation
│   ├── internal/                # Internal development docs
│   ├── history/                 # Historical documentation
│   └── [additional documentation]
├── examples/                     # Standalone examples
│   ├── quickstart_replay.py     # Minimal replay example
│   └── [additional examples]
├── scripts/                      # Utility and demonstration scripts
│   ├── demo_api.py              # Demo API server
│   ├── test_demo_api.py         # Demo API tests
│   ├── quickstart.sh            # Quickstart script
│   └── [additional scripts]
├── spec/                         # Specifications and contracts
│   └── contracts/              # Data contracts and schemas
│       ├── models_v1.py         # V1 core contracts (locked)
│       ├── models_v2_*.py      # V2 contracts
│       └── [additional contracts]
├── src/                         # Source code
│   └── exoarmur/
│       ├── analysis/           # Signal analysis
│       ├── api_models.py       # API data models
│       ├── approval/           # Approval workflows
│       ├── audit/              # Audit logging
│       ├── auth/               # Authentication
│       ├── beliefs/            # Belief generation
│       ├── benchmark/         # Benchmarking
│       ├── boundary/           # Boundary enforcement
│       ├── causal/             # Causal reasoning
│       ├── cli.py              # Command-line interface
│       ├── clock.py            # Clock abstraction
│       ├── collective_confidence/  # Decision aggregation
│       ├── control_plane/      # Control plane implementation
│       ├── core/               # Core phase gate
│       ├── counterfactual/     # Counterfactual reasoning
│       ├── decision/           # Decision engines
│       ├── execution/          # Execution kernel
│       ├── execution_boundary_v2/  # V2 execution boundary
│       ├── feature_flags/      # Feature flag management
│       ├── federation/         # Federation layer
│       ├── identity_containment/  # Identity session containment
│       ├── ids.py              # ID generation
│       ├── integration/        # Integration components
│       ├── interfaces/         # Interface definitions
│       ├── main.py             # FastAPI application
│       ├── nats_client.py      # NATS client
│       ├── observability/      # Observability
│       ├── perception/         # Perception layer
│       ├── plugins/            # Plugin registry
│       ├── proof/              # Proof generation
│       ├── quickstart/         # Quickstart implementation
│       ├── reliability/        # Reliability (circuit breaker)
│       ├── replay/             # Replay engine
│       ├── safety/             # Safety gate
│       ├── sdk/                # SDK
│       ├── stability/          # Stability testing
│       ├── telemetry/          # Telemetry ingestion
│       ├── tenancy/            # Multi-tenancy
│       └── v2_restrained_autonomy/  # V2 restrained autonomy
├── tests/                       # Test suite
│   ├── conftest.py             # Test configuration
│   ├── factories.py            # Test factories
│   ├── test_*.py              # Test files (130+ tests)
│   └── [additional tests]
├── tools/                        # Export + boundary enforcement tooling
│   └── [tooling scripts]
├── .gitignore                   # Git ignore patterns
├── .pre-commit-config.yaml      # Pre-commit hooks
├── .gitleaks.toml              # Secret scanning config
├── conftest.py                  # Root test configuration
├── Dockerfile                   # Docker configuration
├── docker-compose.yml          # Docker compose
├── LICENSE                      # Apache License 2.0
├── Makefile                     # Build and test commands
├── PROJECT_STATUS.md           # Project status
├── pyproject.toml              # Python project configuration
├── requirements.txt             # Python dependencies
├── requirements-quickstart.txt # Quickstart dependencies
├── README.md                   # Project overview
├── CHANGELOG.md                # Changelog
├── CONTRIBUTING.md             # Contributing guidelines (authorized evaluators)
└── SECURITY.md                 # Security policy
```

## Key Components

### Source Code (`src/exoarmur/`)

**Core V1 Components (Locked - Immutable)**:
- `analysis/`: Signal facts derivation from telemetry
- `audit/`: Audit trail generation and storage
- `beliefs/`: Belief generation from signal facts
- `collective_confidence/`: Decision aggregation algorithms
- `safety/`: Safety gate with arbitration precedence
- `execution/`: Execution kernel

**V2 Components (Feature-Flag Gated)**:
- `execution_boundary_v2/`: V2 execution boundary with ProxyPipeline
- `federation/`: Multi-cell federation layer
- `control_plane/`: Control plane (operator auth, approval workflows)
- `decision/`: Decision engines (threat classification)
- `approval/`: Approval workflows
- `identity_containment/`: Identity session containment
- `counterfactual/`: Counterfactual reasoning (placeholder for module)
- `causal/`: Causal reasoning (placeholder for module)

**Infrastructure**:
- `main.py`: FastAPI web application
- `api_models.py`: Pydantic data models
- `cli.py`: Command-line interface
- `clock.py`: Injectable clock for deterministic testing
- `ids.py`: ID generation (ULID-based)
- `nats_client.py`: NATS message streaming client
- `plugins/`: Plugin registry for external modules
- `feature_flags/`: Feature flag management

**Supporting Components**:
- `boundary/`: Boundary enforcement
- `replay/`: Replay engine
- `proof/`: Proof bundle generation
- `benchmark/`: Benchmarking
- `reliability/`: Circuit breaker and reliability
- `stability/`: Stability testing
- `observability/`: Observability
- `telemetry/`: Telemetry ingestion
- `tenancy/`: Multi-tenancy support
- `auth/`: Authentication
- `sdk/`: SDK interfaces
- `integration/`: Integration components

### Contracts (`spec/contracts/`)

**V1 Contracts (Locked - Immutable)**:
- `models_v1.py`: Core data models (TelemetryEventV1, BeliefV1, etc.)

**V2 Contracts**:
- `models_v2_*.py`: V2 contract models (ExecutionProofBundle, etc.)
- Additional V2 contract YAML files

### Tests (`tests/`)

**Constitutional Tests**:
- `test_constitutional_invariants.py`: V1 contract-lock verification
- `test_replay_determinism.py`: Deterministic replay verification
- `test_golden_demo_live.py`: Golden Demo live execution

**V2 Tests (Feature-Flag Gated)**:
- `test_threat_classification_v2.py`: Threat classification decision engine
- `test_v2_feature_flag_isolation.py`: Feature flag isolation
- `test_v2_restrained_autonomy.py`: V2 restrained autonomy
- `test_federation_*.py`: Federation layer tests
- `test_control_plane_*.py`: Control plane tests

**Integration Tests**:
- `test_api_models.py`: API model validation
- `test_replay_bundle.py`: CLI replay bundle tests
- `test_demo_*.py`: Demo integration tests

### Scripts (`scripts/`)

**Demonstration Scripts**:
- `quickstart.sh`: Quickstart script for evaluators
- `demo_api.py`: Demo API server
- `test_demo_api.py`: Demo API tests

**Utility Scripts**:
- Various utility scripts for testing and validation

### Demos (`demos/`)

- `canonical_truth_reconstruction_demo.py`: Golden Demo (CI-verified deterministic proof of execution boundary)

### Documentation (`docs/`)

**Core Documentation (Source of Truth)**:
- `INSTALLATION.md`: Installation guide (private evaluation)
- `PHASE_STATUS.md`: Implementation phase status
- `ARCHITECTURE.md`: System architecture and boundaries
- `FEATURE_FLAGS.md`: Feature flag documentation
- `REPO_STRUCTURE.md`: This file
- `DISTRIBUTION_NOTICE.md`: Distribution notice (proprietary evaluation)

**Technical Documentation**:
- `AUDIT_EVENT_CATALOG.md`: Audit event specifications
- `REPLAY_PROTOCOL.md`: Deterministic replay protocol
- `GOVERNANCE.md`: Governance framework documentation
- `CONSTITUTION.md`: Constitutional rules and constraints
- `CONTRACTS.md`: Contract documentation

**Governance Documentation**:
- `governance/`: Governance-specific documentation
- `internal/`: Internal development documentation
- `history/`: Historical documentation

**Historical Documentation**:
- `LAUNCH_COPY.md`: Historical launch copy (marked as historical)
- `outreach_emails.md`: Historical outreach emails (marked as historical)

### Artifacts (`artifacts/`)

**Canonical Artifacts**:
- `openapi_v1.json`: OpenAPI specification (canonical)
- `schemas/`: JSON schema definitions

## Documentation Source of Truth

The following documentation files are the source of truth for their respective domains:

- **Installation**: `docs/INSTALLATION.md` (not README.md)
- **Phase Status**: `docs/PHASE_STATUS.md` (not PROJECT_STATUS.md)
- **Repository Structure**: `docs/REPO_STRUCTURE.md` (this file)
- **Architecture**: `docs/ARCHITECTURE.md`
- **Feature Flags**: `docs/FEATURE_FLAGS.md`
- **Contracts**: `spec/contracts/` directory

Historical documentation in `docs/history/` and files marked with historical notes (e.g., `LAUNCH_COPY.md`, `outreach_emails.md`) are preserved for reference but do not represent current posture.

## Distribution

ExoArmur Core is distributed as a private evaluation repository. Installation requires authorized access to this repository. See `docs/INSTALLATION.md` for installation instructions.

## Dependencies

**Runtime Dependencies** (requirements.txt):
- FastAPI: Web framework
- Pydantic: Data validation
- NATS: Message streaming (for V2 coordination)
- Additional dependencies as specified in pyproject.toml

**Development Dependencies** (pyproject.toml):
- pytest: Test framework
- Additional development tools

## Test Coverage

Current test coverage: 1,166 passing · 10 skipped · 3 xfailed · 0 failures

See `docs/PHASE_STATUS.md` for detailed test breakdown.

This structure represents ExoArmur Core v2.1.0 as of April 2026.
