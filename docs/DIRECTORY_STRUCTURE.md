# ExoArmur Project Directory Structure

This document provides the complete directory structure of the ExoArmur ADMO project, broken into manageable sections for clarity.

## Root Level Structure

```
.
├── .pytest_cache/
├── .windsurf/
├── docs/
├── spec/
├── artifacts/
├── tests/
├── .github/
├── src/
├── scripts/
├── nats-server-v2.10.9-linux-amd64/
├── BOOTSTRAP_REPORT.md
├── BUILD_PLAN.md
├── GOVERNANCE_HEALTH_REPORT.md
├── WORKFLOW_1_REPORT.md
├── WORKFLOW_2_SKELETON_LOCKED_REPORT.md
└── __init__.py
```

## Configuration and Workflow Files

### .windsurf/ - Development Workflows and Skills
```
.windsurf/
├── workflows/
│   └── exoarmur-workflows.md
├── rules/
│   └── (development rules)
└── skills/
    ├── contract-first-tests/
    │   └── SKILL.md
    ├── no-new-requirements/
    │   └── repo-triage-and-repair.md
    ├── execution-kernel-idempotency/
    │   └── SKILL.md
    ├── repo-triage-and-repair/
    │   └── SKILL.md
    ├── safety-gate-enforcement/
    │   └── SKILL.md
    ├── thin-vertical-slice/
    │   ├── SKILL.md
    │   └── thin-vertical-slice.md
    ├── policy-bundle-and-cache/
    │   ├── SKILL.md
    │   └── policy-bundle.md
    ├── golden-demo-flow/
    │   └── SKILL.md
    ├── spec-integrity-audit/
    │   └── SKILL.md
    ├── docs-consolidator.md
    ├── fastapi-router.md
    ├── policy-bundle.md
    ├── repo-triage.md
    ├── safe-execution.md
    └── test-skill.md
```

### .github/ - CI/CD Configuration
```
.github/
└── workflows/
    └── (GitHub Actions workflow files)
```

### .pytest_cache/ - Test Cache
```
.pytest_cache/
└── v/
    └── cache/
        └── (pytest cache files)
```

## Documentation

### docs/ - Project Documentation
```
docs/
├── specs/
│   └── EXOARMUR_MASTER_SPEC.yaml
├── Ingestion/
│   ├── AUTHORITY_BOUNDARIES.md
│   ├── DECISION_LIMITS.md
│   ├── EVENT_FLOW_MODEL.md
│   ├── NON_GOALS.md
│   ├── ORGANISM_MODEL.md
│   ├── PHASE_MODEL.md
│   ├── SAFETY_INVARIANTS.md
│   └── SYSTEM_OVERVIEW.md
├── ARCHITECTURE.md
├── CONTRACTS.md
├── dev_run.md
├── GOLDEN_DEMO_INTEGRITY.md
├── GOVERNANCE_HYGIENE.md
├── GOVERNANCE.md
├── ORGANISM_PRINCIPLES.md
├── PHASE_2B_FUTURE_CONTRIBUTOR_WARNING.md
├── PHASE_2B_GOVERNANCE_ASSERTIONS.md
├── PHASE_2B_PROTOCOL_LAW.md
├── PHASE_2B_TEST_ENFORCEMENT_MANIFEST.md
├── PHASE_GATE_IMPLEMENTATION.md
├── README.md
├── RUNBOOK.md
├── SPEC_UNDERSTANDING.md
├── TESTING.md
└── tests.md
```

## Specifications and Contracts

### spec/ - System Specifications
```
spec/
└── contracts/
    ├── schemas/
    │   └── (JSON schema files)
    ├── arbitration_precedence_v1.yaml
    ├── audit_federation_v2.yaml
    ├── control_plane_v2.yaml
    ├── coordination_non_goals.md
    ├── coordination_rationale.md
    ├── coordination_safety_invariants.md
    ├── coordination_v2.yaml
    ├── feature_flags_v2.yaml
    ├── federation_identity_v2.yaml
    ├── federation_v2.yaml
    ├── golden_demo_flow_v1.yaml
    ├── models_v1.py
    ├── nats_jetstream_v1.yaml
    ├── operational_defaults_v1.yaml
    ├── operator_approval_v2.yaml
    ├── policy_bundle_v1.yaml
    ├── README.md
    └── safety_gate_v1.yaml
```

### artifacts/ - Generated Artifacts
```
artifacts/
└── schemas/
    └── (generated schema artifacts)
```

## Source Code

### src/ - Main Source Code
```
src/
├── __init__.py
├── main.py
├── main_export.py
├── nats_client.py
├── api_models.py
├── analysis/
│   ├── __init__.py
│   └── facts_deriver.py
├── decision/
│   ├── __init__.py
│   └── local_decider.py
├── perception/
│   ├── __init__.py
│   └── validator.py
├── collective_confidence/
│   ├── __init__.py
│   └── aggregator.py
├── feature_flags/
│   ├── __init__.py
│   ├── config.py
│   └── feature_flags.py
├── core/
│   ├── __init__.py
│   └── phase_gate.py
├── control_plane/
│   ├── __init__.py
│   ├── approval_service.py
│   ├── control_api.py
│   └── operator_interface.py
├── federation/
│   ├── __init__.py
│   ├── federation_identity_manager.py
│   ├── federation_manager.py
│   ├── audit_interface.py
│   ├── identity_audit_emitter.py
│   ├── identity_handshake_state_machine.py
│   ├── identity_transcript_builder.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── federation_identity_v2.py
│   └── coordination/
│       ├── __init__.py
│       ├── coordination_audit_emitter.py
│       ├── coordination_models_v2.py
│       ├── coordination_state_machine.py
│       └── federation_coordination_manager.py
├── beliefs/
│   ├── __init__.py
│   └── belief_generator.py
├── safety/
│   ├── __init__.py
│   └── safety_gate.py
├── execution/
│   ├── __init__.py
│   └── execution_kernel.py
└── audit/
    ├── __init__.py
    └── audit_logger.py
```

## Tests

### tests/ - Test Suite
```
tests/
├── test_api_models.py
├── test_coordination_models_v2.py
├── test_coordination_state_machine.py
├── test_facts_derivation.py
├── test_federation_identity_integration.py
├── test_federation_identity_manager.py
├── test_federation_identity_models_v2.py
├── test_federation_v2_acceptance.py
├── test_golden_demo_flow.py
├── test_golden_demo_live.py
├── test_health.py
├── test_idempotency.py
├── test_identity_audit_emitter.py
├── test_identity_handshake_state_machine.py
├── test_identity_transcript_builder.py
├── test_integration.py
├── test_operator_approval_v2_acceptance.py
├── test_safety_gate.py
├── test_schema_snapshots.py
├── test_v2_feature_flag_isolation.py
└── (additional test files)
```

## Scripts and Tools

### scripts/ - Utility Scripts
```
scripts/
├── audit_integrity.py
├── export_openapi_and_schemas.py
├── validate_contracts.py
├── validate_contracts_simple.py
└── validate_spec_refs.py
```

### External Dependencies

### nats-server-v2.10.9-linux-amd64/ - NATS Server Binary
```
nats-server-v2.10.9-linux-amd64/
└── README.md
```

## Summary Statistics

- **Total Directories**: 47 main directories
- **Source Modules**: 15 primary modules in src/
- **Test Files**: 20+ test files
- **Contract Files**: 15+ specification contracts
- **Documentation Files**: 25+ documentation files
- **Skill Definitions**: 10+ development skills

## Key Architectural Observations

1. **Clean Separation**: Clear separation between source, tests, specs, and docs
2. **Modular Design**: Each functional area has its own module (analysis, decision, safety, etc.)
3. **Federation Layer**: Comprehensive federation implementation with V2 coordination
4. **Contract-First**: Extensive specification contracts before implementation
5. **Feature Flag Isolation**: Complete feature flag system for V2 capabilities
6. **Safety Focus**: Multiple safety and governance documents
7. **Workflow-Driven**: Development workflow definitions and skills

This structure supports the ADMO (Autonomous Defense Mesh Organism) architecture with clear boundaries between different system components and comprehensive governance documentation.
