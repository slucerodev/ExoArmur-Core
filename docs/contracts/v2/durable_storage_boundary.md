# Durable Storage Boundary (Schema-First, KV Semantics)

Purpose: define an abstract, durable KV boundary with deterministic semantics and an in-memory reference contract for tests. No live storage wiring.

## Operations
- `put`: store value by key with optional TTL
- `get`: retrieve latest value by key
- `delete`: remove value by key
- `history`: return ordered history of mutations for a key

## Envelope Fields (for requests)
- `schema`: identifier for versioning (string)
- `operation`: `put` | `get` | `delete` | `history` (string)
- `key`: key name (string)
- `value`: arbitrary JSON value (any) — required for `put`, absent otherwise
- `ttl_seconds`: optional TTL for `put` (number)
- `timestamp`: ISO-8601 UTC timestamp (string)
- `idempotency_key`: client-provided idempotency key (string)

## Envelope Fields (for responses)
- `schema`: identifier for versioning (string)
- `status`: `ok` | `not_found` | `error` (string)
- `key`: key name (string)
- `value`: latest value (any) when applicable
- `history`: array of version records for `history` operation
  - `version`: monotonically increasing integer
  - `timestamp`: ISO-8601 UTC timestamp
  - `value`: stored value at that version

## JSON Examples
### Request — put
```json
{
  "schema": "exoarmur.v2.durable_kv.request.v1",
  "operation": "put",
  "key": "audit:last_checkpoint",
  "value": {"cursor": "block-120"},
  "ttl_seconds": 3600,
  "timestamp": "2026-02-25T10:15:00Z",
  "idempotency_key": "idem-kv-put-001"
}
```

### Response — history
```json
{
  "schema": "exoarmur.v2.durable_kv.response.v1",
  "status": "ok",
  "key": "audit:last_checkpoint",
  "history": [
    {"version": 1, "timestamp": "2026-02-25T09:00:00Z", "value": {"cursor": "block-118"}},
    {"version": 2, "timestamp": "2026-02-25T09:30:00Z", "value": {"cursor": "block-119"}},
    {"version": 3, "timestamp": "2026-02-25T10:00:00Z", "value": {"cursor": "block-120"}}
  ]
}
```
