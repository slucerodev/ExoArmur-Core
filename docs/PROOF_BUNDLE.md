# Proof Bundle Specification

**Version:** 1.0.0  
**Status:** Technical Evaluation  
**Last Updated:** 2025-01-20

## Overview

The ExoArmur Proof Bundle is a cryptographically-verifiable record of deterministic execution. It provides tamper-evidence and replayability for governance decisions, enabling external verification without requiring runtime access.

## Purpose

- **Tamper Detection**: Detect any modification to execution records
- **Deterministic Replay**: Enable exact reproduction of execution decisions
- **External Verification**: Allow third-party verification without runtime access
- **Audit Trail**: Provide immutable evidence of governance decisions

## Bundle Structure

### Top-Level Format

```json
{
  "bundle": {
    "schema_version": "1.0.0",
    "bundle_version": "1.0.0",
    "bundle_id": "string",
    "bundle_created_at": "ISO8601 timestamp",
    "replay_hash": "SHA256 hex string",
    "bundle_checksum": "SHA256 hex string (optional)",
    "intent": { ... },
    "policy_decision": { ... },
    "safety_verdict": { ... },
    "final_verdict": "ALLOW|DENY",
    "approval_records": [ ... ],
    "execution_trace": { ... },
    "executor_result": { ... },
    "governance_evidence": { ... },
    "resolution_evidence": { ... },
    "executor_capabilities": { ... },
    "validation_evidence": { ... },
    "executor_failure_evidence": { ... }
  }
}
```

### Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Bundle schema version |
| `bundle_version` | string | Yes | Bundle format version |
| `bundle_id` | string | Yes | Unique bundle identifier (ULID) |
| `bundle_created_at` | string | Yes | ISO8601 timestamp of bundle creation |
| `replay_hash` | string | Yes | SHA256 hash of canonical execution payload |
| `bundle_checksum` | string | No | SHA256 hash of bundle metadata for integrity |

## Canonical Payload

The `replay_hash` is computed over a canonical JSON representation of the execution payload:

```json
{
  "schema_version": "string",
  "bundle_version": "string",
  "intent": { ... },
  "policy_decision": { ... },
  "safety_verdict": { ... },
  "final_verdict": "string (enum value)",
  "approval_records": [ ... ],
  "execution_trace": { ... },
  "executor_result": { ... },
  "governance_evidence": { ... },
  "resolution_evidence": { ... },
  "executor_capabilities": { ... },
  "validation_evidence": { ... },
  "executor_failure_evidence": { ... }
}
```

### Canonicalization Rules

1. **Stable Key Ordering**: All object keys sorted alphabetically
2. **No Whitespace**: Compact JSON with no extraneous whitespace
3. **Unicode Normalization**: All strings normalized to NFC
4. **Enum Values**: Enum fields use their string values, not enum names
5. **Timestamp Format**: ISO8601 with timezone (UTC preferred)

## Verification Process

### Step 1: Load Bundle

```python
from exoarmur.proof.external_verifier import load_bundle_file

bundle_data = load_bundle_file("proof_bundle.json")
```

### Step 2: Verify Structure

```python
from exoarmur.proof.external_verifier import verify_bundle_data

result = verify_bundle_data(bundle_data)
```

### Step 3: Check Result

```python
if result.passed:
    print("✓ Bundle is valid and untampered")
    print(f"  Hash: {result.computed_hash}")
    print(f"  Algorithm: {result.hash_algorithm}")
else:
    print("✗ Bundle verification failed")
    print(f"  Error: {result.error}")
```

## Verification Output

### Success Case

```
VERIFY_VERDICT=PASS
BUNDLE_FORMAT=EXECUTION_PROOF_BUNDLE
HASH_ALGORITHM=sha256
EXPECTED_HASH=abc123...
COMPUTED_HASH=abc123...
HASH_MATCH=true
CHECKSUM_EXPECTED=xyz789...
CHECKSUM_COMPUTED=xyz789...
CHECKSUM_MATCH=true
ERROR=
```

### Failure Cases

#### Replay Hash Mismatch

```
VERIFY_VERDICT=FAIL
BUNDLE_FORMAT=EXECUTION_PROOF_BUNDLE
HASH_ALGORITHM=sha256
EXPECTED_HASH=abc123...
COMPUTED_HASH=def456...
HASH_MATCH=false
ERROR=REPLAY_HASH_MISMATCH
```

#### Bundle Checksum Mismatch

```
VERIFY_VERDICT=FAIL
BUNDLE_FORMAT=EXECUTION_PROOF_BUNDLE
HASH_ALGORITHM=sha256
...
CHECKSUM_MATCH=false
ERROR=REPLAY_HASH_MISMATCH;BUNDLE_CHECKSUM_MISMATCH
```

#### Invalid Format

```
VERIFY_VERDICT=FAIL
BUNDLE_FORMAT=UNKNOWN
HASH_ALGORITHM=sha256
EXPECTED_HASH=
COMPUTED_HASH=
HASH_MATCH=false
ERROR=VALIDATION_ERROR: Unsupported bundle format
```

## Tamper Detection

### Detectable Tampering

1. **Semantic Changes**: Any modification to intent, policy, or execution data
2. **Structural Changes**: Addition/removal of fields
3. **Order Changes**: Reordering of array elements
4. **Type Coercion**: String "1" vs integer 1, boolean vs string
5. **Timestamp Manipulation**: Any change to timestamps

### Undetectable Changes

None by design. The canonicalization process ensures any change produces a different hash.

## CLI Verification

### Verify a Bundle File

```bash
exoarmur verify-bundle --bundle proof_bundle.json
```

### JSON Output

```bash
exoarmur verify-bundle --bundle proof_bundle.json --json
```

## Security Considerations

### Hash Algorithm

- **Algorithm**: SHA-256
- **Collision Resistance**: Cryptographically secure
- **Preimage Resistance**: Computationally infeasible to reverse

### Bundle Integrity

- **Replay Hash**: Covers entire execution payload
- **Bundle Checksum**: Optional metadata integrity check
- **Nested Hashes**: Individual components may have their own hashes

### Verification Trust Model

- **No Runtime Required**: Verification uses only bundle data
- **No Secrets Needed**: Verification is public-key free
- **Deterministic**: Same input always produces same output

## Migration Support

### Schema Versioning

Bundles include `schema_version` to support future format changes:

```json
{
  "schema_version": "1.0.0",
  ...
}
```

### Migration Path

When schema versions change:
1. Old bundles remain verifiable with their original schema
2. New bundles use the latest schema
3. Migration tools can convert between versions if needed

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `FILE_NOT_FOUND` | Bundle file doesn't exist | Check file path |
| `INVALID_JSON` | Malformed JSON | Validate JSON syntax |
| `UNSUPPORTED_FORMAT` | Missing required fields | Check bundle structure |
| `MIGRATION_ERROR` | Schema migration failed | Contact support |
| `VALIDATION_ERROR` | Pydantic validation failed | Check data types |

## Best Practices

### Bundle Storage

- **Immutable**: Never modify stored bundles
- **Backup**: Store bundles in multiple locations
- **Retention**: Keep bundles per compliance requirements
- **Access Control**: Restrict write access to bundle storage

### Verification

- **Regular**: Verify bundles periodically
- **Automation**: Integrate verification into CI/CD
- **Logging**: Log all verification results
- **Alerting**: Alert on verification failures

### Generation

- **Deterministic**: Use fixed timestamps in tests
- **Complete**: Include all required fields
- **Consistent**: Use consistent field ordering
- **Validated**: Validate bundles before storage

## References

- **External Verifier**: `src/exoarmur/proof/external_verifier.py`
- **Bundle Builder**: `src/exoarmur/execution_boundary_v2/utils/bundle_builder.py`
- **Canonicalization**: `src/exoarmur/replay/canonical_utils.py`
- **Schema**: `artifacts/schemas/ExecutionProofBundle.json`

---

**Status**: Technical Evaluation - Not for production deployment without security review
