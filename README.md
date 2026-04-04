# ExoArmur

**A deterministic execution governance substrate for AI systems that enforces verifiable causal integrity across decision and action pipelines.**

## Problem Statement

AI systems exhibit unpredictable execution behavior and lack auditable decision paths. The same input can produce different actions across runs, making it impossible to verify system behavior, debug failures, or prove compliance. This unpredictability creates fundamental trust issues in production environments where reproducible execution and audit trails are essential.

## What ExoArmur Is

ExoArmur is a governance and execution control layer that creates deterministic, traceable AI system behavior. It enforces policy constraints, captures causal execution traces, and provides replayable execution logs for verification.

ExoArmur treats AI behavior as an executable, verifiable process rather than a black-box response system. Every action passes through a governed execution boundary that records intent, validates against constraints, and generates cryptographically verifiable audit trails.

## Core Capabilities

- **Controlled execution under policy constraints**: All AI actions validated against defined governance rules before execution
- **Deterministic execution traces**: Causal ordering of system actions captured with cryptographic integrity
- **Causal ordering of system actions**: Complete decision pipeline traceability from input to outcome
- **Replayable execution for verification**: Exact reconstruction of execution behavior under identical conditions
- **Audit-grade observability**: Complete decision pipeline visibility with tamper-evident records

## Architecture

### Core Engine (`src/exoarmur/`)
Stable deterministic execution system with trace generation. Provides the foundation for governed execution, safety enforcement, and audit trail maintenance. All core functionality verified with comprehensive test coverage.

### Experimental Layer (`src/exoarmur/execution_boundary_v2/`)
Optional extensions strictly isolated behind feature flags. Tests advanced governance patterns including human approval gates and complex decision pipelines. Disabled by default.

### Tooling Layer (`scripts/`, `demo/`)
Demos, validation scripts, and test harnesses. Provides system validation, performance testing, and educational examples of governance patterns.

## Quickstart

```bash
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
./scripts/quickstart.sh
```

```bash
exoarmur demo --scenario canonical
```

```bash
exoarmur proof
```

## Demo Flow

1. **Initialize system**: Load governance rules and establish execution boundary
2. **Run canonical scenario**: Execute controlled AI actions under policy constraints
3. **Inspect execution trace**: Review causal ordering and decision validation
4. **Verify replay consistency**: Confirm deterministic behavior under identical conditions

## Guarantees / Invariants

- **Execution traces are reconstructible** under identical inputs and constraints
- **System preserves causal ordering** of all actions and decisions
- **Execution is fully auditable** after completion with cryptographic proofs
- **Replay produces verifiable deterministic behavior** under defined conditions

## Positioning / System Class

ExoArmur is an execution governance substrate that provides deterministic control plane capabilities for AI systems. It operates as a causal trace and verification layer, ensuring that AI system behavior is reproducible, auditable, and verifiable under defined governance constraints.

## System Positioning

ExoArmur is a deterministic execution safety substrate that provides byte-for-byte reproducible execution guarantees for AI agent systems through causal traceability and safety gate enforcement.

**Core Identity**: Deterministic layer that ensures identical execution across environments
**Trust Primitive**: Proof Mode provides verifiable deterministic validation  
**Boundaries**: Core engine (stable implementation) vs V2 experimental features
**Guarantees**: Byte-for-byte execution, complete audit trails, safety gate enforcement

[See detailed positioning](docs/POSITIONING.md)

## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contributing

[Contributing guidelines]
