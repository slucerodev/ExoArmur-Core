# ExoArmur

**ExoArmur is a deterministic execution safety substrate for AI agent systems.**

## System Overview

ExoArmur ensures that AI agent systems produce identical results across any environment or execution. It provides byte-for-byte reproducible execution with complete audit trails, allowing you to verify exactly what your system did and when.

**What it enables**: Run AI agents with deterministic guarantees, verify execution integrity, and maintain cryptographically auditable evidence of all system actions.

## Why This Exists

AI agents naturally exhibit nondeterministic behavior - the same agent with the same prompt can produce different outputs across runs. This makes debugging impossible and creates unreproducible failures in real deployments.

ExoArmur fixes this through deterministic replay and verification, ensuring byte-for-byte identical execution across any environment while maintaining complete causal traceability of all actions.

## Get Started in 60 Seconds

### Step 1: Setup

```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
./scripts/quickstart.sh
```

*This sets up the environment and verifies core functionality.*

### Step 2: Trust Validation

```bash
exoarmur proof
```

*This single command proves ExoArmur works deterministically. The same replay hash appears every time, providing cryptographic proof of system correctness.*

**Expected outcome**: You'll see a structured "PROOF COMPLETE" output with a stable replay hash that remains constant across executions.

### Step 3: Deep Exploration

```bash
exoarmur demo --scenario canonical
```

*This demonstrates full system capabilities with policy enforcement and replay verification.*

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

## Entry Points

- **[Quickstart Guide](QUICKSTART.md)** - Detailed setup and execution steps
- **[System Positioning](docs/POSITIONING.md)** - Complete system boundaries and guarantees

## License

[License information]

## Contributing

[Contributing guidelines]
