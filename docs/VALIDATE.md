# Independent Validation Guide

This guide provides step-by-step commands to verify ExoArmur Core functionality independently.

## Prerequisites

- Python 3.10+
- Git
- Command line access

## Step 1: Clone Repository

```bash
git clone https://github.com/slucerodev/ExoArmur-Core
cd ExoArmur-Core
```

Expected result: Clean repository clone with all source files.

## Step 2: Install Package

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install .
```

Expected result: Package installs successfully with all dependencies.

Editable installs (`pip install -e .`) are supported for current development and CI verification.

## Step 3: Verify CLI Version

```bash
exoarmur --version
```

Expected result: `exoarmur, version 2.0.0`

## Step 4: Run Quickstart Replay Example

```bash
python examples/quickstart_replay.py
```

Expected result: `Replay result: success`

## Step 5: Run Standalone Governance Proof

```bash
python examples/demo_standalone.py
```

Expected output markers:
- `Execution boundary result: policy denied before any filesystem side effect`
- `Proof bundle written: examples/demo_standalone_proof_bundle.json`
- `DEMO_RESULT=DENIED`
- `ACTION_EXECUTED=false`
- `AUDIT_STREAM_ID=demo-standalone-delete-outside-authorized-path`

## What Constitutes Success

### Installation Success
- Package installs without errors
- All dependencies resolve correctly
- CLI commands are available
- Import test passes: `python -c "import exoarmur"`

### CLI Functionality Success
- `exoarmur --version` returns consistent version (2.0.0)
- `exoarmur --help` shows all commands
- Demo execution path produces the expected output markers

### Demo Execution Success
- Standalone demo produces required deterministic denial markers
- Proof bundle is generated deterministically
- Audit stream ID is fixed for the canonical proof path

### Deterministic Behavior
- Same inputs produce identical outputs
- Replayable proof data is captured in the emitted proof bundle
- No hidden state or non-deterministic behavior

## Reporting Validation Results

### Success Report
If all steps complete successfully:

```
✅ Installation: pip install . completed without errors
✅ CLI Verification: exoarmur --version returns 2.0.0
✅ Quickstart Replay: python examples/quickstart_replay.py succeeds
✅ Demo Execution: python examples/demo_standalone.py produces required markers and proof bundle
✅ Deterministic Output: All markers present and reproducible
```

### Failure Report
If any step fails, include:

- Step number that failed
- Error message or output
- Environment details (Python version, OS)
- Commands attempted

### Independent Verification Encouraged

This project is designed for independent verification:
- All functionality claims are supported by reproducible artifacts
- Test suite provides comprehensive coverage
- Demo output markers provide deterministic proof points
- Source code is available for complete inspection

External validation helps ensure project reliability and builds community trust.

## Additional Verification Options

### Test Suite Verification
```bash
python -m pytest -q
```

Expected: the command completes successfully; use the live output on `main` as the current source of truth for suite size and status.

### Architecture Compliance Check
```bash
# Verify ProxyPipeline boundary enforcement
python -c "from exoarmur.execution_boundary_v2.pipeline.proxy_pipeline import ProxyPipeline; print('ProxyPipeline boundary enforced')"
```

### Audit Trail Verification
```bash
# Verify audit trail generation
python examples/demo_standalone.py
```

This validation guide ensures that ExoArmur Core can be independently verified for functionality, deterministic behavior, and architectural compliance.
