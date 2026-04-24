#!/bin/bash

echo "=== EXOARMUR REPLAY PROOF DEMO ==="
echo ""

# Check if we're in demo mode (controlled mutation)
DEMO_MODE="${DEMO_MODE:-success}"

# Use fixed correlation_id for determinism testing
CORRELATION_ID="${CORRELATION_ID:-deterministic-test-id-12345}"

# Create a test audit bundle directly
echo "Step 1: Creating test audit bundle..."
echo "Using correlation_id: $CORRELATION_ID"

# Create a minimal valid audit bundle
BUNDLE_FILE="/tmp/prove_it_bundle_${CORRELATION_ID}.json"
python3 << EOF
import json
import uuid
from datetime import datetime, timezone

correlation_id = "$CORRELATION_ID"
audit_bundle_digest = "test_bundle_digest_" + correlation_id
core_version = "2.0.0"
input_hash = "input_hash_" + correlation_id
execution_hash = "execution_hash_" + correlation_id

# Create minimal audit records
audit_records = [
    {
        "schema_version": "1.0.0",
        "audit_id": str(uuid.uuid4()),
        "tenant_id": "test-tenant",
        "cell_id": "test-cell",
        "idempotency_key": "test-key",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "event_kind": "telemetry_ingest",
        "payload_ref": {},
        "event_hash": "hash1"
    }
]

bundle = {
    "correlation_id": correlation_id,
    "audit_bundle_digest": audit_bundle_digest,
    "core_version": core_version,
    "input_hash": input_hash,
    "execution_hash": execution_hash,
    "audit_records": audit_records,
    "retrieved_at": datetime.now(timezone.utc).isoformat()
}

with open("$BUNDLE_FILE", 'w') as f:
    json.dump(bundle, f, indent=2)

print(f"Created bundle: {bundle['correlation_id']}")
print(f"Input Hash: {bundle['input_hash']}")
print(f"Execution Hash: {bundle['execution_hash']}")
EOF

echo ""

# Step 2: Run replay
echo "Step 2: Running replay..."
REPLAY_OUTPUT=$(python -m exoarmur.cli replay --bundle "$BUNDLE_FILE" --json 2>/dev/null)
REPLAY_EXIT_CODE=$?
echo "Exit code: $REPLAY_EXIT_CODE"
echo "$REPLAY_OUTPUT" | python -m json.tool
echo ""

# Step 3: Parse and display strict output
echo "Step 3: Analyzing replay results..."

VERDICT=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['verdict'])")
INPUT_HASH=$(python3 -c "import json; b=json.load(open('$BUNDLE_FILE')); print(b['input_hash'])")
EXECUTION_HASH=$(python3 -c "import json; b=json.load(open('$BUNDLE_FILE')); print(b['execution_hash'])")
REPLAY_HASH=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['replay_hash'])")

# Verify all stages
STAGES_VERIFIED=$(echo "$REPLAY_OUTPUT" | python -c "
import sys, json
data = json.load(sys.stdin)
stages = data.get('stages', [])
all_match = all(s['status'] == 'match' for s in stages)
print('ALL VERIFIED' if all_match else 'PARTIAL')
")

echo "=== REPLAY RESULTS ==="
echo "STATUS: $VERDICT"
echo "EXIT CODE: $REPLAY_EXIT_CODE"
echo "INPUT HASH: $INPUT_HASH"
echo "EXECUTION HASH: $EXECUTION_HASH"
echo "REPLAY HASH: $REPLAY_HASH"
echo "STAGES: $STAGES_VERIFIED"

if [ "$DEMO_MODE" = "failure" ]; then
    # FAILURE DEMO MODE: Introduce controlled mutation
    echo "=== FAILURE DEMO MODE ==="
    echo "Introducing controlled mutation to bundle..."
    
    # Mutate the bundle (change execution_hash)
    MUTATED_BUNDLE="/tmp/prove_it_bundle_mutated_${CORRELATION_ID}.json"
    python3 << EOF
import json
with open('$BUNDLE_FILE', 'r') as f:
    bundle = json.load(f)
bundle['execution_hash'] = 'MUTATED_HASH_' + bundle['execution_hash']
with open('$MUTATED_BUNDLE', 'w') as f:
    json.dump(bundle, f, indent=2)
EOF
    
    echo "Running replay with mutated bundle..."
    REPLAY_OUTPUT=$(python -m exoarmur.cli replay --bundle "$MUTATED_BUNDLE" --json 2>/dev/null)
    REPLAY_EXIT_CODE=$?
    echo "$REPLAY_OUTPUT" | python -m json.tool
    echo ""
    
    # Parse failure output
    VERDICT=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['verdict'])")
    FIRST_DIVERGENCE=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; d=json.load(sys.stdin); print(d.get('mismatch', {}).get('first_divergence_stage', 'N/A'))")
    EXPECTED_HASH=$(python3 -c "import json; b=json.load(open('$BUNDLE_FILE')); print(b['execution_hash'])")
    ACTUAL_HASH=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['replay_hash'])")
    
    echo "=== FAILURE OUTPUT ==="
    echo "STATUS: $VERDICT"
    echo "EXIT CODE: $REPLAY_EXIT_CODE"
    echo "FIRST DIVERGENCE: $FIRST_DIVERGENCE"
    echo "EXPECTED HASH: $EXPECTED_HASH"
    echo "ACTUAL HASH: $ACTUAL_HASH"
    
    # Cleanup
    rm -f "$MUTATED_BUNDLE"
fi

# Cleanup
rm -f "$BUNDLE_FILE"

echo ""
echo "=== PROOF COMPLETE ==="
