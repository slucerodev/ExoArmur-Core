# Known Limitations

*Last updated: post-merge pilot documentation alignment on `main`*

## Overview

This document catalogues the known limitations of ExoArmur-Core on the current
2.2.0 architecture. These limitations are disclosed so users and contributors
can make informed decisions about adoption and contribution.

## Security & Certification Limitations

### No Third-Party Security Audit
- **Status**: Security and compliance are self-validated only
- **Impact**: No independent security review has been conducted
- **Mitigation**: Automated scanning (bandit, pip-audit, gitleaks) is defined in CI; note GitHub Actions could not run for recent merges due to a billing restriction — validation relied on recorded local runs
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
with approvals, durable pauses, evidence, and an operator GUI) is merged on
`main` — see [docs/PILOT.md](PILOT.md). Two application factories exist:

- **`exoarmur.api.server:create_pilot_app`** — the supported pilot surface:
  `/health` plus `/api/pilot/*` only (FastAPI `/docs`, `/redoc`,
  `/openapi.json` schema endpoints are also enabled). This is the factory
  to deploy.
- **`exoarmur.api.server:create_app`** — the legacy/demo surface: it
  additionally mounts `/v1/*`, `/api/v2/*`, and `/api/cli/*`, which remain
  **unauthenticated** and are not part of the supported pilot.

### No Authentication on the Legacy HTTP API
- **Status**: The legacy `exoarmur.api` routes (`/v1/*`, `/api/v2/*`,
  `/api/cli/*`) have no authentication. Approval endpoints
  (`/v1/approvals/{id}/approve|deny`) accept any self-asserted `operator_id`
  header — identification, not authentication.
- **Impact**: Anyone who can reach the legacy app can approve/deny or ingest
  telemetry. Deployments of the supported pilot must use
  `create_pilot_app`, which does not mount these routers at all.
- **Path Forward**: Extend pilot-grade authentication to legacy routes or
  retire them.

### Hardcoded Safety Inputs in ProxyPipeline (legacy path only)
- **Status**: `ProxyPipeline.execute_with_trace()` no longer hardcodes
  permissive inputs — it requires an injectable `SafetyContextProvider` and
  fails closed when trusted inputs are absent. The pilot service supplies
  operator-configured inputs; the `ai-complete` demo passes explicitly
  labeled demo inputs only.
- **Impact**: Callers that construct `ProxyPipeline` without a provider get
  a deterministic deny, not silent permissive defaults.

### Authoritative Kill Switch (pilot scope)
- **Status**: The pilot enforces durable global/tenant `execution_pauses`
  (PostgreSQL `execution_pauses` table) re-checked immediately before
  executor dispatch, including approval resume. This covers the pilot
  governed path only — the legacy routers have no pause enforcement.

### Pilot Scope Limitations
- **Boundary, not interception**: the pilot governs only actions submitted
  through `/api/pilot/*`. Agents must be integrated to route file writes
  through it; ExoArmur does not automatically control an agent's other
  filesystem or network access, and deployments must ensure governed
  operations cannot be performed through unmediated paths.
- **Pauses block subsequent dispatch only**: durable global/tenant pauses
  prevent pending and approved actions from being dispatched (including
  approval resume). They do not interrupt an effect already executing.
- **Filesystem-only, local-only**: the pilot supports `create_file` /
  `modify_file` inside `EXOARMUR_WORKSPACE_ROOT` on local PostgreSQL. No
  other executors, operations, or databases are supported.
- **Ambiguous interrupted executions**: an action stuck in `EXECUTING`
  (e.g., process crash mid-dispatch) is reported as ambiguous, not
  automatically retried — retry semantics are the operator's decision.
- **Unpaginated history**: action listing returns all records for a
  tenant; there is no pagination or retention policy.
- **Evidence is hash consistency, not tamper-proofing**: `verify` detects
  stored records altered after write, but cannot detect an attacker who
  rewrites content and hash together, and signatures are `NOT_CHECKED`.

### Allow-by-Construction Demo Policy (unchanged)
- **Status**: `POST /api/cli/ai-complete` still uses an internal `_AllowPolicy`
  and a mocked REPLAY executor. It is a demo of pipeline mechanics, not a
  governed path, and is explicitly isolated from the pilot boundary.

### Approvals Do Not Resume Execution (legacy path only)
- **Status**: On the legacy `create_app` surface, approval records transition
  PENDING → APPROVED/DENIED in the store, but nothing re-dispatches the
  underlying action intent. The **pilot** path does resume: approval
  re-validates the stored action and dispatches it through the governed
  pipeline (`/api/pilot/*` only).
- **Impact**: Approval workflow is record-keeping only on the legacy demo
  surface; it is functional on the supported pilot path.
- **Path Forward**: Retire or govern the legacy approval routes.

### TrustEvaluator Is Interface-Only; Pilot Trust Is Configured, Not Measured
- **Status**: `kernel/trust_evaluator.py` raises `NotImplementedError`.
  The pilot does not measure trust — the operator policy file supplies a
  configured `trust_score` per principal, which is an operator assertion,
  not a measured or verified signal.
- **Impact**: No real trust scoring logic implemented; governance decisions
  rest on configured values whose correctness is the operator's responsibility.
- **Mitigation**: Formal interface defined for future implementation
- **Path Forward**: Requires an authoritative trust source

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
  The pilot persists governed-action evidence durably in PostgreSQL
  (`002_pilot.sql`); legacy kernel audit records remain in-memory.

### No Built-In Kill Switch or Federation
- **Status**: The pilot governed path has durable global/tenant execution
  pauses (see above); there is no kernel-level or legacy-route pause
  mechanism. Federation crypto exists only as contract specs
  (`src/spec/contracts/federation_v2.yaml`) without a hardened
  implementation on this baseline
- **Impact**: Multi-node federation not production-ready (and not part of the
  bounded pilot goal). The pilot adds durable global/tenant execution pauses
  enforced immediately before dispatch on the governed path.
- **Path Forward**: Federation deferred.

## Summary

ExoArmur-Core on the 2.2.0 baseline is a **public Apache-2.0 reference
implementation** with a deterministic governance kernel, internally evaluated
replay/evidence verification, real local executors (filesystem, SQLite),
executor scaffolds for vendors, and an **unauthenticated** FastAPI demo/CLI
layer. The supported pilot surface — `create_pilot_app` — provides one
authenticated, policy-controlled real file-write workflow with human
approval of the exact action, durable global/tenant pauses, durable evidence
with integrity verification, and an operator GUI; see [docs/PILOT.md](PILOT.md).
Remaining gaps: the legacy `create_app` routes are still unauthenticated,
the pilot covers a single executor/operation set, and evidence verification
is payload-hash consistency only (no signer verification).

## Current Status

- **Version**: 2.2.0
- **License**: Apache-2.0 (see LICENSE)
- **Stage**: Public reference implementation; bounded pilot merged on `main`
- **Distribution**: source version 2.2.0; published PyPI release is 2.1.0 and
  predates the pilot — install from source per [docs/PILOT.md](PILOT.md)
- **Validation note**: GitHub Actions could not run for the pilot merge
  (billing restriction); validation relied on recorded local tests
  (`tests/api/test_pilot.py` — 24 passed against real PostgreSQL; full suite
  398 passed / 17 skipped) and live demonstrations.
- **Last updated**: post-merge pilot documentation alignment on `main`
