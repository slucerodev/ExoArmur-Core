# SAFETY_INVARIANTS.md

## Purpose
Defines the immutable safety rules and constraints that can never be violated in ExoArmur under any circumstances.

## Definitions

**Safety Invariant**: A rule or constraint that must never be violated under any circumstances, including system failures, partitions, or emergency conditions.

**Severity Ladder**: The graduated response model that defaults to safer behaviors when uncertainty exists or dependencies degrade.

**Safety Gate**: The deterministic enforcement mechanism that applies all safety invariants before allowing any execution.

**Safe Default**: The behavior that the system defaults to when uncertainty exists or constraints cannot be verified.

**Irreversible Action**: Any action that has lasting effect and cannot be easily undone, requiring the highest safety constraints.

**Containment Action**: Any action that limits or restricts system behavior, with varying degrees of reversibility.

**Observation Action**: Any action that only gathers information without modifying system behavior.

**Safety Verdict**: The output of the safety gate that determines whether execution may proceed (allow/deny/require_quorum/require_human).

**Risk Assessment**: The evaluation of potential harm, blast radius, and system impact of proposed actions.

## Core Safety Invariants (Immutable)

### Invariant 1: No Central Brain Required
**Statement**: No single service or component may be required for perception, decisioning, safety gating, or execution.
**Rationale**: Ensures system survivability and prevents single points of failure.
**Enforcement**: Each cell must possess all mandatory subsystems and operate autonomously during isolation.
**Violation Detection**: System health monitoring verifies no cell depends on central services for core functions.

### Invariant 2: Safety Overrides Mission
**Statement**: Safety controller verdicts supersede all decision engine outputs and mission objectives.
**Rationale**: Prevents mission-driven optimization from overriding safety constraints.
**Enforcement**: Safety gate must be evaluated after policy authorization but before execution.
**Violation Detection**: Audit trails verify safety verdict is never bypassed or ignored.

### Invariant 3: Beliefs Not Commands
**Statement**: Cells propagate beliefs consisting of observations, confidence, and supporting evidence. Cells never issue direct action commands to other cells.
**Rationale**: Prevents command injection attacks and preserves local decision autonomy.
**Enforcement**: All inter-cell communication must use BeliefV1 schema only.
**Violation Detection**: Message validation ensures no command patterns exist in inter-cell traffic.

### Invariant 4: Evidence-Backed Decisions
**Statement**: Every decision and action must reference sufficient evidence to allow deterministic audit replay and human review.
**Rationale**: Ensures accountability and enables post-incident analysis.
**Enforcement**: All decisions must include evidence_refs with traceable artifacts.
**Violation Detection**: Audit validation verifies all decisions have complete evidence chains.

### Invariant 5: Idempotent Action Execution
**Statement**: All execution intents must be idempotent and safe to retry without unintended side effects.
**Rationale**: Prevents duplicate execution and ensures safe recovery from failures.
**Enforcement**: All ExecutionIntentV1 must include idempotency_key and retry-safe parameters.
**Violation Detection**: Execution logging verifies idempotency key enforcement and duplicate prevention.

### Invariant 6: Partition Survivability
**Statement**: Under network partition, cells continue local reflex operation using cached policy, local belief memory, and deterministic safety behavior.
**Rationale**: Ensures defensive capability continues during network disruptions.
**Enforcement**: Cells must maintain local policy cache and belief store with appropriate TTL.
**Violation Detection**: Partition testing verifies continued operation with degraded functionality.

### Invariant 7: Severity-Graduated Safe Defaults
**Statement**: When uncertainty exists or dependencies degrade, cells follow a severity ladder: Low severity (observe-only), Medium severity (soft containment), High severity (execute if policy authorizes, otherwise escalate).
**Rationale**: Prevents over-reaction when information is incomplete or unreliable.
**Enforcement**: Safety gate must apply severity ladder rules in degraded mode.
**Violation Detection**: Degraded mode testing verifies appropriate default behaviors.

### Invariant 8: Policy-Authorized Autonomy
**Statement**: Cells may execute defensive actions independently only when explicitly authorized by valid, signed tenant policy bundles defining autonomy envelopes.
**Rationale**: Prevents unauthorized autonomous actions and ensures policy compliance.
**Enforcement**: Policy verification must succeed before any execution beyond A0.
**Violation Detection**: Policy validation ensures no execution without verified bundle authorization.

### Invariant 9: Trust-Constrained Autonomy
**Statement**: Trust scores limit autonomy based on cell reputation and historical accuracy. Low trust forces escalation for high-impact actions.
**Rationale**: Prevents low-reputation cells from executing high-impact actions independently.
**Enforcement**: Safety gate must enforce trust floor constraints before allowing execution.
**Violation Detection**: Trust validation verifies no execution below trust floors.

### Invariant 10: Non-Authoritative Learning
**Statement**: Learning systems may propose improvements but may never directly authorize irreversible actions in production environments.
**Rationale**: Prevents uncontrolled learning system behavior and ensures human oversight.
**Enforcement**: All learning system outputs must be treated as suggestions requiring human approval.
**Violation Detection**: Learning system monitoring verifies no direct action authorization.

## Severity Ladder Safe Defaults

### Low Severity Events
**Default Behavior**: A0_observe (observation-only)
**Conditions**: Uncertainty exists, evidence insufficient, or system degraded
**Allowed Actions**: Logging, tagging, notification, metric collection
**Forbidden Actions**: Any execution that modifies system behavior

### Medium Severity Events
**Default Behavior**: A1_soft_containment_or_observe
**Conditions**: Moderate confidence but uncertainty remains
**Allowed Actions**: Reversible containment with TTL, rate limiting, temporary restrictions
**Forbidden Actions**: Irreversible actions, permanent modifications

### High Severity Events
**Default Behavior**: A2_or_escalate
**Conditions**: High confidence but policy or safety constraints not fully satisfied
**Allowed Actions**: Hard containment if explicitly authorized, otherwise escalation
**Forbidden Actions**: A3 actions without explicit approval

### Critical Severity Events
**Default Behavior**: A2_or_A3_with_strict_gates
**Conditions**: Maximum confidence with all constraints satisfied
**Allowed Actions**: Any action class with appropriate approval gates
**Forbidden Actions**: Any action without satisfying all safety and policy requirements

## Safety Gate Enforcement Rules

### Ordering Requirements (Immutable)
1. Kill switches evaluated first
2. Policy verification evaluated second
3. Conflict constraints evaluated third
4. Trust constraints evaluated fourth
5. Threshold checks evaluated fifth
6. Approval gates evaluated sixth
7. Final allow/deny decision evaluated last

### Prohibition Rules
- No execution when any kill switch is active (except A0)
- No execution when policy verification fails (except A0)
- No execution when safety verdict is "deny"
- No A3 execution when conflicts are detected without human approval
- No A2/A3 execution when trust scores are below minimum floors
- No execution when quorum requirements are not satisfied

### Escalation Requirements
- Escalate to human approval when confidence thresholds are not met
- Escalate to quorum when local execution constraints are not satisfied
- Escalate to higher authority when conflicts are detected
- Escalate to observation-only when system is degraded

## Allowed Safety Behaviors

### Safe Decision Making
- Apply all safety invariants before any execution
- Use severity ladder when uncertainty exists
- Require appropriate approvals for high-impact actions
- Enforce trust constraints and collective thresholds

### Safe Execution
- Execute only idempotent actions with proper keys
- Maintain complete audit trails with evidence chains
- Roll back or compensate when execution fails
- Monitor for unintended side effects

### Safe Degradation
- Continue observation-only operations during failures
- Use cached policies when verification is unavailable
- Apply stricter safety constraints in degraded mode
- Maintain defensive posture even with reduced capabilities

## Forbidden Safety Behaviors

### Prohibited Shortcuts
- No bypassing of safety gate evaluation
- No execution before all constraints are satisfied
- No ignoring of kill switch prohibitions
- No overriding of safety denials by any authority

### Prohibited Risk Taking
- No execution with insufficient evidence
- No high-impact actions without appropriate approvals
- No ignoring of trust score limitations
- No bypassing of quorum requirements

### Prohibited Autonomy
- No self-modification of safety constraints
- No independent action beyond policy authorization
- No learning system direct action authorization
- No emergency override of safety rules

## Example

Safety gate evaluation for A3 action:

1. **Kill Switch Check**: No global or tenant kill switches active
2. **Policy Verification**: Policy bundle valid and verified
3. **Conflict Check**: No conflicts detected between beliefs
4. **Trust Check**: Cell trust score 0.92 above 0.80 minimum for A3
5. **Threshold Check**: Local confidence 0.98 above 0.97, collective confidence 0.94 above 0.92
6. **Approval Check**: Human approval granted for A3 action
7. **Final Decision**: Allow execution with all safety invariants satisfied

## Non-Example

Safety gate bypass for emergency response:

1. **Kill Switch Check**: Global kill switch active but ignored
2. **Policy Verification**: Policy verification failed but bypassed
3. **Trust Check**: Cell trust score 0.45 below 0.80 but ignored
4. **Threshold Check**: Local confidence 0.75 below 0.97 but ignored
5. **Approval Check**: No human approval but emergency override claimed
6. **Execution**: A3 action executed without safety constraints

This violates multiple safety invariants by ignoring kill switches, policy verification, trust constraints, confidence thresholds, and approval requirements.
