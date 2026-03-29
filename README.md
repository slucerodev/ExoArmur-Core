# ExoArmur - AI Agent Governance Framework

ExoArmur is an AI agent governance framework that provides deterministic governance runtime for autonomous and AI-driven systems. It makes decisions replayable, auditable, and enforceable under an immutable contract layer with comprehensive audit trails and safety checks.

It is designed for teams building AI agents or autonomous workflows that require strict accountability, reproducibility, and policy enforcement.

## Why AI Agent Governance?

AI agents are making autonomous decisions in production environments without proper oversight. ExoArmur provides the governance framework needed for safe AI agent deployment through:

- **Audit Trail**: Complete decision logging for compliance and debugging
- **Safety Checks**: Pre-execution validation and policy enforcement
- **Replay System**: Deterministic replay of autonomous decisions
- **Risk Management**: Controlled execution with approval workflows

## What It Does

- Executes decisions under immutable governance contracts
- Produces verifiable audit records
- Enables deterministic replay of decision paths
- Enforces phase-gated and feature-flag boundaries
- Provides a stable Core with gated V2 capability scaffolding

## What It Is Not

- Not an orchestration framework
- Not an LLM agent framework
- Not a general workflow engine
- Not a distributed systems research project

## Architectural Role

ExoArmur Core is the invariant enforcement layer within a modular execution architecture. It sits between upstream decision systems and downstream execution targets, ensuring that autonomous system execution remains deterministic, replayable, and independently verifiable through proper governance and audit trails.

Core deliberately separates intelligence from enforcement. Decision systems may evolve independently, but execution integrity and audit guarantees remain stable at this layer.

### Execution Pipeline

```
Gateway → ActionIntent → ProxyPipeline.execute_with_trace() → PolicyDecisionPoint → SafetyGate → Approval Workflow → ExecutorPlugin → ExecutionTrace → ExecutionProofBundle
```

### Key Architectural Invariants

- **ProxyPipeline is the sole execution boundary** - All actions must pass through this governance boundary
- **Executors are untrusted capability modules** - Treated as external, sandboxed components
- **Execution must remain deterministic** - Same inputs always produce identical outputs
- **Evidence artifacts must be replayable** - Audit trails enable exact reconstruction of decisions
- **CI invariant gates enforce integrity** - Automated checks preserve architectural guarantees

### Feature Flags & V2 Capabilities

V2 capabilities are gated behind feature flags to ensure safe, incremental adoption:

- `v2_federation_enabled` - Enables multi-cell coordination
- `v2_control_plane_enabled` - Activates governance control plane
- `v2_operator_approval_required` - Requires human approval for actions

V2 defaults to disabled - Core remains fully functional without any V2 features.

## Status

Architecture / Contract: v1.0.0 (stable)
Package (pip): 0.3.0

The core architecture is contract-stable. Public interfaces evolve only through test-verified changes.

## Installation

### Requirements

- Python >= 3.8 (CI tested on 3.12.x)

### Testing prerequisites

- Pytest is a **dev** dependency (not installed with runtime deps).
- Minimal test setup:

```bash
python -m pip install pytest pytest-asyncio
python -m pytest -q
```

- Optional dev extra (installs pytest + async support):

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

- Golden Demo is optional and requires NATS JetStream + Docker; if you skip it, the rest of the suite still runs.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
pip install ".[v2]"   # optional extras
```

Editable installs (`pip install -e .` and `pip install -e ".[v2]"`) are supported for current development and CI validation.

### Import Surface

- Runtime and CLI imports should use the installed `exoarmur.*` namespace.
- V1 contracts are available via `exoarmur.spec.contracts.models_v1`.
- `spec.contracts.models_v1` remains available as an installed compatibility surface for existing V1 consumers.
- Repo-root compatibility shims such as `main.py` and `models_v1.py` are not installed package entry points and should not be treated as canonical imports.

## 5-Minute Proof

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
exoarmur --help
python examples/quickstart_replay.py
```

## CLI

```bash
exoarmur --help
```

## Quick Start (Infra-Free)

```bash
python examples/quickstart_replay.py
python -m pytest -q
```

## AI Agent Framework Integration

ExoArmur integrates with existing AI agent frameworks as a governance layer, adding audit trails and safety checks to autonomous decision making without requiring changes to your existing agent architecture.

## V2 Restrained Autonomy Demo

The V2 demo shows ExoArmur's governance pipeline with operator approval:

```bash
# Enable V2 capabilities and run demo with deny decision
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
python scripts/demo_v2_restrained_autonomy.py --operator-decision deny
```

**Expected Output Markers:**
```
DEMO_RESULT=DENIED
ACTION_EXECUTED=false
AUDIT_STREAM_ID=<stream-id>
```

**Replay the audit stream:**
```bash
python scripts/demo_v2_restrained_autonomy.py --replay <AUDIT_STREAM_ID>
```

## Live Golden Demo (Requires NATS JetStream)

Requirements:
- Docker
- Docker Compose
- Running NATS JetStream server

```bash
docker compose up -d
EXOARMUR_LIVE_DEMO=1 python -m pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

## OpenAPI Snapshot Governance

- Snapshot file: `artifacts/openapi_v1.json`
- Regenerate: `python scripts/export_openapi_and_schemas.py`
- CI enforces contract stability via snapshot tests.

## Architecture Principles

- Determinism
- Explicit safety enforcement
- Replay-verifiable audit chains
- Phase-gated feature activation

## Optional Proprietary Modules

Core is fully functional on its own. Optional proprietary modules can extend capabilities but are not required and remain opt-in.

## V2 status

V2 paths are gated scaffolding; defaults keep V2 disabled. `docs/PHASE_STATUS.md` is a historical phase snapshot rather than the authoritative current-state status page for `main`.

## Versioning Discipline

- Patch: bug fixes and documentation-only changes with no contract impact.
- Minor: additive, backward-compatible changes (feature-flagged by default) with updated docs.
- Major: any contract change or incompatible behavior (requires governance and updated Golden Demo alignment).

## How This Project Has Been Validated

### Installation Verification
```bash
pip install .  # Clean package installation from source
```

### CLI Verification
```bash
exoarmur --version  # Returns consistent version across all components
```

### Quickstart Replay Example
```bash
python examples/quickstart_replay.py  # Demonstrates deterministic replay functionality
```

### Demo Execution Path
```bash
exoarmur demo --operator-decision deny  # V2 restrained autonomy with human approval
```

### Deterministic Demo Markers
The V2 demo produces verifiable output markers:
- `DEMO_RESULT=DENIED` - Action approval decision
- `ACTION_EXECUTED=false` - Execution status  
- `AUDIT_STREAM_ID=<stream-id>` - Replayable audit stream identifier

### CI Invariant Gate Enforcement
- Core invariant gates prevent architectural violations
- Automated enforcement of ProxyPipeline execution boundary
- Deterministic replay verification through test suites
- Schema stability checks prevent contract drift

### Current Verified Lanes
- `pip install .` in a fresh isolated environment
- `pip install -e .` in a fresh isolated environment
- `pip install -e ".[v2]"` with the V2 deny demo
- `tests/test_v2_restrained_autonomy.py` with 18 passing tests

### Reproducible Release Notes
- `RELEASE_NOTES_v0.2.0.md` provides complete release documentation
- Release notes capture release-time state and should not be treated as the current status of `main`
- Demo output markers provide deterministic proof points

### Transparency Statement
This project has been validated through continuous integration and deterministic demo execution. All functionality claims are supported by reproducible artifacts in the repository. External independent validation is encouraged - the complete test suite and demo markers provide verification capability for any interested party.

## Documentation

### Architecture Overview
- Architecture Overview → docs/ARCHITECTURE_SIMPLE.md
- Design Principles → docs/DESIGN_PRINCIPLES.md
- Validation Guide → VALIDATE.md
- Reviewer Checklist → docs/REVIEW_CHECKLIST.md
- Technical Systems Paper → docs/EXOARMUR_SYSTEMS_PAPER.md
