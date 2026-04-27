# Contributing to ExoArmur Core

## Contribution Policy

ExoArmur Core is proprietary software. Contributions are accepted only by written agreement.

### Authorized Contributors

If you have a written agreement to contribute:

1. Ensure all changes pass the full test suite: `python -m pytest -q`
2. Verify CLI functionality: `exoarmur --version` and `exoarmur demo --operator-decision deny`
3. Check that no architectural invariants are violated
4. Update documentation if applicable
5. Submit changes through the agreed-upon review process

### IP and Licensing

All submitted changes require explicit IP/licensing agreement before acceptance. Without a signed agreement, contributions cannot be accepted.

## Development Setup (For Authorized Evaluators)

### Prerequisites
- Python 3.10+
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

### Test Expectations
- All tests should pass; use the live CI output as the source of truth for current totals
- Some tests are intentionally skipped with documented justification
- Expected failures (xfailed) are documented and acceptable

## Architecture Safety Rules

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

## Architecture Resources

### Key Documents
- `docs/ARCHITECTURE.md` - High-level architecture overview
- `docs/GOVERNANCE.md` - Governance model details
- `docs/PHASE_STATUS.md` - Current development phase status

### Understanding the Codebase
- Start with `src/exoarmur/cli.py` for CLI interface
- Review `src/exoarmur/core/` for core governance components
- Check `spec/contracts/` for contract definitions
