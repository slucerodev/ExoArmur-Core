# ADMO v1 Contract Files

This directory contains the canonical contract files for ExoArmur Autonomous Defense Mesh Organism v1.

## Files Overview

### models_v1.py
Pydantic v2 models with strict validation for all ADMO data types.
- **Usage:** Import in cell implementations for data validation
- **Models:** TelemetryEventV1, SignalFactsV1, BeliefV1, LocalDecisionV1, ExecutionIntentV1, AuditRecordV1
- **Validation:** Strict field validation, ULID format checking, enum constraints

### nats_jetstream_v1.yaml
NATS JetStream configuration for mesh communication.
- **Usage:** Configure NATS subjects, streams, and consumer behavior
- **Contents:** Subject taxonomy, stream defaults, retention policies, deduplication keys
- **Purpose:** Ensures reliable, durable message delivery across the organism

### policy_bundle_v1.yaml
Signed tenant policy bundle format and enforcement parameters.
- **Usage:** Define tenant-specific policies, autonomy envelopes, and kill switches
- **Contents:** Bundle metadata, signing requirements, autonomy envelopes, trust governance
- **Purpose:** Authoritative policy source for cell decision-making

### safety_gate_v1.yaml
Deterministic safety gate rules and verdict contract.
- **Usage:** Implement safety controller that validates all execution intents
- **Contents:** Severity ladder, gating rules, trust constraints, approval requirements
- **Purpose:** Final safety validation that overrides all other considerations

## How to Use

### For Cell Implementation
1. Import models from `models_v1.py` for data validation
2. Configure NATS using `nats_jetstream_v1.yaml` subjects and streams
3. Load policy bundles according to `policy_bundle_v1.yaml` format
4. Implement safety gate using `safety_gate_v1.yaml` rules

### For Policy Management
1. Create policy bundles following `policy_bundle_v1.yaml` schema
2. Sign bundles with accepted algorithms (ed25519, rsa-pss-sha256)
3. Distribute to cells with verification keys
4. Monitor bundle expiration and refresh as needed

### For Safety Implementation
1. Implement safety controller with ordered rule evaluation
2. Apply severity ladder defaults when uncertainty exists
3. Enforce trust-based constraints and approval requirements
4. Generate safety verdicts with required fields

## Validation

Run the contract validation script to ensure all files are valid:
```bash
python3 scripts/validate_contracts.py
python3 scripts/validate_spec_refs.py
```

## Integration

These contracts are referenced from `EXOARMUR_MASTER_SPEC.yaml` and must be used consistently across all ADMO implementations. Any changes to contract schemas should be coordinated across the organism to ensure compatibility.