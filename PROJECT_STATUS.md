# Project Status

*Last validated: pilot merge validation November 15, 2026 (local runs; GitHub Actions blocked by billing restriction); earlier test counts dated May 31, 2026*

## At a glance

| Dimension | Status |
|---|---|
| **Stage** | Open source reference implementation, seeking pilot integrations and formal verification partners |
| **Current version** | `2.2.0` (see `pyproject.toml`) |
| **Organizational sponsors** | None |
| **Announced adopters / pilots** | None — seeking first integration |
| **External security audit** | Not yet conducted |
| **Internal audit discipline** | Self-audited; CI invariants enforced |
| **Test suite** | 398 passed / 17 skipped at last full local run; `tests/api/test_pilot.py` 24 passed against real PostgreSQL (Nov 15, 2026). Earlier dated run: 338 passed / 17 skipped (May 31, 2026) |
| **CI workflows** | 10 defined (see `.github/workflows/`); GitHub Actions could not run for the pilot merge due to a billing restriction — validation evidence is recorded local runs |
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
- **Authenticated governed execution (pilot path)** — validated on
  `create_pilot_app`: API-key auth, session binding to the issuing key,
  server-side permission/tenant checks, digest-pinned operator policy.
  The legacy `create_app` routes (`/v1/*`, `/api/v2/*`, `/api/cli/*`) remain
  **unauthenticated** and are not part of the supported pilot.
- **Authoritative kill switches (pilot path)** — durable global/tenant
  `execution_pauses` in PostgreSQL are re-checked immediately before
  executor dispatch, including approval resume. They block subsequent
  dispatch only; they do not interrupt an already-running effect. The
  legacy routes have no pause enforcement.
- **Trusted safety inputs (pilot path)** — `ProxyPipeline` requires an
  injectable `SafetyContextProvider` and fails closed without one; the
  pilot supplies operator-configured values (configured, not measured).
  The `ai-complete` demo passes explicitly labeled demo inputs.
- **Operator policy source** — `EXOARMUR_POLICY_FILE` +
  `EXOARMUR_POLICY_SHA256` pin a versioned JSON policy by digest;
  missing/altered/unmatched policy denies. `POST /api/cli/ai-complete`
  (legacy demo) still uses an allow-by-construction policy and REPLAY
  (mocked) executor.
- **Approval-to-execution resume (pilot path)** — approval re-validates
  the stored action and dispatches it through the governed pipeline.
  Legacy approval records remain record-keeping only.
- **Real vendor executors** — OpenAI/Anthropic/HuggingFace/LangChain executors
  are scaffolds returning mock data; only FileSystem and SQLite
  DatabaseExecutor perform real local effects. The pilot exercises the
  FileSystemExecutor only.

## Bounded pilot (implemented on `main`)

The pilot — **one authenticated, policy-controlled real workflow** — is
implemented and merged: an authenticated agent principal submits governed
file-write proposals, an authenticated approver reviews the exact frozen
parameters, approval resumes dispatch through `ProxyPipeline` → safety
gate → `FileSystemExecutor` confined to `EXOARMUR_WORKSPACE_ROOT`, durable
global/tenant pauses are enforced immediately before dispatch, and
evidence is persisted with hash-consistency verification. An operator GUI
is served at `/api/pilot/gui`. Runbook: [`docs/PILOT.md`](docs/PILOT.md).

Remaining pilot limits: legacy `create_app` routes are unauthenticated;
evidence verification is stored-content hash consistency (no signer
verification); interrupted `EXECUTING` actions are reported as ambiguous,
not retried; action history is unpaginated; the pilot covers one executor
and two file operations on local PostgreSQL/filesystem only.

## Roadmap signal

Development on `main` is guided by a phased plan. The bounded pilot is
merged; near-term work is hardening the pilot surface (legacy route
authentication or retirement, pagination, additional governed operations)
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
