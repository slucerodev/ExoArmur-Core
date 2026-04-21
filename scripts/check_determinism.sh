#!/bin/bash
# Determinism Gate CI/CD Integration Script
# Runs all determinism checks as part of CI/CD pipeline
# Fails if any violations are detected

set -e

echo "========================================"
echo "DETERMINISM GATE - CI/CD CHECK"
echo "========================================"
echo ""

# Set PYTHONHASHSEED for determinism
export PYTHONHASHSEED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# 1. Run static analysis scanner
echo "Step 1: Running static analysis scanner..."
python -m exoarmur.stability.determinism_scanner src/exoarmur --protected-only
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Static analysis failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Static analysis passed${NC}"
fi
echo ""

# 2. Run adversarial determinism tests
echo "Step 2: Running adversarial determinism tests..."
python -m pytest tests/test_adversarial_determinism.py -v --tb=short
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Adversarial determinism tests failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Adversarial determinism tests passed${NC}"
fi
echo ""

# 3. Run replay determinism tests
echo "Step 3: Running replay determinism tests..."
python -m pytest tests/replay/test_determinism.py -v --tb=short
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Replay determinism tests failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Replay determinism tests passed${NC}"
fi
echo ""

# 4. Run integration determinism tests
echo "Step 4: Running integration determinism tests..."
python -m pytest tests/integration/test_execution_intent_determinism.py -v --tb=short
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Integration determinism tests failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Integration determinism tests passed${NC}"
fi
echo ""

# 5. Check for environment parity
echo "Step 5: Checking environment parity..."
python -c "from exoarmur.stability.env_parity import enforce_determinism_requirements; enforce_determinism_requirements()"
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Environment parity check failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Environment parity check passed${NC}"
fi
echo ""

# 6. Run ordering enforcement and replay hash consistency tests
echo "Step 6: Running ordering enforcement and replay hash consistency tests..."
python -m pytest tests/test_deterministic_ordering_replay.py -v --tb=short
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Ordering enforcement and replay hash consistency tests failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Ordering enforcement and replay hash consistency tests passed${NC}"
fi
echo ""

# 7. Run Determinism Proof Harness with full verification (including process-isolated)
echo "Step 7: Running Determinism Proof Harness with closed-loop verification (including process-isolated)..."
python -m exoarmur.cli prove-determinism --runs 5 --mode all
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Determinism Proof Harness failed${NC}"
    echo -e "${RED}  Process-isolated mode or hash mismatch detected${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Determinism Proof Harness passed (CLOSED-LOOP)${NC}"
    echo -e "${GREEN}  Process-isolated mode verified${NC}"
fi
echo ""

# 8. Run Full Audit for public scrutiny preparation
echo "Step 8: Running Full Audit for public scrutiny preparation..."
bash scripts/full_audit.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Full audit failed${NC}"
    echo -e "${RED}  Repository not ready for public scrutiny${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Full audit passed${NC}"
    echo -e "${GREEN}  Repository ready for public scrutiny${NC}"
fi
echo ""

# Summary
echo "========================================"
echo "DETERMINISM GATE SUMMARY"
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All determinism checks passed${NC}"
    echo "No nondeterministic patterns detected"
    exit 0
else
    echo -e "${RED}✗ Determinism checks failed${NC}"
    echo "CI/CD pipeline blocked - fix violations before merging"
    exit 1
fi
