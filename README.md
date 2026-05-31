# ExoArmur Core

**Minimal deterministic governance kernel for autonomous systems.**

ExoArmur is a minimal deterministic governance kernel for autonomous systems. It enforces policy gates, produces cryptographic audit trails, and enables deterministic replay verification.

## What ExoArmur Is

A deterministic governance runtime that sits between an AI decision layer and execution targets. Every action passes through a policy gate, produces a cryptographic audit trail, and is deterministically replayable.

## What ExoArmur Is Not

- **Not** a full autonomous system — it is a governance layer, not an agent
- **Not** a platform executor — Core does not include vendor SDK integrations (LangChain, OpenAI, Anthropic, HuggingFace are scaffolds only)
- **Not** production-certified — this is a reference implementation seeking formal verification
- **Not** externally audited — security and compliance are self-validated, not third-party audited
- **Not** a web service — the kernel is importable as a pure Python library with zero network dependencies

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

## Quickstart (5-Minute Proof)

Run the health check to verify installation:

```bash
exoarmur health
```

Run the demo to see deterministic governance in action:

```bash
exoarmur demo
```

## CLI Usage

```bash
Usage: exoarmur [OPTIONS] COMMAND [ARGS]...

  ExoArmur Core — deterministic governance and replayable audit layer

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  demo        Run demonstration scenarios
  evidence    Evidence pack operations
  health      Quick health check
  proof       Run deterministic proof mode - single command system...
  verify-all  Run complete system verification
```

## Current Validation Status

**Test Suite:** 338 passed, 17 skipped, 0 failed

```bash
python -m pytest tests/ -q -rs
```

**E2E Tests:** 22 passed, 0 failed

```bash
python -m pytest tests/e2e/ -v
```

**DACT Compliance:** Levels 1-5 are internally validated by the ExoArmur test suite. Third-party audit has not yet been completed. Level 6 remains pending external/formal review.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for detailed validation status.

## Executors

**Core Executors (included in exoarmur-core):**
- **FileSystemExecutor** — governs file operations (create, delete, rename, modify) with automatic rollback and state hash verification
- **DatabaseExecutor** — governs database operations with transaction rollback and state verification

**Platform Executor Scaffolds (reference implementations only):**
- **langchain_executor.py** — Scaffold for LangChain agent governance
- **openai_executor.py** — Scaffold for OpenAI API governance
- **anthropic_executor.py** — Scaffold for Anthropic API governance
- **huggingface_executor.py** — Scaffold for HuggingFace model governance

**Note:** Real platform integrations (with actual API calls) belong in optional addon packages (e.g., `exoarmur-openai-executor`). Core provides the plugin infrastructure and evidence schema for external effects, but does not include vendor SDK integrations.

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

ExoArmur-Core implements the Deterministic Autonomy Compliance Test (DACT) v0.2:

| Level | Requirement | Status |
|-------|-------------|--------|
| 1 | Deterministic Replay | ✅ Internally validated |
| 2 | Cryptographic Attestation | ✅ Internally validated |
| 3 | Counterfactual Analysis | ✅ Internally validated |
| 4 | ML Isolation | ✅ Internally validated |
| 5 | Air-Gap Integrity | ✅ Internally validated |
| 6 | Formal Verification | ⏳ Pending third-party review |

**Note:** Levels 1-5 are internally validated by the ExoArmur test suite. Third-party audit has not yet been completed.

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

**Total kernel: ~1,680 lines**

## Status

Reference implementation. Single maintainer. Not production-certified. Not externally audited. Seeking formal verification partnership and pilot integrations in high-assurance environments (defense, sovereign infrastructure, critical systems).

## Documentation

- [Documentation Index](docs/README.md) — Table of contents for all documentation
- [The ExoArmur Doctrine](docs/DOCTRINE.md) — Verified claims and compliance
- [Architecture](docs/ARCHITECTURE.md) — System architecture
- [ML Isolation Policy](docs/ML_ISOLATION.md) — Advisory-only ML components
- [DACT Standard v0.2](docs/DACT_STANDARD_v0.2.md) — Deterministic Autonomy Compliance Test specification
- [Formal Verification Invariants](docs/formal_verification/INVARIANTS.md) — Formal specifications for DACT Level 6
- [LangChain Executor Integration](docs/integrations/LANGCHAIN_EXECUTOR.md) — Scaffold integration guide
- [Project Status](PROJECT_STATUS.md) — Current validation status and roadmap
- [Security Policy](SECURITY.md) — Security policy and threat model
- [Contributing](CONTRIBUTING.md) — Contribution policy and development setup
- [Changelog](CHANGELOG.md) — Version history

## License

License/status: private repository; evaluation/licensing terms available by written agreement.

This repository is not currently distributed as open source. Do not redistribute without written permission.

See the [LICENSE](LICENSE) file for details.

**Note:** License language should be reviewed by legal counsel before public release, commercial licensing, or acquisition.

## Contributing

For technical review, architecture feedback, or formal verification collaboration, please open an issue on GitHub.
