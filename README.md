# ExoArmur Core

ExoArmur is a deterministic governance runtime for autonomous and AI-driven systems. It makes decisions replayable, auditable, and enforceable under an immutable contract layer.

It is designed for teams building AI agents or autonomous workflows that require strict accountability, reproducibility, and policy enforcement.

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

ExoArmur Core is the invariant enforcement layer within a modular execution architecture. It sits between upstream decision systems and downstream execution targets, ensuring that execution remains deterministic, replayable, and independently verifiable.

Core deliberately separates intelligence from enforcement. Decision systems may evolve independently, but execution integrity and audit guarantees remain stable at this layer.

## Status

Architecture / Contract: v1.0.0 (stable)
Package (pip): 0.2.0

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

Editable installs (`pip install -e .`) are currently unsupported due to upstream packaging issues.

## CLI

```bash
exoarmur --help
```

## Quick Start (Infra-Free)

```bash
python examples/quickstart_replay.py
python -m pytest -q
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

V2 paths are gated scaffolding; defaults keep V2 disabled. See `docs/PHASE_STATUS.md` for current phase and expectations.

## Versioning Discipline

- Patch: bug fixes and documentation-only changes with no contract impact.
- Minor: additive, backward-compatible changes (feature-flagged by default) with updated docs.
- Major: any contract change or incompatible behavior (requires governance and updated Golden Demo alignment).
