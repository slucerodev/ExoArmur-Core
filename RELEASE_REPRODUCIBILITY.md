# Phase 6 Cold Reviewer Reproducibility Guide

## QUICK START

### 1. Environment Setup
```bash
# Clone and navigate to repository
cd /path/to/ExoArmur

# Ensure Python 3.8+ is available
python3 --version

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

### 2. Execute Phase 6 Verification
```bash
# Run complete Phase 6 test suite
python3 scripts/phase6_final_reality_run.py

# Expected output:
# - All 4 test suites should show "PASS"
# - Final status should show "ALL GATES GREEN"
# - Evidence bundle generated in artifacts/reality_run_008/
```

### 3. Verify Evidence Bundle
```bash
# Check final gate status
cat artifacts/reality_run_008/PASS_FAIL.txt

# Expected output:
# Gate 1: PASS
# Gate 2: PASS
# Gate 3: PASS
# Gate 4: PASS
# Gate 5: PASS
# Gate 6: PASS
# Gate 7: PASS
# Gate 8: PASS
# PHASE 6: COMPLETE - ALL GATES GREEN
```

## DETAILED VERIFICATION STEPS

### Step 1: Individual Test Execution
```bash
# Test 1: Timeout Enforcement
python3 -m tests.test_phase6_timeout_simple
# Expected: "ALL TIMEOUT ENFORCEMENT TESTS PASSED"

# Test 2: Retry Policy
python3 -m tests.test_phase6_retry_minimal
# Expected: "ALL RETRY POLICY TESTS PASSED"

# Test 3: Backpressure
python3 -m tests.test_phase6_backpressure_minimal
# Expected: "ALL BACKPRESSURE TESTS PASSED"

# Test 4: Circuit Breakers
python3 -m tests.test_phase6_circuit_breaker_minimal
# Expected: "ALL CIRCUIT BREAKER TESTS PASSED"
```

### Step 2: Evidence Bundle Verification
```bash
# List all evidence files
ls -la artifacts/reality_run_008/

# Key files to examine:
# - 13_final_evidence_bundle.json (complete bundle)
# - PASS_FAIL.txt (final gate status)
# - 00_reliability_surface.md (failure inventory)
# - 01_timeout_design.md through 07_circuit_breaker_design.md (design docs)
# - 10_load_test_results.md (scale validation)
# - 12_chaos_test_results.md (chaos testing)
```

### Step 3: Scale Validation Check
```bash
# Verify load test results
grep -A 5 "1000 Logical Nodes" artifacts/reality_run_008/10_load_test_results.md
# Expected: Shows 786 unique nodes (validated range: 700-800)

grep -A 5 "500 Peer Identities" artifacts/reality_run_008/10_load_test_results.md
# Expected: Shows 469 unique peers (validated range: 400-500)
```

## EXPECTED OUTPUTS

### Successful Test Execution Output
```
============================================================
PHASE 6: TIMEOUT ENFORCEMENT TESTS
============================================================
Testing timeout manager...
✓ Timeout manager configuration works correctly
...
============================================================
TIMEOUT ENFORCEMENT TEST RESULTS: 5 passed, 0 failed
============================================================
✅ ALL TIMEOUT ENFORCEMENT TESTS PASSED
```

### Final Reality Run Output
```
================================================================================
PHASE 6 FINAL RESULTS
================================================================================
Gate 1: PASS
Gate 2: PASS
Gate 3: PASS
Gate 4: PASS
Gate 5: PASS
Gate 6: PASS
Gate 7: PASS
Gate 8: PASS

========================================
🎉 PHASE 6: COMPLETE - ALL GATES GREEN
✅ GATE 7: FAILURE SURVIVAL & CRASH CONSISTENCY - GREEN
✅ GATE 8: BOUNDED LOAD & BACKPRESSURE - GREEN
```

## TROUBLESHOOTING

### Module Import Errors
If you encounter "ModuleNotFoundError: No module named 'reliability'":
```bash
# Verify src directory exists
ls src/

# Verify reliability module exists
ls src/reliability/

# Run with explicit Python path
PYTHONPATH=src python3 scripts/phase6_final_reality_run.py
```

### Test Failures
If individual tests fail:
1. Check test output for specific error messages
2. Verify all required dependencies are installed
3. Ensure Python 3.8+ is being used
4. Check that src/reliability/ module is intact

### Evidence Bundle Issues
If evidence files are missing:
```bash
# Create artifacts directory
mkdir -p artifacts/reality_run_008

# Re-run the reality run
python3 scripts/phase6_final_reality_run.py
```

## OPEN-CORE BOUNDARY CLARITY

### Core Components (Included)
- ✅ Timeout enforcement manager
- ✅ Retry policy framework with idempotency
- ✅ Backpressure and rate limiting
- ✅ Circuit breakers for external dependencies
- ✅ Audit and observability systems

### Experimental Components (Future)
- ⚠️ Advanced machine learning integration
- ⚠️ Federated learning capabilities
- ⚠️ External API integrations beyond core
- ⚠️ Advanced analytics dashboards

### Core Boundary Definition
The open-core release includes all reliability substrate components required for production deployment. Experimental features are clearly marked and not included in the core release bundle.

## VERIFICATION CHECKLIST

- [ ] All 4 test suites pass individually
- [ ] Phase 6 final reality run completes successfully
- [ ] All 8 gates show PASS status
- [ ] Evidence bundle contains all required files
- [ ] Scale validation shows accurate ranges (700-800 nodes, 400-500 peers)
- [ ] No ModuleNotFoundError during execution
- [ ] Golden Demo remains unchanged and passes
- [ ] No new dependencies introduced

## REPRODUCTION COMMANDS

```bash
# Complete verification sequence
cd /path/to/ExoArmur
python3 scripts/phase6_final_reality_run.py
cat artifacts/reality_run_008/PASS_FAIL.txt

# Individual component verification
python3 -m tests.test_phase6_timeout_simple
python3 -m tests.test_phase6_retry_minimal
python3 -m tests.test_phase6_backpressure_minimal
python3 -m tests.test_phase6_circuit_breaker_minimal
```

All commands should be copy/paste reproducible without additional setup.
