# Signed Operator Intent (SOI) v1 — Contract Definition

**Stage**: V2 Stage 1 (contracts only, inert)

This contract defines the normative surface for **Signed Operator Intent (SOI)**
objects and their verification semantics. It is implementation-agnostic and
contains no executable behavior.

## 1) Roles (Normative)
- **Operator**: The party asserting an intent for a controlled action.
- **Approver**: A party authorized to approve or reject an intent.
- **Auditor**: A party authorized to verify intent integrity and provenance.

## 2) Intent Object (Minimum Required Fields)
An SOI object MUST contain, at minimum:
- **soi_id**: Deterministic identifier for the intent.
- **soi_version**: Contract version ("v1").
- **operator_id**: Identifier for the Operator.
- **intent_summary**: Human-readable statement of the intended action.
- **intent_scope**: Explicit scope boundary for the intended action.
- **created_at**: Intent creation timestamp.
- **expires_at**: Intent expiry timestamp.
- **approver_requirements**: Required approver roles or identifiers.
- **canonicalization_hash**: Hash over the canonicalized intent payload.
- **signatures**: One or more operator signatures over the canonicalized payload.

The intent object MUST be immutable once signed.

## 3) Versioning and Canonicalization
- SOI objects MUST declare their version explicitly.
- Canonicalization MUST be deterministic and MUST be applied before signing.
- Any verifier MUST be able to reproduce the canonicalization result.

## 4) Verification States
Verification of an SOI yields one of the following states:
- **VALID**: All required fields present; canonicalization is reproducible; all
  required signatures verify; intent is within temporal bounds.
- **INVALID**: Required fields missing, canonicalization mismatch, signature
  failure, or intent outside temporal bounds.
- **INCONCLUSIVE**: Verification cannot be completed due to missing evidence or
  inaccessible signer metadata; no execution is permitted in this state.

## 5) Proof Obligations
A verifier MUST be able to prove:
- The SOI payload is complete and immutable.
- Canonicalization is deterministic and reproducible.
- Signatures bind the Operator to the canonicalized payload.
- The intent is within its declared temporal bounds at verification time.

## 6) MUST-NOT Clauses
- An SOI MUST NOT be executed or implicitly acted upon by default.
- Verification MUST NOT silently downgrade INVALID to INCONCLUSIVE.
- Approvals MUST NOT be inferred without explicit approver evidence.
- SOI records MUST NOT be retroactively altered to justify an action.

## 7) Non-Goals (Explicit Exclusions)
SOI v1 does NOT provide:
- Runtime execution, orchestration, or enforcement logic.
- Policy evaluation or approvals automation.
- Network transport, storage, or identity key management.

This contract is strictly a semantic boundary for intent verification.
