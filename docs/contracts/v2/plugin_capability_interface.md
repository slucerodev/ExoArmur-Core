# Plugin Capability Interface (Schema-First)

Purpose: define contract-driven capability registration/activation/denial envelopes without runtime wiring.

## Capability Registration Envelope
- `schema`: identifier (string)
- `capability_id`: unique capability identifier (string)
- `provider`: module/provider name (string)
- `version`: semantic version (string)
- `capability_class`: e.g., `pod`, `bft`, `counterfactual` (string)
- `endpoints`: list of advertised endpoints or methods (array[string])
- `metadata`: optional key/value metadata (object)

### JSON Example — Registration
```json
{
  "schema": "exoarmur.v2.capability.registration.v1",
  "capability_id": "cap-pod-001",
  "provider": "pod-provider-acme",
  "version": "0.1.0",
  "capability_class": "pod",
  "endpoints": ["verify_proof", "generate_proof"],
  "metadata": {
    "proof_type": "zkp",
    "deterministic": true
  }
}
```

## Capability Activation Envelope
- `schema`: identifier (string)
- `capability_id`: unique capability identifier (string)
- `requested_by`: requester identity (string)
- `activation_context`: context info (object)
- `idempotency_key`: idempotency key (string)
- `timestamp`: ISO-8601 UTC timestamp (string)

### JSON Example — Activation
```json
{
  "schema": "exoarmur.v2.capability.activation.v1",
  "capability_id": "cap-pod-001",
  "requested_by": "controller",
  "activation_context": {
    "intent_id": "intent-123",
    "tenant_id": "acme"
  },
  "idempotency_key": "idem-activate-001",
  "timestamp": "2026-02-26T10:00:00Z"
}
```

## Capability Denial Envelope
- `schema`: identifier (string)
- `capability_id`: unique capability identifier (string)
- `denied_by`: authority identity (string)
- `reason`: human-readable reason (string)
- `timestamp`: ISO-8601 UTC timestamp (string)
- `correlation_id`: optional correlation id (string)

### JSON Example — Denial
```json
{
  "schema": "exoarmur.v2.capability.denial.v1",
  "capability_id": "cap-pod-001",
  "denied_by": "phase-gate",
  "reason": "Phase 2 not enabled (EXOARMUR_PHASE=1)",
  "timestamp": "2026-02-26T10:01:00Z",
  "correlation_id": "corr-77"
}
```
