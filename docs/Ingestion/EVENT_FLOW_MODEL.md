# EVENT_FLOW_MODEL.md

## Purpose
Defines the immutable event processing flow from telemetry ingestion through audit recording, including all required transformations and decision points with complete deterministic replay capability.

## Definitions

**Event Flow**: The fixed sequence of processing steps that all telemetry must follow through the ExoArmur cognition loop with deterministic replay verification.

**TelemetryEventV1**: Canonical input event received by a cell. Validated at ingest with schema enforcement and ULID identifiers.

**SignalFactsV1**: Normalized facts and features derived from telemetry used for policy evaluation and decisioning.

**BeliefV1**: Evidence-backed claim emitted by a cell and propagated through the mesh with confidence scores and TTL.

**LocalDecisionV1**: A cell-local decision derived from facts and beliefs, before safety gating, with classification and recommended intents.

**ExecutionIntentV1**: Idempotent execution request produced after policy and safety gating with approval context and parameters and canonical hash verification.

**AuditRecordV1**: Append-only audit evidence record for deterministic replay and compliance with canonical serialization, stable hashing, and integrity verification.

**Cognition Loop**: The fixed processing sequence: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1.

**Correlation ID**: Identifier that links all processing steps for a single telemetry event through the entire cognition loop.

**Trace ID**: Identifier that enables distributed tracing across multiple cells and processing steps.

**Idempotency Key**: Unique identifier that ensures execution intents can be safely retried without unintended side effects.

**Deterministic Replay**: The capability to reconstruct exact organism behavior from audit logs, ensuring the same inputs produce the same outputs every time.

**Canonical Serialization**: Stable JSON representation with sorted keys and normalized types for consistent hashing.

**Stable Hashing**: SHA-256 based hash computation using canonical form for immutable intent verification.

## Required Event Flow Sequence (Immutable)

### Step 1: Telemetry Ingestion
- Input: External telemetry from sensors, EDRs, logs, or other sources
- Processing: Schema validation, ULID generation, timestamp normalization
- Output: TelemetryEventV1 with validated structure and metadata
- Requirements: Must validate all required fields, enforce size limits, generate correlation_id and trace_id

### Step 2: Signal Fact Derivation
- Input: TelemetryEventV1
- Processing: Feature extraction, normalization, entity mapping, subject identification
- Output: SignalFactsV1 with canonical features and claim hints
- Requirements: Must preserve source evidence, apply deterministic transformations, maintain correlation

### Step 3: Belief Generation
- Input: SignalFactsV1 (and optional existing beliefs for context)
- Processing: Classification, confidence scoring, evidence collection, policy context attachment
- Output: BeliefV1 with confidence, severity, evidence references, and TTL
- Requirements: Must include evidence references, apply confidence scoring, set appropriate TTL

### Step 4: Collective Confidence Aggregation
- Input: BeliefV1 (local and propagated from other cells)
- Processing: Deduplication, confidence weighting, quorum counting, conflict detection
- Output: Aggregate confidence score and quorum status
- Requirements: Must deduplicate beliefs, apply trust weighting, detect conflicts, compute thresholds

### Step 5: Safety Gate Evaluation
- Input: LocalDecisionV1, collective confidence, policy state, trust state
- Processing: Arbitration precedence application, threshold checks, approval requirement determination
- Output: Safety verdict (allow/deny/require_quorum/require_human) with rationale
- Requirements: Must follow arbitration precedence, apply all safety rules, generate verdict with reasoning

### Step 6: Execution Intent Generation
- Input: Safety verdict, policy authorization, decision context
- Processing: Intent finalization, idempotency key generation, approval context attachment
- Output: ExecutionIntentV1 with all required context and safety validation
- Requirements: Must include idempotency key, policy context, safety context, correlation tracking

### Step 7: Audit Recording
- Input: ExecutionIntentV1 and execution result
- Processing: Canonical serialization, stable hash generation, evidence capture, compliance metadata
- Output: AuditRecordV1 with complete decision chain and integrity verification data
- Requirements: Must be append-only, include canonical hashes, maintain correlation, enable deterministic replay

## Allowed Event Flow Behaviors

### Processing Requirements
- All events must follow the complete 7-step sequence
- Each step must complete before the next step begins
- Correlation IDs must be preserved across all steps
- Trace IDs must enable end-to-end distributed tracing

### Data Transformations
- TelemetryEventV1 to SignalFactsV1 must be deterministic and reversible
- SignalFactsV1 to BeliefV1 must include confidence scoring and evidence
- BeliefV1 aggregation must use weighted confidence and deduplication
- Safety evaluation must apply arbitration precedence in fixed order
- All transformations must use canonical serialization for deterministic hashing

### Decision Making
- Local decisions must be based on facts and beliefs only
- Safety gates must apply all constraint rules before allowing execution
- Execution intents must be idempotent and include approval context with canonical hash
- Audit records must capture complete decision chains with stable hashes for replay verification

### Error Handling
- Schema validation failures must reject events at Step 1
- Processing failures must generate audit records of the failure
- Safety denials must prevent execution and generate audit trails
- System failures must degrade gracefully rather than bypass safety
- Replay failures must detect tampering and integrity violations

### Replay Verification
- All audit records must enable deterministic reconstruction of decisions
- Intent hash verification must prevent tampering with execution parameters
- Payload integrity validation must detect unauthorized modifications
- Replay must reproduce identical safety gate verdicts and execution outcomes

## Forbidden Event Flow Behaviors

### Sequence Violations
- No skipping of steps in the cognition loop
- No parallel processing of steps that must be sequential
- No bypassing of safety gate evaluation
- No execution without audit recording

### Data Integrity Violations
- No modification of correlation IDs during processing
- No loss of evidence references between steps
- No execution without idempotency keys
- No audit records without complete decision chains

### Safety Violations
- No execution before safety gate evaluation
- No bypassing of arbitration precedence
- No ignoring of trust constraints or collective thresholds
- No execution when kill switches are active

### Authority Violations
- No execution without policy authorization
- No overriding of safety denials by any authority
- No ignoring of human approval requirements
- No execution when quorum thresholds are not satisfied

## Example

Complete event flow for suspicious authentication:

1. **Telemetry Ingestion**: External auth failure event received
   - Validates TelemetryEventV1 schema
   - Generates event_id, correlation_id, trace_id
   - Records source, timestamp, severity

2. **Signal Fact Derivation**: Process raw auth data
   - Extracts user, host, timestamp, failure patterns
   - Maps to subject: {subject_type: "user", subject_id: "user-123"}
   - Generates claim hints: ["brute_force", "credential_stuffing"]

3. **Belief Generation**: Classify and score
   - Determines claim_type: "brute_force_attack"
   - Calculates confidence: 0.87 based on pattern matching
   - Attaches evidence: event_ids, feature hashes
   - Sets TTL: 3600 seconds

4. **Collective Confidence**: Aggregate with other cells
   - Receives similar beliefs from 2 other cells
   - Deduplicates beliefs with overlapping evidence
   - Computes aggregate_score: 0.91
   - Determines quorum_count: 3 cells

5. **Safety Gate Evaluation**: Apply all constraints
   - Checks kill switches: none active
   - Verifies policy: valid and allows A2 with quorum
   - Applies trust: all cells above 0.50 threshold
   - Returns verdict: "allow" with rationale

6. **Execution Intent Generation**: Create actionable intent
   - Sets intent_type: "disable_user_temporarily"
   - Assigns action_class: "A2_hard_containment"
   - Generates idempotency_key: unique hash
   - Includes approval context: quorum satisfied

7. **Audit Recording**: Complete decision chain
   - Records all steps with timestamps
   - Includes hashes of all data objects
   - Captures safety verdict and rationale
   - Enables complete replay of decision process

## Non-Example

Cell detects threat and immediately blocks access:

- Skips SignalFactsV1 derivation
- Ignores BeliefV1 generation and propagation
- Bypasses collective confidence aggregation
- Overrides safety gate evaluation
- Executes without idempotency key
- Fails to generate complete audit trail

This violates the event flow model by skipping required steps, bypassing safety constraints, and failing to maintain auditability.
