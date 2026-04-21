# ML Isolation Policy

**Version 1.0 — April 2026**

## Core Principle

All Machine Learning (ML) components in ExoArmur are **advisory-only** and **non-binding**.

> **ML outputs may inform decisions but never bypass policy gates.**

## Policy Statement

### 1. Advisory-Only Classification

All ML-generated outputs in ExoArmur are classified as **recommendations**, not **decisions**:

- Recommendations carry `status="pending"` until reviewed
- Recommendations require separate enforcement action
- Recommendations do not trigger autonomous actions directly

### 2. Non-Binding Architecture

The ExoArmur decision pipeline enforces strict separation between ML and authority:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   ML Components │────▶│  Recommendation  │────▶│ Policy Decision │
│  (Advisory)     │     │  Queue (Pending) │     │ Point (Binding) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  Execution Gate │
                                                │   (Binding)     │
                                                └─────────────────┘
```

**Key invariant:** ML outputs never skip the Policy Decision Point.

### 3. Deterministic Decision Path

The core decision pipeline (`ProxyPipeline`) uses **deterministic policy evaluation**:

- `PolicyDecisionPoint.evaluate()` — rule-based, deterministic
- `SafetyGate.evaluate_safety()` — deterministic state machine
- `FinalVerdict.resolve()` — deterministic resolution logic

**No probabilistic components** are present in the authority path.

### 4. ML Disable Safety

Disabling all ML components **must not** affect:
- Decision correctness
- Deterministic operation
- Policy enforcement
- Audit trail completeness

**Test:** Run decision pipeline with ML disabled → identical deterministic results.

## Verified Components

### IdentityContainmentRecommender

**Location:** `src/exoarmur/identity_containment/recommender.py`

**Behavior:**
- Generates `IdentityContainmentRecommendationV1` with `status="pending"`
- Recommendations queue for approval, not direct execution
- Audit trail includes all recommendation evidence

**Verification:**
```python
recommendation = recommender.generate_recommendations()
assert recommendation.status == "pending"
assert not recommendation.is_binding  # Cannot execute directly
```

### ThreatClassificationEngine

**Location:** `src/exoarmur/decision/threat_classification_engine_v2.py`

**Behavior:**
- Produces advisory threat classifications
- Classifications feed into deterministic policy rules
- Policy rules (not ML) make binding decisions

## Compliance Verification

### Test: ML Disable Test

```bash
cd /home/oem/CascadeProjects/ExoArmur && python -m pytest tests/test_ml_isolation.py -v
```

**Expected Result:**
- Decision pipeline runs with ML enabled → valid results
- Decision pipeline runs with ML disabled → valid, identical results
- No degradation in correctness or determinism

### Test: Authority Path Inspection

```python
from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline

# Verify no ML in critical path
assert not hasattr(ProxyPipeline, 'ml_decision_component')
assert 'ML' not in ProxyPipeline.__init__.__code__.co_varnames
```

## Architecture Boundaries

### Where ML is Allowed

1. **Pre-decision analysis** — threat classification, pattern detection
2. **Recommendation generation** — containment scope suggestions
3. **Post-decision logging** — confidence scoring, explainability

### Where ML is Prohibited

1. **Policy decision point** — no ML in binding verdicts
2. **Safety gate** — deterministic state machine only
3. **Execution dispatch** — no ML in action triggering
4. **Audit chain** — cryptographic integrity, no ML modification

## Violation Detection

The following patterns indicate ML isolation violations:

- ML output directly triggers execution
- Policy bypasses when ML confidence is high
- Non-deterministic behavior correlates with ML enable/disable
- Audit records modified by ML components

**Report violations to:** Security architecture team immediately.

## Doctrine Alignment

This document implements **Claim 4** of The ExoArmur Doctrine:

> "ML outputs are: advisory‑only, non‑binding, fully traceable"

**Status:** ✅ VERIFIED — All ML components are isolated from the authority path.

## References

- `src/exoarmur/identity_containment/recommender.py` — Advisory recommendation engine
- `src/exoarmur/execution_boundary_v2/pipeline/proxy_pipeline.py` — Deterministic decision pipeline
- `tests/test_ml_isolation.py` — ML isolation compliance test
- `docs/DOCTRINE.md` — Claim 4: ML Isolation from Authority Path
