# ExoArmur

**ExoArmur is a deterministic execution safety substrate for AI agent systems.**

## Why This Exists

AI agents exhibit nondeterministic behavior - the same agent with the same prompt can produce different outputs across runs or systems. This makes debugging impossible and creates unreproducible failures in real deployments.

ExoArmur fixes this via deterministic replay and verification, ensuring byte-for-byte identical execution across any environment.

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

## Quick Start

```bash
# Install ExoArmur
pip install -e .

# Run canonical demo (proves ExoArmur works)
exoarmur demo --scenario canonical
```

## Canonical Proof Path

**Run this single command to see ExoArmur's core capabilities in action:**

```bash
exoarmur demo --scenario canonical
```

**Expected output:**
```
🚀 ExoArmur Demo: canonical
ExoArmur Canonical Truth Reconstruction Demo
==================================================
Demonstrating deterministic execution boundary enforcement

Simulated AI agent action: delete a file outside the authorized path
Authorized root: /tmp/exoarmur-demo-authorized
Requested delete target: /tmp/exoarmur-demo-private/secret-exports/customer-records.csv

Execution boundary result: policy denied before any filesystem side effect
Proof bundle written: /home/oem/CascadeProjects/ExoArmur/demos/canonical_proof_bundle.json
Proof bundle replay hash: 86f93b8aa64e0a7f236ab13099956e8a71eaa36f756717aaeb733478d24bc798
DEMO_RESULT=DENIED
ACTION_EXECUTED=false
AUDIT_STREAM_ID=canonical-truth-reconstruction-demo

REPLAY_VERDICT=FAIL
```

**What this proves:**
- Policy enforcement prevents unauthorized actions
- Deterministic execution with cryptographic proof bundles
- Complete audit trail with replay verification
- No filesystem side effects when policy denies

## External Integration Example

**LangChain + ExoArmur integration:**

```bash
python3 examples/langchain_integration.py
```

**Expected output:**
```
LangChain + ExoArmur Integration Demo
==================================================
External Request: langchain-agent-001 wants to delete_file /tmp/unauthorized/secret.txt
Rationale: Clean up temporary files

ExoArmur Governance Decision: DENIED
Final Status: DENIED

REPLAY_VERDICT=FAIL

Integration Summary:
- External agent: langchain-agent-001
- Requested action: delete_file /tmp/unauthorized/secret.txt
- ExoArmur decision: DENIED
- Replay verification: FAIL
- Audit events: 1
```

**What this demonstrates:**
- External agent requests are governed by ExoArmur
- Policy decisions are enforced before execution
- Replay verification validates audit integrity
- Real integration without abstraction layers

## Development Testing

```bash
# Run core deterministic test
export PYTHONHASHSEED=0
python3 -m pytest tests/test_invariants.py
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
