# ExoArmur Core

**Minimal deterministic governance kernel for autonomous systems.**

ExoArmur is a minimal deterministic governance kernel for autonomous systems. It routes action intents through a policy and safety boundary before executor dispatch, produces canonical-hash audit records, and supports deterministic replay verification of recorded evidence.

## What ExoArmur Is

A deterministic governance runtime that sits between an AI decision layer and execution targets. Every action that reaches the `ProxyPipeline` boundary passes through policy evaluation, a safety gate, target validation, and executor dispatch, with an execution trace recorded along the way.

## What ExoArmur Is Not

- **Not** a full autonomous system — it is a governance layer, not an agent
- **Not** a platform executor — Core does not include vendor SDK integrations (LangChain, OpenAI, Anthropic, HuggingFace are scaffolds only; real vendor calls live in optional addon packages)
- **Not production-certified** — this is a reference implementation seeking formal verification
- **Not** externally audited — security and compliance are self-validated, not third-party audited
- **Not a complete governed service out of the box** — the kernel is importable as a pure Python library, and the repository also ships an optional FastAPI API/demo layer (`exoarmur.api`) that is **not yet authenticated or fully governed** (see [Known Limitations](docs/KNOWN_LIMITATIONS.md))

## Pilot Goal (Bounded)

The bounded pilot — one authenticated, policy-controlled real file-write workflow with human approval of the exact action, durable global/tenant pauses, durable evidence, and an operator GUI — is merged on `main`. Serve it with `exoarmur.api.server:create_pilot_app` (health + `/api/pilot/*` only); the legacy demo routers remain on the separate `create_app` factory and are unauthenticated — see [docs/PILOT.md](docs/PILOT.md) and [Known Limitations](docs/KNOWN_LIMITATIONS.md).

## Installation

```bash
pip install exoarmur-core
```

Requires Python 3.10 or later.

**Optional Demo API:**

To run the optional FastAPI demo server (not required for Core runtime):

```bash
pip install exoarmur-core[demo-api]
python scripts/demo_api.py
```

## Quickstart

Install and verify the package imports:

```bash
pip install -e .
python -c "import exoarmur; print(exoarmur.__version__)"
```

The `exoarmur` CLI currently exposes `version` and `info` commands:

```bash
exoarmur --help
exoarmur version
```

Requires Python 3.10 or later.

**Optional Demo API:**

To run the optional FastAPI demo/CLI-bridge server (not required for Core runtime):

```bash
pip install exoarmur-core[demo-api]
uvicorn exoarmur.api.server:create_app --factory
```

The API layer is a developer/demo interface. It is **not authenticated** and several of its governed-execution paths use demo policy defaults — see [Known Limitations](docs/KNOWN_LIMITATIONS.md) before relying on it.

## CLI Usage

```bash
Usage: exoarmur [OPTIONS] COMMAND [ARGS]...

  ExoArmur Core – deterministic governance and replayable audit layer for execution.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  info      Show ExoArmur Core information.
  version   Show ExoArmur Core version information.
```

## Current Validation Status

**Test Suite (last recorded full run, May 31, 2026):** 338 passed, 17 skipped, 0 failed. The suite has grown since that run (396 tests collected on the 2.2.0 baseline); re-run before citing current numbers.

```bash
python -m pytest tests/ -q -rs
```

**E2E Tests (same dated run):** 22 passed, 0 failed

```bash
python -m pytest tests/e2e/ -v
```

See [PROJECT_STATUS.md](PROJECT_STATUS.md) and [docs/VALIDATION_MATRIX.md](docs/VALIDATION_MATRIX.md) for detailed, dated validation status.

## Executors

**Core Executors (included in exoarmur-core):**
- **FileSystemExecutor** — governs file operations (create, delete, rename, modify) with rollback plans and state-hash verification against the local filesystem
- **DatabaseExecutor** — governs SQLite operations with transaction rollback and state verification

**Platform Executor Scaffolds (reference implementations only — no live vendor calls):**
- **openai_executor.py** — Scaffold returning mock data; `_execute_openai_operation()` does not call the OpenAI API
- **anthropic_executor.py** — Scaffold for Anthropic API governance
- **huggingface_executor.py** — Scaffold for HuggingFace model governance
- **langchain_executor.py** — Scaffold for LangChain agent governance

**Note:** A class existing does not establish a functioning vendor integration. Real platform integrations (with actual API calls) belong in optional addon packages (e.g., `exoarmur-openai-executor`). Core provides the plugin infrastructure and evidence schema for external effects, but does not include vendor SDK integrations. The `POST /api/cli/ai-complete` endpoint uses the external `exoarmur-openai-executor` package in **REPLAY (mocked) mode only** — it does not perform live OpenAI calls.

## Demo Artifacts

ExoArmur includes demo artifacts in `examples/demo_artifacts/` that are safe public sample data generated from real Core E2E flows. These artifacts are intended for future Web UI/demo use and require no vendor SDKs, network calls, secrets, or machine-specific paths.

See [examples/demo_artifacts/README.md](examples/demo_artifacts/README.md) for details.

## Determinism

The kernel enforces deterministic replay through:
- Canonical JSON (sorted keys, no whitespace variation)
- Controlled clock abstraction (deterministic time for replay, wall-clock for coordination)
- Zero randomness in the decision path
- Zero ML in the authority path

## DACT Compliance

DACT (Deterministic Autonomy Compliance Test) v0.2 is **ExoArmur's own evaluation framework**, defined in [docs/DACT_STANDARD_v0.2.md](docs/DACT_STANDARD_v0.2.md) — it is not an independent standard or certification body.

| Level | Requirement | Status |
|-------|-------------|--------|
| 1 | Deterministic Replay | ✅ Internally evaluated by the test suite |
| 2 | Cryptographic Attestation | ✅ Internally evaluated (canonical hashes; evidence signatures are recorded but **not** verified — see below) |
| 3 | Counterfactual Analysis | ✅ Internally evaluated |
| 4 | ML Isolation | ✅ Internally evaluated |
| 5 | Air-Gap Integrity | ✅ Internally evaluated (kernel scope) |
| 6 | Formal Verification | ⏳ Pending external/formal review |

**Note:** Levels 1-5 are internally evaluated by the ExoArmur test suite. This is self-assessment against our own framework — not third-party certification. Level 6 remains pending.

**Honest scope of "replay verification":** the replay endpoints recompute canonical hashes from stored records and compare them. Recomputing a hash from stored content alone does not prove the original content was preserved — it detects inconsistencies between stored fields, not tampering that rewrote both content and hash. Separately, `kernel/replay_verification.py` compares stored request/response hashes against canonical recomputation (`VERIFIED`/`MISMATCH`/`MALFORMED`/`NOT_CHECKED`), and evidence signatures are explicitly reported as `NOT_CHECKED` because signature verification is not implemented.

## Architecture

The kernel consists of:

| Module | Purpose |
|--------|---------|
| `kernel/boundary.py` | Minimal routing: Intent → Policy → Safety → Executor → Audit |
| `kernel/clock.py` | Clock abstraction with utc_now and DeterministicClock |
| `kernel/ids.py` | Deterministic ULID generation for governance entities |
| `kernel/trust_evaluator.py` | Formal interface (raises NotImplementedError) |
| `kernel/external_effect.py` | External effect evidence and replay verification |
| `kernel/replay_verification.py` | Replay verification engine |
| `kernel/plugin_registry.py` | Plugin discovery and registration |
| `kernel/canonicalization.py` | Canonical JSON encoding |
| `executors/file_system_executor.py` | FileSystemExecutor with governance integration |
| `executors/database_executor.py` | DatabaseExecutor with transaction rollback |
| `executors/langchain_executor.py` | LangChainExecutor scaffold (reference implementation) |
| `executors/openai_executor.py` | OpenAIExecutor scaffold (reference implementation) |
| `executors/anthropic_executor.py` | AnthropicExecutor scaffold (reference implementation) |
| `executors/huggingface_executor.py` | HuggingFaceExecutor scaffold (reference implementation) |

**Total kernel: ~1,800 lines** (the `kernel/` package alone; executors and the API layer are additional)

## Status

Reference implementation (v2.2.0). Single maintainer. Apache-2.0 licensed, public repository. Not production-certified. Not externally audited. The deterministic kernel and replay verification are internally evaluated. The supported pilot surface (`create_pilot_app`: authenticated, policy-controlled file-write workflow with approvals, durable pauses, evidence, and an operator GUI) is on `main` — see [docs/PILOT.md](docs/PILOT.md). The legacy HTTP demo layer (`create_app`) is **not authenticated** — see [Known Limitations](docs/KNOWN_LIMITATIONS.md). GitHub Actions could not run for the pilot merge due to a billing restriction; validation relied on recorded local tests and live demonstrations. Seeking formal verification partnership and pilot integrations in high-assurance environments (defense, sovereign infrastructure, critical systems).

## Documentation

- [Documentation Index](docs/README.md) — Table of contents for all documentation
- [The ExoArmur Doctrine](docs/DOCTRINE.md) — Verified claims and compliance
- [Architecture](docs/ARCHITECTURE.md) — System architecture
- [ML Isolation Policy](docs/ML_ISOLATION.md) — Advisory-only ML components
- [DACT Standard v0.2](docs/DACT_STANDARD_v0.2.md) — Deterministic Autonomy Compliance Test specification
- [Formal Verification Invariants](docs/formal_verification/INVARIANTS.md) — Formal specifications for DACT Level 6
- [LangChain Executor Integration](docs/integrations/LANGCHAIN_EXECUTOR.md) — Scaffold integration guide
- [Project Status](PROJECT_STATUS.md) — Current validation status and roadmap
- [Known Limitations](docs/KNOWN_LIMITATIONS.md) — Disclosed gaps, including unauthenticated API and incomplete governance wiring
- [Validation Matrix](docs/VALIDATION_MATRIX.md) — Dated test/security validation results
- [Security Policy](SECURITY.md) — Security policy and threat model
- [Contributing](CONTRIBUTING.md) — Contribution policy and development setup
- [Changelog](CHANGELOG.md) — Version history

## License

Apache 2.0 — see [LICENSE](LICENSE) for full terms.

ExoArmur Core is free, open-source software. You may use, modify, and distribute it under the terms of the Apache License 2.0. Commercial support, hosted offerings, and proprietary module integrations are not covered by this license and require separate agreement.

## Contributing

We welcome contributions — bug reports, architecture feedback, porting efforts, and formal verification collaboration. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, guidelines, and safety rules.

Please open an issue before proposing large changes so we can align on design.
