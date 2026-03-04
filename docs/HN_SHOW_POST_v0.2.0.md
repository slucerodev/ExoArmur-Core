rootTitle:
Show HN: ExoArmur — Deterministic Governance Runtime for AI Agents (v0.2.0)

## Problem

AI agents and autonomous workflows execute decisions that must be accountable after the fact. Most stacks lack deterministic replay and audit guarantees, so execution truth is hard to prove. Without immutable boundaries, enterprises cannot easily demonstrate what happened or enforce the limits they intended.

## What ExoArmur Does

ExoArmur executes decisions under immutable governance contracts and emits verifiable audit artifacts. It keeps decision paths replayable and enforces phase-gated capability boundaries, so expansions stay controlled. The Core remains stable while advanced capabilities are explicitly gated.

## 5-Minute Install Proof

python -m venv .venv
source .venv/bin/activate
python -m pip install .
exoarmur --help
python examples/quickstart_replay.py

Quickstart prints:
Replay result: success

## What Exists Today

- Core governance runtime
- Replay + audit
- Feature flags + phase gating
- CI packaging smoke
- Snapshot-gated OpenAPI

## What Is Intentionally Gated

- Federated / V2 capabilities
- Live Golden Demo requires NATS JetStream
- Acceptance tests xfailed intentionally

## Known Limitations

- Requires Python 3.12+
- Golden Demo requires JetStream
- Not an orchestration framework

## Feedback Requested

- Architecture critique
- Determinism edge cases
- Replay model feedback
- Governance boundary clarity
