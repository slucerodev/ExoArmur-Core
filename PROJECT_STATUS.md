# Project Status

*Last validated: May 31, 2026 (test counts); documentation aligned to the 2.2.0 baseline on `baseline-2.2.0-alignment`*

## At a glance

| Dimension | Status |
|---|---|
| **Stage** | Open source reference implementation, seeking pilot integrations and formal verification partners |
| **Current version** | `2.2.0` (see `pyproject.toml`) |
| **Organizational sponsors** | None |
| **Announced adopters / pilots** | None — seeking first integration |
| **External security audit** | Not yet conducted |
| **Internal audit discipline** | Self-audited; CI invariants enforced |
| **Test suite** | 338 passed / 17 skipped / 0 failed at last recorded run (May 31, 2026); 396 tests collected on the 2.2.0 baseline — re-run before citing |
| **CI workflows** | 10 active (see `.github/workflows/`) |
| **Licensing** | Apache 2.0 (see LICENSE) |

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
- **Replay verification** — `kernel/replay_verification.py` compares stored
  canonical request/response hashes and reports `VERIFIED`/`MISMATCH`/
  `MALFORMED`/`NOT_CHECKED`; evidence signatures are not verified (reported as
  `NOT_CHECKED`). Recomputing hashes from stored content detects field
  inconsistency; it does not by itself prove original content was preserved.
- **Contract immutability** — V1 contracts (`src/spec/contracts/`) are locked;
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
  BFT consensus, and no fault-injection framework exists on the 2.2.0 baseline
  (earlier branches contained `src/exoarmur/replay/byzantine_fault_injection.py`,
  which is not part of this architecture).
- **Federation in hostile environments** — federation crypto and handshake
  state machine have not been exercised against an external red team.
- **Authenticated governed execution** — the HTTP API (`exoarmur.api`) has no
  authentication. Approval endpoints accept a self-asserted `operator_id`
  header, and telemetry ingest treats `operator_id` as audit metadata only.
- **Authoritative kill switches** — `kernel/boundary.py::ProxyPipeline` accepts
  kill-switch flags as inputs but currently constructs them hardcoded to
  `False`; there is no durable switch store or pre-dispatch enforcement on this
  baseline.
- **Trusted safety inputs** — `ProxyPipeline.execute_with_trace()` hardcodes
  `policy_verified=True`, `emitter_trust_score=0.85`, and
  `required_approval="none"` when building the safety state. These are
  placeholders, not measured or verified values.
- **Operator policy source** — no digest-pinned or otherwise verified policy
  file mechanism exists on this baseline; `POST /api/cli/ai-complete` uses an
  allow-by-construction demo policy and REPLAY (mocked) executor mode only.
- **Approval-to-execution resume** — approvals recorded via the API flip status
  in the approval store; nothing re-dispatches the underlying intent after
  APPROVED.
- **Real vendor executors** — OpenAI/Anthropic/HuggingFace/LangChain executors
  are scaffolds returning mock data; only FileSystem and SQLite
  DatabaseExecutor perform real local effects.

## Bounded pilot goal

The target pilot is **one authenticated, policy-controlled real workflow**:
an authenticated operator principal, a verified operator policy, human
approvals for elevated action classes, durable evidence records, an emergency
pause (kill switch), and an operator GUI. All of these are **planned**; the
kernel boundary, replay verification, and executor scaffolding exist, but the
items under "What is NOT validated" above are prerequisites, not completed
work.

## Roadmap signal

Development on `main` is guided by a phased plan. Near-term work is baseline
governance hardening on the 2.2.0 architecture: trusted safety inputs,
operator policy, authentication, durable kill switches, and approval resume —
followed by federation maturity and reserved extension surfaces.

See [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) for the disclosed
gap list and [`docs/VALIDATION_MATRIX.md`](docs/VALIDATION_MATRIX.md) for dated
validation results.

## How to evaluate this repository

1. Review [`README.md`](README.md) and run the quickstart locally
2. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the layered model
3. Read [`SECURITY.md`](SECURITY.md) for the threat model
4. Inspect [`.github/workflows/`](.github/workflows/) to see what CI enforces
5. Inspect [`src/spec/contracts/`](src/spec/contracts/) for the immutable V1 data shapes
6. Run `pip install -r requirements.lock && pip install --no-deps -e ".[dev]" && python -m pytest -q` to reproduce the test suite

## Contact

- **Bugs / Features:** Open a GitHub issue
- **Security issues:** Follow the responsible disclosure process in [`SECURITY.md`](SECURITY.md)
- **Formal verification collaboration:** Open an issue with "formal verification" in the title
