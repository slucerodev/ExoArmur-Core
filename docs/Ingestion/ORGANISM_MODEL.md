# ORGANISM_MODEL.md

## Purpose
Defines the organism architecture, cell anatomy, and belief propagation model that enables coordinated defense without centralized control, including federation identity capabilities and deterministic replay.

## Definitions

**Cell Anatomy**: The mandatory subsystems that every cell must possess to function as an autonomous defensive unit with cryptographic verification and deterministic replay capabilities.

**Sensors**: Subsystems that ingest local telemetry and validate canonical TelemetryEvent schemas.

**Normalization and Feature Extraction**: Subsystems that transform raw telemetry into structured facts usable for policy evaluation and decisioning.

**Local Policy Cache and OPA**: Subsystems that maintain cached policy bundles and provide Open Policy Agent evaluation capabilities.

**Decision Engine**: Subsystems that produce LocalDecision objects containing severity, confidence, classification, and recommended execution intents.

**Safety Controller**: Subsystems that enforce irreversible-action rules, autonomy envelopes, and severity-based safety ladders.

**Execution Kernel**: Subsystems that execute idempotent ExecutionIntent objects through adapters, supporting rollback semantics where feasible.

**Belief Store**: Subsystems that maintain short-term belief memory with TTL, decay, and deduplication.

**Gossip Mesh Interface**: Subsystems that disseminate beliefs across the mesh using bounded gossip protocols with cryptographic verification.

**Local Audit Ledger**: Subsystems that provide append-only local audit buffers enabling deterministic replay, export, and non-blocking compliance evidence capture.

**Federation Identity Store**: Subsystems that maintain cryptographic identities, nonces, and handshake sessions for secure cell-to-cell communication.

**Protocol Enforcer**: Subsystems that enforce cryptographic verification, replay protection, and protocol boundaries for federation handshakes.

**Belief Model**: The data structure and propagation rules for evidence-backed claims emitted by cells with cryptographic integrity verification.

**Collective Confidence**: The mechanism by which autonomous cells form a coherent organism-level posture without centralized command through belief aggregation and quorum formation.

**Dynamic Trust**: A reputation mechanism per cell that adjusts based on historical accuracy, policy compliance, and action outcomes.

**Deterministic Replay Engine**: Subsystems that reconstruct exact organism behavior from audit logs using canonical serialization and stable hashing.

## Allowed Behaviors

### Cell Operations
- Each cell maintains all mandatory subsystems in operational state
- Cells process telemetry through the full cognition pipeline independently
- Cells cache verified policy bundles for local evaluation during partitions
- Cells maintain belief stores with configurable TTL and decay parameters
- Cells participate in gossip protocols with bounded fanout and rate limiting
- Cells maintain federation identity stores for secure inter-cell communication
- Cells operate deterministic replay engines for compliance verification
- Cells enforce cryptographic verification for all federation communications

### Belief Propagation
- Cells emit beliefs with confidence scores, evidence references, and policy context
- Cells propagate beliefs using gossip-based distribution with deduplication and cryptographic verification
- Cells aggregate beliefs by claim_type+subject using weighted confidence formulas
- Cells apply conflict resolution when opposing beliefs are detected
- Cells decay belief confidence over time using exponential half-life models
- Cells verify cryptographic signatures on all received beliefs and federation messages

### Collective Decision Making
- Cells compute aggregate scores using independent supporting beliefs
- Cells verify quorum satisfaction with distinct cell requirements
- Cells apply trust-based autonomy constraints based on dynamic trust scores
- Cells trigger deliberation when thresholds are not met or conflicts exist
- Cells execute actions only when collective confidence thresholds are satisfied

### Trust and Reputation
- Cells maintain dynamic trust scores in range [0.0, 1.0] for other cells
- Cells update trust based on confirmed true positives, false positives, and policy compliance
- Cells apply trust constraints to autonomy envelopes for high-impact actions
- Cells use trust scores as weights in collective confidence aggregation

## Forbidden Behaviors

### Cell Operations
- No cell may operate without all mandatory subsystems functional
- No cell may process telemetry without schema validation
- No cell may evaluate policy without bundle verification
- No cell may execute actions without safety gate evaluation

### Belief Propagation
- No cell may issue commands to other cells (only beliefs are allowed)
- No cell may propagate beliefs without evidence references
- No cell may duplicate beliefs to inflate confidence scores
- No cell may ignore belief deduplication rules
- No cell may propagate beliefs with expired TTL

### Collective Decision Making
- No cell may execute A2/A3 actions without quorum satisfaction unless explicitly policy-authorized
- No cell may override safety gate verdicts with collective confidence
- No cell may ignore conflict detection and resolution procedures
- No cell may execute actions when trust scores are below minimum thresholds

### Trust and Reputation
- No cell may fabricate trust scores or reputation data
- No cell may use trust scores to bypass safety constraints
- No cell may ignore trust updates from confirmed action outcomes
- No cell may allow trust scores to exceed configured maximums

## Example

Three cells (cell-a, cell-b, cell-c) detect lateral movement:

1. **cell-a** processes TelemetryEventV1 for auth failure on host-123
   - Derives SignalFactsV1 with suspicious process patterns
   - Produces LocalDecisionV1: suspicious, 0.85 confidence
   - Emits BeliefV1: "lateral_movement", confidence 0.85, evidence [event-1, event-2]
   - Propagates belief via gossip to cell-b and cell-c

2. **cell-b** receives similar telemetry for host-123
   - Emits BeliefV1: "lateral_movement", confidence 0.78, evidence [event-3, event-4]
   - Aggregates with cell-a belief: aggregate_score = 1 - (1-0.85)*(1-0.78) = 0.967
   - Quorum count = 2 (distinct cells)

3. **cell-c** receives the beliefs and computes collective confidence
   - Verifies A2_hard_containment threshold: quorum>=2 AND aggregate_score>=0.85
   - Trust scores: cell-a=0.85, cell-b=0.82 (both above 0.50 floor)
   - Safety gate allows A2 execution with collective confidence

## Non-Example

A single cell detects minor suspicious activity and immediately executes A3 irreversible action:

- No belief propagation to other cells
- No quorum formation or collective confidence
- No safety gate evaluation for A3 requirements
- No human approval despite policy requirement
- No evidence collection beyond local telemetry

This violates organism model by bypassing belief coordination, collective decision making, and safety constraints.
