#!/bin/bash
# Prove clean installation works for ExoArmur
# This script creates a fresh venv and tests the complete installation

set -e  # Exit on any error

echo "🔧 ExoArmur Clean Installation Proof"
echo "=================================="

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create fresh venv
VENV_DIR="$PROJECT_ROOT/.venv_clean_install"
if [ -d "$VENV_DIR" ]; then
    echo "🗑️  Removing existing clean venv..."
    rm -rf "$VENV_DIR"
fi

echo "📦 Creating fresh virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate venv
echo "🔌 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install editable
echo "📥 Installing ExoArmur in editable mode..."
cd "$PROJECT_ROOT"
pip install -e .

# Test CLI health
echo "🏥 Testing CLI health check..."
exoarmur health

# Test demo smoke
echo "🚀 Testing demo smoke (deny mode)..."
exoarmur demo --operator-decision deny

# Test verify_all (fast mode for now)
echo "🔍 Testing verify_all (fast mode)..."
exoarmur verify-all --fast

echo ""
echo "✅ CLEAN INSTALLATION PROOF COMPLETE"
echo "=================================="
echo "All commands executed successfully!"
echo ""
echo "To use this environment:"
echo "  source $VENV_DIR/bin/activate"
echo "  exoarmur --help"
