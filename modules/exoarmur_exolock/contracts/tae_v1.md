# Temporal Authority Envelope (TAE) v1 — Contract Definition

**Stage**: V2 Stage 1 (contracts only, inert)

This contract defines the normative surface for deterministic incident
**time-locking**. It is implementation-agnostic and contains no executable
behavior.

## 1) Incident Epoch
An **Incident Epoch** is a bounded temporal interval that begins at a verifiable
**epoch entry marker** and ends at a verifiable **epoch exit marker**. The entry
marker MUST define the authoritative start of the epoch and MUST be sufficient
to deterministically identify the epoch's sealed context.

## 2) Sealed Data at Epoch Entry
At epoch entry, the following data MUST be sealed and treated as immutable
for the duration of the epoch:
- The epoch entry marker and its associated evidence.
- The bounded context snapshot used to evaluate in-epoch decisions.
- The identities and authority scope that define who may author in-epoch
  decisions.

Sealed data MUST be reproducible during verification and MUST NOT be replaced
or mutated after epoch entry.

## 3) Sealed Evidence Set (SES)
The **Sealed Evidence Set (SES)** is the complete set of evidence admissible
for in-epoch decisions. The SES MUST be closed at Incident Epoch entry and
MUST include all sealed data required to evaluate in-epoch decisions.

## 4) Prohibited Evidence Set (PES)
The **Prohibited Evidence Set (PES)** is any evidence originating after epoch
entry or from explicitly excluded sources. The PES MUST NOT influence in-epoch
decisions.

## 5) Time-Locked Decision
A **time-locked decision** is valid only if all evidence it references is:
- Sealed at epoch entry, or
- Produced strictly within the epoch boundary.

A time-locked decision MUST NOT depend on evidence created outside the epoch.

## 6) Prohibition on Future Knowledge
Future knowledge, post-epoch state, or out-of-epoch context MUST NOT influence
in-epoch decisions. Any decision that is shown to rely on out-of-epoch evidence
is INVALID under this contract.

## 7) MUST-NOT Dependency Rule
The SES MUST NOT depend on the PES, directly or transitively. Any replay or
verification MUST be able to demonstrate PES exclusion.

## 8) Replay and Verification Guarantees
Verification MUST be deterministic and read-only. A verifier MUST be able to:
- Reconstruct the epoch entry context from sealed data.
- Confirm that all referenced evidence is inside the epoch boundary.
- Confirm that no out-of-epoch evidence influenced the decision.

### Proof Obligations
A verifier MUST be able to show:
- SES completeness at epoch entry.
- PES exclusion.
- Deterministic replay using SES only.

The contract provides no implementation details for how verification is
performed.

## 9) Non-Goals (Explicit Exclusions)
TAE v1 does NOT provide:
- Execution, scheduling, or orchestration behavior.
- Automated enforcement actions.
- Cryptographic algorithm selection or key management.
- Runtime integrations or feature activation.

This contract is strictly a semantic boundary for time-locked decision
reasoning.
