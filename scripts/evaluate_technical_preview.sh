#!/bin/bash
set -e

echo "========================================"
echo "ExoArmur Technical Evaluation"
echo "========================================"
echo ""

# 1. Health check
echo "[1/6] Health check..."
if exoarmur health | grep -q "System healthy"; then
    echo "✓ Health check passed"
else
    echo "✗ Health check failed"
    exit 1
fi
echo ""

# 2. Run canonical demo
echo "[2/6] Running canonical demo..."
if python demos/canonical_truth_reconstruction_demo.py | grep -q "REPLAY_VERDICT=PASS"; then
    echo "✓ Canonical demo passed"
else
    echo "✗ Canonical demo failed"
    exit 1
fi
echo ""

# 3. Verify demo bundle (key-value)
echo "[3/6] Verifying demo bundle (key-value)..."
if exoarmur verify-bundle --bundle demos/canonical_proof_bundle.json | grep -q "VERIFY_VERDICT=PASS"; then
    echo "✓ Bundle verification (key-value) passed"
else
    echo "✗ Bundle verification (key-value) failed"
    exit 1
fi
echo ""

# 4. Verify demo bundle (JSON)
echo "[4/6] Verifying demo bundle (JSON)..."
if exoarmur verify-bundle --bundle demos/canonical_proof_bundle.json --json | grep -q '"verify_verdict": "PASS"'; then
    echo "✓ Bundle verification (JSON) passed"
else
    echo "✗ Bundle verification (JSON) failed"
    exit 1
fi
echo ""

# 5. Run verifier tests
echo "[5/6] Running external verifier tests..."
if python -m pytest tests/test_external_bundle_verifier.py -q | grep -q "13 passed"; then
    echo "✓ Verifier tests passed"
else
    echo "✗ Verifier tests failed"
    exit 1
fi
echo ""

# 6. Run proof demo tests
echo "[6/6] Running proof demo tests..."
if python -m pytest tests/test_proof_demo_user_input.py -q | grep -q "14 passed"; then
    echo "✓ Proof demo tests passed"
else
    echo "✗ Proof demo tests failed"
    exit 1
fi
echo ""

echo "========================================"
echo "TECHNICAL_EVALUATION_RESULT=PASS"
echo "========================================"
