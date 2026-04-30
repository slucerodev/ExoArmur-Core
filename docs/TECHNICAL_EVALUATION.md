# Technical Evaluation Guide

## Status

**READY FOR TECHNICAL EVALUATION**

ExoArmur-Core is ready for serious technical evaluation of its core proof claims. This evaluation is intended for technical reviewers to verify the repository's deterministic replay and audit verifiability guarantees without external services.

**Important boundaries:**
- Not production-ready
- Not externally audited
- Not production certified
- Not BFT consensus
- Not post-quantum
- Not a complete production system

This evaluation proves specific technical properties of the ExoArmur-Core governance boundary and replay verification system.

---

## What This Evaluation Proves

This technical evaluation demonstrates:

1. **Canonical demo runs deterministically**
   - The canonical truth reconstruction demo produces stable, reproducible output
   - Hash values remain consistent across runs
   - No runtime metadata enters the verification hash

2. **Governed action produces deterministic proof bundle**
   - Actions executed through the ProxyPipeline governance boundary produce replay-verifiable proof bundles
   - The demo bundle captures all execution artifacts needed for reconstruction
   - Canonicalization produces stable JSON with sorted keys

3. **External verifier accepts valid demo bundle**
   - The `verify-bundle` CLI command validates demo-produced bundles
   - Verification confirms hash integrity and bundle structure
   - Machine-readable output enables automated validation

4. **JSON verifier output is machine-readable**
   - `--json` flag produces structured output for tool integration
   - All verification fields are consistently named
   - Exit codes indicate pass/fail status

5. **Targeted verifier tests pass**
   - External verifier test suite validates bundle verification logic
   - Tests cover valid bundles, invalid JSON, missing files, and format errors
   - All 13 tests pass consistently

6. **Full suite can be run locally**
   - The complete test suite (1312 tests) runs without external services
   - No cloud dependencies, no external databases, no network calls
   - Tests validate core invariants, replay determinism, and governance boundaries

---

## What This Evaluation Does Not Prove

This evaluation does NOT prove:

- **Production readiness**: This is a technical evaluation of core properties, not a production deployment readiness assessment
- **External audit**: No third-party security audit has been conducted
- **Security certification**: No formal security certification (SOC 2, ISO 27001, etc.) has been obtained
- **Real production scale**: Performance at production scale has not been tested
- **BFT consensus**: ExoArmur does not implement Byzantine Fault Tolerance
- **Real-world hostile federation hardening**: Resistance to sophisticated federation attacks has not been tested in production
- **Post-quantum security**: No post-quantum cryptographic claims are made
- **Natural language policy**: This evaluation covers the governance boundary and replay system, not NL policy engines
- **TEE integration**: Trusted Execution Environment integration is not covered in this evaluation

---

## Environment

**Requirements:**
- Python 3.12.3 (preferred)
- No external services required
- No cloud dependencies

**Installation:**

```bash
# Install locked dependencies
python -m pip install -r requirements.lock

# Install ExoArmur-Core in editable mode
python -m pip install --no-deps -e ".[dev]"
```

**Important:** Use `--no-deps` to prevent dependency upgrades that could break determinism. The `requirements.lock` file pins all dependency versions.

---

## Health Check

Verify the system is healthy before running evaluation:

```bash
exoarmur health
```

**Expected output includes:**
```
🏥 ExoArmur Health Check
✅ Core imports working
✅ Feature flags loaded: 8 configured
✅ Governed runtime subsystems importable
🎯 System healthy
```

If health check fails, do not proceed with evaluation.

---

## Run Canonical Demo

Execute the canonical truth reconstruction demo:

```bash
python demos/canonical_truth_reconstruction_demo.py
```

**Expected markers:**
```
REPLAY_VERDICT=PASS
CANONICALIZATION_VERSION=v1
HASH_ALGORITHM=sha256
HASH=cfd322c8a4360a4fedf85682f4bdeb8838ef1e4f2188b23e929ac2d7475b740e
```

**What this proves:**
- The demo executes a governed action (delete attempt outside authorized path)
- The governance boundary denies the action
- A proof bundle is written to `demos/canonical_proof_bundle.json`
- The hash is stable and reproducible

---

## Verify Demo Bundle Externally

Verify the demo-produced bundle using the external verifier:

**Key-value output:**
```bash
exoarmur verify-bundle --bundle demos/canonical_proof_bundle.json
```

**Expected output:**
```
VERIFY_VERDICT=PASS
BUNDLE_FORMAT=CANONICAL_DEMO_BUNDLE
HASH_ALGORITHM=sha256
EXPECTED_HASH=7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b
COMPUTED_HASH=7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b
HASH_MATCH=true
CHECKSUM_EXPECTED=
CHECKSUM_COMPUTED=
CHECKSUM_MATCH=
ERROR=
```

**JSON output:**
```bash
exoarmur verify-bundle --bundle demos/canonical_proof_bundle.json --json
```

**Expected output:**
```json
{
  "bundle_format": "CANONICAL_DEMO_BUNDLE",
  "checksum_computed": "",
  "checksum_expected": "",
  "checksum_match": null,
  "computed_hash": "7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b",
  "error": "",
  "expected_hash": "7eb0f264dd6d6e67925ece66ec2218ac73716ae6bc8a770ef84a8defd28bf47b",
  "hash_algorithm": "sha256",
  "hash_match": true,
  "verify_verdict": "PASS"
}
```

**What this proves:**
- The external verifier can read and validate demo bundles
- Hash integrity is verified (HASH_MATCH=true)
- Bundle format is correctly identified (CANONICAL_DEMO_BUNDLE)
- Both key-value and JSON output formats work correctly

---

## Run Verifier Tests

Execute the external verifier test suite:

```bash
python -m pytest tests/test_external_bundle_verifier.py -v
```

**Expected result:**
```
13 passed
```

**What this proves:**
- Bundle verification logic is tested
- Valid bundles are accepted
- Invalid JSON is rejected
- Missing files are handled correctly
- Format errors are detected
- Both output formats work

---

## Run Proof Demo Tests

Execute the proof demo user input test suite:

```bash
python -m pytest tests/test_proof_demo_user_input.py -v
```

**Expected result:**
```
14 passed
```

**What this proves:**
- Demo accepts user-supplied bundles
- Tamper detection works (value, remove-field, add-field, reorder)
- Validation rejects malformed JSON
- Hash changes are detected
- File not found is handled cleanly

---

## Run Full Suite

Execute the complete test suite (takes several minutes):

```bash
python -m pytest tests/ -q --timeout=300
```

**Expected baseline:**
```
1312 passed, 10 skipped, 3 xfailed
```

**What this proves:**
- All core invariants hold
- Replay determinism is preserved
- Governance boundaries are enforced
- No external services are required
- Tests are stable and reproducible

---

## Interpreting Skipped/Xfailed Tests

The test suite includes:
- **10 skipped tests**: Expected skips for live demos or platform-specific tests (e.g., NATS JetStream live tests)
- **3 xfailed tests**: Expected failures for features not yet implemented or intentionally disabled

These are documented and intentional. They do not indicate test instability or core issues. Skipped tests are marked with `@pytest.mark.skip` with explicit reasons. Xfailed tests are marked with `@pytest.mark.xfail` with expected failure reasons.

---

## Claim Boundaries

**No production-ready claim:** ExoArmur-Core is ready for technical evaluation of specific properties, not production deployment. Production readiness requires additional hardening, security audit, and operational maturity.

**No external audit claim:** No third-party security audit has been conducted. All verification is internal and reproducible by running the test suite.

**No BFT claim:** ExoArmur does not implement Byzantine Fault Tolerance. It provides deterministic replay verification for single-executor governance boundaries.

**Deterministic replay is verified for tested paths:** The tests prove deterministic replay for the canonical demo and all test scenarios. Determinism is enforced through canonical JSON with sorted keys and controlled list ordering.

---

## One-Command Evaluation

For a faster automated evaluation, run:

```bash
bash scripts/evaluate_technical_preview.sh
```

This script runs the core evaluation steps (health check, demo, verify-bundle, targeted tests) in sequence and exits with a clear pass/fail result.

---

## Next Steps for Production Readiness

Per the 30/60/90 production execution plan documented in REMEDIATION_REPORT.md:

1. **Day 0-30:** Truth alignment + backend foundations
2. **Day 31-60:** Backend completion + PoD/DPO completion + UI wiring
3. **Day 61-90:** UI overhaul + SRE/security + launch readiness

Production readiness requires:
- External security audit
- Production deployment evidence
- Production certification
- SLO/error budget configuration
- Incident runbook validation
- Canary deployment validation
