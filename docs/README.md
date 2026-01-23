# ExoArmur ADMO Documentation

ExoArmur Autonomous Defense Mesh Organism (ADMO) is an enterprise-grade autonomous defense platform that ingests telemetry, correlates threats, evaluates policy, decides actions, and executes responses with safety rails, auditability, and optional human approval gates.

## Current Status Snapshot

**Phase 1.5 State:**
- ✅ **V1 Accepted & Immutable**: Core cognition loop, Golden Demo, and all V1 contracts are locked and fully functional
- 🚧 **V2 Scaffolding**: Federation and control plane contracts created with inert stub implementations
- 🔒 **Strict Governance**: Zero pytest.skip, zero skipped tests, strict xfail for future gates only
- ✅ **Live Golden Demo**: V1 Golden Demo passes with live NATS JetStream (mandatory regression gate)

## What Exists Today

### V1 Core (Immutable)
- **Cognition Pipeline**: Telemetry → SignalFacts → Belief → CollectiveConfidence → SafetyGate → ExecutionIntent → Audit
- **Golden Demo**: End-to-end live test proving V1 functional requirements
- **Contracts**: 7 V1 contract files defining data models, messaging, policy, and safety
- **Safety System**: Deterministic safety gates with arbitration precedence

### V2 Scaffolding (Additive Only)
- **Federation Layer**: Multi-cell federation protocols (not implemented)
- **Control Plane**: Operator approval workflows (not implemented)
- **Feature Flags**: All V2 flags default OFF, inert when disabled
- **Acceptance Tests**: 15 tests marked xfail(strict=True) as future gates

## Quick Links

- [Governance](GOVERNANCE.md) - Binary green definition, testing policies
- [Runbook](RUNBOOK.md) - Local setup and validation procedures
- [Architecture](ARCHITECTURE.md) - V1 core vs V2 external layers
- [Contracts](CONTRACTS.md) - V1 and V2 contract index
- [Testing](TESTING.md) - Test taxonomy and V2 acceptance gates

## Golden Demo Law

**The V1 Golden Demo is the mandatory regression gate for all changes.**

- `tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream` must ALWAYS pass
- No modification to V1 cognition pipeline behavior is permitted
- V2 features must remain inert and never interfere with V1 operations
- Any change causing Golden Demo failure is a hard blocker

## Getting Started

1. [Set up local environment](RUNBOOK.md#local-setup)
2. [Run validation suite](RUNBOOK.md#validation-suite)
3. [Review architecture boundaries](ARCHITECTURE.md)
4. [Understand testing strategy](TESTING.md)

## Development Philosophy

ExoArmur follows strict governance with binary outcomes:
- **Green**: 0 failed, 0 errors, 0 skipped
- **V1 Immutable**: Core cognition loop never changes
- **V2 Additive**: New features are external layers only
- **Feature Flags**: Default OFF, require explicit enablement

This ensures the autonomous defense mesh remains reliable, auditable, and safe while enabling controlled evolution through external layers.
