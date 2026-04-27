# ExoArmur Core

[![CI](https://github.com/slucerodev/ExoArmur-Core/actions/workflows/core-invariant-gates.yml/badge.svg)](https://github.com/slucerodev/ExoArmur-Core/actions/workflows/core-invariant-gates.yml)
[![PyPI](https://img.shields.io/pypi/v/exoarmur-core)](https://pypi.org/project/exoarmur-core/)
[![Python](https://img.shields.io/pypi/pyversions/exoarmur-core)](https://pypi.org/project/exoarmur-core/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.1.0-green)](https://github.com/slucerodev/ExoArmur-Core/releases)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Codespaces-purple)](https://codespaces.new/slucerodev/ExoArmur-Core)

**A governance layer for AI agents that enforces policy before execution, produces cryptographic audit trails, and enables deterministic replay.**

ExoArmur sits between your AI decision layer and execution targets. It ensures every action is:
- **Policy-gated** — evaluated before it runs
- **Auditable** — cryptographically traceable to original intent
- **Replayable** — deterministic reconstruction of execution traces
- **Approvable** — can be queued for human operator review

🚀 **[Try the Live Demo](https://codespaces.new/slucerodev/ExoArmur-Core)** — One-click browser environment, no installation needed.

> **Status (April 2026):** Single-maintainer reference implementation. CI invariant
> gates enforce determinism, module boundaries, and three-run stability. No external
> audit yet. Seeking first pilot integration. See [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
> for full detail.

---

## Quick Start

Install and run in 30 seconds:

```bash
pip install exoarmur-core
python examples/quickstart_replay.py
```

**Expected output:** `Replay result: success`

For a guided setup with verification, run:
```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
./scripts/quickstart.sh
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for detailed instructions.

---

## Integration Example

The primary public API is the deterministic replay engine:

```python
from exoarmur import ReplayEngine
from exoarmur.replay.event_envelope import CanonicalEvent
import hashlib, json

# Construct a canonical event with cryptographic payload hash
payload = {"kind": "inline", "ref": {"event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"}}
event = CanonicalEvent(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="belief_creation_started",
    actor="demo",
    correlation_id="corr-1",
    payload=payload,
    payload_hash=hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest(),
)

# Replay deterministically from the audit trail
engine = ReplayEngine(audit_store={"corr-1": [event]})
report = engine.replay_correlation("corr-1")
print("Replay result:", getattr(report.result, "value", report.result))
print("Failures:", report.failures or "none")
```

**Note:** The V2 execution boundary (`ProxyPipeline`, `ActionIntent`) is an internal implementation detail. For agent framework integrations, see the examples in the `examples/` directory.

---

## Golden Demo (Full Governance Pipeline)

The canonical demo exercises the complete execution boundary: policy evaluation, denial before side effects, audit trail emission, and cryptographic replay verification.

```bash
pip install exoarmur-core
python demos/canonical_truth_reconstruction_demo.py
```

**Expected output** (deterministic, identical across runs):
```
Proof bundle written: .../demos/canonical_proof_bundle.json
Proof bundle replay hash: 7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b
DEMO_RESULT=DENIED
ACTION_EXECUTED=false
AUDIT_STREAM_ID=canonical-truth-reconstruction-demo
REPLAY_VERDICT=PASS
```

This demo runs in CI on every push — see [`.github/workflows/v2-demo-smoke.yml`](.github/workflows/v2-demo-smoke.yml).

---

## 5-Minute Proof

Or try the replay engine inline:

```python
from exoarmur import ReplayEngine
from exoarmur.replay.event_envelope import CanonicalEvent
import hashlib, json

payload = {"kind": "inline", "ref": {"event_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV"}}
event = CanonicalEvent(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="belief_creation_started",
    actor="demo",
    correlation_id="corr-1",
    payload=payload,
    payload_hash=hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest(),
)
engine = ReplayEngine(audit_store={"corr-1": [event]})
report = engine.replay_correlation("corr-1")
print("Replay result:", getattr(report.result, "value", report.result))
print("Failures:", report.failures or "none")
```

Run the full suite (1166 tests, three-run stability gate) with the same dependency set CI uses:

```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
pip install -r requirements.lock           # exact CI-pinned runtime deps
pip install --no-deps -e ".[dev]"          # editable install + dev extras
python -m pytest -q
```

The two-step install is deliberate: `requirements.lock` pins every runtime
dependency (including `fastapi==0.127.1` and `pydantic==2.12.5`) to the
exact versions the committed OpenAPI snapshot was generated against, and
`--no-deps` prevents `pip` from silently upgrading them when applying the
`dev` extras. This is the same sequence every CI workflow uses — see
[`.github/workflows/core-invariant-gates.yml`](.github/workflows/core-invariant-gates.yml).

---

## What It Does

ExoArmur sits between your AI decision layer and execution targets. It enforces that every action:

- Passes a **policy decision point** before it runs
- Produces a **cryptographic audit trail** tied to the original intent
- Is **deterministically replayable** — same inputs always reconstruct the same trace
- Can be **vetoed or queued** for operator approval

```
Decision Source → ActionIntent → PolicyDecisionPoint → SafetyGate → [Approval?] → Executor → ExecutionProofBundle
```

## What It Is Not

- Not an LLM or agent framework
- Not a general workflow engine
- Not a distributed systems platform

ExoArmur is a **governance and accountability layer** that wraps whatever agent framework you already use.

## Capabilities and Limitations

Honest disclosure of what this system does and does not provide:

**What it provides:**
- Deterministic execution boundary enforcement via `ProxyPipeline`
- Cryptographic audit trails with SHA-256 payload hashes and Ed25519 signatures
- Three-run deterministic replay verification with CI-enforced stability
- Cross-node replay determinism verification with adversarial input corruption testing
- A/B replay diffing (counterfactual engine) — compares original vs modified replay outputs
- Plane isolation enforced at import-time by dependency edge guards
- Idempotent audit ingestion with deterministic content-addressed keys

**What it does not provide (known limitations):**
- **Not Byzantine Fault Tolerance (BFT)** — the fault injection system verifies replay determinism under corrupted inputs, not consensus under malicious nodes
- **Not causal inference** — the counterfactual engine performs deterministic replay diffing, not statistical causal analysis
- **Trust evaluator is a stub** — currently returns a fixed trust score of `0.85` regardless of input; see `src/exoarmur/safety/trust_evaluator.py` for TODO list
- **Only mock executor ships** — `MockActionExecutor` is the only bundled executor; real integrations must be written as `ExecutorPlugin` implementations
- **Single-node in-memory stores** — default `IntentStore` and `FederateIdentityStore` are in-memory; durable Postgres/JetStream backends require manual configuration
- **Federation is feature-flag gated** — multi-cell coordination requires `EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true`

## Architecture

| Layer | Path | Purpose |
|---|---|---|
| Core engine | `src/exoarmur/` | Deterministic replay, audit, policy enforcement |
| V2 governance | `src/exoarmur/execution_boundary_v2/` | ProxyPipeline, approval workflow, executor boundary |
| Contracts | `spec/contracts/` | Immutable V1 data shapes |
| Examples | `examples/` | Quickstart and demo scripts |

**Key invariants:**
- ProxyPipeline is the sole execution boundary — all actions route through it
- Executors are sandboxed, untrusted plugins
- Determinism is enforced by CI — three-run stability gate on every push
- V1 contracts are immutable — new capabilities are additive and feature-flag gated

### Feature Flags

V2 capabilities default to **off**:

| Flag | Purpose |
|---|---|
| `EXOARMUR_FLAG_V2_FEDERATION_ENABLED` | Multi-cell coordination |
| `EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED` | Governance control plane |
| `EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED` | Human approval gate |

## Benchmark Proof

Validate deterministic execution under high concurrency:

```bash
exoarmur benchmark --determinism-load --runs 100 --concurrency 500
```

Expected output:
```
DETERMINISM
-----------
Concurrency: 500
Executions: 100
Unique Hashes: 1
STATUS: PASS
```

This proves that hash consistency holds even under extreme concurrent load. See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for full benchmark suite documentation.

## CI

Every push runs:
- **Core Invariant Gates** — three deterministic test runs, boundary enforcement, repo cleanliness
- **Multi-Platform Tests** — Python 3.12 on Linux, macOS, Windows (minimum supported: 3.10)
- **Security Scan** — CodeQL + pip-audit
- **V2 Demo Smoke Test** — full governance pipeline end-to-end

Current: **1166 passing, 10 skipped, 3 xfailed**. Skipped tests require optional external components (live NATS demo, filesystem/HTTP executor plugins, PoD provider, external waiver file). No external infrastructure required for the core suite.

## Live Demo (Requires NATS JetStream)

```bash
docker compose up -d
EXOARMUR_LIVE_DEMO=1 python -m pytest tests/test_golden_demo_live.py -v
```

## Documentation

- [Security & Threat Model](SECURITY.md) — Security policy, threat model, and vulnerability reporting
- [Architecture](docs/ARCHITECTURE.md) — Full system architecture
- [The ExoArmur Doctrine](docs/DOCTRINE.md) — Verified claims and compliance
- [Doctrine Verification](docs/DOCTRINE_VERIFICATION.md) — Test evidence and status
- [ML Isolation Policy](docs/ML_ISOLATION.md) — Advisory-only ML components
- [Governance](docs/GOVERNANCE.md) — Reversibility guarantees and approval gates
- [Design Principles](docs/DESIGN_PRINCIPLES.md)
- [Validation Guide](docs/VALIDATE.md)
- [Phase Status](docs/PHASE_STATUS.md)
- [Whitepaper](docs/EXOARMUR_SYSTEMS_PAPER.md)

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contributing

Issues and PRs welcome. All contributions must pass the full gate suite including the three-run stability check (`python scripts/infra/stability_ci.py`).
