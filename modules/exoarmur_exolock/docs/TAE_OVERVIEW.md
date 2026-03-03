# Temporal Authority Envelope (TAE) Overview

## Purpose
The Temporal Authority Envelope (TAE) defines a contract-only boundary for
**deterministic incident time-locking**. It establishes a shared semantic
surface for isolating decisions within a verified Incident Epoch without
introducing any runtime behavior.

## Stage 1 Scope (Contracts Only)
- Defines terminology and invariants for time-locked decision evidence.
- Establishes what information is sealed at epoch entry.
- Prohibits post-epoch or future knowledge from influencing in-epoch decisions.

No execution logic, integration wiring, or feature flags are provided at Stage 1.

## Core Definitions
- **Incident Epoch**: A bounded temporal interval defined by a verifiable
  entry marker and immutable context snapshot.
- **Temporal Authority Envelope**: The contract surface describing what is
  sealed, what is excluded, and how verification must interpret evidence.
- **Time-Locked Decision**: A decision whose validity is evaluated only against
  data sealed at epoch entry and evidence produced within the epoch boundary.

## Determinism and Verification
- Replay must remain deterministic and read-only.
- Verification must confirm that all referenced evidence is inside the epoch
  boundary and that no out-of-epoch data informed the decision.

## Non-Goals
- No enforcement engine.
- No scheduling, automation, or orchestration behavior.
- No cryptographic implementation details beyond the contract language.

Normative contract language is defined in `contracts/tae_v1.md`.
