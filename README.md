<p align="center">
  <img src="docs/assets/exoarmur-logo.png" width="180" />
</p>

# ExoArmur Core

**Deterministic & Auditable — Beta**

ExoArmur Core is a deterministic execution safety substrate designed to enforce
guardrails, preserve auditability, and enable replayable decision verification
for automation and autonomous-adjacent systems.

This repository contains the open-core foundation of ExoArmur.

It does not implement autonomous behavior, orchestration logic, or response
automation. Those capabilities are intentionally excluded.

---

## What ExoArmur Core Provides

ExoArmur Core provides (as verified by tests in this repository):

- Deterministic IDs for facts, decisions, beliefs, and execution intents
- JetStream publish/consume paths for beliefs and audit records
- Idempotency enforcement for audit emission
- Explicit safety enforcement (kill switches, approvals, tenant isolation)
- Bounded retries and backpressure (phase 6 tests)
- Replay and determinism tests for audit chains
- Offline evidence bundle export compatible with ExoArmur-DPO

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

The core architecture is frozen. Public interfaces change only when verified
and documented by tests in this repository.

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
pip install .

# Run tests
python -m pytest tests/ -v

# Run Golden Demo (live NATS JetStream acceptance test)
EXOARMUR_LIVE_DEMO=1 python -m pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

### Developer Note: editable installs
- Affects: `pip install -e .` only (editable installs)
- Symptom: `packaging.version.InvalidVersion: ''` during dependency marker evaluation on Python 3.12
- Cause: upstream pip/importlib issue; not caused by ExoArmur-Core packaging
- Status: No verified workaround at this time; editable installs are currently non-functional
- Production/CI: unaffected (non-editable installs and wheels work normally)

---

## Reality / Status

**WHAT EXISTS (V1):**
- V1 core is implemented and immutable
- Live Golden Demo exercises JetStream publish/consume and audit flow
- Feature flags default OFF

**WHAT IS GATED (V2):**
- V2 scaffolding exists behind feature flags
- Optional extra: `pip install -e ".[v2]"`

**WHAT IS NOT IMPLEMENTED YET:**
- Federation control plane orchestration runtime (beyond test scaffolding)
- Full operator orchestration runtime

**DPO INTEGRATION (OFFLINE):**
- Core can export deterministic evidence bundles to filesystem
- ExoArmur-DPO can verify these bundles offline

## Audit vs Logging
- Audit artifacts (AuditRecordV1 and related envelopes) are authoritative, immutable evidence for decisions.
- Logging is diagnostic and non-authoritative; logs cannot substitute for audit artifacts.
- Audits must remain replayable; logging content must not be treated as proof of behavior.

## Versioning Discipline
- Patch: bug fixes and documentation-only changes with no contract impact.
- Minor: additive, backward-compatible changes (feature-flagged by default) with updated docs.
- Major: any contract change or incompatible behavior (requires governance and updated Golden Demo alignment).
