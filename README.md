<p align="center">
  <img src="docs/assets/exoarmur-logo.png" width="180" />
</p>

# ExoArmur Core

**Audit-Verified — Beta**

ExoArmur Core is a deterministic execution safety substrate designed to enforce
guardrails, preserve auditability, and enable replayable decision verification
for automation and autonomous-adjacent systems.

This repository contains the open-core foundation of ExoArmur.

It does not implement autonomous behavior, orchestration logic, or response
automation. Those capabilities are intentionally excluded.

---

## What ExoArmur Core Provides

ExoArmur Core guarantees:

- Deterministic execution classification
- Durable event persistence
- Idempotent execution under retries
- Crash-consistent recovery
- Explicit safety enforcement (kill switches, approvals, tenant isolation)
- Bounded retries and backpressure
- Deterministic failure classification
- Replayable decision history from durable artifacts
- Cold-reviewer reproducibility

If ExoArmur Core permits or denies an action, that decision can be reproduced
later using only the recorded evidence bundle.

---

## What This Is Not

ExoArmur Core is intentionally **not**:

- an autonomous agent
- a decision-making intelligence
- a workflow orchestrator
- a SOAR or SIEM replacement
- a prompt-based system
- a real-time automation engine

All behavior layers are additive and out of scope for this repository.

---

## Project Status

**v1.0.0-beta**

The core execution substrate has undergone independent verification and
reproducibility review.

The core architecture is frozen.

Public interfaces may evolve based on early adopter feedback.

---

## Running the Core

### Requirements

- Docker
- Docker Compose

### Start the runtime

```bash
docker compose up -d
```

---

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install ExoArmur Core
pip install -e .

# Run tests
python -m pytest tests/ -v

# Run Golden Demo (live NATS JetStream acceptance test)
python -m pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

---

## Reality / Status

**WHAT EXISTS (V1):**
- V1 core is implemented and immutable
- Golden Demo uses real NATS JetStream semantics  
- Feature flags default OFF

**WHAT IS GATED (V2):**
- V2 scaffolding exists behind feature flags
- Optional extra: `pip install -e ".[v2]"`

**WHAT IS NOT IMPLEMENTED YET:**
- Federation logic not implemented
- Control plane logic not implemented  
- Operator orchestration runtime not implemented