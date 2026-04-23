#!/bin/bash
set -e

echo "=== EXOARMUR REPLAY PROOF DEMO ==="
echo ""

# Check if we're in demo mode (controlled mutation)
DEMO_MODE="${DEMO_MODE:-success}"

# Step 1: Run prove-determinism to get a correlation_id
echo "Step 1: Running prove-determinism..."
PROVE_OUTPUT=$(python -m exoarmur.cli prove-determinism --runs 3 2>&1)
echo "$PROVE_OUTPUT"

# Extract correlation_id from output
CORRELATION_ID=$(echo "$PROVE_OUTPUT" | grep -oP 'correlation_id: \K[0-9A-Z]+' || echo "")

if [ -z "$CORRELATION_ID" ]; then
    echo "ERROR: Could not extract correlation_id from prove-determinism output"
    exit 1
fi

echo "Extracted correlation_id: $CORRELATION_ID"
echo ""

# Step 2: Fetch bundle from core API
echo "Step 2: Fetching audit bundle..."
BUNDLE_RESPONSE=$(curl -s http://localhost:8000/v1/audit/$CORRELATION_ID/bundle)
echo "$BUNDLE_RESPONSE" | python -m json.tool
echo ""

# Check if bundle was found
if echo "$BUNDLE_RESPONSE" | grep -q "not found"; then
    echo "ERROR: Audit bundle not found for correlation_id $CORRELATION_ID"
    exit 1
fi

# Step 3: Write bundle to temp file
TEMP_BUNDLE="/tmp/prove_it_bundle_$CORRELATION_ID.json"
echo "$BUNDLE_RESPONSE" > "$TEMP_BUNDLE"

# Step 4: Run replay
echo "Step 3: Running replay..."
REPLAY_OUTPUT=$(python -m exoarmur.cli replay --bundle "$TEMP_BUNDLE" --json 2>&1)
echo "$REPLAY_OUTPUT" | python -m json.tool
echo ""

# Step 5: Parse and display strict output
if [ "$DEMO_MODE" = "failure" ]; then
    # FAILURE DEMO MODE: Introduce controlled mutation
    echo "=== FAILURE DEMO MODE ==="
    echo "Introducing controlled mutation to bundle..."
    
    # Mutate the bundle (change execution_hash)
    MUTATED_BUNDLE="/tmp/prove_it_bundle_mutated_$CORRELATION_ID.json"
    python -c "
import json
with open('$TEMP_BUNDLE', 'r') as f:
    bundle = json.load(f)
bundle['execution_hash'] = 'MUTATED_HASH_' + bundle['execution_hash']
with open('$MUTATED_BUNDLE', 'w') as f:
    json.dump(bundle, f, indent=2)
"
    
    echo "Running replay with mutated bundle..."
    REPLAY_OUTPUT=$(python -m exoarmur.cli replay --bundle "$MUTATED_BUNDLE" --json 2>&1)
    echo "$REPLAY_OUTPUT" | python -m json.tool
    echo ""
    
    # Parse failure output
    VERDICT=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['verdict'])")
    FIRST_DIVERGENCE=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; d=json.load(sys.stdin); print(d.get('mismatch', {}).get('first_divergence_stage', 'N/A'))")
    EXPECTED_HASH=$(echo "$BUNDLE_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['execution_hash'])")
    ACTUAL_HASH=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['replay_hash'])")
    
    echo "=== FAILURE OUTPUT ==="
    echo "STATUS: $VERDICT"
    echo "FIRST DIVERGENCE: $FIRST_DIVERGENCE"
    echo "EXPECTED HASH: $EXPECTED_HASH"
    echo "ACTUAL HASH: $ACTUAL_HASH"
    
    # Cleanup
    rm -f "$MUTATED_BUNDLE"
else
    # SUCCESS CASE
    VERDICT=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['verdict'])")
    INPUT_HASH=$(echo "$BUNDLE_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['input_hash'])")
    EXECUTION_HASH=$(echo "$BUNDLE_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['execution_hash'])")
    REPLAY_HASH=$(echo "$REPLAY_OUTPUT" | python -c "import sys, json; print(json.load(sys.stdin)['replay_hash'])")
    
    # Verify all stages
    STAGES_VERIFIED=$(echo "$REPLAY_OUTPUT" | python -c "
import sys, json
data = json.load(sys.stdin)
stages = data.get('stages', [])
all_match = all(s['status'] == 'match' for s in stages)
print('ALL VERIFIED' if all_match else 'PARTIAL')
")
    
    echo "=== SUCCESS OUTPUT ==="
    echo "STATUS: $VERDICT"
    echo "INPUT HASH: $INPUT_HASH"
    echo "EXECUTION HASH: $EXECUTION_HASH"
    echo "REPLAY HASH: $REPLAY_HASH"
    echo "STAGES: $STAGES_VERIFIED"
fi

# Cleanup
rm -f "$TEMP_BUNDLE"

echo ""
echo "=== PROOF COMPLETE ==="
