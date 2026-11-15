# ExoArmur Development Setup

This guide covers setting up a clean development environment for ExoArmur ADMO V2.

## Prerequisites

- Python 3.8+ (tested with Python 3.12)
- Git
- Virtual environment tool (venv recommended)

## Clean Environment Setup

### 1. Create Clean Virtual Environment

```bash
# Create new venv
python3 -m venv exoarmur-dev

# Activate it
source exoarmur-dev/bin/activate  # Linux/Mac
# or
exoarmur-dev\Scripts\activate     # Windows
```

### 2. Install ExoArmur in Editable Mode

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd exoarmur

# Install in editable mode
pip install -e .
```

This installs:
- All dependencies from pyproject.toml
- The exoarmur package in editable mode
- Command-line tools and scripts

### 3. Verify Installation

```bash
# Test core imports
python3 -c "from spec.contracts.models_v1 import TelemetryEventV1; print('✅ Imports work')"

# Run verification
python3 scripts/verify_all.py
```

Note: phase6_final_reality_run performs a boundary guard preflight to enforce repository hygiene.

## Test Suites

ExoArmur defines three explicit test suites (see docs/TEST_SUITES.md):

### verify_core
Fast constitutional tests that must always pass.
```bash
python3 -m pytest tests/ -m "not integration and not slow"
```

### verify_all  
Full test suite with no ignores. Primary CI gate.
```bash
python3 -m pytest tests/
```

### verify_integration
Tests requiring external systems only.
```bash
python3 -m pytest tests/ -m integration
```

## Running from Any Directory

After `pip install -e .`, all scripts work from any working directory:

```bash
# From any directory
python3 -m exoarmur.scripts.verify_all

# Or directly if scripts/ is in PATH
verify_all.py

# Run demos as modules
python3 -m exoarmur.demos.handshake_demo
python3 -m exoarmur.demos.visibility_demo
```

## Development Workflow

### 1. Make Changes
Edit code in the `src/` directory.

### 2. Run Tests
```bash
# Quick feedback
python3 -m pytest tests/ -m "not integration and not slow"

# Full validation  
python3 scripts/verify_all.py
```

### 3. Check Import Sanity
```bash
python3 -c "
from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1
from src.audit import AuditInterface
from src.federation import FederateIdentityStore
print('✅ Core imports work')
"
```

## Package Structure

```
exoarmur/
├── src/                 # Source code (Python packages)
│   ├── audit/          # Audit interfaces
│   ├── federation/     # Federation components  
│   ├── safety/         # Safety gates
│   └── ...
├── tests/              # Test suite
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── spec/               # Contracts and schemas
└── pyproject.toml      # Package configuration
```

## Import Patterns

Use absolute imports from package root:

```python
# ✅ Good - absolute imports
from src.federation import FederateIdentityStore
from spec.contracts.models_v1 import TelemetryEventV1

# ❌ Bad - relative imports
from ..federation import FederateIdentityStore
```

## Troubleshooting

### Import Errors
```bash
# Ensure editable install is current
pip install -e .

# Check package discovery
python3 -c "import exoarmur; print(exoarmur.__file__)"
```

### Test Collection Issues
```bash
# Verify pytest can find tests
python3 -m pytest --collect-only -q

# Should show: 417 tests collected
```

### Path Issues
Never use PYTHONPATH hacks. All imports should work after editable install.

## CI/CD Integration

The CI pipeline uses:
```bash
pip install -e .
python3 scripts/verify_all.py
```

This is equivalent to the `verify_all` test suite.

## Next Steps

1. Run `python3 scripts/verify_all.py` to verify setup
2. Check docs/TEST_SUITES.md for test suite details  
3. Review the code in `src/` to understand the architecture
4. Start with `verify_core` tests for quick feedback during development

## Governed Execution: Authentication & Operator Policy (Pilot)

Execution-capable endpoints require an API key and an operator-approved,
digest-pinned policy. There are no default or test credentials in the
application path — configure both before use.

### Environment variables

| Variable | Purpose |
|---|---|
| `EXOARMUR_API_KEY_STORE` | Path to JSON file of API key records (SHA-256 hashes only) |
| `EXOARMUR_POLICY_FILE` | Path to versioned operator policy JSON (operator-controlled) |
| `EXOARMUR_POLICY_SHA256` | Operator-pinned SHA-256 of the policy file bytes |
| `EXOARMUR_OPERATOR_TRUST_SCORE` | Configured trust (0.0–1.0) for the pilot principal — not a measured score |
| `NATS_URL` | NATS server for durable kill-switch state (default `nats://localhost:4222`) |

### 1. Bootstrap one principal

```bash
python examples/bootstrap_api_key.py \
    --key-id pilot-key-1 \
    --principal-id agent-001 \
    --tenant-id tenant-1 \
    --permission execute:A0 --permission execute:A1 \
    --permission approval:request --permission approval:grant \
    --permission approval:deny --permission status:view \
    --store /etc/exoarmur/api_keys.json
```

The raw key is printed once — store it in your secret manager. The store
file contains only hashes.

### 2. Install the operator policy

Write the policy file (see `src/exoarmur/policy/operator_policy.py` for the
schema: `version`, `rules[]` with `tenant_id`, `principal_id`, `operations`,
`action_classes`, `required_approval`), then pin its digest:

```bash
sha256sum /etc/exoarmur/policy.json
export EXOARMUR_POLICY_FILE=/etc/exoarmur/policy.json
export EXOARMUR_POLICY_SHA256=<digest-from-sha256sum>
export EXOARMUR_API_KEY_STORE=/etc/exoarmur/api_keys.json
export EXOARMUR_OPERATOR_TRUST_SCORE=0.9
```

Any edit to the policy file without updating the pinned digest denies all
policy-governed execution. Missing/invalid policy or credentials fail
explicitly before execution.

### 3. Make an authenticated request

```bash
curl -X POST http://localhost:8000/v1/telemetry/ingest \
    -H "Content-Type: application/json" \
    -H "X-API-Key: <RAW-KEY-FROM-STEP-1>" \
    -d '{
      "schema_version": "1.0.0",
      "event_id": "<ULID>",
      "tenant_id": "tenant-1",
      "cell_id": "cell-1",
      "observed_at": "2025-01-01T00:00:00Z",
      "received_at": "2025-01-01T00:00:00Z",
      "source": {"kind": "edr", "name": "test", "host": "h1", "sensor_id": "s1"},
      "event_type": "process_start",
      "severity": "low",
      "attributes": {"process_name": "notepad.exe"},
      "correlation_id": "corr-1",
      "trace_id": "trace-1"
    }'
```

Approval actions use the same header; `operator_id` in the request body
must equal the authenticated principal or the request is rejected:

```bash
curl -X POST http://localhost:8000/v1/approvals/<approval_id>/approve \
    -H "X-API-Key: <RAW-KEY>" \
    -H "Content-Type: application/json" \
    -d '{"operator_id": "agent-001"}'
```

Permissions: `execute:A0`–`execute:A3` gate dispatch per resolved action
class; `approval:request` gates approval creation; `approval:grant` /
`approval:deny` gate approval decisions; `status:view` gates status reads.
