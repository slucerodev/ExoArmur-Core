#!/bin/bash
# Full Audit Runner
# Runs all audit scripts in order to verify repository is ready for public scrutiny

set -e

echo "========================================"
echo "FULL AUDIT - PUBLIC SCRUTINY PREPARATION"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
FAILED=0

# 1. Clean Environment Repro
echo "Step 1: Clean Environment Reproducibility Check..."
bash scripts/verify_clean_install.sh
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Clean environment reproducibility check failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Clean environment reproducibility check passed${NC}"
fi
echo ""

# 2. Proof Output Validation
echo "Step 2: Proof Output Validation..."
python scripts/validate_proof_output.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Proof output validation failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Proof output validation passed${NC}"
fi
echo ""

# 3. Process Isolation Stability (already in verify_clean_install.sh)
echo "Step 3: Process Isolation Stability Check..."
echo -e "${GREEN}✓ Process isolation stability check completed in Step 1${NC}"
echo ""

# 4. Repo Structure Audit
echo "Step 4: Repository Structure Audit..."
python scripts/audit_repo_structure.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Repository structure audit failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Repository structure audit passed${NC}"
fi
echo ""

# 5. Dependency Audit
echo "Step 5: Dependency Audit..."
python scripts/audit_dependencies.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Dependency audit failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Dependency audit passed${NC}"
fi
echo ""

# 6. Determinism Attack Test
echo "Step 6: Determinism Attack Simulation..."
python scripts/determinism_attack_test.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Determinism attack test failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Determinism attack test passed${NC}"
fi
echo ""

# 7. Docs Validation
echo "Step 7: Documentation Validation..."
python scripts/validate_docs.py
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Documentation validation failed${NC}"
    FAILED=1
else
    echo -e "${GREEN}✓ Documentation validation passed${NC}"
fi
echo ""

# Summary
echo "========================================"
echo "AUDIT RESULTS"
echo "========================================"
echo ""
echo "Reproducibility: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Proof Integrity: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Process Isolation: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Structure: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Dependencies: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Determinism Resistance: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo "Docs Alignment: $( [ $FAILED -eq 0 ] && echo -e "${GREEN}PASS${NC}" || echo -e "${RED}FAIL${NC}" )"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}FINAL STATUS: READY FOR PUBLIC SCRUTINY${NC}"
    echo ""
    echo "✓ Repository installs and runs in clean environment without intervention"
    echo "✓ Proof output is complete and consistent"
    echo "✓ Process isolation is stable across runs"
    echo "✓ No repo clutter or naming inconsistencies"
    echo "✓ Determinism holds under attack scenarios"
    echo "✓ Docs match real behavior exactly"
    echo ""
    exit 0
else
    echo -e "${RED}FINAL STATUS: NOT READY FOR PUBLIC SCRUTINY${NC}"
    echo ""
    echo "Fix the above failures before proceeding with public release"
    echo ""
    exit 1
fi
