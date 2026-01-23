# PHASE 2B PROTOCOL LAW

## LEGAL STATUS

**THIS PROTOCOL IS LEGALLY IMMUTABLE**

The Federation Coordination Protocol v2.0, as defined in `spec/contracts/coordination_v2.yaml`, is declared legally immutable under ExoArmur ADMO governance. Any modification requires formal governance approval with unanimous consent from the ADMO governance board.

## ALLOWED MESSAGE TYPES (EXACTLY FIVE)

1. `coordination.announcement.v2`
   - Purpose: "I am available to coordinate X"
   - Semantic: Descriptive availability announcement

2. `coordination.claim.v2`
   - Purpose: "I am coordinating X until T"
   - Semantic: Descriptive activity claim

3. `coordination.release.v2`
   - Purpose: "I am no longer coordinating X"
   - Semantic: Descriptive release notification

4. `coordination.observation.v2`
   - Purpose: "I observed Y at time T"
   - Semantic: Non-authoritative observation sharing

5. `coordination.intent.broadcast.v2`
   - Purpose: "I intend to do Z"
   - Semantic: Non-binding intent broadcast

**NO OTHER MESSAGE TYPES ARE PERMITTED.**

## ALLOWED FIELDS PER MESSAGE

### coordination.announcement.v2
- `coordination_id` (UUID, required)
- `sender_cell_id` (string, required)
- `owner_cell_id` (string, required)
- `scope` (object, required)
- `issued_at` (datetime, required)
- `expires_at` (datetime, required)
- `schema_version` (string, required)
- `coordination_type` (enum: "availability_announcement", required)
- `capabilities` (array of strings, required)
- `preferences` (array of strings, required)

### coordination.claim.v2
- `coordination_id` (UUID, required)
- `sender_cell_id` (string, required)
- `owner_cell_id` (string, required)
- `scope` (object, required)
- `issued_at` (datetime, required)
- `expires_at` (datetime, required)
- `schema_version` (string, required)
- `coordination_type` (enum: "temporary_coordination", required)
- `coordination_activity` (enum: "coordinating", "participating", "observing", required)
- `claimed_resources` (array of strings, required)

### coordination.release.v2
- `coordination_id` (UUID, required)
- `sender_cell_id` (string, required)
- `owner_cell_id` (string, required)
- `scope` (object, required)
- `issued_at` (datetime, required)
- `expires_at` (datetime, required)
- `schema_version` (string, required)
- `coordination_type` (enum: "temporary_coordination", required)
- `release_reason` (string, required)
- `final_state` (enum: "released", "expired", "failed", required)

### coordination.observation.v2
- `coordination_id` (UUID, required)
- `sender_cell_id` (string, required)
- `owner_cell_id` (string, required)
- `scope` (object, required)
- `issued_at` (datetime, required)
- `expires_at` (datetime, required)
- `schema_version` (string, required)
- `coordination_type` (enum: "observation_sharing", required)
- `observation_type` (string, required)
- `observed_data` (object, required)
- `observation_metadata` (object, required)
  - `observation_method` (string, required)
  - `observation_timestamp` (datetime, required)
  - `data_source` (string, optional)

### coordination.intent.broadcast.v2
- `coordination_id` (UUID, required)
- `sender_cell_id` (string, required)
- `owner_cell_id` (string, required)
- `scope` (object, required)
- `issued_at` (datetime, required)
- `expires_at` (datetime, required)
- `schema_version` (string, required)
- `coordination_type` (enum: "intent_broadcast", required)
- `intent_type` (string, required)
- `intent_data` (object, required)
- `target_cells` (array of strings, required)

**NO OTHER FIELDS ARE PERMITTED.**

## FORBIDDEN FIELDS (EXPLICIT LIST)

- `execute`
- `command`
- `instruction`
- `requirement`
- `obligation`
- `permission`
- `approval`
- `decision`
- `consensus`
- `vote`
- `delegate`
- `authorize`
- `mandate`
- `directive`
- `order`
- `priority`
- `confidence`
- `rank`
- `score`
- `weight`
- `trust`
- `reliability`
- `importance`
- `urgency`
- `level`
- `grade`
- `rating`
- `metric`
- `measure`
- `value`
- `worth`
- `merit`

**ANY ATTEMPT TO ADD THESE FIELDS IS A GOVERNANCE VIOLATION.**

## FORBIDDEN INTERPRETATIONS

### Forbidden Semantic Interpretations
- Treating "preferences" as requirements
- Treating "coordination_activity" as authority
- Treating "observation_metadata" as confidence
- Treating any message as permission to act
- Treating any message as obligation to participate
- Treating any message as approval of actions
- Treating any message as guidance for decisions

### Forbidden Behavioral Interpretations
- Ranking messages by any criteria
- Optimizing based on coordination data
- Learning from coordination patterns
- Aggregating coordination information
- Creating trust from observations
- Inferring capabilities from messages
- Scheduling based on intents
- Resolving conflicts automatically
- Making decisions based on coordination

### Forbidden Implementation Patterns
- Storing coordination history
- Analyzing coordination patterns
- Creating coordination analytics
- Building coordination recommendations
- Implementing coordination optimization
- Creating coordination-based scheduling
- Building coordination-based resource allocation
- Implementing coordination-based conflict resolution

**ANY ATTEMPT TO IMPLEMENT THESE INTERPRETATIONS IS A GOVERNANCE VIOLATION.**

## GOVERNANCE ENFORCEMENT

### Violation Classification
All violations of this protocol law are classified as **GOVERNANCE FAILURES**, not bugs.

### Consequences
- Immediate code rejection
- Mandatory governance review
- Potential contributor sanctions
- System rollback if deployed

### Approval Requirements
Any schema or semantic change requires:
- Formal governance proposal
- Security impact assessment
- ADMO governance board approval (unanimous consent)
- Full regression testing
- Formal protocol amendment

## NO EXTENSION BY INTERPRETATION CLAUSE

This protocol cannot be extended through interpretation, convention, or "reasonable extension." The allowed message types, fields, and interpretations are exhaustive and final.

Any attempt to extend protocol functionality through:
- Implicit conventions
- Reasonable interpretations
- Common usage patterns
- Industry standards
- Best practices
- Efficiency improvements

Is explicitly forbidden and constitutes a governance violation.

## ENFORCEMENT MECHANISMS

### Automated Enforcement
- Schema validation must reject forbidden fields
- Content validation must reject forbidden patterns
- Runtime checks must prevent forbidden behaviors
- Tests must enforce all constraints

### Manual Enforcement
- Code review must check protocol compliance
- Architecture review must verify no intelligence pathways
- Security review must verify no authority transfer
- Governance review must verify no semantic drift

### Audit Enforcement
- All coordination messages must be audited
- All violations must be logged and reported
- All attempts at protocol violation must be tracked
- All enforcement actions must be documented

## PERMANENCE CLAUSE

This protocol law is permanent. It cannot be:
- Modified by majority vote
- Suspended for efficiency
- Relaxed for convenience
- Ignored for compatibility
- Overridden by authority

Any attempt to modify this permanence clause is itself a governance violation.

## FINAL DECLARATION

The Federation Coordination Protocol v2.0 is hereby declared legally immutable, permanently enforced, and non-extendable by interpretation. All violations are governance failures subject to immediate rejection and sanctions.

**Signed and effective immediately.**
