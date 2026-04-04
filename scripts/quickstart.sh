#!/bin/bash
# ExoArmur Quickstart Runner
# Idempotent script to set up environment and run quickstart

set -e  # Exit on any error

echo "🚀 ExoArmur Quickstart Setup"
echo "=========================="

# Check if Python 3.12+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed or not in PATH"
    echo "Please install Python 3.12+ and try again"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.12"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    echo "❌ Python $REQUIRED_VERSION+ is required (found $PYTHON_VERSION)"
    echo "Please upgrade Python and try again"
    exit 1
fi

echo "✅ Python version check passed ($PYTHON_VERSION)"

# Check if we're in the ExoArmur repository root
if [ ! -f "pyproject.toml" ] || [ ! -d "src/exoarmur" ]; then
    echo "❌ Not in ExoArmur repository root"
    echo "Please run this script from the ExoArmur-Core repository root"
    exit 1
fi

echo "✅ Repository root check passed"

# Create virtual environment if it doesn't exist
VENV_DIR="venv_quickstart"

if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install requirements
if [ -f "requirements-quickstart.txt" ]; then
    echo "📦 Installing quickstart requirements..."
    pip install -r requirements-quickstart.txt > /dev/null 2>&1
    echo "✅ Quickstart requirements installed"
elif [ -f "requirements.txt" ]; then
    echo "📦 Installing requirements..."
    pip install -r requirements.txt > /dev/null 2>&1
    echo "✅ Requirements installed"
else
    echo "⚠️  No requirements file found, installing package in development mode..."
    pip install -e . > /dev/null 2>&1
    echo "✅ Package installed in development mode"
fi

# Install ExoArmur package in development mode
echo "📦 Installing ExoArmur-Core in development mode..."
pip install -e . > /dev/null 2>&1
echo "✅ ExoArmur-Core installed"

# Run quickstart
echo ""
echo "🎯 Running ExoArmur Quickstart..."
echo "=============================="
python -m exoarmur.quickstart.run_quickstart

# Capture exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 Quickstart completed successfully!"
    echo "ExoArmur-Core is properly installed and functional."
else
    echo ""
    echo "❌ Quickstart failed with exit code $EXIT_CODE"
    echo "Please check the error messages above."
    exit $EXIT_CODE
fi
