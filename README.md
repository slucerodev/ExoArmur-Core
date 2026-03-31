# ExoArmur

**ExoArmur is a deterministic execution safety substrate for AI agent systems.**

## Why This Exists

AI agents exhibit nondeterministic behavior - the same agent with the same prompt can produce different outputs across runs or systems. This makes debugging impossible and creates unreproducible failures in production.

ExoArmur fixes this via deterministic replay and verification, ensuring byte-for-byte identical execution across any environment.

## Architecture

ExoArmur has a 3-layer architecture with strict separation:

### 🔧 Core Engine (`src/exoarmur/`)
**Production-grade deterministic execution system**
- **Deterministic replay**: 100% reproducible execution with byte-for-byte identical outputs
- **Safety enforcement**: Kill switches, approvals, and tenant isolation
- **Audit & replay**: Complete traceability with cryptographic evidence
- **Consensus verification**: Multi-node agreement verification
- **Status**: ✅ Production ready, 78/78 tests passing

### 🧪 V2 Experimental (`src/exoarmur/execution_boundary_v2/`)
**Feature-flagged experimental autonomy boundary**
- **Execution boundary**: Action intent → policy decision → execution dispatch
- **Operator approval**: Human-in-the-loop decision gates
- **Mock executors**: Test implementations for development
- **Status**: 🧪 Experimental, behind feature flags (default OFF)

### 📊 Scripts & Validation (`scripts/`)
**Demo, validation, and infrastructure tools**
- **`demo/`**: System demos and examples
- **`validation/`**: External validation and positioning tests
- **`infra/`**: Determinism checking and verification tools
- **`experiments/`**: Production drift demos and research experiments
- **Status**: 🛠️ Development tools, non-production

## Execution Model

1. **Input**: Security event or telemetry data
2. **Analysis**: Deterministic fact derivation and belief formation
3. **Safety**: Multi-layer safety gates with approval requirements
4. **Execution**: Action dispatch with complete audit trail
5. **Verification**: Replay verification and consensus agreement

## Quick Start

```bash
# Install ExoArmur
pip install -e .

# Run core deterministic test
export PYTHONHASHSEED=0
python3 -m pytest tests/test_invariants.py

# Run production drift demo (shows the problem)
python3 scripts/experiments/production_drift_presentation.py
```

## Golden Path - See Execution Divergence in Action

**Run this to see execution divergence and how ExoArmur verifies it:**

```bash
python3 scripts/experiments/production_drift_presentation.py
```

This demo shows:
- Same AI agent with same prompt
- Different execution outcomes (production drift)
- How ExoArmur detects and verifies the divergence
- Why this matters for production AI systems

## Determinism Guarantees

- **Same inputs → Same outputs**: Byte-for-byte identical across runs
- **No wall-clock dependencies**: Uses deterministic timestamp generation
- **Stable hashing**: SHA-256 hashes remain constant across executions
- **Replay verification**: Complete execution reconstruction without side effects

## Feature Flags

All V2 capabilities are behind strict feature flags:

```bash
# Enable V2 restrained autonomy
export EXOARMUR_FLAG_V2_RESTRAINED_AUTONOMY_ENABLED=true

# Enable federation
export EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true
```

## Testing

```bash
# Core deterministic tests
export PYTHONHASHSEED=0
pytest tests/test_invariants.py

# V2 experimental tests
pytest tests/test_v2_restrained_autonomy.py

# Integration tests
pytest tests/test_integration.py
```

## What Runs Deterministically

- ✅ **Core replay engine**: 100% reproducible execution
- ✅ **Safety enforcement**: Deterministic kill switches and approvals
- ✅ **Audit trails**: Complete traceability with stable hashes
- ✅ **Consensus verification**: Multi-node agreement verification

## What Is Experimental

- 🧪 **V2 execution boundary**: Behind feature flags (default OFF)
- 🧪 **Autonomy pipeline**: Operator approval workflows
- 🧪 **Mock executors**: Test implementations

## What Is Demo/Validation

- 🛠️ **Production drift demos**: Research experiments
- 🛠️ **External validation**: Positioning and clarity tests
- 🛠️ **Infrastructure tools**: Determinism checking and verification

## License

[License information]

## Contributing

[Contributing guidelines]
