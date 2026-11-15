# ExoArmur Documentation

This directory contains comprehensive documentation for ExoArmur Core.

## Table of Contents

### Core Documentation

- [Architecture](ARCHITECTURE.md) — System architecture overview, kernel components, determinism guarantees
- [The ExoArmur Doctrine](DOCTRINE.md) — Verified claims and compliance requirements
- [ML Isolation Policy](ML_ISOLATION.md) — Advisory-only ML components and verification
- [DACT Standard v0.2](DACT_STANDARD_v0.2.md) — Deterministic Autonomy Compliance Test specification (ExoArmur's own evaluation framework, not an independent standard)
- [Known Limitations](KNOWN_LIMITATIONS.md) — Disclosed gaps and pilot status: legacy unauthenticated routes, scaffold executors, unverified signatures
- [Pilot Runbook](PILOT.md) — Bounded governed file-write workflow: setup, approvals, pauses, evidence, operator GUI
- [Validation Matrix](VALIDATION_MATRIX.md) — Dated test, security-scan, and dependency validation results
- [Dependency Review](DEPENDENCY_REVIEW.md) — Third-party dependency inventory and license review

### Formal Verification

- [Formal Verification Invariants](formal_verification/INVARIANTS.md) — Formal specifications for DACT Level 6 compliance

### Integration Guides

- [LangChain Executor Integration](integrations/LANGCHAIN_EXECUTOR.md) — Scaffold integration guide for LangChain (reference implementation only)

### Security

- [Security Audit Receipt](security/SECURITY_AUDIT_RECEIPT.md) — Internal (self-validated) security scanning receipt; no third-party audit conducted

### Planned Documentation (Not Yet Available)

- **DEVELOPING_EXECUTORS.md** — Guide for creating custom executors (planned)
- **DEVELOPING_PLUGINS.md** — Guide for creating plugins (planned)
- **EXTERNAL_EFFECT_SCHEMA.md** — External effect evidence schema documentation (planned)
- **REPLAY_VERIFICATION.md** — Replay verification guide (planned)
- **TROUBLESHOOTING.md** — Common issues and solutions (planned)

## Documentation Status

All core documentation is current and accurate as of May 30, 2026. Integration guides for platform executors are scaffold/reference implementations only — real platform integrations belong in optional addon packages.

## Quick Links

- [Main README](../README.md) — Project overview and quickstart
- [Project Status](../PROJECT_STATUS.md) — Current validation status
- [Security Policy](../SECURITY.md) — Security policy and threat model
- [Contributing](../CONTRIBUTING.md) — Contribution policy and development setup
- [Changelog](../CHANGELOG.md) — Version history
