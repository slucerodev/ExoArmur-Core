# ExoArmur ADMO Runbook

## Local Setup Prerequisites

### System Requirements
- Python 3.12+
- NATS JetStream server (for live Golden Demo)
- Git

### Dependencies
```bash
# Clone repository
git clone <repository-url>
cd ExoArmur

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### NATS JetStream Setup
```bash
# Start NATS with JetStream enabled
docker run -d --name nats -p 4222:4222 -p 8222:8222 \
  nats:latest -js -m 8222

# Or using docker-compose (included in repo)
docker-compose up -d
```

## Validation Suite

### Run All Tests
```bash
source venv/bin/activate
pytest -q
```

**Expected output:**
```
59 passed, 15 xfailed, 155 warnings in X.XXs
```

### Run V1 Golden Demo (Live)
```bash
source venv/bin/activate
pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

**Expected output:**
```
=========================== 1 passed, X warnings in X.XXs ===========================
```

### Run Spec Reference Validation
```bash
source venv/bin/activate
python scripts/validate_spec_refs.py
```

**Expected output:**
```
✓ All spec references validated successfully!
```

### Run Spec Integrity Audit
```bash
source venv/bin/activate
python scripts/audit_integrity.py
```

**Expected output:**
```
🎉 SPEC READY - All audit checks passed!
```

## Interpreting Results

### Green Status
**All commands must show:**
- **pytest**: 0 failed, 0 errors, 0 skipped
- **validate_spec_refs.py**: "All spec references validated successfully!"
- **audit_integrity.py**: "SPEC READY - All audit checks passed!"

### Red Status - Troubleshooting

#### Test Failures
```bash
# Run with verbose output to see failure details
pytest -v --tb=short

# Run specific failing test
pytest tests/path/to/failing_test.py::test_name -v --tb=long
```

**Common causes:**
- NATS JetStream not running (for Golden Demo)
- Dependencies not installed
- Code changes breaking existing functionality

#### Spec Validation Failures
```bash
# Check spec file syntax
python -c "import yaml; yaml.safe_load(open('docs/specs/EXOARMUR_MASTER_SPEC.yaml'))"

# Check referenced files exist
python scripts/validate_spec_refs.py
```

**Common causes:**
- Missing contract files
- Invalid YAML syntax
- Broken reference paths

#### Audit Integrity Failures
```bash
# Run audit with detailed output
python scripts/audit_integrity.py
```

**Common causes:**
- Missing required keys in contracts
- Invalid arbitration order
- V1 scope lock violations

## V2 Feature Flag Verification

### Confirm V2 Remains Inert
```bash
source venv/bin/activate
pytest tests/test_v2_feature_flag_isolation.py -v
```

**Expected output:**
```
================================= 7 passed in X.XXs =================================
```

### Check Feature Flag State
```bash
source venv/bin/activate
python -c "
from src.feature_flags import get_feature_flags
flags = get_feature_flags()
print('V2 Federation:', flags.is_v2_federation_enabled())
print('V2 Control Plane:', flags.is_v2_control_plane_enabled())
print('V2 Operator Approval:', flags.is_v2_operator_approval_required())
"
```

**Expected output:**
```
V2 Federation: False
V2 Control Plane: False  
V2 Operator Approval: False
```

## Development Workflow

### Before Making Changes
1. Run full validation suite to ensure green baseline
2. Create feature branch from main
3. Make changes following governance policies

### After Making Changes
1. Run full validation suite
2. Verify V2 isolation tests still pass
3. Confirm Golden Demo still passes
4. Submit pull request with validation results

### Common Development Commands

```bash
# Run tests continuously during development
pytest -f  # Watch mode

# Run tests with coverage
pytest --cov=src --cov-report=html

# Check code formatting
black --check src/ tests/
isort --check-only src/ tests/

# Type checking
mypy src/
```

## Production Deployment

### Pre-deployment Checklist
- [ ] Full validation suite passes
- [ ] V2 feature flags confirmed disabled
- [ ] Golden Demo passes in production-like environment
- [ ] No pytest.skip in codebase
- [ ] All xfail have proper reasons
- [ ] Spec validation passes
- [ ] Audit integrity passes

### Deployment Commands
```bash
# Validate production readiness
source venv/bin/activate
pytest -q
python scripts/validate_spec_refs.py
python scripts/audit_integrity.py

# Check V2 isolation
pytest tests/test_v2_feature_flag_isolation.py -v

# Verify Golden Demo
pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

## Emergency Procedures

### Golden Demo Failure
1. **Immediate**: Rollback last changes
2. **Investigate**: Run Golden Demo with verbose output
3. **Fix**: Address root cause before proceeding
4. **Validate**: Full validation suite must pass

### V2 Interference Detected
1. **Immediate**: Disable all V2 feature flags
2. **Investigate**: Run V2 isolation tests
3. **Fix**: Remove interfering V2 code
4. **Validate**: Confirm V1 immutability preserved

## Monitoring

### Health Checks
- Golden Demo execution time < 30 seconds
- Test suite execution time < 2 minutes
- Zero skipped tests in any run
- V2 feature flags remain disabled by default

### Alerts
- Any pytest.skip occurrence
- Any skipped test in CI/CD
- Golden Demo failure
- V2 isolation test failure
- Spec validation failure

This runbook ensures ExoArmur ADMO operates reliably and safely while maintaining strict governance compliance.
