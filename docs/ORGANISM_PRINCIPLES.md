# ExoArmur ADMO Organism Principles

These are the invariant axioms that govern ExoArmur ADMO's behavior, evolution, and authority boundaries. These principles are constitutional, not aspirational, and must never be violated.

## Core Principles

### 1. V1 Cognition Immutability
The V1 cognition pipeline (TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGateV1 → ExecutionIntentV1 → AuditRecordV1) is immutable. No modification to V1 core behavior, data models, or decision logic is permitted.

### 2. External Epistemic Authority
Epistemic authority remains external to the system. ExoArmur processes evidence and forms beliefs but does not define truth. Truth claims originate from external sources, sensors, and human operators.

### 3. Provisional and Replayable Beliefs
All beliefs are provisional and replayable. BeliefV1 objects represent current evidence-based conclusions and must be reproducible from the same inputs and policies.

### 4. Arbitration Preserves Dissent
Arbitration precedence (KillSwitch > PolicyVerification > SafetyGate > PolicyAuthorization > TrustConstraints > CollectiveConfidence > LocalDecision) preserves dissent. Lower-precedence decisions remain valid and auditable even when overridden.

### 5. Federation Coordinates, Does Not Define Truth
Federation coordinates truth across cells but does not define truth. Cross-cell belief aggregation and quorum computation are coordination mechanisms, not truth-creation mechanisms.

### 6. No Irreversible Action Without Explicit Approval
No irreversible action may be executed without explicit approval. High-severity actions require human operator approval through documented workflows with audit trails.

### 7. Verification Outranks Trust
Verification outranks trust. All policy bundles, certificates, and identity claims must be cryptographically verified before acceptance. Trust is established through verification, not assumption.

### 8. Feature Flags Default OFF
All V2 feature flags default to OFF. New capabilities must be explicitly enabled and remain inert when disabled. Feature flags provide emergency disable capability.

### 9. V2 Layers Are Additive-Only
V2 layers (federation, control plane) are additive-only. They coordinate externally but never modify V1 core cognition, data models, or safety gate precedence.

### 10. Golden Demo Supremacy as Regression Law
The Golden Demo is the supreme regression law. `tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream` must always pass. Any change causing Golden Demo failure is prohibited.

### 11. Auditability Outranks Optimization
Auditability outranks optimization. Complete audit trails (AuditRecordV1) must be maintained for all decisions and actions. Performance optimizations must not compromise audit completeness.

### 12. Safety Outranks Performance
Safety outranks performance. Safety gate evaluation and arbitration precedence must complete with deterministic results, regardless of performance impact.

### 13. Transparency Outranks Autonomy
Transparency outranks autonomy. All decisions must be explainable through audit trails and policy references. Autonomous action must not compromise explainability.

## Authority Boundaries

### V1 Core Authority
- **Controls**: Core cognition pipeline, safety evaluation, local execution
- **Cannot**: Be modified by V2 layers, bypass safety gates, alter audit trails

### V2 External Authority  
- **Controls**: Cross-cell coordination, operator workflows, policy distribution
- **Cannot**: Modify V1 cognition, execute actions directly, alter signed policies

### Human Operator Authority
- **Controls**: Policy bundle signing, emergency approvals, governance exceptions
- **Cannot**: Bypass safety gates, modify audit trails, violate immutable principles

## Enforcement Mechanisms

### Technical Enforcement
- Feature flags prevent V2 activation
- Immutable V1 contracts prevent core changes
- Safety gate precedence prevents action bypass
- Audit trails provide verification

### Governance Enforcement
- Binary green testing (0 failed, 0 errors, 0 skipped)
- Golden Demo regression testing
- Spec reference validation
- Integrity audit compliance

### Operational Enforcement
- Emergency disable via feature flags
- KillSwitch override capability (safety precedence only)
- Human approval workflows
- Audit trail verification

## Terminology Clarifications

### "Policy Override" Meaning
When documentation refers to "policy override," this means:
- Operator-approved external coordination procedures
- Emergency response coordination through documented workflows
- Human approval of actions that require additional oversight
- Coordination that respects V1 safety gate precedence

This does NOT mean:
- Modifying signed V1 policy bundles
- Bypassing V1 safety gate decisions
- Altering V1 audit trails
- Direct execution inside V1 cognition pipeline

## Evolution Constraints

### Allowed Evolution
- Additive V2 contracts and capabilities
- Enhanced monitoring and observability
- Improved operator interfaces
- Expanded federation coordination

### Prohibited Evolution
- V1 cognition pipeline modification
- Safety gate precedence changes
- Audit trail reduction or elimination
- Feature flag default state changes

These principles ensure ExoArmur remains a reliable, auditable, and safe autonomous defense system while enabling controlled evolution through external layers that never compromise core safety or reliability.
