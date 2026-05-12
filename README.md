# ExoArmur Core

**Minimal deterministic governance kernel for autonomous systems.**

ExoArmur is a ~1,100-line Python kernel that provides a deterministic governance boundary for autonomous execution. It enforces policy gates, produces cryptographic audit trails, and enables deterministic replay verification.

The kernel has:
- **Zero network dependencies**
- **Zero web interfaces**
- **Zero ML in the authority path**
- Importable as a pure Python library

## Executors

- **FileSystemExecutor** — governs file operations (create, delete, rename, modify) with automatic rollback and state hash verification

## Determinism

The kernel enforces deterministic replay through:
- Canonical JSON (sorted keys, no whitespace variation)
- Controlled clock abstraction (deterministic time for replay, wall-clock for coordination)
- Zero randomness in the decision path
- Zero ML in the authority path

## DACT Compliance

ExoArmur-Core implements the Deterministic Autonomy Compliance Test (DACT) v0.2 Levels 1-5:

| Level | Requirement | Status |
|-------|-------------|--------|
| 1 | Deterministic Replay | ✅ Verified |
| 2 | Cryptographic Attestation | ✅ Verified |
| 3 | Counterfactual Analysis | ✅ Verified |
| 4 | ML Isolation | ✅ Verified |
| 5 | Air-Gap Integrity | ✅ Verified |
| 6 | Formal Verification | ⏳ Pending third-party review |

## Architecture

The kernel consists of:

| Module | Lines | Purpose |
|--------|-------|---------|
| `kernel/boundary.py` | 749 | Minimal routing: Intent → Policy → Safety → Executor → Audit |
| `kernel/clock.py` | 97 | Clock abstraction with utc_now and DeterministicClock |
| `kernel/ids.py` | 174 | Deterministic ULID generation for governance entities |
| `kernel/trust_evaluator.py` | 57 | Formal interface (raises NotImplementedError) |
| `executors/file_system_executor.py` | - | FileSystemExecutor with governance integration |

**Total kernel: 1,077 lines**

## Status

Reference implementation. Single maintainer. Not production-certified. Not externally audited. Seeking formal verification partnership and pilot integrations in high-assurance environments (defense, sovereign infrastructure, critical systems).

## Documentation

- [The ExoArmur Doctrine](docs/DOCTRINE.md) — Verified claims and compliance
- [Architecture](docs/ARCHITECTURE.md) — System architecture
- [ML Isolation Policy](docs/ML_ISOLATION.md) — Advisory-only ML components

## License

ExoArmur-Core is open-source under the Apache License 2.0.

Optional commercial/proprietary modules may be distributed separately and are not part of this Core repository unless explicitly included.

See the [LICENSE](LICENSE) file for details.

## Contributing

For technical review, architecture feedback, or formal verification collaboration, please open an issue on GitHub.
