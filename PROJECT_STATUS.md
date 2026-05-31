# Project Status

*Last validated: May 31, 2026*

## At a glance

| Dimension | Status |
|---|---|
| **Stage** | Private reference implementation, buyer/pilot evaluation ready |
| **Current version** | `2.1.0` (see `pyproject.toml`) |
| **Organizational sponsors** | None |
| **Announced adopters / pilots** | None — seeking first integration |
| **External security audit** | Not yet conducted |
| **Internal audit discipline** | Self-audited; CI invariants enforced |
| **Test suite** | 338 passed / 17 skipped / 0 failed, three-run stability gate |
| **CI workflows** | 10 active (see `.github/workflows/`) |
| **Licensing** | Proprietary evaluation license (see LICENSE) |

## What ExoArmur is

A deterministic governance runtime that sits between an AI decision layer and
execution targets. Every action passes through a policy gate, produces a
cryptographic audit trail, and is deterministically replayable.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`README.md`](README.md) for the
technical overview.

## What is validated

- **Determinism** — enforced by CI (`core-invariant-gates.yml`, three-run gate)
- **Module boundaries** — enforced by CI (`module-boundary-enforcement.yml`)
- **Cross-platform compatibility** — CI matrix across Py 3.10–3.12 and three OSes (minimum supported: 3.10)
- **Security scanning** — CodeQL + pip-audit on every push
- **Replay boundary** — ReplayEngine consumes only CanonicalEvent inputs; no
  raw audit records, no wall-clock fields
- **Contract immutability** — V1 contracts (`spec/contracts/`) are locked;
  new capabilities are additive and feature-flag gated

## Phase 2A Status (Test Suite Hardening)

**Status:** GREEN-WITH-KNOWN-SKIPS

**Validation Command:**
```bash
python -m pytest tests/ -q -rs
```

**Result:** 338 passed, 17 skipped, 0 failed

**Known Skip Categories:**
- **FileSystemExecutor does not expose get_state_hash()** (10 skips)
  - get_state_hash() exists on platform executors (LangChain, OpenAI, Anthropic, HuggingFace)
  - get_state_hash() does NOT exist on FileSystemExecutor
  - get_state_hash() is NOT defined in ExecutorPlugin protocol
  - Tests assume all executors have this method, but it's not part of the formal contract

- **ExecutorPlugin does not define get_execution_history()** (2 skips)
  - get_execution_history() is NOT defined in ExecutorPlugin protocol
  - Tests assume a method that's not part of the contract

- **Executor evidence dict structure is not standardized across executors** (2 skips)
  - ExecutorResult.evidence is a dict, but structure varies between executors
  - Tests assumed specific fields (execution_id, intent_id) that FileSystemExecutor doesn't provide
  - Evidence structure is not part of the formal contract

- **Some executor boundary structures are defined outside kernel** (2 skips)
  - TargetValidationResult and ExecutorCapabilities are in executors module
  - Tests are in kernel/test_boundary.py but test executors module structures

- **One executor capability comparison is environment-dependent** (1 skip)
  - Tests that different executors have different supported_targets
  - In test environment, both may have ['/tmp']

**Future Work Note:**
Executor Contract Formalization should decide whether state hashing, execution history, and evidence schema should become formal executor protocol requirements. This is not implemented in Phase 2A.

## What is NOT validated

- **External security audit** — none conducted. Threat model is self-documented
  in `SECURITY.md` but has not been independently reviewed.
- **Formal proofs** — invariants are tested, not formally proven. Methodology
  is documented in the internal blueprint; no theorem-prover output exists yet.
- **Production deployment at scale** — no known production deployments.
- **Byzantine Fault Tolerance (BFT)** — the system does NOT claim or implement
  BFT consensus. The `FaultInjector` framework (see `src/exoarmur/replay/byzantine_fault_injection.py`)
  verifies replay determinism under adversarial input corruption; it is not a
  consensus protocol and has not been exercised in a real distributed setting.
- **Federation in hostile environments** — federation crypto and handshake
  state machine have not been exercised against an external red team.

## Roadmap signal

Development on `main` is guided by a phased plan: hardening of determinism and
contract discipline → control-plane completeness → federation maturity →
reserved extension surfaces for future private modules and advanced deployment modes.

See [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md) for the current phase board
and [`docs/ROADMAP.md`](docs/ROADMAP.md) for near-term planning.

## How to evaluate this repository

If you are a prospective buyer, pilot evaluator, or reviewer:

1. Contact the repository owner for evaluation authorization
2. Review [`README.md`](README.md) and run the quickstart locally
3. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the layered model
4. Read [`SECURITY.md`](SECURITY.md) for the threat-model and evaluation access terms
5. Inspect [`.github/workflows/`](.github/workflows/) to see what CI actually enforces
6. Inspect [`spec/contracts/`](spec/contracts/) for the immutable V1 data shapes
7. Run `pip install -r requirements.lock && pip install --no-deps -e ".[dev]" && python -m pytest -q` to reproduce the test suite (same command CI runs)

## Contact

For licensing, pilot, partnership, or acquisition discussions, contact the repository owner. Security issues: follow the private disclosure process in [`SECURITY.md`](SECURITY.md).
