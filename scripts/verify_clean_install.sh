#!/bin/bash
# Clean Environment Reproducibility Verification Script
# Creates a fresh virtual environment, installs project, and runs determinism proof
# Fails if any errors occur or hashes mismatch

set -e

echo "========================================"
echo "CLEAN ENVIRONMENT REPRODUCIBILITY CHECK"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# Create temp directory for venv
TEMP_DIR=$(mktemp -d)
echo "Creating temporary venv in: $TEMP_DIR"

# Create virtual environment
python3 -m venv "$TEMP_DIR/venv"
source "$TEMP_DIR/venv/bin/activate"

echo "Installing project in clean environment..."
pip install -e . > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Clean install failed${NC}"
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo -e "${GREEN}✓ Clean install succeeded${NC}"
echo ""

# Run determinism proof with failure demo
echo "Running determinism proof with failure demo..."
OUTPUT=$(python -m exoarmur.cli prove-determinism --runs 3 --mode all --include-failure-demo 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ Determinism proof command failed${NC}"
    echo "$OUTPUT"
    rm -rf "$TEMP_DIR"
    exit 1
fi
echo -e "${GREEN}✓ Determinism proof command succeeded${NC}"
echo ""

# Validate output contains required fields
echo "Validating proof output fields..."

# Check for Input Hash
if echo "$OUTPUT" | grep -q "Input Hash:"; then
    echo -e "${GREEN}✓ Input Hash present${NC}"
else
    echo -e "${RED}✗ Input Hash missing${NC}"
    FAILED=1
fi

# Check for Execution Hash
if echo "$OUTPUT" | grep -q "Execution Hash:"; then
    echo -e "${GREEN}✓ Execution Hash present${NC}"
else
    echo -e "${RED}✗ Execution Hash missing${NC}"
    FAILED=1
fi

# Check for Replay Verification
if echo "$OUTPUT" | grep -q "Replay Verification:"; then
    echo -e "${GREEN}✓ Replay Verification present${NC}"
else
    echo -e "${RED}✗ Replay Verification missing${NC}"
    FAILED=1
fi

# Check for Unique Hashes = 1
if echo "$OUTPUT" | grep -q "Unique Hashes Observed: 1"; then
    echo -e "${GREEN}✓ Unique Hashes = 1${NC}"
else
    echo -e "${RED}✗ Unique Hashes not equal to 1${NC}"
    FAILED=1
fi

# Check for Noise Injection
if echo "$OUTPUT" | grep -q "Noise Injection:"; then
    echo -e "${GREEN}✓ Noise Injection present${NC}"
else
    echo -e "${RED}✗ Noise Injection missing${NC}"
    FAILED=1
fi

# Check for Failure Detection
if echo "$OUTPUT" | grep -q "Failure Detection:"; then
    echo -e "${GREEN}✓ Failure Detection present${NC}"
else
    echo -e "${RED}✗ Failure Detection missing${NC}"
    FAILED=1
fi

# Check for STATUS: VERIFIED
if echo "$OUTPUT" | grep -q "STATUS: VERIFIED"; then
    echo -e "${GREEN}✓ STATUS: VERIFIED present${NC}"
else
    echo -e "${RED}✗ STATUS: VERIFIED missing${NC}"
    FAILED=1
fi

echo ""

# Process Isolation Stability Check
echo "Running process isolation stability check (5 iterations)..."
SUCCESS_COUNT=0
for i in {1..5}; do
    echo "  Iteration $i/5..."
    # Run process-isolated mode to verify it runs consistently
    ISO_OUTPUT=$(python -m exoarmur.cli prove-determinism --mode process-isolated --runs 3 2>&1)
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Process isolation iteration $i failed${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Check that process-isolated mode passed
    if echo "$ISO_OUTPUT" | grep -q "Process-Isolated:.*PASS"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ Process isolation iteration $i did not pass${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
done

if [ $SUCCESS_COUNT -eq 5 ]; then
    echo -e "${GREEN}✓ Process isolation stability check passed (all 5 iterations successful)${NC}"
else
    echo -e "${RED}✗ Process isolation stability check failed ($SUCCESS_COUNT/5 iterations successful)${NC}"
    FAILED=1
fi

echo ""

# Cleanup
rm -rf "$TEMP_DIR"

# Final status
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Clean environment reproducibility check passed${NC}"
    exit 0
else
    echo -e "${RED}✗ Clean environment reproducibility check failed${NC}"
    exit 1
fi
