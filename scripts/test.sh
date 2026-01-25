#!/bin/bash
# ExoArmur Constitutional Test Runner
# Always uses ./.venv/bin/python to avoid system/venv drift

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

# Verify ./.venv/bin/python exists
if [ ! -f "./.venv/bin/python" ]; then
    echo "ERROR: ./.venv/bin/python not found. Virtual environment may be corrupted."
    exit 1
fi

# Run tests with the correct Python interpreter
echo "🧪 Running ExoArmur test suite with ./.venv/bin/python..."
echo "Repository: $REPO_ROOT"
echo "Python: $(./.venv/bin/python --version)"
echo ""

exec ./.venv/bin/python -m pytest "$@"
