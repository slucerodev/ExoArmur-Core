# SYSTEM_OVERVIEW.md

## Purpose
Defines what ExoArmur is, its architectural classification, and its fundamental operating boundaries.

## Definitions

**ExoArmur**: An Autonomous Defense Mesh Organism (ADMO) that operates as a distributed system of autonomous defensive cells with complete deterministic audit replay capability.

**Autonomous Defense Mesh Organism (ADMO)**: A distributed, self-coordinating defensive intelligence substrate composed of autonomous defensive cells. Each cell is capable of local perception, decision-making, safety evaluation, and execution, while synchronizing beliefs across a resilient mesh with full cryptographic verification.

**Cell**: The atomic deployable unit of the ADMO. Each cell possesses local cognition, conscience, memory, and actuation capability. A cell can operate autonomously during isolation or partial failure, with complete audit trail integrity.

**Organism**: The collection of all cells operating as a coordinated defensive system through belief propagation, not centralized command distribution. The organism maintains complete cryptographic verification and deterministic replay capability.

**Coordination**: The process by which cells synchronize beliefs consisting of observations, confidence, and supporting evidence. Coordination never involves direct action commands between cells and includes cryptographic verification of all federated communications.

**Autonomy**: The capability of a cell to execute defensive actions independently when explicitly authorized by valid, signed tenant policy bundles defining autonomy envelopes. ExoArmur does not have general autonomy - it has policy-authorized autonomy only with cryptographic enforcement.

**Decision**: A determination made by a cell based on facts, beliefs, and policy evaluation. Decisions propose execution intents but are subject to safety gating, approval requirements, and complete cryptographic verification.

**Deterministic Replay**: The capability to reconstruct exact organism behavior from audit logs, ensuring the same inputs produce the same outputs every time. This enables complete verification, compliance, and forensic analysis.

**Cryptographic Verification**: Ed25519-based signing and verification of all federation communications, ensuring message integrity, authenticity, and replay protection.

## Allowed Behaviors

- Cells ingest telemetry and validate canonical TelemetryEvent schemas
- Cells transform raw telemetry into structured facts usable for policy evaluation
- Cells produce LocalDecision objects containing severity, confidence, classification, and recommended execution intents
- Cells emit evidence-backed beliefs with confidence scores and TTL
- Cells propagate beliefs through the mesh using bounded gossip protocols
- Cells evaluate policy bundles signed and verified by trusted authorities
- Cells enforce deterministic safety gating rules
- Cells execute idempotent actions through adapters with rollback semantics
- Cells maintain append-only audit buffers enabling complete deterministic replay and export
- Cells operate locally during network partitions using cached policy and belief memory
- Cells participate in federation identity handshakes with cryptographic verification
- Cells maintain deterministic audit trails with canonical serialization and stable hashing
- Cells enforce replay protection through nonce tracking and signature verification

## Forbidden Behaviors

- No single service or component may be required for perception, decisioning, safety gating, or execution
- Cells never issue direct action commands to other cells
- Cells never execute actions without explicit policy authorization
- Safety controller verdicts never defer to mission objectives
- No execution occurs without sufficient evidence for deterministic audit replay
- No actions are executed that are not idempotent and safe to retry
- Learning systems never directly authorize irreversible actions in production environments
- No execution occurs when safety constraints deny, regardless of policy authorization
- No federation communications occur without cryptographic verification
- No audit trails may be modified or tampered with after recording
- No replay attacks may succeed due to nonce reuse or signature bypass

## Example

A cell detects suspicious authentication failures from host-123. It:
1. Validates the TelemetryEventV1 schema
2. Derives SignalFactsV1 with normalized features
3. Produces LocalDecisionV1 classifying the activity as suspicious with 0.85 confidence
4. Emits BeliefV1 claiming "c2_beaconing" with supporting evidence
5. Propagates the belief to other cells via gossip protocol
6. Evaluates policy bundle allowing A1_soft_containment for this scenario
7. Applies safety gate rules allowing local A1 execution with 0.80+ confidence
8. Executes isolate_host intent with idempotency key
9. Records AuditRecordV1 of the complete decision chain with canonical hashing
10. Enables deterministic replay of the entire decision process with integrity verification

## Non-Example

A cell detects a threat and immediately blocks network access for an entire subnet without:
- Policy bundle authorization for the action
- Safety gate evaluation of blast radius
- Belief propagation to other affected cells
- Evidence collection supporting the decision
- Idempotency key for the execution intent
- Audit trail reconstruction capability

This behavior is forbidden because it bypasses policy authorization, safety gating, belief coordination, and audit requirements.
