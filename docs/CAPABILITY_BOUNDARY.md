# Capability Boundary (Core vs Modules)

Principle: Core must run standalone and never import module code. Modules are optional capabilities loaded only via explicit contracts/registration.

## Core Responsibilities (must run standalone)
- Deterministic execution kernel, audit/replay, safety/phase gates, transport guard defaults.
- Feature flag loading/reset, environment baselines, governance checks.
- Contract definitions and schema validation for plugin interfaces.
- Default hermetic test lane (no external transport/storage by default).

## Module Responsibilities (optional capabilities)
- Provide additional capabilities (e.g., PoD proofs, BFT quorum, Counterfactual reasoning).
- Implement contract-defined interfaces only; no Core patching.
- Register capabilities via contract envelopes (capability registration/activation/denial) — not by direct import from Core.

## Separation Rules
- Core MUST NOT import module code (one-way boundary). Modules may import Core contracts/utilities.
- Runtime discovery MUST be contract-driven (envelopes/registry), not static imports from Core into modules.
- Core remains fully operational without any modules present.

## Implications
- Packaging: module extras may be optional dependencies; Core must install and run without them.
- Testing: hermetic defaults ensure module absence does not break Core imports.
- Governance: PhaseGate + capability flags prevent accidental activation in Phase 1.
