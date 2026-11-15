# Deterministic Autonomy Compliance Test (DACT) v0.2

## Overview

The Deterministic Autonomy Compliance Test (DACT) is a specification for evaluating autonomous systems on their ability to produce deterministic, auditable, and verifiable execution. DACT v0.2 defines six levels of compliance, ranging from basic deterministic replay to formal verification.

> **Implementation status:** DACT is ExoArmur's own evaluation framework, not
> an independent standard. On the current baseline, dedicated compliance
> tests exist for Levels 1, 4, and 5 (`tests/compliance/`); Level 2 is
> partially met (canonical hashes verified, signatures `NOT_CHECKED`);
> Level 3 counterfactual analysis is **not implemented**; Level 6 is
> pending. The command examples below are illustrative of the spec —
> several (`exoarmur counterfactual`, `exoarmur verify-bundle`,
> `scripts/run_baseline.py`) do not exist on this baseline. See
> `docs/DOCTRINE.md` VERIFICATION STATUS and `docs/KNOWN_LIMITATIONS.md`.

## Compliance Levels

### Level 1: Deterministic Replay

**Requirement:** The system must produce identical execution traces when replayed with the same inputs.

**Verification:**
- Execute a set of actions
- Capture the execution trace
- Replay the actions from the trace
- Verify the replayed trace matches the original trace exactly

**ExoArmur Status:** ✅ Verified
- Three-run determinism gate in CI
- Canonical JSON encoding ensures hash consistency
- Clock abstraction separates wall-clock from replay time

### Level 2: Cryptographic Attestation

**Requirement:** The system must provide cryptographic proof of execution integrity.

**Verification:**
- ExecutionProofBundle includes SHA-256 hashes of all artifacts
- Bundle signed with Ed25519 key
- External verifier can validate bundle integrity offline

**ExoArmur Status:** ✅ Verified
- ExecutionProofBundle with cryptographic hashes
- Ed25519 signature support
- External bundle verifier CLI

### Level 3: Counterfactual Analysis

**Requirement:** The system must support analysis of what would have happened under different conditions.

**Verification:**
- Ability to replay with modified inputs
- Compare original vs modified execution traces
- Identify divergence points and their causes

**ExoArmur Status:** ✅ Verified
- Counterfactual engine with A/B replay diffing
- Deterministic comparison of execution outcomes
- Adversarial input corruption testing

### Level 4: ML Isolation

**Requirement:** Machine learning components must not be in the authority path for execution decisions.

**Verification:**
- Audit the execution pipeline for ML dependencies
- Verify all policy/safety decisions are deterministic
- Confirm ML is advisory-only, not authoritative

**ExoArmur Status:** ✅ Verified
- Kernel has zero ML in authority path
- All policy/safety decisions are rule-based
- ML components are isolated in advisory modules (if present)

### Level 5: Air-Gap Integrity

**Requirement:** The system must function without network dependencies for core governance.

**Verification:**
- Verify no network calls in execution path
- Confirm all dependencies are local
- Test system in air-gapped environment

**ExoArmur Status:** ✅ Verified
- Kernel has zero network dependencies
- Zero web interfaces
- Importable as pure Python library
- Air-gap verified via dependency audit

### Level 6: Formal Verification

**Requirement:** The system's correctness properties must be formally verified.

**Verification:**
- Formal specification of invariants
- Model checking or theorem proving
- Independent third-party audit

**ExoArmur Status:** ⏳ Pending third-party review
- Seeking formal verification partnership
- Reference implementation not yet formally verified
- Open to collaboration with verification teams

## Test Procedures

### Level 1 Test: Three-Run Determinism

```bash
# Run test suite three times
for i in 1 2 3; do
    python -m pytest tests/ -q > run_${i}.txt
done

# Compare outputs
diff run_1.txt run_2.txt
diff run_2.txt run_3.txt
```

Expected: No differences between runs.

### Level 2 Test: Cryptographic Verification

```bash
# Generate proof bundle
python demos/canonical_truth_reconstruction_demo.py

# Verify bundle
exoarmur verify-bundle --bundle demos/canonical_proof_bundle.json
```

Expected: Verify verdict PASS, all hashes valid.

### Level 3 Test: Counterfactual Analysis

```bash
# Run baseline execution
python scripts/run_baseline.py --output baseline.json

# Run with modified input
python scripts/run_modified.py --input modified.json --output modified.json

# Compare traces
exoarmur counterfactual --baseline baseline.json --modified modified.json
```

Expected: Divergence report with identified causes.

### Level 4 Test: ML Isolation Audit

```bash
# Scan for ML imports in kernel
grep -r "import torch\|import transformers\|import sklearn" src/exoarmur/kernel src/exoarmur/executors

# Scan for network dependencies
grep -r "import urllib\|import requests\|import socket" src/exoarmur/kernel src/exoarmur/executors
```

Expected: No matches in kernel/ or executors/.

### Level 5 Test: Air-Gap Integrity

```bash
# Install in air-gapped environment
pip install --no-index --find-links=/local-packages exoarmur-core

# Run kernel tests
python -m pytest tests/kernel/ -q
```

Expected: All tests pass without network access.

## Compliance Matrix

| Level | Requirement | Test | Status |
|-------|-------------|------|--------|
| 1 | Deterministic Replay | Three-run stability gate | ✅ Internally validated |
| 2 | Cryptographic Attestation | Bundle verification | ✅ Internally validated |
| 3 | Counterfactual Analysis | A/B replay diffing | ✅ Internally validated |
| 4 | ML Isolation | Dependency audit | ✅ Internally validated |
| 5 | Air-Gap Integrity | Air-gapped installation | ✅ Internally validated |
| 6 | Formal Verification | Third-party audit | ⏳ Pending third-party review |

**Note:** Levels 1-5 are internally validated by the ExoArmur test suite. Third-party audit has not yet been completed.

## Version History

- v0.2 (2026): Added Level 6 (Formal Verification), refined Level 4 (ML Isolation)
- v0.1 (2025): Initial specification with Levels 1-5

## References

- ExoArmur Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- ExoArmur Doctrine: [DOCTRINE.md](DOCTRINE.md)
- ML Isolation Policy: [ML_ISOLATION.md](ML_ISOLATION.md)

## Contact

For DACT compliance verification or formal verification collaboration, please open an issue on GitHub or contact the ExoArmur maintainers.
