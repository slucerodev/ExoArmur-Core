# ML Isolation Policy

**Version 2.0 — May 2026**

## Core Principle

The ExoArmur kernel has **zero ML in the authority path**. All decision-making is deterministic and rule-based.

> **The kernel contains no ML components whatsoever. ML components, if present in external modules, must be advisory-only and non-binding.**

## Policy Statement

### 1. Zero ML in Kernel

The ExoArmur kernel (~1,100 lines) contains:

- **No ML imports** in kernel modules
- **No ML dependencies** in core execution path
- **No probabilistic components** in decision pipeline
- **Zero ML in authority path**

### 2. Deterministic Decision Path

The kernel uses **deterministic policy evaluation**:

- `PolicyDecisionPoint.evaluate()` — rule-based, deterministic
- `SafetyGate.evaluate_safety()` — deterministic state machine
- `ProxyPipeline.execute_with_trace()` — deterministic execution flow

**No probabilistic components** are present in the kernel.

### 3. External ML Modules (Optional)

If external ML modules are added, they must be:

- **Advisory-only**: ML outputs classified as recommendations, not decisions
- **Non-binding**: Recommendations require separate enforcement action
- **Fully traceable**: All ML outputs logged to audit trail
- **Isolated**: ML modules cannot bypass policy gates

### 4. ML Disable Safety

Disabling all ML components **must not** affect:
- Decision correctness
- Deterministic operation
- Policy enforcement
- Audit trail completeness

## Kernel Verification

### Dependency Audit

The kernel has been verified to have zero ML dependencies:

```bash
# Scan for ML imports in kernel
grep -r "import torch\|import transformers\|import sklearn\|import tensorflow" \
  src/exoarmur/kernel src/exoarmur/executors

# Expected: No matches
```

**Result:** ✅ No ML imports found in kernel or executors.

### Network Dependency Audit

The kernel has been verified to have zero network dependencies:

```bash
# Scan for network imports
grep -r "import urllib\|import requests\|import socket\|import nats" \
  src/exoarmur/kernel src/exoarmur/executors

# Expected: No matches
```

**Result:** ✅ No network imports found in kernel or executors.

## Architecture Boundaries

### Where ML is Prohibited in Kernel

| Component | ML Status | Reason |
|-----------|-----------|--------|
| `kernel/boundary.py` | ❌ Prohibited | Core governance must be deterministic |
| `kernel/clock.py` | ❌ Prohibited | Time abstraction must be deterministic |
| `kernel/ids.py` | ❌ Prohibited | ID generation must be deterministic |
| `kernel/trust_evaluator.py` | ❌ Prohibited | Trust evaluation uses formal interface |
| `executors/file_system_executor.py` | ❌ Prohibited | Executor must be deterministic |
| `executors/database_executor.py` | ❌ Prohibited | Executor must be deterministic |

### Where ML is Allowed (External Modules Only)

1. **Pre-decision analysis** — threat classification, pattern detection
2. **Recommendation generation** — containment scope suggestions
3. **Post-decision logging** — confidence scoring, explainability

**Constraint:** External ML modules must integrate through ProxyPipeline and respect policy/safety gates.

## Compliance Verification

### Test: Kernel ML Isolation

```bash
# Verify kernel has no ML dependencies
python -c "
import sys
sys.path.insert(0, 'src')
from exoarmur import kernel, executors
print('Kernel imports verified')
"
```

**Expected Result:** No ML import errors.

### Test: Deterministic Execution

```bash
# Run kernel tests with deterministic clock
python -m pytest tests/executors/ -v
```

**Expected Result:** All tests pass with deterministic results.

## Violation Detection

The following patterns indicate ML isolation violations:

- ML imports in kernel modules
- ML components in authority path
- Non-deterministic behavior in decision pipeline
- Network dependencies in kernel

**Report violations to:** Security architecture team immediately.

## Doctrine Alignment

This document implements **Claim 4** of The ExoArmur Doctrine:

> "ML outputs are: advisory‑only, non‑binding, fully traceable"

**Status:** ✅ VERIFIED — The kernel has zero ML in the authority path. External ML modules, if present, must be advisory-only.

## DACT Compliance

This document supports **DACT v0.2 Level 4 (ML Isolation)**:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Zero ML in authority path | ✅ Verified | Kernel has no ML imports |
| Deterministic decision path | ✅ Verified | All decisions are rule-based |
| ML disable safety | ✅ Verified | Kernel has no ML to disable |

## References

- `src/exoarmur/kernel/` — Core kernel modules (zero ML)
- `src/exoarmur/executors/` — Executor implementations (zero ML)
- `docs/DACT_STANDARD_v0.2.md` — DACT Level 4 specification
- `docs/DOCTRINE.md` — Claim 4: ML Isolation from Authority Path
