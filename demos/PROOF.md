# ExoArmur Full Audit-Bundle Replay Proof

## Version Information
- Canonicalization Version: v1
- Hash Algorithm: sha256
- Proof Lockdown: v1.0 (comprehensive adversarial hardening)

## Run Proof
```bash
python demos/canonical_truth_reconstruction_demo.py
```

Expected Output:
```
REPLAY_VERDICT=PASS
CANONICALIZATION_VERSION=v1
HASH_ALGORITHM=sha256
HASH=cfd322c8a4360a4fedf85682f4bdeb8838ef1e4f2188b23e929ac2d7475b740e
```

## Verify Determinism
Run the proof again:
```bash
python demos/canonical_truth_reconstruction_demo.py
```
Hash must be identical to the previous run.

## Tamper Modes
The demo supports multiple tamper modes to test detection capabilities:

### Value Tamper
Changes a semantic value to verify hash change detection:
```bash
python demos/canonical_truth_reconstruction_demo.py --tamper value
```
Expected Output:
```
REPLAY_VERDICT=FAIL
REASON=HASH_MISMATCH
```

### Remove-Field Tamper
Removes a required field to verify missing field detection:
```bash
python demos/canonical_truth_reconstruction_demo.py --tamper remove-field
```
Expected Output:
```
REPLAY_VERDICT=FAIL
REASON=MISSING_FIELD: intent.action_type - required field is missing
```

### Add-Field Tamper
Adds an unknown field to verify unknown field detection:
```bash
python demos/canonical_truth_reconstruction_demo.py --tamper add-field
```
Expected Output:
```
REPLAY_VERDICT=FAIL
REASON=UNKNOWN_FIELD: intent.unknown_field - field not in coverage manifest
```

### Reorder Tamper
Reorders fields to verify ordering enforcement:
```bash
python demos/canonical_truth_reconstruction_demo.py --tamper reorder
```
Expected Output:
```
REPLAY_VERDICT=FAIL
REASON=HASH_MISMATCH
```

## Explain Mode
Use the `--explain` flag to get detailed failure explanations:
```bash
python demos/canonical_truth_reconstruction_demo.py --input /tmp/tampered.json --explain
```

Expected output on failure:
```
REPLAY_VERDICT=FAIL
REASON=UNKNOWN_FIELD: intent.evil_field - field not in coverage manifest
EXPLANATION=Validation failed: UNKNOWN_FIELD: intent.evil_field - field not in coverage manifest
DETAIL=Field not defined in CANONICAL_COVERAGE.json. All fields must be explicitly classified as HASHED or EXCLUDED_NONDETERMINISTIC.
```

## Exact Claims

This proof demonstrates the following adversarial guarantees:

### Claim 1: Complete Hash Coverage
**Claim:** Every field in the audit bundle is explicitly classified as HASHED or EXCLUDED_NONDETERMINISTIC in CANONICAL_COVERAGE.json. No field is validated but not hashed unless explicitly documented.

**Proof:** `tests/test_canonical_hash_coverage.py` recursively walks the sample bundle and verifies:
- Every field has a classification in CANONICAL_COVERAGE.json
- HASHED fields change the hash when mutated
- EXCLUDED_NONDETERMINISTIC fields do not change the hash when mutated
- Unknown injected fields cause UNKNOWN_FIELD failures
- Manifest includes canonicalization_version and hash_algorithm metadata

**Reference:** `artifacts/canonical/CANONICAL_COVERAGE.json`

### Claim 2: Single Canonical Verification Pipeline
**Claim:** The only allowed verification flow is: raw bundle → recursive validation → replay/reconstruction → canonical representation → deterministic canonical JSON → sha256 hash. No alternative paths exist.

**Proof:** `tests/test_hash_pipeline_integrity.py` verifies:
- `verify_bundle()` is the single explicit function boundary
- Hash input is canonical JSON only, not raw bundle
- Canonical JSON has sorted object keys
- Default and --input paths reach the same verification logic
- Internal assertions enforce pipeline invariants

**Reference:** `demos/canonical_truth_reconstruction_demo.py::verify_bundle()`

### Claim 3: Replay/Canonical Consistency
**Claim:** Source audit bundle, reconstructed execution representation, and canonical representation are consistent. Semantic fields appear in reconstructed representation, and canonical derives from reconstructed.

**Proof:** `tests/test_replay_canonical_consistency.py` verifies:
- Valid bundles reconstruct expected canonical representation
- Semantic field changes affect hash or fail
- Nested field changes affect hash or fail
- Counts match actual records/events
- Final status matches terminal state
- Canonical derives from reconstructed, not raw copy

### Claim 4: Locked List Semantics
**Claim:** Every list path has explicit ordering semantics (ORDERED_SEMANTIC, UNORDERED_SET, or REJECTED_IF_REORDERED). No implicit ordering assumptions exist.

**Proof:** `tests/test_list_semantics_lockdown.py` verifies:
- Every list path in sample bundle is classified in ORDERING_RULES.json
- ORDERED_SEMANTIC list reorders change hash or fail
- UNORDERED_SET lists have explicit sort keys or documentation
- Nested list ordering is enforced
- Duplicate elements handled deterministically

**Reference:** `artifacts/canonical/ORDERING_RULES.json`

### Claim 5: Deep Adversarial Tamper Detection
**Claim:** Comprehensive adversarial mutations (structural, type, semantic) are detected. Every mutation either FAILS with explicit reason or produces different hash. No mutation passes with identical hash.

**Proof:** `tests/test_deep_adversarial_tamper_matrix.py` tests:
- **Structural:** Add unknown field at root/nested, remove required field, replace object with list, replace list with object, empty required list
- **Type:** int→string, bool→string, string→int, null instead of value, empty string where nonempty required
- **Semantic:** Change event sequence, action type, target, final status, event count, terminal event

**Result:** 18/18 mutations detected (either FAIL or hash change)

## Invariants
- Full audit bundle structure (not just summary)
- Recursive validation of nested structures
- All fields are covered by CANONICAL_COVERAGE.json with explicit HASHED/EXCLUDED_NONDETERMINISTIC classification
- Required fields are enforced (MISSING_FIELD detection)
- Unknown fields are rejected (fail-closed, UNKNOWN_FIELD)
- Type mismatches are rejected (no implicit casting, including "true"/"false" strings)
- Null values are rejected in required fields
- Ordering rules are enforced (object keys sorted, lists preserve order per ORDERING_RULES.json)
- Hash is computed from canonical form only (verified by internal assertions)
- Accurate failure reasons (no collapse to HASH_MISMATCH)
- Single verification pipeline (verify_bundle function only)
- Replay/canonical consistency (source → reconstructed → canonical flow)
- List semantics locked (every list path explicitly classified)
- Deep adversarial tamper detection (18+ mutation vectors tested)

## Attack Guide

### Attack Vector 1: Inject Unknown Field
**Attempt:** Add a new field not defined in CANONICAL_COVERAGE.json to bypass validation.
```json
{
  "intent": {
    "action_type": "delete",
    "target": "/tmp/test",
    "malicious_field": "evil_value"
  }
}
```
**Result:** FAIL with `UNKNOWN_FIELD: intent.malicious_field - field not in coverage manifest`
**Why:** All fields must be explicitly classified. Fail-closed validation rejects unknown fields.

### Attack Vector 2: Remove Required Field
**Attempt:** Delete a required field to hide evidence.
```json
{
  "intent": {
    "target": "/tmp/test"
    // action_type removed
  }
}
```
**Result:** FAIL with `MISSING_FIELD: intent.action_type - required field is missing`
**Why:** Required fields are enforced by coverage manifest.

### Attack Vector 3: Type Coercion
**Attempt:** Use string "true" instead of boolean true to bypass type checks.
```json
{
  "execution_trace": {
    "events": [{
      "ok": "true"  // String instead of boolean
    }]
  }
}
```
**Result:** FAIL with `TYPE_MISMATCH: $.execution_trace.events[0].ok has string 'true' instead of boolean`
**Why:** No implicit type coercion allowed. Exact type matching enforced.

### Attack Vector 4: Reorder Events
**Attempt:** Reorder execution trace events to change narrative while preserving hash.
```json
// Swap event[0] and event[1]
```
**Result:** FAIL with `HASH_MISMATCH` or validation failure
**Why:** Execution trace events are ORDERED_SEMANTIC. Sequence order is part of hash.

### Attack Vector 5: Replace Object with List
**Attempt:** Replace a structured object with a list to break validation.
```json
{
  "intent": ["malicious", "list"]
}
```
**Result:** FAIL with TYPE_MISMATCH or UNKNOWN_FIELD
**Why:** Recursive validation enforces structure. Type mismatches are detected.

### Attack Vector 6: Empty Required List
**Attempt:** Empty the events list to hide execution evidence.
```json
{
  "execution_trace": {
    "events": []
  }
}
```
**Result:** FAIL with HASH_MISMATCH or MISSING_FIELD
**Why:** Required lists cannot be empty. Count validation enforced.

### Attack Vector 7: Null in Required Field
**Attempt:** Use null instead of value to hide data.
```json
{
  "intent": {
    "action_type": null
  }
}
```
**Result:** FAIL with NULL_VALUE or MISSING_FIELD
**Why:** Null values rejected in required fields.

### Attack Vector 8: Change Final Status Without Changing Events
**Attempt:** Change final_verdict to "approve" while keeping deny events.
```json
{
  "final_verdict": "approve",
  "execution_trace": {
    "events": [/* deny events unchanged */]
  }
}
```
**Result:** FAIL with HASH_MISMATCH or consistency check
**Why:** Replay/canonical consistency checks enforce terminal state matches replayed events.

## Test with Your Own Local Copy

You can test the replay proof with your own edited bundle. This demonstrates that:
- User controls the data
- ExoArmur controls the verification rules
- Invalid or tampered data fails deterministically

### Write Sample Bundle
```bash
python demos/canonical_truth_reconstruction_demo.py --write-sample /tmp/exo_sample.json
```

This writes the valid default demo bundle to `/tmp/exo_sample.json` as JSON.

### Test with User-Supplied Bundle
```bash
python demos/canonical_truth_reconstruction_demo.py --input /tmp/exo_sample.json
```

Expected Output:
```
REPLAY_VERDICT=PASS
CANONICALIZATION_VERSION=v1
HASH_ALGORITHM=sha256
HASH=cfd322c8a4360a4fedf85682f4bdeb8838ef1e4f2188b23e929ac2d7475b740e
```

### Edit and Verify Detection
1. Edit the sample bundle:
```bash
# Edit /tmp/exo_sample.json and change one value
# For example, change "intent.action_type" from "delete" to "read"
```

2. Rerun the proof:
```bash
python demos/canonical_truth_reconstruction_demo.py --input /tmp/exo_sample.json
```

3. Expected result:
- The hash will change (semantic mutation detected)
- Or the proof will fail with explicit reason (e.g., UNKNOWN_FIELD, TYPE_MISMATCH, MISSING_FIELD)

### Tamper with User-Supplied Bundle
You can also apply tamper modes to user-supplied bundles:
```bash
python demos/canonical_truth_reconstruction_demo.py --input /tmp/exo_sample.json --tamper value
```

### Failure Modes
User-supplied input fails cleanly for:
- Missing file: `REPLAY_VERDICT=FAIL REASON=FILE_NOT_FOUND`
- Malformed JSON: `REPLAY_VERDICT=FAIL REASON=MALFORMED_JSON`
- Unknown field: `REPLAY_VERDICT=FAIL REASON=UNKNOWN_FIELD:<path>`
- Type mismatch: `REPLAY_VERDICT=FAIL REASON=TYPE_MISMATCH:<path>`
- Missing required field: `REPLAY_VERDICT=FAIL REASON=MISSING_FIELD:<path>`
- Null value in required field: `REPLAY_VERDICT=FAIL REASON=NULL_VALUE:<path>`
- Hash mismatch (tamper detected): `REPLAY_VERDICT=FAIL REASON=HASH_MISMATCH`

All validation rules apply equally to default and user-supplied bundles.

## Test Suite
Run the full adversarial test suite:
```bash
python -m pytest tests/test_canonical_hash_coverage.py -v
python -m pytest tests/test_hash_pipeline_integrity.py -v
python -m pytest tests/test_replay_canonical_consistency.py -v
python -m pytest tests/test_list_semantics_lockdown.py -v
python -m pytest tests/test_deep_adversarial_tamper_matrix.py -v
python -m pytest tests/test_explain_mode.py -v
```

All tests must pass with binary green. No skips allowed.
