# Demo Script

*Prepared for: Prospective Acquirers and Strategic Buyers*
*Date: June 1, 2026*
*Version: 2.1.0*

## Overview

This script provides a step-by-step demonstration of ExoArmur-Core capabilities for acquisition evaluation.

## Prerequisites

### System Requirements
- Python 3.10 or later
- Linux, macOS, or Windows
- 50MB disk space
- Terminal/command line access

### Installation

```bash
# Clone the repository
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install ExoArmur-Core
pip install -e .
```

## Demo Steps

### Step 1: Health Check

Verify installation and system health.

```bash
exoarmur health
```

**Expected Output:**
```
✅ ExoArmur Core is healthy
Version: 2.1.0
Python: 3.10+
Deterministic clock: enabled
Plugin registry: active
```

**What This Demonstrates:**
- Successful installation
- Core system health
- Deterministic clock configuration
- Plugin registry functionality

### Step 2: CLI Help

Explore available commands.

```bash
exoarmur --help
```

**Expected Output:**
```
Usage: exoarmur [OPTIONS] COMMAND [ARGS]...

  ExoArmur Core — deterministic governance and replayable audit layer

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  demo        Run demonstration scenarios
  evidence    Evidence pack operations
  health      Quick health check
  proof       Run deterministic proof mode
  verify-all  Run complete system verification
```

**What This Demonstrates:**
- CLI interface
- Available commands
- Command structure

### Step 3: Run Demo Scenarios

Execute built-in demonstration scenarios.

```bash
exoarmur demo
```

**Expected Output:**
```
Running ExoArmur Core demonstration...

Scenario 1: FileSystemExecutor - Allow
✅ Action allowed: /tmp/demo_file.txt
✅ Audit trail generated
✅ Replay verification passed

Scenario 2: FileSystemExecutor - Deny
✅ Action denied: /etc/passwd
✅ Safety gate triggered
✅ Audit trail generated

Scenario 3: DatabaseExecutor - Allow
✅ Action allowed: INSERT INTO users
✅ Transaction rollback available
✅ Audit trail generated

Scenario 4: Replay Verification
✅ Replay verification passed
✅ Deterministic behavior confirmed

Demonstration complete.
```

**What This Demonstrates:**
- FileSystemExecutor governance
- DatabaseExecutor governance
- Policy gate enforcement
- Safety gate enforcement
- Audit trail generation
- Replay verification
- Deterministic behavior

### Step 4: Generate Demo Artifacts

Generate safe public sample data for evaluation.

```bash
python examples/generate_demo_artifacts.py
```

**Expected Output:**
```
Generating demo artifacts...
Generated: manifest.json
Generated: filesystem_allow_trace.json
Generated: filesystem_deny_trace.json
Generated: database_allow_trace.json
Generated: external_effect_replay_verified.json
Generated: external_effect_tamper_detected.json

All artifacts generated in: examples/demo_artifacts
```

**What This Demonstrates:**
- Artifact generation capability
- Evidence structure
- Safe public data generation
- No machine-specific paths
- No secrets or sensitive data

### Step 5: Inspect Demo Artifacts

Review generated artifacts to understand evidence structure.

```bash
# View manifest
cat examples/demo_artifacts/manifest.json

# View filesystem allow trace
cat examples/demo_artifacts/filesystem_allow_trace.json

# View replay verification artifact
cat examples/demo_artifacts/external_effect_replay_verified.json
```

**What This Demonstrates:**
- Evidence schema
- Canonical JSON structure
- Deterministic ID generation
- Cryptographic audit trail structure
- Replay verification evidence

### Step 6: Run Verification

Execute complete system verification.

```bash
exoarmur verify-all
```

**Expected Output:**
```
Running complete system verification...

✅ Deterministic clock: enabled
✅ Plugin registry: active
✅ Core modules: loaded
✅ Executors: registered
✅ Canonical JSON: functional
✅ Replay verification: functional

System verification complete. All checks passed.
```

**What This Demonstrates:**
- Complete system health
- Module loading
- Executor registration
- Canonical JSON functionality
- Replay verification functionality

### Step 7: Run Test Suite

Execute comprehensive test suite.

```bash
python -m pytest tests/ -q -rs
```

**Expected Output:**
```
...
==================== 338 passed, 17 skipped, 0 failed ====================
```

**What This Demonstrates:**
- Test suite execution
- Test coverage (338 tests)
- Known skip categories (17 skips)
- System reliability

### Step 8: Run E2E Tests

Execute end-to-end tests.

```bash
python -m pytest tests/e2e/ -v
```

**Expected Output:**
```
...
====================== 22 passed in 0.30s ======================
```

**What This Demonstrates:**
- E2E test execution
- Integration testing
- Real-world scenario coverage
- System reliability

### Step 9: Run Security Scans

Execute security scanning tools.

```bash
# Bandit SAST
bandit -r src/

# pip-audit (in fresh venv with upgraded pip)
python -m venv /tmp/exoarmur_audit_venv
/tmp/exoarmur_audit_venv/bin/python -m pip install --upgrade pip
/tmp/exoarmur_audit_venv/bin/pip install .
/tmp/exoarmur_audit_venv/bin/pip-audit
```

**Expected Output:**
```
# Bandit
Run started:2026-06-01 00:00:00
Test results:
        No issues identified.

# pip-audit
No known vulnerabilities found
```

**What This Demonstrates:**
- Security scanning capabilities
- SAST coverage
- Dependency vulnerability scanning
- Clean security posture

### Step 10: Inspect Plugin Registry

View registered plugins and executors.

```bash
python -c "from exoarmur.kernel.plugin_registry import PluginRegistry; registry = PluginRegistry(); print('Registered plugins:', registry.list_plugins())"
```

**Expected Output:**
```
Registered plugins: ['exoarmur.pod.default']
```

**What This Demonstrates:**
- Plugin registry functionality
- Plugin discovery
- Extensibility architecture

## Advanced Demo Steps

### Step 11: Custom Executor Integration

Demonstrate custom executor integration (advanced).

```bash
# Create custom executor
cat > my_executor.py << 'EOF'
from exoarmur.executors.base import ExecutorPlugin, ExecutorResult

class MyExecutor(ExecutorPlugin):
    def validate_target(self, target: str) -> bool:
        return target.startswith("/safe/")
    
    def execute(self, intent) -> ExecutorResult:
        return ExecutorResult(success=True, evidence={"custom": True})
EOF

# Register custom executor (conceptual - requires entry point configuration)
# This demonstrates the plugin architecture pattern
```

**What This Demonstrates:**
- Plugin architecture
- Custom executor pattern
- Extensibility

### Step 12: Deterministic Replay

Demonstrate deterministic replay capability.

```bash
# Run an action twice and verify identical results
python -c "
from exoarmur.kernel.clock import DeterministicClock
clock = DeterministicClock()
t1 = clock.utc_now()
clock.advance(seconds=1)
t2 = clock.utc_now()
print(f'Time 1: {t1}')
print(f'Time 2: {t2}')
print(f'Deterministic: {t2 > t1}')
"
```

**Expected Output:**
```
Time 1: 2026-06-01T00:00:00.000000Z
Time 2: 2026-06-01T00:00:01.000000Z
Deterministic: True
```

**What This Demonstrates:**
- Deterministic clock
- Reproducible time
- Determinism guarantees

## Evaluation Criteria

During the demo, evaluate the following:

### Functional Criteria
- [ ] Installation completes without errors
- [ ] Health check passes
- [ ] CLI commands work as expected
- [ ] Demo scenarios execute successfully
- [ ] Demo artifacts generate correctly
- [ ] Test suite passes (338 passed, 17 skipped)
- [ ] E2E tests pass (22 passed)
- [ ] Security scans show no issues

### Technical Criteria
- [ ] Code quality is high (black/isort/mypy clean)
- [ ] Security posture is clean (bandit/pip-audit clean)
- [ ] Architecture is well-organized
- [ ] Documentation is comprehensive
- [ ] Plugin architecture is functional
- [ ] Determinism is verifiable

### Business Criteria
- [ ] Aligns with strategic objectives
- [ ] Fits technical requirements
- [ ] Integration requirements are feasible
- [ ] Resource requirements are acceptable
- [ ] Timeline is acceptable
- [ ] Cost is within budget

## Common Issues and Solutions

### Issue: ModuleNotFoundError
**Solution:** Ensure virtual environment is activated and package is installed with `pip install -e .`

### Issue: Permission denied on file operations
**Solution:** Run demo in a directory where you have write permissions (e.g., /tmp)

### Issue: pip-audit shows vulnerabilities
**Solution:** Ensure pip is upgraded to 26.1.2 in a fresh virtual environment

### Issue: Tests fail
**Solution:** Ensure all dependencies are installed with `pip install -e ".[dev]"`

## Next Steps

After completing the demo:

1. Review generated demo artifacts
2. Inspect source code structure
3. Review documentation (see BUYER_FAQ.md for reference)
4. Assess integration requirements
5. Evaluate build vs buy analysis (BUY_VS_BUILD.md)
6. Proceed to due diligence checklist (DILIGENCE_CHECKLIST.md)

## Contact

For questions about the demo or to request a guided demonstration, contact the repository owner via GitHub.

## Conclusion

This demo script provides a comprehensive overview of ExoArmur-Core capabilities. All steps are designed to be reproducible and verifiable, enabling thorough evaluation for acquisition due diligence.
