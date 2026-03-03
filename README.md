# ExoArmur Core

Deterministic governance and replay infrastructure for auditable execution. ExoArmur Core freezes decisions into immutable intents, enforces safety and tenant isolation gates, and produces replayable audit trails that can be verified independently. It does not generate autonomous behavior; it verifies and governs execution downstream of external decision sources.

## Architectural Role

ExoArmur Core is the deterministic governance layer within a modular execution architecture. It is designed to sit beneath higher-order automation, orchestration, and analysis systems, ensuring that execution remains invariant-bound, replayable, and independently verifiable regardless of the upstream decision source.

Core intentionally separates enforcement from intelligence. Decision-making systems may evolve independently, but execution integrity and audit guarantees remain stable at this layer. It enforces invariants, produces replayable evidence, and makes downstream execution verifiable. Optional proprietary modules can extend capabilities, but the governance core remains OSS and contract-stable.

## Status

Architecture / Contract: v1.0.0 (stable)
Package (pip): 0.2.0

The core architecture is contract-stable. Public interfaces evolve only through test-verified changes.

## What ExoArmur Core Provides

- Deterministic IDs and replayable audit chains
- JetStream publish/consume paths for audit evidence
- Idempotent audit emission with bounded retries and backpressure
- Explicit safety enforcement (kill switches, approvals, tenant isolation)

## What This Is Not

- An autonomous agent or decision-maker
- A workflow orchestrator or SOAR/SIEM replacement
- A prompt-based or real-time automation engine

## Installation

### Requirements

- Python >= 3.8 (CI tested on 3.12.x)

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

## Versioning Discipline

- Patch: bug fixes and documentation-only changes with no contract impact.
- Minor: additive, backward-compatible changes (feature-flagged by default) with updated docs.
- Major: any contract change or incompatible behavior (requires governance and updated Golden Demo alignment).
