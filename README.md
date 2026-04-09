# ExoArmur Core

[![CI](https://github.com/slucerodev/ExoArmur-Core/actions/workflows/core-invariant-gates.yml/badge.svg)](https://github.com/slucerodev/ExoArmur-Core/actions/workflows/core-invariant-gates.yml)
[![PyPI](https://img.shields.io/pypi/v/exoarmur-core)](https://pypi.org/project/exoarmur-core/)
[![Python](https://img.shields.io/pypi/pyversions/exoarmur-core)](https://pypi.org/project/exoarmur-core/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/slucerodev/ExoArmur-Core/releases)

**Deterministic execution governance for AI agents.** Every action passes through a policy gate, produces a cryptographic audit trail, and is deterministically replayable.

---

## 5-Minute Proof

```bash
pip install exoarmur-core
python examples/quickstart_replay.py
```

Or inline:

```python
from exoarmur import ReplayEngine
from exoarmur.replay.event_envelope import CanonicalEvent
import hashlib, json

payload = {"kind": "quickstart", "ref": "demo"}
event = CanonicalEvent(
    event_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
    event_type="quickstart_replay",
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

Run the full suite (1033 tests, three-run stability gate):

```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
pip install ".[dev]"
python -m pytest -q
```

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

## Governance Pipeline Demo

```bash
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
python scripts/demo_v2_restrained_autonomy.py --operator-decision deny
```

Expected output:
```
DEMO_RESULT=DENIED
ACTION_EXECUTED=false
AUDIT_STREAM_ID=det-...
```

Replay the audit stream:
```bash
python scripts/demo_v2_restrained_autonomy.py --replay <AUDIT_STREAM_ID>
```

## CI

Every push runs:
- **Core Invariant Gates** — three deterministic test runs, boundary enforcement, repo cleanliness
- **Multi-Platform Tests** — Python 3.8–3.12 on Linux, macOS, Windows
- **Security Scan** — CodeQL + pip-audit
- **V2 Demo Smoke Test** — full governance pipeline end-to-end

Current: **1033 passing, 11 skipped, 11 xfailed**. No external infrastructure required for the core suite.

## Live Demo (Requires NATS JetStream)

```bash
docker compose up -d
EXOARMUR_LIVE_DEMO=1 python -m pytest tests/test_golden_demo_live.py -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE_SIMPLE.md)
- [Design Principles](docs/DESIGN_PRINCIPLES.md)
- [Validation Guide](VALIDATE.md)
- [Phase Status](docs/PHASE_STATUS.md)
- [Whitepaper](docs/EXOARMUR_WHITEPAPER.md)

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
