# ExoArmur

**ExoArmur is a deterministic execution safety substrate for AI agent systems.**

## Why This Exists

AI agents exhibit nondeterministic behavior - the same agent with the same prompt can produce different outputs across runs or systems. This makes debugging impossible and creates unreproducible failures in real deployments.

ExoArmur fixes this via deterministic replay and verification, ensuring byte-for-byte identical execution across any environment.

## Get Started in 60 Seconds

### Step 1: Setup (30 seconds)

```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
./scripts/quickstart.sh
```

This automatically:
- Sets up a Python virtual environment
- Installs required dependencies  
- Runs a minimal demo execution
- Shows you the system is working

### Step 2: Trust Validation (15 seconds)

```bash
exoarmur proof
```

**Expected output:**
```
EXOARMUR PROOF MODE
====================

Scenario: canonical
Execution Mode: deterministic
Tenant: exoarmur-core

RESULT:
- Decision: DENIED
- Action Executed: False
- Replay Hash: 854bcac0688515227d560022eedae4d0abd0a2c268694a4a4f89a9bd8b69d3c0
- Correlation ID: <uuid>

VERDICT:
PROOF COMPLETE
```

This single command proves ExoArmur works deterministically. The same replay hash appears every time.

### Step 3: Deep Exploration (15 seconds)

```bash
exoarmur demo --scenario canonical
```

This demonstrates full system capabilities with policy enforcement and replay verification.

**That's it.** You now have a working ExoArmur system with deterministic guarantees.

---

## System Positioning

ExoArmur is a deterministic execution safety substrate that provides byte-for-byte reproducible execution guarantees for AI agent systems through causal traceability and safety gate enforcement.

**Core Identity**: Deterministic layer that ensures identical execution across environments
**Trust Primitive**: Proof Mode provides verifiable deterministic validation  
**Boundaries**: Core engine (stable implementation) vs V2 experimental features
**Guarantees**: Byte-for-byte execution, complete audit trails, safety gate enforcement

[See detailed positioning](docs/POSITIONING.md)

---

## Architecture

ExoArmur has a 3-layer architecture with strict separation:

### 🔧 Core Engine (`src/exoarmur/`)
**Deterministic execution system**
- **Deterministic replay**: 100% reproducible execution with byte-for-byte identical outputs
- **Safety enforcement**: Kill switches, approvals, and tenant isolation
- **Audit & replay**: Complete traceability with cryptographic evidence
- **Consensus verification**: Multi-node agreement verification
- **Status**: ✅ Core functionality verified, 78/78 tests passing

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
- **`experiments/`**: System behavior demos and research experiments
- **Status**: 🛠️ Development tools, for testing and validation

## Execution Model

1. **Input**: Security event or telemetry data
2. **Analysis**: Deterministic fact derivation and belief formation
3. **Safety**: Multi-layer safety gates with approval requirements
4. **Execution**: Action dispatch with complete audit trail
5. **Verification**: Replay verification and consensus agreement

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

- 🛠️ **System behavior demos**: Research experiments
- 🛠️ **External validation**: Positioning and clarity tests
- 🛠️ **Infrastructure tools**: Determinism checking and verification

## License

[License information]

## Contributing

[Contributing guidelines]
