# DECISION_LIMITS.md

## Purpose
Defines the decision boundaries, confidence thresholds, and action class limitations that constrain all decision making in ExoArmur.

## Definitions

**Decision Limits**: The predefined boundaries that constrain what decisions cells may make and under what conditions.

**Action Classes**: Four categories of defensive actions with different risk profiles and approval requirements.

**A0_observe**: Observation-only actions including logging, tagging, and notification. No execution side effects.

**A1_soft_containment**: Reversible containment actions with explicit TTL or rollback support. Minimal impact.

**A2_hard_containment**: Strong containment actions requiring higher confidence thresholds. Moderate impact.

**A3_irreversible**: High-impact or destructive actions with lasting effect. Maximum impact.

**Confidence Thresholds**: Minimum confidence scores required for different action classes and decision scenarios.

**Autonomy Envelope**: The policy-defined boundary of what actions a cell may execute independently versus requiring approval.

**Quorum Requirements**: Minimum number of distinct cells that must contribute evidence for high-impact actions.

**Aggregate Score**: The collective confidence computed from multiple independent beliefs using weighted confidence formulas.

**Trust Floors**: Minimum trust scores required for cells to execute certain action classes independently.

## Action Class Definitions and Limits

### A0_observe (Observation)
**Purpose**: Information gathering and monitoring without system modification
**Examples**: Logging events, tagging entities, sending notifications, updating metrics
**Impact**: No execution side effects
**Approval Requirements**: None (local authority sufficient)
**Confidence Threshold**: None required (observation is always allowed)
**Trust Requirements**: None required
**Quorum Requirements**: None required

### A1_soft_containment (Reversible Containment)
**Purpose**: Reversible containment with minimal impact and explicit rollback capability
**Examples**: Temporary rate limiting, short-term network isolation, process suspension, file quarantine
**Impact**: Low and reversible
**Approval Requirements**: Local if policy authorized
**Confidence Threshold**: 0.80 minimum local confidence
**Trust Requirements**: Trust score >= 0.35 for any execution
**Quorum Requirements**: None required for local execution

### A2_hard_containment (Strong Containment)
**Purpose**: Strong containment actions with moderate impact and limited reversibility
**Examples**: Network segmentation, host isolation, user account suspension, service shutdown
**Impact**: Moderate and potentially difficult to reverse
**Approval Requirements**: Local if confidence >= 0.90 OR quorum >= 2 with aggregate_score >= 0.85
**Confidence Threshold**: 0.90 minimum local confidence OR collective thresholds
**Trust Requirements**: Trust score >= 0.50 for local execution, >= 0.35 for any execution
**Quorum Requirements**: 2 distinct cells minimum for collective execution

### A3_irreversible (High-Impact Actions)
**Purpose**: High-impact or destructive actions with lasting effect
**Examples**: Permanent user disable, data deletion, system reconfiguration, credential revocation
**Impact**: High and potentially irreversible
**Approval Requirements**: Human approval OR quorum >= 3 with aggregate_score >= 0.92
**Confidence Threshold**: 0.97 minimum local confidence AND collective thresholds
**Trust Requirements**: Trust score >= 0.80 for local execution, >= 0.35 for any execution
**Quorum Requirements**: 3 distinct cells minimum for collective execution

## Confidence Threshold Matrix

| Action Class | Local Confidence | Aggregate Score | Quorum | Trust Floor |
|--------------|------------------|-----------------|---------|-------------|
| A0_observe | Not required | Not required | None | None |
| A1_soft_containment | >= 0.80 | Not required | None | >= 0.35 |
| A2_hard_containment | >= 0.90 OR | >= 0.85 | >= 2 | >= 0.50 local, >= 0.35 any |
| A3_irreversible | >= 0.97 AND | >= 0.92 | >= 3 | >= 0.80 local, >= 0.35 any |

## Decision Logic Rules

### Local Decision Authority
A cell may execute actions locally when:
- Policy authorizes the action class
- Safety gate evaluation returns "allow"
- Local confidence meets minimum threshold
- Cell trust score meets minimum floor
- No conflicts are detected that prohibit execution

### Collective Decision Authority
A cell may execute actions based on collective confidence when:
- Policy authorizes the action class
- Safety gate evaluation returns "allow"
- Quorum requirements are satisfied
- Aggregate confidence meets minimum threshold
- Sufficient distinct cells contribute non-duplicate evidence
- No conflicts are detected that require human approval

### Escalation Requirements
Actions must be escalated when:
- Confidence thresholds are not met
- Quorum requirements are not satisfied
- Trust scores are below minimum floors
- Conflicts are detected between credible beliefs
- Safety gate evaluation requires escalation
- Policy verification fails or is unavailable

## Allowed Decision Behaviors

### Threshold-Based Decisions
- Cells may execute A1 actions when local confidence >= 0.80 and policy allows
- Cells may execute A2 actions when local confidence >= 0.90 OR collective thresholds met
- Cells may execute A3 actions only when local confidence >= 0.97 AND collective thresholds met
- Cells may always execute A0 actions regardless of confidence

### Trust-Based Decisions
- Cells with trust scores >= 0.80 may execute A3 actions locally if other thresholds met
- Cells with trust scores >= 0.50 may execute A2 actions locally if confidence >= 0.90
- Cells with trust scores < 0.35 may only execute A0/A1 actions
- Trust scores may limit autonomy but never override safety denials

### Collective Decisions
- Multiple cells may form quorum for A2 actions with 2+ distinct cells
- Multiple cells may form quorum for A3 actions with 3+ distinct cells
- Aggregate confidence must meet minimum thresholds for collective execution
- Beliefs must be deduplicated to prevent confidence inflation

### Escalation Decisions
- Cells may request human approval when thresholds are not met
- Cells may require quorum when local confidence is insufficient
- Cells may degrade to lower action classes when constraints not satisfied
- Cells may observe-only when no execution criteria are met

## Forbidden Decision Behaviors

### Threshold Violations
- No execution of A1 actions with confidence < 0.80
- No execution of A2 actions with confidence < 0.90 without collective support
- No execution of A3 actions with confidence < 0.97 under any circumstances
- No execution when trust scores are below minimum floors

### Authority Violations
- No execution without policy authorization
- No execution when safety gate denies
- No execution when kill switches are active
- No bypassing of human approval requirements

### Collective Violations
- No counting duplicate beliefs for quorum satisfaction
- No execution when quorum requirements are not met
- No ignoring of conflict detection requirements
- No fabrication of collective confidence scores

### Trust Violations
- No execution by cells with trust scores below minimum floors
- No manipulation of trust scores to bypass constraints
- No ignoring of trust-based autonomy limitations
- No execution when trust constraints require escalation

## Example

Cell decides on A2 hard containment action:

1. **Policy Check**: Policy allows A2 actions with local_or_quorum approval
2. **Local Confidence**: Cell calculates 0.88 confidence (below 0.90 threshold)
3. **Trust Check**: Cell trust score is 0.82 (above 0.50 floor)
4. **Collective Check**: 
   - 2 other cells emit similar beliefs
   - Aggregate confidence = 0.91 (above 0.85 threshold)
   - Quorum count = 3 (above 2 minimum)
5. **Safety Check**: Safety gate allows A2 with collective confidence
6. **Decision**: Execute A2 action based on collective authority

## Non-Example

Cell executes A3 irreversible action with low confidence:

1. **Local Confidence**: Cell calculates 0.85 confidence (below 0.97 minimum)
2. **Trust Check**: Cell trust score is 0.75 (below 0.80 floor for A3)
3. **Collective Check**: Only 1 cell (itself) has evidence
4. **Safety Check**: Safety gate requires human approval for A3
5. **Action**: Cell executes A3 action anyway

This violates decision limits by ignoring confidence thresholds, trust requirements, quorum needs, and safety constraints.
