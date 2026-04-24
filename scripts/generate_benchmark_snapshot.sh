#!/bin/bash
# Benchmark Snapshot Generator
# Generates reproducible benchmark snapshot for public-facing proof

set -e

SNAPSHOT_FILE="docs/BENCHMARK_SNAPSHOT.md"

echo "Generating benchmark snapshot..."

# Capture system info
CPU=$(nproc 2>/dev/null || echo "unknown")
RAM=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' || echo "unknown")
OS=$(uname -s -r)
PYTHON=$(python --version 2>&1)
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

# Run all benchmarks
echo "Running full benchmark suite..."
FULL_OUTPUT=$(python -m exoarmur.cli benchmark --all --runs 200 --concurrency 10,50,100,500,1000 2>&1)

# Run high-concurrency determinism test
echo "Running high-concurrency determinism test..."
DETERMINISM_OUTPUT=$(python -m exoarmur.cli benchmark --determinism-load --runs 500 --concurrency 1000 2>&1)

# Write snapshot
cat > "$SNAPSHOT_FILE" <<EOF
# BENCHMARK SNAPSHOT

## Full Benchmark Suite

Command:
\`\`\`
python -m exoarmur.cli benchmark --all --runs 200 --concurrency 10,50,100,500,1000
\`\`\`

System:
- CPU: $CPU cores
- RAM: $RAM
- OS: $OS
- Python: $PYTHON

Results:
\`\`\`
$FULL_OUTPUT
\`\`\`

## High-Concurrency Determinism Test

Command:
\`\`\`
python -m exoarmur.cli benchmark --determinism-load --runs 500 --concurrency 1000
\`\`\`

Results:
\`\`\`
$DETERMINISM_OUTPUT
\`\`\`

Timestamp: $TIMESTAMP
EOF

echo "Benchmark snapshot written to $SNAPSHOT_FILE"
