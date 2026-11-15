# Known Limitations

*Last updated: aligned to the 2.2.0 baseline (`baseline-2.2.0-alignment`)*

## Overview

This document catalogues the known limitations of ExoArmur-Core on the current
2.2.0 architecture. These limitations are disclosed so users and contributors
can make informed decisions about adoption and contribution.

## Security & Certification Limitations

### No Third-Party Security Audit
- **Status**: Security and compliance are self-validated only
- **Impact**: No independent security review has been conducted
- **Mitigation**: Automated scanning (bandit, pip-audit, gitleaks) is enforced via CI
- **Path Forward**: Seeking third-party security audit partnership

### No Production Certification
- **Status**: Not certified for production use
- **Impact**: Cannot claim production readiness or compliance certifications
- **Mitigation**: Reference implementation status clearly documented
- **Path Forward**: Seeking formal verification partnership and pilot integrations

### DACT Level 6 Pending
- **Status**: DACT is ExoArmur's own evaluation framework (see
  `docs/DACT_STANDARD_v0.2.md`), not an independent standard. Levels 1-5 are
  internally evaluated by the test suite; Level 6 pending external/formal review
- **Impact**: Formal verification not yet completed; "DACT compliant" claims are
  self-assessment, not certification
- **Mitigation**: Invariants tested via comprehensive test suite
- **Path Forward**: Formal verification requires theorem-prover output or formal specification proofs

## Governance Limitations (2.2.0 baseline)

The bounded pilot (one authenticated, policy-controlled file-write workflow
with approvals, durable pauses, evidence, and an operator GUI) is implemented
on the `pilot/governed-workflow` branch — see [docs/PILOT.md](PILOT.md). On
the `main`/`baseline-2.2.0-alignment` baseline the following gaps remain:

### No Authentication on the Legacy HTTP API
- **Status**: The pre-pilot `exoarmur.api` routes (`/v1/*`, `/api/v2/*`,
  `/api/cli/*`) have no authentication. Approval endpoints
  (`/v1/approvals/{id}/approve|deny`) accept any self-asserted `operator_id`
  header — identification, not authentication.
- **Impact**: On the baseline, anyone who can reach those routes can
  approve/deny or ingest telemetry. The pilot router (`/api/pilot/*`) is the
  authenticated surface; legacy routes remain unauthenticated by design until
  migrated.
- **Path Forward**: Extend pilot-grade authentication to legacy routes or
  retire them.

### Hardcoded Safety Inputs in ProxyPipeline (baseline)
- **Status**: On the baseline, `ProxyPipeline.execute_with_trace()` uses
  hardcoded `policy_verified=True`, `emitter_trust_score=0.85`,
  `required_approval="none"`, kill-switch flags `False`. The pilot branch
  replaces this with an injectable `SafetyContextProvider` that fails closed
  when trusted inputs are absent; the `ai-complete` demo passes explicitly
  labeled demo inputs only.
- **Impact**: Baseline pipeline mechanics run, but not against trustworthy
  operational evidence.

### No Authoritative Kill Switch (baseline)
- **Status**: Baseline pipeline has no durable pause store. The pilot branch
  adds durable global/tenant `execution_pauses` re-checked immediately before
  dispatch, including approval resume.

### Allow-by-Construction Demo Policy (unchanged)
- **Status**: `POST /api/cli/ai-complete` still uses an internal `_AllowPolicy`
  and a mocked REPLAY executor. It is a demo of pipeline mechanics, not a
  governed path, and is explicitly isolated from the pilot boundary.

### Approvals Do Not Resume Execution
- **Status**: Approval records transition PENDING → APPROVED/DENIED in the
  store, but nothing re-dispatches the underlying action intent after approval.
- **Impact**: The approval workflow is record-keeping only on this baseline.
- **Path Forward**: Wire approved intents back through the governed pipeline
  with fresh policy/safety/kill-switch checks.

### TrustEvaluator Is Interface-Only
- **Status**: `kernel/trust_evaluator.py` raises `NotImplementedError`
- **Impact**: No real trust scoring logic implemented; the `0.85` value used by
  the pipeline is a hardcoded placeholder
- **Mitigation**: Formal interface defined for future implementation
- **Path Forward**: Requires an authoritative trust source (e.g., operator
  configuration clearly labeled as configured, not measured, trust)

## Implementation Limitations

### Platform Executors Are Scaffolds
- **Status**: LangChain, OpenAI, Anthropic, HuggingFace executors are reference implementations only — `_execute_*` methods return mock data and make no vendor API calls
- **Impact**: No actual vendor SDK integrations; a class existing does not establish a functioning vendor integration
- **Mitigation**: Plugin infrastructure and evidence schema provided
- **Path Forward**: Production-ready integrations belong in optional addon packages

### Executor Contract Inconsistency
- **Status**: Some methods (get_state_hash, get_execution_history) not part of formal ExecutorPlugin protocol
- **Impact**: Test skips due to contract assumptions not matching implementation
- **Mitigation**: Known skip categories documented in test suite
- **Path Forward**: Executor contract formalization needed to decide protocol requirements

## Evidence & Replay Limitations

### Replay Hashes Detect Inconsistency, Not Tampering
- **Status**: `/api/cli/replay` and `verify_evidence_integrity` recompute
  canonical hashes from stored records and compare them
- **Impact**: Recomputing a hash from stored content alone does not establish
  that the original content was preserved — an attacker who rewrites both
  content and stored hash is not detected. What is verified is internal
  consistency between stored hash fields and stored payloads.
- **Mitigation**: `verify_request_matches_evidence` additionally checks
  provider, operation type, and canonical request hash against stored evidence.
- **Path Forward**: External anchoring or signed evidence bundles for
  tamper-evidence against store compromise.

### Evidence Signatures Not Verified
- **Status**: `ExternalEffectEvidence.evidence_signature` is stored but
  `verify_evidence_integrity` reports signature checks as `NOT_CHECKED`
  (`signature_verification_not_implemented`)
- **Impact**: No cryptographic signer verification exists; "cryptographic
  attestation" claims are limited to unkeyed canonical hashes
- **Path Forward**: Implement signature verification or remove the field's
  implied guarantee from docs.

## Operational Limitations

### No Known Production Deployments
- **Status**: No real-world operational history
- **Impact**: No production-scale performance data or operational experience
- **Mitigation**: E2E test coverage exists (`tests/e2e/`, 22 tests at last run)
- **Path Forward**: Seeking pilot integrations in high-assurance environments

### No Production Monitoring Infrastructure
- **Status**: No SLOs, alerting, or observability infrastructure defined
- **Impact**: Cannot guarantee production operational readiness
- **Mitigation**: `GET /health` endpoint reports service liveness/version
- **Path Forward**: Production monitoring requires SLO definition and observability stack

### No Incident Response Procedures
- **Status**: No documented incident response runbooks
- **Impact**: No validated incident response procedures
- **Mitigation**: Security policy defines vulnerability reporting process
- **Path Forward**: Incident response procedures require operational experience

## Testing Limitations

### Test Skips
- **Status**: 338 passed, 17 skipped, 0 failed at last recorded run (May 31,
  2026); suite has since grown — see `docs/VALIDATION_MATRIX.md`
- **Impact**: Some functionality not fully tested due to contract inconsistencies
- **Mitigation**: All skip categories documented and justified
- **Path Forward**: Executor contract formalization will reduce skips

### No Red Team Exercises
- **Status**: No adversarial testing against external red teams on this baseline
- **Impact**: Adversarial testing not conducted
- **Path Forward**: Red team exercises require external security partnership

### No Byzantine Fault Tolerance Testing
- **Status**: No BFT fault-injection framework exists on this baseline
- **Impact**: BFT consensus not validated (and not claimed)
- **Path Forward**: Out of scope for the bounded pilot goal

## Documentation Limitations

### License Is Apache-2.0; No Legal Encumbrance on the Repository
- **Status**: The repository is publicly available under Apache-2.0 (see
  LICENSE). Earlier drafts of this document described a proprietary evaluation
  license and pre-release status; that no longer reflects the repository.
- **Impact**: None for use; contributors should note the Apache-2.0 grant in
  CONTRIBUTING.md
- **Path Forward**: THIRD_PARTY_NOTICES.md should be kept current as dependencies change

### No Production Deployment Guide
- **Status**: No operational runbooks or deployment documentation
- **Impact**: Production deployment guidance not available
- **Mitigation**: Installation and API quickstart documentation provided
- **Path Forward**: Production deployment guide requires operational experience

## Dependency Limitations

### Dependency Security Responsibility
- **Status**: Third-party dependencies out of scope for direct security reporting
- **Impact**: Vulnerabilities in dependencies must be reported to vendors
- **Mitigation**: pip-audit scans for known vulnerabilities on every push
- **Path Forward**: Dependency monitoring requires ongoing maintenance

### Python Version Support
- **Status**: Minimum supported Python version is 3.10
- **Impact**: Cannot run on Python < 3.10
- **Mitigation**: Tested across Python 3.10, 3.11, 3.12
- **Path Forward**: Older Python support not planned

## Architectural Limitations

### Kernel Has No Built-in Persistence; API Has Dual-Write Stores
- **Status**: `kernel/` is a pure library with no storage. The `exoarmur.api`
  layer includes in-memory stores with optional PostgreSQL dual-write
  (`api/db.py`, `api/stores.py`, migration `api/migrations/001_init.sql`),
  but kernel-level audit persistence requires external integration.
- **Impact**: Kernel audit evidence is in-memory unless the host persists it.
  The pilot branch persists governed-action evidence durably in PostgreSQL
  (`002_pilot.sql`); legacy kernel audit records remain in-memory.

### No Built-In Kill Switch or Federation
- **Status**: No emergency pause mechanism; federation crypto exists only as
  contract specs (`src/spec/contracts/federation_v2.yaml`) without a hardened
  implementation on this baseline
- **Impact**: Multi-node federation not production-ready (and not part of the
  bounded pilot goal). The pilot branch adds durable global/tenant execution
  pauses enforced immediately before dispatch.
- **Path Forward**: Federation deferred; kill switch implemented on the pilot
  branch.

## Summary

ExoArmur-Core on the 2.2.0 baseline is a **public Apache-2.0 reference
implementation** with a deterministic governance kernel, internally evaluated
replay/evidence verification, real local executors (filesystem, SQLite),
executor scaffolds for vendors, and an **unauthenticated** FastAPI demo/CLI
layer. It lacks third-party certification and production operational
experience. On the `pilot/governed-workflow` branch, the bounded goal —
one authenticated, policy-controlled real file-write workflow with human
approval of the exact action, durable global/tenant pauses, durable evidence
with integrity verification, and an operator GUI — is implemented and covered
by focused tests against real PostgreSQL; see [docs/PILOT.md](PILOT.md).
Remaining gaps: legacy routes are still unauthenticated, the pilot covers a
single executor/operation set, and evidence verification is payload-hash
consistency only (no signer verification).

## Current Status

- **Version**: 2.2.0
- **License**: Apache-2.0 (see LICENSE)
- **Stage**: Public reference implementation; bounded pilot implemented on `pilot/governed-workflow`
- **Last updated**: pilot branch `pilot/governed-workflow`
