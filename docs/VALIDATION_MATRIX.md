# Validation Matrix

*Last validated: June 1, 2026*

## Overview

This matrix documents the current validation status of ExoArmur-Core across all quality, security, and compliance dimensions.

## Test Suite Status

| Category | Command | Result | Status |
|----------|---------|--------|--------|
| Unit Tests | `python -m pytest tests/ -q -rs` | 338 passed, 17 skipped, 0 failed | ✅ GREEN |
| E2E Tests | `python -m pytest tests/e2e/ -v` | 22 passed, 0 failed | ✅ GREEN |
| Three-Run Stability | `for i in 1 2 3; do pytest; done` | Consistent results | ✅ GREEN |

## Code Quality Status

| Tool | Command | Result | Status |
|------|---------|--------|--------|
| Black | `black --check src tests` | All files compliant | ✅ CLEAN |
| Isort | `isort --check-only src tests` | All imports compliant | ✅ CLEAN |
| Mypy | `mypy src` | No errors (informational notes only) | ✅ CLEAN |

## Security Scanning Status

| Tool | Command | Result | Status |
|------|---------|--------|--------|
| Bandit SAST | `bandit -r src/` | No issues identified (10 B608 properly suppressed) | ✅ CLEAN |
| pip-audit (clean install) | Fresh venv with pip 26.1.2 | No known vulnerabilities | ✅ CLEAN |
| pip check | `python -m pip check` | No broken requirements | ✅ CLEAN |
| Gitleaks | `gitleaks detect --no-git --redact` | No secrets in working tree | ✅ CLEAN |

## DACT Compliance Status

| Level | Requirement | Validation Method | Status |
|-------|-------------|-------------------|--------|
| 1 | Deterministic Replay | Internal test suite | ✅ Internally validated |
| 2 | Cryptographic Attestation | Internal test suite | ✅ Internally validated |
| 3 | Counterfactual Analysis | Internal test suite | ✅ Internally validated |
| 4 | ML Isolation | Internal test suite | ✅ Internally validated |
| 5 | Air-Gap Integrity | Internal test suite | ✅ Internally validated |
| 6 | Formal Verification | Third-party review | ⏳ Pending |

## Known Test Skips (17 total)

| Category | Count | Reason |
|----------|-------|--------|
| FileSystemExecutor get_state_hash() | 10 | Method not part of ExecutorPlugin protocol |
| ExecutorPlugin get_execution_history() | 2 | Method not part of ExecutorPlugin protocol |
| Evidence dict structure variance | 2 | Evidence structure not standardized across executors |
| Executor boundary structure location | 2 | Some structures defined outside kernel module |
| Environment-dependent capability comparison | 1 | Test environment may have overlapping supported_targets |

## Dependency Security Status

| Package | Version | Known Vulnerabilities | Status |
|---------|---------|---------------------|--------|
| pydantic | 2.12.5 | None | ✅ Clean |
| pydantic-core | 2.41.5 | None | ✅ Clean |
| cryptography | 48.0.0 | None | ✅ Clean |
| python-ulid | 3.1.0 | None | ✅ Clean |
| click | 8.4.1 | None | ✅ Clean |
| python-json-logger | 4.1.0 | None | ✅ Clean |
| typing-extensions | 4.15.0 | None | ✅ Clean |
| typing-inspection | 0.4.2 | None | ✅ Clean |
| cffi | 2.0.0 | None | ✅ Clean |
| annotated-types | 0.7.0 | None | ✅ Clean |

**Note**: All dependencies scanned with pip-audit using upgraded pip (26.1.2) in fresh virtual environment.

## Code Suppression Audit

| Type | Count | Scope | Justification |
|------|-------|-------|---------------|
| type: ignore | 6 | Line-specific | Import-untyped, dynamic plugin loading, method overrides |
| nosec | 15 | Line-specific | SQL injection (validated by _validate_sql_identifier), constant strings |
| noqa | 0 | - | - |
| pragma: no cover | 0 | - | - |

**Conclusion**: No broad/global suppressions. All suppressions are narrow and justified.

## Platform Compatibility

| Platform | Python Version | Status |
|----------|---------------|--------|
| Linux | 3.10, 3.11, 3.12 | ✅ Tested |
| macOS | 3.10, 3.11, 3.12 | ✅ Tested |
| Windows | 3.10, 3.11, 3.12 | ✅ Tested |

## Not Validated

- **Third-party security audit** - None conducted. Self-validated only.
- **Formal proofs** - Invariants tested, not formally proven.
- **Production deployment at scale** - No known production deployments.
- **Byzantine Fault Tolerance** - Framework exists, not tested in distributed settings.
- **Federation in hostile environments** - Not exercised against external red team.

## Validation Commands

Reproduce validation results:

```bash
# Code quality
black --check src tests
isort --check-only src tests
mypy src

# Security scanning
bandit -r src/
python -m pip check

# Test suite
python -m pytest tests/ -q -rs
python -m pytest tests/e2e/ -v

# Clean install security audit
python -m venv /tmp/exoarmur_audit_venv
/tmp/exoarmur_audit_venv/bin/python -m pip install --upgrade pip
/tmp/exoarmur_audit_venv/bin/pip install .
/tmp/exoarmur_audit_venv/bin/pip-audit
```

## Current Baseline

- **Version**: 2.1.0
- **License**: Proprietary evaluation license
- **Status**: Private reference implementation, buyer/pilot evaluation ready
- **Last validated**: June 1, 2026
