# ExoArmur

**ExoArmur is a deterministic execution safety substrate for AI agent systems.**

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
python3 -m pytest tests/test_invariants.py

# Run V2 demo (requires feature flags)
EXOARMUR_V2_ENABLED=true python3 scripts/demo/demo_v2_restrained_autonomy.py

# Run production drift experiment
python3 scripts/experiments/production_drift_demo.py
```

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
pytest tests/test_invariants.py

# V2 experimental tests
pytest tests/test_v2_restrained_autonomy.py

# Integration tests
pytest tests/test_integration.py
```

## License

[License information]

## Contributing

[Contributing guidelines]
