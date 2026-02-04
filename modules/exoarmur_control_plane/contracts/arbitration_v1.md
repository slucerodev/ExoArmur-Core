# Arbitration Record v1 — Contract Definition

**Stage**: V2 Stage 1 (contracts only, inert)

This contract defines the normative surface for arbitration records used to
resolve disputes over operator intent, approvals, and control-plane actions.
It is implementation-agnostic and contains no executable behavior.

## 1) Roles (Normative)
- **Operator**: Party whose intent is under arbitration.
- **Approver**: Party whose approval or rejection is under arbitration.
- **Auditor**: Party verifying the arbitration record and its evidence.

## 2) Arbitration Record (Minimum Required Fields)
An arbitration record MUST contain, at minimum:
- **arbitration_id**: Deterministic identifier for the record.
- **arbitration_version**: Contract version ("v1").
- **subject_soi_id**: The SOI under arbitration.
- **subject_scope**: Scope of the intent under arbitration.
- **dispute_reason**: Normative reason for arbitration.
- **evidence_set**: Enumerated evidence items admissible to the record.
- **created_at**: Record creation timestamp.
- **adjudicator_id**: Identifier for the adjudicating authority.
- **decision_summary**: Human-readable decision summary.
- **decision_outcome**: Approved, rejected, or escalated.
- **canonicalization_hash**: Hash over the canonicalized arbitration payload.
- **signatures**: One or more adjudicator signatures over the canonicalized payload.

The arbitration record MUST be immutable once signed.

## 3) Evidence Semantics
- Evidence MUST be explicitly enumerated.
- Evidence MUST be admissible under the applicable governance policy.
- Evidence MUST NOT include post-hoc justification generated after the disputed
  action.

## 4) Verification States
Verification of an arbitration record yields one of:
- **VALID**: All required fields present; canonicalization is reproducible;
  signatures verify; evidence set is admissible.
- **INVALID**: Required fields missing, canonicalization mismatch, signature
  failure, or inadmissible evidence present.
- **INCONCLUSIVE**: Verification cannot be completed due to missing evidence or
  inaccessible signer metadata.

## 5) Proof Obligations
A verifier MUST be able to prove:
- The arbitration record payload is complete and immutable.
- Canonicalization is deterministic and reproducible.
- Signatures bind the adjudicator to the canonicalized payload.
- Evidence admissibility and enumeration are explicit.

## 6) MUST-NOT Clauses
- Arbitration MUST NOT be performed or recorded retroactively to justify an
  already executed action.
- Evidence MUST NOT be silently omitted or replaced.
- Decisions MUST NOT be treated as executable control-plane directives.

## 7) Non-Goals (Explicit Exclusions)
Arbitration v1 does NOT provide:
- Runtime enforcement or automated execution of decisions.
- Policy engines or dispute-resolution algorithms.
- Network transport or storage specifications.

This contract is strictly a semantic boundary for arbitration records.
