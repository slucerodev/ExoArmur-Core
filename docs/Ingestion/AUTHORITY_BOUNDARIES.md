# AUTHORITY_BOUNDARIES.md

## Purpose
Defines where authority exists in the ExoArmur system, where it explicitly does not exist, and the immutable precedence rules that govern all decision making.

## Definitions

**Authority**: The legitimate power to make decisions or take actions within the system. Authority in ExoArmur is distributed, not centralized.

**Arbitration Precedence**: The fixed ordering of authority that resolves conflicts between kill switches, policy verification, safety gating, trust constraints, collective confidence, and local decisions.

**Kill Switch Authority**: The highest authority that can immediately prohibit all execution except A0 observation. Both global and tenant-level kill switches exist.

**Policy Authority**: The authority to define what actions are permitted and what approvals are required. Policy authorizes but does not force execution.

**Safety Authority**: The authority to permit or deny actions based on deterministic safety rules. Safety verdicts override all other authorities except kill switches.

**Trust Authority**: The authority to modify autonomy based on cell reputation and historical accuracy. Trust constraints can force escalation but never override safety denials.

**Collective Authority**: The authority of multiple cells acting together through quorum formation and aggregate confidence. Collective authority applies to A2/A3 actions requiring distributed consensus.

**Local Authority**: The authority of a single cell to make decisions and propose actions. Local authority is subject to all higher-level constraints.

**Human Authority**: The authority granted to human operators through approval gates. Human approval satisfies policy requirements but never overrides safety denials.

## Authority Hierarchy (Immutable Order)

1. **Kill Switch Authority** (Level 1)
   - Global kill switch overrides everything
   - Tenant kill switch overrides everything for that tenant
   - Only A0_observe actions permitted when active

2. **Policy Verification Authority** (Level 2)
   - Invalid or unverified policy bundles prohibit execution beyond A0
   - Forces escalation per severity ladder
   - Cannot be overridden by any other authority

3. **Safety Authority** (Level 3)
   - Safety gate verdicts override decision engine and policy allowances
   - Safety can deny or require escalation even if policy allows
   - Safety constraints are never overridden by collective or local authority

4. **Policy Authorization Authority** (Level 4)
   - Policy determines what actions are allowed and approval requirements
   - Policy cannot force execution; it only authorizes
   - Policy authorization is subject to safety authority

5. **Trust Authority** (Level 5)
   - Trust scores modify autonomy envelopes
   - Low trust can prohibit A2/A3 local execution
   - Trust constraints force escalation but never override safety

6. **Collective Authority** (Level 6)
   - Determines quorum satisfaction and aggregate confidence thresholds
   - Applies to A2/A3 actions requiring distributed consensus
   - Subject to all higher-level authorities

7. **Local Authority** (Level 7)
   - Local decisions propose intents and confidence
   - Used only after all higher-level constraints are satisfied
   - Cannot override any higher authority

## Allowed Authority Exercised

### Kill Switch Authority
- Global operators may engage global kill switch
- Tenant administrators may engage tenant-specific kill switch
- Kill switches immediately prohibit all execution except A0 observation
- Kill switch status is propagated to all cells

### Policy Authority
- Policy authorities may define action allowances and approval requirements
- Policy authorities may set autonomy envelopes and trust constraints
- Policy authorities may sign and issue verified policy bundles
- Policy authority applies only to authorized actions

### Safety Authority
- Safety controllers may deny any action regardless of policy authorization
- Safety controllers may require escalation for high-impact actions
- Safety controllers may enforce severity ladder defaults
- Safety authority is absolute except for kill switches

### Trust Authority
- Trust systems may modify autonomy based on cell reputation
- Trust constraints may force escalation for low-trust cells
- Trust authority may limit local execution of A2/A3 actions
- Trust authority never overrides safety denials

### Collective Authority
- Multiple cells may form quorum for A2/A3 actions
- Collective confidence may satisfy thresholds for high-impact actions
- Collective authority applies only when policy authorizes and safety permits
- Collective authority never overrides safety or policy denials

### Local Authority
- Individual cells may make decisions and propose execution intents
- Local authority includes A0 observation and A1 soft containment when authorized
- Local authority is subject to all higher-level constraints
- Local authority never overrides higher authorities

### Human Authority
- Human operators may grant approval for actions requiring human gates
- Human approval satisfies policy requirements but not safety constraints
- Human authority is documented and auditable
- Human authority never overrides safety denials

## Forbidden Authority Exercised

### Centralized Authority
- No central brain or controller may direct cell actions
- No single point of failure may be required for system operation
- No hierarchical command structure may exist between cells
- No cell may issue commands to other cells

### Policy Override Authority
- Policy may not force execution of actions
- Policy may not override safety gate denials
- Policy may not bypass kill switch prohibitions
- Policy may not authorize actions outside defined autonomy envelopes

### Safety Override Authority
- Safety constraints may not be overridden by mission objectives
- Safety denials may not be bypassed by collective confidence
- Safety rules may not be suspended for any reason
- Safety authority may not be delegated or transferred

### Trust Override Authority
- Trust scores may not be used to bypass safety constraints
- Trust authority may not override kill switch prohibitions
- Trust constraints may not be ignored for any action class
- Trust scores may not be fabricated or manipulated

### Collective Override Authority
- Collective confidence may not override safety denials
- Quorum formation may not bypass policy requirements
- Collective authority may not execute unauthorized actions
- Collective decisions may not ignore trust constraints

### Local Override Authority
- Local decisions may not override safety constraints
- Local authority may not bypass policy verification
- Local execution may not ignore trust constraints
- Local cells may not issue commands to other cells

## Example

A cell wants to execute A3 irreversible action:

1. **Kill Switch Check**: No global or tenant kill switches active
2. **Policy Verification**: Policy bundle is valid and verified
3. **Policy Authorization**: Policy allows A3 actions with human approval
4. **Safety Evaluation**: Safety gate permits A3 with human approval required
5. **Trust Check**: Cell trust score 0.92 exceeds 0.80 minimum for A3
6. **Collective Check**: Quorum of 3 cells with aggregate score 0.94 exceeds thresholds
7. **Local Decision**: Local confidence 0.98 exceeds 0.97 minimum
8. **Human Approval**: Human operator grants approval
9. **Execution**: Action executes with all authorities satisfied

## Non-Example

A cell executes A3 action without human approval because collective confidence is high:

- Policy requires human approval for A3 actions
- Safety gate allows A3 with human approval
- Collective confidence exceeds thresholds
- Cell bypasses human approval requirement
- Action executes without satisfying all authority levels

This violates authority boundaries by ignoring policy approval requirements and attempting to override the established authority hierarchy.
