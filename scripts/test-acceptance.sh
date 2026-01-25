#!/bin/bash
# ExoArmur Acceptance Test Runner
# Runs only V2 acceptance and Golden Demo tests

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Ensure we're in the repo root
cd "$REPO_ROOT"

# Verify ./.venv exists
if [ ! -d "./.venv" ]; then
    echo "ERROR: ./.venv not found. Run: python -m venv ./.venv && ./.venv/bin/pip install -e ."
    exit 1
fi

# Run acceptance tests only
echo "🎯 Running ExoArmur acceptance test suite..."
echo "Repository: $REPO_ROOT"
echo "Python: $(./.venv/bin/python --version)"
echo "Including: v2_acceptance, golden_demo (xfail/skip allowed)"
echo ""

exec ./.venv/bin/python -m pytest -m "v2_acceptance or golden_demo" "$@"
