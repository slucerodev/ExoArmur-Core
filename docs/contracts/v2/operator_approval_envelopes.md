# Operator Approval Envelopes (Schema-First)

Purpose: define deterministic envelopes for operator approval requests and decisions under PhaseGate control.

## Request Envelope Fields
- `schema`: identifier for versioning (string)
- `approval_id`: unique approval request id (string)
- `intent_id`: bound intent identifier (string)
- `idempotency_key`: client-provided idempotency key (string)
- `requested_by`: originator identity (string)
- `requested_at`: ISO-8601 UTC timestamp (string)
- `justification`: human-readable reason/context (string)
- `metadata`: arbitrary key/value metadata (object)

### JSON Example — Request
```json
{
  "schema": "exoarmur.v2.operator_approval.request.v1",
  "approval_id": "appr-12345",
  "intent_id": "intent-9f8c",
  "idempotency_key": "idem-req-001",
  "requested_by": "operator-alice",
  "requested_at": "2026-02-25T10:05:00Z",
  "justification": "High-risk action requires human approval",
  "metadata": {
    "tenant": "acme",
    "risk_score": 7
  }
}
```

## Decision Envelope Fields
- `schema`: identifier for versioning (string)
- `approval_id`: unique approval request id (string)
- `decision`: `approved` | `denied` (string)
- `decided_by`: operator identity (string)
- `decided_at`: ISO-8601 UTC timestamp (string)
- `reason`: optional operator note (string)
- `idempotency_key`: decision idempotency key (string)
- `bindings`: list of bound resources/intents (array[object])
  - `type`: resource type (string)
  - `id`: resource identifier (string)

### JSON Example — Decision
```json
{
  "schema": "exoarmur.v2.operator_approval.decision.v1",
  "approval_id": "appr-12345",
  "decision": "approved",
  "decided_by": "operator-bob",
  "decided_at": "2026-02-25T10:10:00Z",
  "reason": "Validated risk mitigation steps",
  "idempotency_key": "idem-decision-001",
  "bindings": [
    {"type": "intent", "id": "intent-9f8c"},
    {"type": "resource", "id": "vm-4455"}
  ]
}
```
