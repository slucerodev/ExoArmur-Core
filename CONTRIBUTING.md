# Contributing to ExoArmur Core

Thank you for your interest in ExoArmur. This project is a minimal deterministic governance kernel — correctness and replayability are more important than features. Every contribution must preserve the architectural invariants documented below.

## Quick Start

```bash
git clone https://github.com/slucerodev/ExoArmur-Core
cd ExoArmur-Core
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m pytest -q
```

## Before You Contribute

1. **Open an issue first** for large changes (new features, API changes, refactors).
2. **One-axis changes only** — each PR should target exactly one of: replay correctness, dependency isolation, determinism under concurrency, or interface normalization.
3. **All tests must pass** with no new skips or xfails.
4. **The test suite must remain green** — run `python -m pytest -q` before submitting.

## Running Tests

```bash
# Full suite
python -m pytest -q

# With coverage
python -m pytest --cov=src/exoarmur --cov-report=term-missing -q

# Determinism gate (run three times, hashes must match)
for i in 1 2 3; do python -m pytest tests/ -q; done
```

## Architecture Safety Rules (Non-Negotiable)

These rules are the project's contract with its users. Violating any of them is grounds for immediate rejection, regardless of how clever or useful the change is.

### 1. ProxyPipeline Is the Sole Execution Boundary
- Every action that produces a real-world side effect must pass through `ProxyPipeline.execute_with_trace()`.
- No direct executor invocation. No governance bypass. No exceptions.

### 2. Executors Are Untrusted
- Executors receive only `ActionIntent` objects.
- Executors return only `ExecutorResult` objects.
- Executors may not access governance components, modify traces, or read/write audit state.

### 3. Determinism Is Not Optional
- Same inputs + same clock → identical outputs + identical trace hashes.
- No `time.time()` outside the clock abstraction. No randomness in the decision path. No unordered collection iteration in trace generation.
- If a change breaks replay determinism, it is rejected.

### 4. V1 Contracts Are Immutable
- Files in `src/spec/contracts/` are locked. Additive-only changes via new versions.
- No weakening of existing assertions. No test skips to mask failures.

### 5. No Hidden State
- All state that affects output must be captured in the trace or the intent.
- If replaying a trace produces a different result, there is a bug.

## What We Need Help With

- **Formal verification** — theorem-prover proofs of the ProxyPipeline invariants
- **Language ports** — Rust, Go, or TypeScript implementations aligned with the kernel's deterministic contracts
- **Executor implementations** — real platform integrations (OpenAI, Anthropic, etc.) as separate installable packages
- **Documentation** — clearer explanations, diagrams, integration guides
- **Bug reports** — especially determinism violations or replay hash mismatches

## What We Will Likely Reject

- Features that add non-determinism (wall-clock timeouts, UUID generation, randomness)
- Changes that weaken the executor boundary
- "Simplifications" that break existing tests
- Vendor-specific code in the Core kernel (belongs in separate packages)

## Code Style

- `black` + `isort` are enforced in CI.
- `mypy --strict` is encouraged; type hints on all public APIs.
- Docstrings use Google style.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.

## Resources

- [Architecture](docs/ARCHITECTURE.md) — System design and component map
- [DACT Standard](docs/DACT_STANDARD_v0.2.md) — Deterministic Autonomy Compliance Test (project's own framework)
- [Security Policy](SECURITY.md) — Threat model and responsible disclosure
- [Project Status](PROJECT_STATUS.md) — What's validated, what's pending
