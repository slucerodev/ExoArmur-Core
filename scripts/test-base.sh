#!/bin/bash
# ExoArmur Base Test Runner
# Runs core functionality tests excluding acceptance gates

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

# Run base tests (exclude acceptance markers)
echo "🧪 Running ExoArmur base test suite..."
echo "Repository: $REPO_ROOT"
echo "Python: $(./.venv/bin/python --version)"
echo "Excluding: v2_acceptance, golden_demo"
echo ""

exec ./.venv/bin/python -m pytest -m "not v2_acceptance and not golden_demo" "$@"
