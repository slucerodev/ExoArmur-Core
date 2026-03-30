# Contributing to ExoArmur Core

## Project Philosophy

ExoArmur Core is built on three fundamental principles:

### Determinism
- Same inputs must always produce identical outputs
- All execution paths must be replayable and verifiable
- No hidden state or non-deterministic behavior in core components

### Governance
- ProxyPipeline is the sole execution boundary for all actions
- Executors are untrusted capability modules treated as external components
- All decisions must produce verifiable audit trails

### Invariant Protection
- V1 contracts and Golden Demo behavior are locked by repository policy and regression gates
- CI invariant gates enforce architectural guarantees
- No weakening of assertions or bypassing of safety checks

## Development Setup

### Prerequisites
- Python 3.8+
- Git
- Docker (optional, for live demos)

### Installation
```bash
# Clone the repository
git clone https://github.com/slucerodev/ExoArmur-Core
cd ExoArmur-Core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install .
```

### Development Installation
```bash
# Install with development dependencies
pip install ".[dev]"
```

### Editable Installs - Important Notice

**Editable installs (`pip install -e .`) are supported and are part of the current validation flow.**

**Recommended development workflow:**
1. Make changes to source code
2. Install in editable mode: `pip install -e .` or `pip install -e ".[dev]"`
3. Run tests to verify changes
4. Commit changes when tests pass

**Testing changes:**
```bash
# After making changes, reinstall and test
pip install -e .
python -m pytest -q
exoarmur demo --operator-decision deny
```

## Running Tests

### Full Test Suite
```bash
python -m pytest -q
```

### Specific Test Categories
```bash
# Core functionality tests
python -m pytest tests/test_replay_determinism.py tests/test_safety_gate.py tests/test_boundary_enforcement.py

# V2 feature tests
python -m pytest tests/test_v2_restrained_autonomy.py

# Golden demo tests (optional; requires Docker and NATS JetStream)
EXOARMUR_LIVE_DEMO=1 python -m pytest tests/test_golden_demo_live.py::test_golden_demo_flow_live_jetstream -v
```

### Test Expectations
- All tests should pass; use the live CI output as the source of truth for current totals
- Some tests are intentionally skipped with documented justification
- Expected failures (xfailed) are documented and acceptable

## Submitting Pull Requests

### Before Submitting
1. Ensure all tests pass: `python -m pytest -q`
2. Verify CLI functionality: `exoarmur --version` and `exoarmur demo --operator-decision deny`
3. Check that no architectural invariants are violated
4. Update documentation if applicable

### PR Process
1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes following the coding expectations below
4. Ensure all tests pass
5. Submit a pull request with:
   - Clear description of changes
   - Reasoning for architectural decisions
   - Test results summary

### PR Review Criteria
- No breaking changes to V1 contracts or behavior
- All tests passing (including new tests for new functionality)
- Documentation updated if needed
- Architectural invariants preserved
- No weakening of assertions or safety checks

## Coding Expectations

### Architecture Safety Rules

**CRITICAL: These rules must never be violated**

1. **ProxyPipeline is the sole execution boundary**
   - All actions must pass through ProxyPipeline.execute_with_trace()
   - No direct executor invocation or bypass of governance controls
   - No real-world side effects outside the governance path

2. **Executors must remain untrusted modules**
   - Executors receive only ActionIntent objects
   - Executors return only ExecutorResult objects
   - Executors cannot access governance components or modify traces

3. **Deterministic execution must not be violated**
   - Same inputs must always produce identical outputs
   - No hidden state or non-deterministic behavior
   - All audit trails must be replayable

4. **CI invariant gates must pass**
   - All automated checks must pass
   - No weakening of assertions or test skips
   - Golden Demo behavior must remain unchanged

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for public functions and classes
- Keep functions focused and small

### Testing
- Add tests for new functionality
- Ensure test coverage for critical paths
- Use deterministic test data
- No mocking of core governance components

### Documentation
- Update README.md for user-facing changes
- Update relevant docs/ files for architectural changes
- Add inline documentation for complex logic

## Feature Development

### V2 Development
- V2 features must be feature-flagged with default OFF
- V2 must be additive and non-invasive to V1
- No cross-boundary imports from V2 to V1
- V2 features must be isolated and optional

### Adding New Features
1. Determine if feature belongs in Core or as optional module
2. For Core features: ensure V1 compatibility and add proper tests
3. For V2 features: implement with feature flags and isolation
4. Update documentation and examples
5. Verify all invariant gates pass

## Getting Help

### Questions
- Open an issue for questions about contributing
- Check existing issues and documentation first
- Be specific about your use case and constraints

### Bug Reports
- Include reproduction steps
- Include environment details (Python version, OS)
- Include test output if applicable
- Follow the template in the issue tracker

### Security Issues
- Do not open public issues for security vulnerabilities
- See SECURITY.md for responsible disclosure process

## Architecture Resources

### Key Documents
- `docs/ARCHITECTURE.md` - High-level architecture overview
- `docs/GOVERNANCE.md` - Governance model details
- `OPEN_CORE_BOUNDARIES.md` - Core vs module boundaries
- `docs/PHASE_STATUS.md` - Current development phase status

### Understanding the Codebase
- Start with `src/exoarmur/cli.py` for CLI interface
- Review `src/exoarmur/core/` for core governance components
- Examine `tests/test_v2_restrained_autonomy.py` for V2 patterns
- Check `spec/contracts/` for contract definitions

## Review Process

All contributions are reviewed for:
1. **Architectural compliance** - Does it respect invariants?
2. **Determinism** - Is execution deterministic and replayable?
3. **Test coverage** - Are changes properly tested?
4. **Documentation** - Is the change well documented?
5. **Safety** - Does it weaken any security or governance controls?

Thank you for contributing to ExoArmur Core!
