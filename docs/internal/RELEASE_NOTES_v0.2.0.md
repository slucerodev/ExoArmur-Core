# ExoArmur Core v0.2.0 Release Notes

This document captures the release-time state for `v0.2.0` and should not be treated as the authoritative current-state status of `main`.

## Release Overview

ExoArmur Core v0.2.0 is a deterministic governance runtime for autonomous and AI-driven systems. This release establishes the foundation for replayable, auditable, and enforceable execution under an immutable contract layer.

## Key Features

### 🏗️ Deterministic Execution Pipeline
- **ProxyPipeline**: Sole execution boundary enforcing governance controls
- **PolicyDecisionPoint**: Deterministic policy evaluation and decision making
- **SafetyGate**: Explicit safety enforcement with configurable rules
- **Approval Workflow**: Human-in-the-loop approval for critical actions
- **ExecutorPlugin**: Untrusted capability module architecture
- **ExecutionTrace**: Complete audit trail with cryptographic evidence
- **ExecutionProofBundle**: Verifiable proof bundles for replay and compliance

### 🛡️ Governance Boundary
- **Immutable contracts**: V1 contracts are stable and never change
- **Deterministic guarantees**: Same inputs always produce identical outputs
- **Replayable evidence**: Complete reconstruction of any execution
- **CI invariant gates**: Automated enforcement of architectural integrity
- **Feature-flagged V2**: Safe, incremental capability adoption

### 🎭 Restrained Autonomy Demo
- **V2 governance pipeline**: Complete demo of operator approval workflow
- **Deterministic markers**: `DEMO_RESULT=DENIED`, `ACTION_EXECUTED=false`, `AUDIT_STREAM_ID=<stream-id>`
- **Replay functionality**: Full audit stream replay with verification
- **Feature flag controls**: Safe demonstration of V2 capabilities

## Installation

```bash
# Quick install
python -m venv .venv
source .venv/bin/activate
pip install exoarmur-core
```

V2 capabilities ship as separate installable packages (e.g.
`exoarmur-pod`, `exoarmur-bft`, `exoarmur-counterfactual`) that
register themselves via plugin entry points. There is no `[v2]` extras
group on `exoarmur-core` itself.

## Quick Start

```bash
# Basic CLI
exoarmur --help

# V2 Demo with governance
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
python scripts/demo_v2_restrained_autonomy.py --operator-decision deny
```

## Architecture

```
Gateway → ActionIntent → ProxyPipeline.execute_with_trace() → PolicyDecisionPoint → SafetyGate → Approval Workflow → ExecutorPlugin → ExecutionTrace → ExecutionProofBundle
```

## Key Invariants

- **ProxyPipeline is the sole execution boundary**
- **Executors are untrusted capability modules**
- **Execution must remain deterministic**
- **Evidence artifacts must be replayable**
- **CI invariant gates enforce integrity**

## What's New

### 🆕 v0.2.0 Features
- Complete deterministic execution pipeline
- V2 restrained autonomy demo
- Operator approval workflow
- Replayable audit trails
- Feature flag system for safe V2 adoption
- Comprehensive CI invariant gates
- Professional documentation and quick-start

### 🔧 Improvements
- Enhanced README with architecture diagrams
- Improved installation instructions
- Added V2 demo documentation
- Repository hygiene and cleanup
- Professional CI workflows

### 🛠️ Technical Details
- **Python**: >= 3.8 (tested on 3.12.x)
- **Dependencies**: 9 runtime dependencies, minimal footprint
- **CLI**: `exoarmur` and `v2-demo` entry points
- **Testing**: Comprehensive test suite with deterministic validation
- **CI**: 5 workflows ensuring quality and invariant enforcement

## Breaking Changes

None. This release maintains full backward compatibility with V1 contracts.

## Security & Compliance

- **Immutable audit trails**: Tamper-evident evidence chains
- **Deterministic replay**: Exact reconstruction of decisions
- **Operator approval**: Human oversight for critical actions
- **Feature flags**: Safe, incremental capability deployment
- **CI gates**: Automated enforcement of architectural integrity

## Known Limitations

- V2 capabilities are feature-flagged and disabled by default
- This document reflects release-time state; current editable-install behavior should be verified against the live `main` branch documentation and CI
- Golden Demo requires NATS JetStream + Docker infrastructure

## Future Roadmap

- Enhanced executor ecosystem
- Advanced policy decision frameworks
- Multi-cell coordination capabilities
- Extended compliance and reporting features

## Support

- **Documentation**: Complete README and inline documentation
- **Issues**: GitHub Issues for bug reports and feature requests
- **Community**: Open source core with optional proprietary modules

## Acknowledgments

This release represents a significant milestone in providing deterministic governance for autonomous systems. The architecture ensures that AI agents and autonomous workflows can operate with strict accountability, reproducibility, and policy enforcement while maintaining the highest standards of security and compliance.

---

**ExoArmur Core v0.2.0**: Deterministic governance for the autonomous age.
