# ExoArmur 3.0

Autonomous Defense Mesh Organism (ADMO)

ExoArmur is an enterprise-grade autonomous defense/orchestration platform implemented as a distributed mesh of autonomous cells. This repository contains the ExoArmur 3.0 codebase (V1 contracts are stable; V2 federation scaffolding is additive and feature-flagged).

**Status: v1.0.0-beta - Phase 6 Certified**

Project site (GitHub Pages): https://CYLIX-V2.github.io/ExoArmur-3.0

## 🚨 Repository Hygiene Notice
- **Runtime state** (data/, artifacts/reality_run_*/) is generated locally, not stored in Git
- **Evidence bundles** are reproducible via `scripts/phase6_final_reality_run.py`
- Repository is optimized for public cloning with minimal size
- See `RELEASE_REPRODUCIBILITY.md` for complete regeneration instructions

Overview

- Cognition pipeline: TelemetryEventV1 → SignalFactsV1 → BeliefV1 → CollectiveConfidence → SafetyGate → ExecutionIntentV1 → AuditRecordV1
- Design goals: deterministic behavior, auditable decision trails, human-in-the-loop for critical actions, and strict governance for changes.

Quick start

```bash
# Run verification checks
make verify

# Run tests
make test

# Run a specific test
python3 -m pytest tests/test_constitutional_invariants.py -v
```

Demo (V2 restrained autonomy)

```bash
# Run the V2 demo (feature flags may be required)
python3 scripts/demo_v2_restrained_autonomy.py
```

Repository structure

- src/ - implementation code (federation scaffolding, controllers)
- spec/contracts/ - canonical ADMO contract schemas and models
- tests/ - test suite and acceptance gates
- docs/ - documentation site (published to GitHub Pages)

Publishing the docs

This repository is configured to publish the contents of the `docs/` folder to GitHub Pages via an Actions workflow. After pushing to the `main` branch the site should publish automatically; allow a minute for the workflow to complete.

Contributing

- V1 contracts are immutable
- V2 work must be additive and feature-flagged (default OFF)
- All changes require tests and must preserve constitutional invariants described in the docs

License

[License information to be added]