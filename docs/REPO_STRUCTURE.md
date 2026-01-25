# ExoArmur Repository Structure

## Directory Overview

This document describes the complete repository structure as of the 2025-01-25 snapshot.

```
ExoArmur/
├── .git/                          # Git repository (excluded from distribution)
├── .github/                       # GitHub workflows
│   └── workflows/
│       ├── phase-0d-boundary-enforcement.yml
│       └── v2-demo-smoke.yml
├── .windsurf/                     # IDE configuration
│   └── workflows/
├── artifacts/                     # Generated artifacts and schemas
│   ├── schemas/                   # JSON schema definitions
│   │   ├── AuditRecordV1.json
│   │   ├── AuditResponseV1.json
│   │   ├── BeliefV1.json
│   │   └── [additional schemas]
│   └── openapi_v1.json           # OpenAPI specification
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md
│   ├── CONSTITUTION.md
│   ├── FEATURE_FLAGS.md
│   ├── PHASE_STATUS.md
│   ├── REPO_STRUCTURE.md
│   └── [additional documentation]
├── scripts/                      # Utility and demonstration scripts
│   ├── boundary_gate.py
│   ├── demo_handshake.py
│   ├── demo_identity_containment.py
│   ├── demo_v2_restrained_autonomy.py
│   └── [additional scripts]
├── spec/                         # Specifications and contracts
│   └── contracts/               # Data contracts and schemas
│       ├── arbitration_precedence_v1.yaml
│       ├── audit_federation_v2.yaml
│       ├── models_v1.py
│       └── [additional contracts]
├── src/                         # Source code
│   ├── analysis/                # Signal analysis components
│   │   ├── __init__.py
│   │   └── facts_deriver.py
│   ├── audit/                   # Audit logging and storage
│   │   ├── __init__.py
│   │   └── audit_logger.py
│   ├── beliefs/                 # Belief generation
│   │   ├── __init__.py
│   │   └── belief_generator.py
│   ├── collective_confidence/   # Decision aggregation
│   │   ├── __init__.py
│   │   └── aggregator.py
│   ├── feature_flags/           # Feature flag management
│   │   ├── __init__.py
│   │   └── feature_flags.py
│   ├── governance/              # Governance and policy
│   │   ├── __init__.py
│   │   └── governance_engine.py
│   ├── safety/                  # Safety gate and arbitration
│   │   ├── __init__.py
│   │   ├── safety_gate.py
│   │   └── arbitration_precedence.py
│   ├── v2/                      # Phase 2A threat classification
│   │   ├── __init__.py
│   │   └── threat_classification.py
│   ├── __init__.py
│   ├── api_models.py            # API data models
│   ├── cli.py                   # Command-line interface
│   ├── clock.py                 # Clock abstraction
│   ├── main.py                  # FastAPI application
│   └── [additional core modules]
├── tests/                       # Test suite
│   ├── conftest.py              # Test configuration
│   ├── factories.py             # Test factories
│   ├── federation_fixtures.py    # Federation test fixtures
│   ├── test_api_models.py
│   ├── test_constitutional_invariants.py
│   ├── test_boundary_enforcement.py
│   ├── test_replay_determinism.py
│   ├── test_threat_classification_v2.py
│   ├── test_v2_feature_flag_isolation.py
│   ├── test_v2_restrained_autonomy.py
│   └── [additional tests]
├── .gitignore                   # Git ignore patterns
├── conftest.py                  # Root test configuration
├── Makefile                     # Build and test commands
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Python dependencies
└── README.md                    # Project overview
```

## Key Components

### Source Code (`src/`)

**Core V1 Components (Immutable)**:
- `analysis/`: Signal facts derivation from telemetry
- `audit/`: Audit trail generation and storage
- `beliefs/`: Belief generation from signal facts
- `collective_confidence/`: Decision aggregation algorithms
- `safety/`: Safety gate with arbitration precedence

**V2 Components (Phase 2A)**:
- `v2/threat_classification.py`: Decision-only threat classification
- `feature_flags/`: Feature flag management for V2 capabilities
- `governance/`: Governance enforcement for V2 decisions

**Infrastructure**:
- `main.py`: FastAPI web application
- `api_models.py`: Pydantic data models
- `cli.py`: Command-line interface
- `clock.py`: Injectable clock for deterministic testing

### Contracts (`spec/contracts/`)

**V1 Contracts (Immutable)**:
- `models_v1.py`: Core ADMO data models
- `arbitration_precedence_v1.yaml`: Safety gate precedence rules

**V2 Contracts**:
- `audit_federation_v2.yaml`: V2 audit event schemas

### Tests (`tests/`)

**Constitutional Tests**:
- `test_constitutional_invariants.py`: V1 immutability verification
- `test_boundary_enforcement.py`: V1/V2 boundary validation
- `test_replay_determinism.py`: Deterministic replay verification

**Phase 2A Tests**:
- `test_threat_classification_v2.py`: Threat classification decision engine
- `test_v2_feature_flag_isolation.py`: Feature flag isolation
- `test_v2_restrained_autonomy.py`: V2 autonomy demo tests

**Integration Tests**:
- `test_integration.py`: End-to-end integration scenarios
- `test_api_models.py`: API model validation

### Scripts (`scripts/`)

**Demonstration Scripts**:
- `demo_v2_restrained_autonomy.py`: V2 restrained autonomy demo
- `demo_identity_containment.py`: Identity session containment demo
- `boundary_gate.py`: Boundary enforcement demonstration

**Utility Scripts**:
- `demo_handshake.py`: Handshake protocol demonstration

### Documentation (`docs/`)

**Core Documentation**:
- `ARCHITECTURE.md`: System architecture and boundaries
- `CONSTITUTION.md`: Constitutional rules and constraints
- `FEATURE_FLAGS.md`: Feature flag documentation
- `PHASE_STATUS.md`: Current implementation status

**Technical Documentation**:
- `AUDIT_EVENT_CATALOG.md`: Audit event specifications
- `REPLAY_PROTOCOL.md`: Deterministic replay protocol
- `GOVERNANCE.md`: Governance framework documentation

### Artifacts (`artifacts/`)

**Schemas**:
- JSON schema definitions for all data models
- OpenAPI specification for REST API
- Generated contract schemas

## Excluded from Distribution

The following directories are excluded from the ship-ready snapshot:
- `.git/`: Version control metadata
- `__pycache__/`: Python bytecode cache
- `.pytest_cache/`: Test cache
- `.mypy_cache/`: Type checking cache
- `.coverage/`: Code coverage reports
- `dist/`, `build/`: Build artifacts
- `*.egg-info/`: Python package metadata

## Dependencies

**Runtime Dependencies** (requirements.txt):
- FastAPI: Web framework
- Pydantic: Data validation
- NATS: Message streaming (for V2 coordination)
- Additional dependencies as specified

**Development Dependencies** (pyproject.toml):
- pytest: Test framework
- mypy: Type checking
- Additional development tools

This structure represents ExoArmur exactly as implemented on 2025-01-25, with no speculative additions or future-facing artifacts.
