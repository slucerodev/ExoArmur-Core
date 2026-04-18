# Project Status

*Last updated: April 2026*

## At a glance

| Dimension | Status |
|---|---|
| **Stage** | Single-maintainer reference implementation |
| **Current version** | `2.1.0` (see `pyproject.toml`) |
| **Organizational sponsors** | None |
| **Announced adopters / pilots** | None — seeking first integration |
| **External security audit** | Not yet conducted |
| **Internal audit discipline** | Self-audited; CI invariants enforced |
| **Test suite** | 1033+ passing, three-run stability gate |
| **CI workflows** | 10 active (see `.github/workflows/`) |
| **Licensing** | Apache-2.0 |

## What ExoArmur is

A deterministic governance runtime that sits between an AI decision layer and
execution targets. Every action passes through a policy gate, produces a
cryptographic audit trail, and is deterministically replayable.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`README.md`](README.md) for the
technical overview.

## What is validated

- **Determinism** — enforced by CI (`core-invariant-gates.yml`, three-run gate)
- **Module boundaries** — enforced by CI (`module-boundary-enforcement.yml`)
- **Cross-platform compatibility** — CI matrix across Py 3.8–3.12 and three OSes
- **Security scanning** — CodeQL + pip-audit on every push
- **Replay boundary** — ReplayEngine consumes only CanonicalEvent inputs; no
  raw audit records, no wall-clock fields
- **Contract immutability** — V1 contracts (`spec/contracts/`) are locked;
  new capabilities are additive and feature-flag gated

## What is NOT validated

- **External security audit** — none conducted. Threat model is self-documented
  in `SECURITY.md` but has not been independently reviewed.
- **Formal proofs** — invariants are tested, not formally proven. Methodology
  is documented in the internal blueprint; no theorem-prover output exists yet.
- **Production deployment at scale** — no known production deployments.
- **Federation in hostile environments** — Byzantine fault-tolerance logic is
  present but has not been exercised against a red team.

## Roadmap signal

Development on `main` is guided by a phased plan: hardening of determinism and
contract discipline → control-plane completeness → federation maturity →
evolution toward the broader ADMO (Autonomous Defense Mesh Organism) vision.

See [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md) for the current phase board
and [`docs/ROADMAP.md`](docs/ROADMAP.md) for near-term planning.

## How to evaluate this repository

If you are a prospective adopter or reviewer:

1. Read [`README.md`](README.md) and run the 5-minute quickstart
2. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the layered model
3. Read [`SECURITY.md`](SECURITY.md) for the threat-model and responsible-disclosure policy
4. Inspect [`.github/workflows/`](.github/workflows/) to see what CI actually enforces
5. Inspect [`spec/contracts/`](spec/contracts/) for the immutable V1 data shapes
6. Run `pip install -r requirements.lock && pip install --no-deps -e ".[dev]" && python -m pytest -q` to reproduce the test suite (same command CI runs)

## Contact

See `README.md` for contribution guidelines. Security issues: follow the
coordinated-disclosure process in [`SECURITY.md`](SECURITY.md).
