#!/bin/bash
# Benchmark Consistency Validator
# Runs determinism benchmark 3 times and compares results
# FAILS if any run diverges or reports failure

set -e

echo "Running benchmark consistency validation..."

# Store results
declare -a unique_hashes
declare -a statuses

# Run benchmark 3 times
for i in {1..3}; do
    echo "Run $i/3..."
    output=$(python -m exoarmur.cli benchmark --determinism-load --runs 50 --concurrency 100 --minimal 2>&1)
    
    # Extract minimal section (after "DETERMINISM" header)
    minimal_output=$(echo "$output" | sed -n '/^DETERMINISM$/,/^$/p')
    
    # Extract unique hash count (from minimal output)
    unique_hash=$(echo "$minimal_output" | grep "Unique Hashes:" | awk '{print $3}')
    unique_hashes+=("$unique_hash")
    
    # Extract status (from minimal output)
    status=$(echo "$minimal_output" | grep "STATUS:" | awk '{print $2}')
    statuses+=("$status")
    
    echo "  Unique Hashes: $unique_hash, Status: $status"
done

# Compare results
first_hash="${unique_hashes[0]}"
first_status="${statuses[0]}"

echo ""
echo "Consistency Check:"
echo "  Run 1: Hash=$first_hash, Status=$first_status"
echo "  Run 2: Hash=${unique_hashes[1]}, Status=${statuses[1]}"
echo "  Run 3: Hash=${unique_hashes[2]}, Status=${statuses[2]}"

# Verify all hashes are 1 (deterministic)
for hash in "${unique_hashes[@]}"; do
    if [ "$hash" != "1" ]; then
        echo "❌ FAIL: Hash divergence detected (expected 1, got $hash)"
        exit 1
    fi
done

# Verify all statuses are PASS
for status in "${statuses[@]}"; do
    if [ "$status" != "PASS" ]; then
        echo "❌ FAIL: Status failure detected (expected PASS, got $status)"
        exit 1
    fi
done

echo "✓ PASS: All runs are consistent"
exit 0
