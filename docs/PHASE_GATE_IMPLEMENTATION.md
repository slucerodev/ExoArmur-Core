# ADMO Phase Gate Implementation

## Purpose and Governance Compliance

This Phase Gate mechanism resolves the governance contradiction where V2 functionality exists at the ragged edge without violating Phase 1 isolation.

### ADMO Organism Law Compliance

**LAW-01: No Central Brain** - Phase gate is a local decision mechanism, not a centralized controller.

**LAW-06: Evidence-Backed Decisions** - Phase changes are explicit, auditable environment variables (`EXOARMUR_PHASE=2`) that provide clear evidence for governance decisions.

**LAW-09: Graceful Degradation** - Phase 1 remains fully functional and safe without Phase 2 components.

### Governance Problem Solved

**Before Phase Gate:**
- `enabled=True` activated real behavior immediately
- Isolation tests expected `NotImplementedError` 
- Acceptance tests required future behavior
- This created a governance contradiction

**After Phase Gate:**
- `enabled=True` + Phase gate NOT present → raises `NotImplementedError`
- `enabled=True` + Phase gate present → allows prototype behavior
- `enabled=False` → inert (no-op)
- Isolation tests pass without modification
- Acceptance tests can explicitly opt into Phase 2

### Behavior Rules

1. **Phase 1 (Default)**: `EXOARMUR_PHASE=1` or unset
   - All V2 components raise `NotImplementedError` when `enabled=True`
   - Phase 1 core loop remains fully functional
   - No prototype behavior leaks into production

2. **Phase 2 (Explicit)**: `EXOARMUR_PHASE=2`
   - V2 components can activate prototype behavior
   - Used for development and acceptance testing
   - Requires explicit opt-in via environment variable

### Implementation Pattern

```python
# In each V2 component method
if self.config.enabled:
    # Phase Gate enforcement
    PhaseGate.check_phase_2_eligibility("ComponentName")
    # Phase 2 implementation here
else:
    # Phase 1 safe behavior (no-op)
```

### Components Protected

All V2 components now enforce strict Phase isolation:
- `FederationManager` - Multi-cell federation coordination
- `CrossCellAggregator` - Belief aggregation across cells  
- `ApprovalService` - Human operator approval workflows
- `ControlAPI` - Operator control plane REST API
- `OperatorInterface` - Human operator interaction

### Usage

**Phase 1 (Production Safe):**
```bash
# Default or explicit
export EXOARMUR_PHASE=1
python -m pytest tests/test_v2_feature_flag_isolation.py  # Passes
```

**Phase 2 (Development/Acceptance):**
```bash
# Explicit opt-in required
export EXOARMUR_PHASE=2
python -m pytest tests/test_federation_v2_acceptance.py  # Can pass
```

This mechanism ensures Phase 1 isolation while allowing prototype development at the ragged edge, maintaining strict ADMO governance principles.
