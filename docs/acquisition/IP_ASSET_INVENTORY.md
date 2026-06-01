# IP Asset Inventory

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Overview

This document catalogs all intellectual property assets included in the ExoArmur-Core acquisition package.

## Source Code Assets

### Core Kernel (~1,680 lines)
**Location:** `src/exoarmur/kernel/`

| Module | Lines | Purpose | Status |
|--------|-------|---------|--------|
| boundary.py | ~200 | ProxyPipeline execution boundary | Internally validated |
| clock.py | ~100 | Clock abstraction | Internally validated |
| ids.py | ~150 | Deterministic ULID generation | Internally validated |
| trust_evaluator.py | ~50 | Formal interface (NotImplementedError) | Interface-only |
| external_effect.py | ~100 | External effect evidence | Internally validated |
| replay_verification.py | ~150 | Replay verification engine | Internally validated |
| plugin_registry.py | ~100 | Plugin discovery | Internally validated |
| canonicalization.py | ~50 | Canonical JSON encoding | Internally validated |

### Core Executors
**Location:** `src/exoarmur/executors/`

| Executor | Lines | Purpose | Status |
|----------|-------|---------|--------|
| file_system_executor.py | ~400 | FileSystemExecutor with governance | Internally validated |
| database_executor.py | ~500 | DatabaseExecutor with transaction rollback | Internally validated |
| __init__.py | ~50 | Executor exports | Internally validated |

### Platform Executor Scaffolds
**Location:** `src/exoarmur/executors/`

| Executor | Lines | Purpose | Status |
|----------|-------|---------|--------|
| langchain_executor.py | ~300 | LangChain integration scaffold | Reference only |
| openai_executor.py | ~300 | OpenAI integration scaffold | Reference only |
| anthropic_executor.py | ~300 | Anthropic integration scaffold | Reference only |
| huggingface_executor.py | ~300 | HuggingFace integration scaffold | Reference only |

### CLI and Entry Points
**Location:** `src/exoarmur/` and `src/`

| Module | Lines | Purpose | Status |
|--------|-------|---------|--------|
| cli.py | ~200 | CLI interface | Internally validated |
| main.py | ~100 | Main entry point | Internally validated |
| main_export.py | ~10 | Export shim | Internally validated |

### Contracts and Specifications
**Location:** `src/spec/contracts/`

| Module | Lines | Purpose | Status |
|--------|-------|---------|--------|
| models_v1.py | ~800 | V1 data models | Immutable |
| shared_primitives_v1.py | ~300 | Shared primitives | Immutable |

## Test Assets

### Test Suite
**Location:** `tests/`

| Category | Files | Tests | Status |
|----------|-------|-------|--------|
| Kernel tests | 10 files | ~100 tests | 338 passed, 17 skipped |
| Executor tests | 6 files | ~80 tests | All passing |
| Integration tests | 2 files | ~20 tests | All passing |
| Compliance tests | 3 files | ~50 tests | All passing |
| E2E tests | 2 files | 22 tests | All passing |
| Security tests | 1 file | ~15 tests | All passing |
| Performance tests | 1 file | ~20 tests | All passing |
| CLI tests | 1 file | ~5 tests | All passing |

**Total Test Coverage:** 338 passed, 17 skipped, 0 failed

### Test Fixtures and Data
**Location:** `tests/` and `examples/`

| Asset | Purpose | Status |
|-------|---------|--------|
| Test fixtures | Unit test data | Internally validated |
| Demo artifacts | Safe public sample data | Internally validated |
| Example scripts | Demonstration scripts | Internally validated |

## Documentation Assets

### Core Documentation
**Location:** `docs/`

| Document | Purpose | Status |
|----------|---------|--------|
| README.md | Project overview and quickstart | Complete |
| ARCHITECTURE.md | System architecture | Complete |
| DOCTRINE.md | Verified claims and compliance | Complete |
| ML_ISOLATION.md | ML isolation policy | Complete |
| DACT_STANDARD_v0.2.md | DACT specification | Complete |
| SECURITY.md | Security policy and threat model | Complete |
| CONTRIBUTING.md | Contribution policy | Complete |
| CHANGELOG.md | Version history | Complete |
| PROJECT_STATUS.md | Current validation status | Complete |
| VALIDATION_MATRIX.md | Validation status matrix | Complete |
| KNOWN_LIMITATIONS.md | Known limitations disclosure | Complete |
| DEPENDENCY_REVIEW.md | Dependency analysis | Complete |

### Acquisition Documentation
**Location:** `docs/acquisition/`

| Document | Purpose | Status |
|----------|---------|--------|
| BUYER_MEMO.md | Executive summary for buyers | Complete |
| TECHNICAL_DILIGENCE.md | Technical deep-dive | Complete |
| IP_ASSET_INVENTORY.md | This document | Complete |
| BUY_VS_BUILD.md | Build vs buy analysis | Complete |
| BUYER_FAQ.md | Frequently asked questions | Complete |
| DILIGENCE_CHECKLIST.md | Due diligence checklist | Complete |
| DEMO_SCRIPT.md | Demonstration script | Complete |

### Security Documentation
**Location:** `docs/security/`

| Document | Purpose | Status |
|----------|---------|--------|
| SECURITY_AUDIT_RECEIPT.md | Security audit status | Complete |

### Integration Documentation
**Location:** `docs/integrations/`

| Document | Purpose | Status |
|----------|---------|--------|
| LANGCHAIN_EXECUTOR.md | LangChain integration guide | Complete |

### Formal Verification Documentation
**Location:** `docs/formal_verification/`

| Document | Purpose | Status |
|----------|---------|--------|
| INVARIANTS.md | Formal specifications for DACT Level 6 | Complete |

## Configuration Assets

### Build Configuration
**Location:** Root directory

| File | Purpose | Status |
|------|---------|--------|
| pyproject.toml | Package configuration and dependencies | Internally validated |
| requirements.lock | Pinned dependency versions | Internally validated |
| .github/workflows/ | CI/CD workflows | Internally validated |
| .gitleaks.toml | Secret scanning configuration | Internally validated |

### Development Configuration
**Location:** Root directory

| File | Purpose | Status |
|------|---------|--------|
| pytest.ini | Test configuration | Internally validated |
| .mypy.ini | Type checking configuration | Internally validated |
| pyproject.toml (dev deps) | Development dependencies | Internally validated |

## Demo Assets

### Demo Artifacts
**Location:** `examples/demo_artifacts/`

| Artifact | Purpose | Status |
|----------|---------|--------|
| manifest.json | Demo manifest | Safe public data |
| filesystem_allow_trace.json | Filesystem allow trace | Safe public data |
| filesystem_deny_trace.json | Filesystem deny trace | Safe public data |
| database_allow_trace.json | Database allow trace | Safe public data |
| external_effect_replay_verified.json | Replay verification | Safe public data |
| external_effect_tamper_detected.json | Tamper detection | Safe public data |

### Demo Scripts
**Location:** `examples/`

| Script | Purpose | Status |
|--------|---------|--------|
| generate_demo_artifacts.py | Artifact generation script | Internally validated |
| demo_api.py | Optional FastAPI demo server | Optional |

## License Assets

### Legal Documents
**Location:** Root directory

| Document | Purpose | Status |
|----------|---------|--------|
| LICENSE | Proprietary evaluation license | Requires legal review |
| THIRD_PARTY_NOTICES.md | Third-party license attributions | Complete |

## CI/CD Assets

### GitHub Workflows
**Location:** `.github/workflows/`

| Workflow | Purpose | Status |
|----------|---------|--------|
| core-invariant-gates.yml | Determinism enforcement | Internally validated |
| module-boundary-enforcement.yml | Module boundary checks | Internally validated |
| security-scan.yml | Security scanning (bandit, pip-audit, gitleaks) | Internally validated |
| test-suite.yml | Test suite execution | Internally validated |
| cross-platform.yml | Cross-platform testing matrix | Internally validated |

## IP Classification

### Internally Validated Assets
- Core kernel (1,680 lines)
- Core executors (FileSystemExecutor, DatabaseExecutor)
- CLI and entry points
- V1 contracts (immutable)
- Test suite (338 tests)
- Core documentation
- CI/CD workflows
- Demo artifacts

### Reference-Only Assets
- Platform executor scaffolds (LangChain, OpenAI, Anthropic, HuggingFace)
- TrustEvaluator interface (raises NotImplementedError)

### Interface-Only Assets
- TrustEvaluator (formal interface, no implementation)

### Requires Legal Review
- LICENSE (proprietary evaluation license)

## IP Exclusions

The following are **not included** in this acquisition package:
- Third-party dependencies (managed via pip)
- External audit reports (none conducted)
- Production deployment infrastructure (none exists)
- Customer data (none exists)
- Operational runbooks (none exists)
- Incident response procedures (none exists)

## IP Rights

### Ownership
- All source code is owned by the repository owner
- All documentation is owned by the repository owner
- All test assets are owned by the repository owner
- All configuration files are owned by the repository owner

### Third-Party Rights
- Dependencies are subject to their respective licenses (see THIRD_PARTY_NOTICES.md)
- No third-party code is included without proper attribution
- All third-party licenses are permissive (MIT, BSD, Apache 2.0)

### License Terms
- Current license: Proprietary evaluation license
- Requires written agreement for commercial use
- License language requires legal review before public/commercial use

## Asset Summary

| Category | Count | Status |
|----------|-------|--------|
| Source code modules | 20+ | Internally validated |
| Test files | 30+ | Internally validated |
| Documentation files | 20+ | Complete |
| Configuration files | 10+ | Internally validated |
| Demo artifacts | 6 | Safe public data |
| CI/CD workflows | 5+ | Internally validated |

**Total Lines of Code:** ~5,453 lines (source only, excluding tests and docs)

## Conclusion

ExoArmur-Core includes a complete, internally validated governance kernel with comprehensive test coverage, documentation, and CI/CD infrastructure. The IP package is well-organized and clearly documented, with appropriate separation between internally validated components and reference implementations. Note: This is a reference implementation with no third-party security audit, not production-certified.
