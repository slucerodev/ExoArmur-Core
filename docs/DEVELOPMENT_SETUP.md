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
