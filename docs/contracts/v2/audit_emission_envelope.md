# Audit Emission Envelope (Schema-First)

Purpose: define the envelope for audit events emitted by V2-capable components without requiring live transport in default tests.

## Fields
- `schema`: identifier for versioning (string)
- `event_kind`: audit event type (string)
- `payload_ref`: reference to payload (hash, URI, or inline selector) (string)
- `correlation_id`: correlation identifier (string)
- `trace_id`: trace/span identifier (string)
- `tenant_id`: tenant identifier (string)
- `cell_id`: originating cell identifier (string)
- `idempotency_key`: idempotency key (string)
- `timestamp`: ISO-8601 UTC timestamp (string)
- `metadata`: optional key/value metadata (object)

## JSON Example
```json
{
  "schema": "exoarmur.v2.audit_emission.v1",
  "event_kind": "approval_decision",
  "payload_ref": "sha256:2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae",
  "correlation_id": "corr-8844",
  "trace_id": "trace-11aa",
  "tenant_id": "acme",
  "cell_id": "cell-nyc-001",
  "idempotency_key": "idem-audit-001",
  "timestamp": "2026-02-25T10:20:00Z",
  "metadata": {
    "decision": "approved",
    "operator": "operator-bob"
  }
}
```
