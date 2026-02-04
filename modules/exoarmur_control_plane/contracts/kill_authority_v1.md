# Kill Authority v1 — Contract Definition

**Stage**: V2 Stage 1 (contracts only, inert)

This contract defines the normative surface for emergency stop authority
assertions and their recording semantics. It is implementation-agnostic and
contains no executable behavior.

## 1) Roles (Normative)
- **Operator**: Party subject to emergency stop authority.
- **Approver**: Party authorized to assert kill authority.
- **Auditor**: Party verifying kill authority assertions and evidence.

## 2) Kill Authority Record (Minimum Required Fields)
A kill authority record MUST contain, at minimum:
- **kill_id**: Deterministic identifier for the kill authority record.
- **kill_version**: Contract version ("v1").
- **subject_scope**: Scope of systems or actions affected.
- **asserted_by**: Identifier for the authority asserting the kill.
- **asserted_at**: Timestamp of assertion.
- **reason**: Normative reason for the emergency stop.
- **evidence_set**: Evidence supporting the assertion, if any.
- **canonicalization_hash**: Hash over the canonicalized record payload.
- **signatures**: One or more authority signatures over the canonicalized payload.

The kill authority record MUST be immutable once signed.

## 3) Verification States
Verification of a kill authority record yields one of:
- **VALID**: All required fields present; canonicalization is reproducible;
  signatures verify; asserted scope is explicit.
- **INVALID**: Required fields missing, canonicalization mismatch, signature
  failure, or scope ambiguity.
- **INCONCLUSIVE**: Verification cannot be completed due to missing evidence or
  inaccessible signer metadata.

## 4) Proof Obligations
A verifier MUST be able to prove:
- The record payload is complete and immutable.
- Canonicalization is deterministic and reproducible.
- Signatures bind the authority to the canonicalized payload.
- Scope and reason are explicit and non-ambiguous.

## 5) MUST-NOT Clauses
- Kill authority MUST NOT be asserted silently or without an explicit record.
- Kill authority assertions MUST NOT be automated by default.
- Records MUST NOT be retroactively altered to justify emergency actions.

## 6) Non-Goals (Explicit Exclusions)
Kill Authority v1 does NOT provide:
- Runtime enforcement or execution of emergency stops.
- Automated policy evaluation or approvals.
- Network transport or identity key management.

This contract is strictly a semantic boundary for emergency stop authority.
