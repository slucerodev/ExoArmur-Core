# ExoArmur Module Research — Concise Pass

**Date:** 2026-05-02  
**Scope:** Research & architecture definition only. No code.

---

## Core Invariant Guardrail
> Same input + same environment + same policy state = same proof outcome.

Any module that weakens this is rejected.

---

## A. Module Candidates

### Build Now (5)

| # | Module | Solves | Output | Complexity | Why Now |
|---|---|---|---|---|---|
| 1 | **Policy Snapshot / Freeze** | "What policy was in force?" | `policy_snapshot.json` with hash bound to proof bundle | Low | Every audit asks this first |
| 2 | **Tool Invocation Proof** | "Did the agent call the right tool with the right args?" | Canonicalized tool params + hash in bundle | Low | Top-3 AI agent failure mode |
| 3 | **Human Approval Ceremony** | "Who approved this, and can we prove it?" | Ed25519-signed `approval_certificate.json` | Medium | Weak link in the proof chain |
| 4 | **Environment Fingerprint** | "Will replay diverge on a different machine?" | `environment_fingerprint.json` with env hash | Medium | Required for cross-machine trust |
| 5 | **Compliance Evidence Export** | "Can our auditor read this without Python?" | PDF/JSON reports per framework (SOX, GDPR, NIST) | Medium | Primary enterprise budget line |

### Design Later (4)

| # | Module | Solves | Why Later |
|---|---|---|---|
| 6 | **Incident Reconstruction** | Multi-correlation timeline replay | Complex merge rules; needs replay engine hardened |
| 7 | **Rollback / Reversal Proof** | "Can we prove we fixed the mistake?" | Low priority until production deployments |
| 8 | **External Verifier SDK** | Java/Go/Rust verifiers | High value but needs Core proof formats to stabilize |
| 9 | **Agent Identity & Delegation** | "Which agent, on whose authority?" | Needs federation module mature |

### Reconsider (2)

| # | Module | Risk |
|---|---|---|
| 10 | **Simulation / Dry-Run** | Leaks historical data; not a proof capability |
| 11 | **Proof Redaction** | Merkle proofs are complex; wait for concrete multi-party need |

### Reject (13)

| Module | Rejection Reason |
|---|---|
| Policy Drift Detector | SIEM territory; not proof |
| Multi-agent Accountability Graph | Nondeterministic social graph; revisit after Agent Identity |
| Governance Scorecard | Subjective scoring dilutes proof positioning |
| Third-party Auditor Portal | Product feature, not proof module; use SDK instead |
| SaaS/API Executor | Integration, not strategic module |
| GitHub Executor | Integration, not strategic module |
| Database Executor | Integration, not strategic module |
| Customer-Supplied Invariant Tester | Introduces nondeterminism and attack surface |
| Regulated Audit Pack | Duplicates Compliance Export without specificity |
| ML Anomaly Detection | Nondeterministic; violates core invariant |
| Auto-Healing | Violates fail-closed principle |
| NL Policy Engine | Ambiguous; destroys deterministic replay |
| Generic Workflow Engine | Competes with Temporal/Airflow; out of scope |

---

## B. Top 5 — Why ExoArmur Wins

### 1. Policy Snapshot / Freeze
**Why us:** Core already canonicalizes JSON. Extending `PolicyDecision` with `policy_snapshot_hash` is a natural evolution. Replay engine validates the frozen hash.
**Sell:** *"Prove the exact policy in force at decision time—not just that a decision was made."*
**MVP:** `PolicySnapshot` dataclass + CLI `freeze-policy` + replay hash validation.
**Full:** Git auto-freeze, policy diff, multi-policy composition.
**Never add:** Policy effectiveness scoring, auto-generation, real-time monitoring.

### 2. Tool Invocation Proof
**Why us:** `ActionIntent` already carries `tool_name` and `parameters`. Canonicalization already sorts JSON deterministically. Executor boundary is the single execution point.
**Sell:** *"Prove the agent called `send_email` with `recipient=audit@company.com`, not `attacker@evil.com`."*
**MVP:** `ToolInvocationProof` dataclass with `tool_name`, `canonical_params_hash`, `schema_version`.
**Full:** Schema registry, parameter type validation, tool-result binding (output hash bound to input hash).
**Never add:** Tool implementation, auto-discovery, effectiveness scoring.

### 3. Human Approval Ceremony
**Why us:** Approval workflow exists in V2. Proof bundle already captures approvals. Ed25519 signatures are deterministic and fast. `verify-bundle` can validate offline.
**Sell:** *"Not 'approved by Alice'—but 'cryptographically signed by Alice's HSM key at 14:32:07, bound to the exact intent hash.'"*
**MVP:** `ApprovalCertificate` with operator ID, intent hash, signature, pubkey fingerprint.
**Full:** HSM integration (YubiKey, AWS KMS, Vault), multi-sig, time-bound approvals, revocation lists.
**Never add:** Biometric storage, NL approval rationale, social graphs.

### 4. Environment Fingerprint
**Why us:** Core enforces `PYTHONHASHSEED=0`. Replay engine validates deterministic execution. Adding env snapshot is a natural extension—critical for External Verifier SDK credibility.
**Sell:** *"This bundle was produced on Python 3.12.3 + pydantic 2.12.5. Your verifier runs 3.13.0. Replay may diverge."*
**MVP:** `EnvironmentFingerprint` with `python_version`, `exoarmur_version`, `dependency_hash`, `env_vars_hash`.
**Full:** Kernel version, container image digest, network availability snapshot, feature flag fingerprint.
**Never add:** Performance metrics, network traffic capture, real-time monitoring.

### 5. Compliance Evidence Export
**Why us:** All raw evidence exists in the proof bundle. Canonicalization produces deterministic JSON. External verifier validates integrity. Compliance is the #1 enterprise budget for governance tools.
**Sell:** *"Your auditor doesn't need Python. PDF with every hash, every signature, every decision—verifiable via link."*
**MVP:** CLI `export-compliance --framework sox --bundle ... --output report.pdf` with deterministic sections.
**Full:** SOX, GDPR Art. 30, NIST 800-53, ISO 27001, HIPAA; batch export; GRC platform integration.
**Never add:** Compliance scoring, auto-remediation, real-time monitoring.

---

## C. Commercial Packaging

| Tier | Contents | Target | Price Signal |
|---|---|---|---|
| **Free / Open** | Core + demo + verify-bundle + replay + health | Evaluators, researchers | Free |
| **Developer** | PoD, DPO, Environment Fingerprint, Tool Invocation Proof, External Verifier SDK | Engineering teams | Per-seat / per-agent |
| **Enterprise** | Policy Snapshot, Human Approval Ceremony, Agent Identity, Compliance Export | Security, compliance, governance | Per-org, annual |
| **Regulated** | Full compliance frameworks, Incident Reconstruction, Rollback Proof, Proof Redaction | Financial, healthcare, gov | Per-org + audit support |
| **Integration** | Filesystem, SaaS/API, GitHub, Database executors | DevOps, platform | Low / bundled |

**Principle:** Core stays free and small. Proof modules create developer stickiness. Governance modules create enterprise revenue. Evidence modules create regulated-industry lock-in.

---

## D. Build Order

| Order | Module | Why This Order | Effort |
|---|---|---|---|
| **1** | Policy Snapshot / Freeze | Unblocks every compliance conversation | 2–3 wks |
| **2** | Tool Invocation Proof | Closes execution-to-proof gap; top failure mode | 2–3 wks |
| **3** | Human Approval Ceremony | Transforms weakest proof link into strongest | 3–4 wks |
| **4** | Environment Fingerprint | Required for verifier credibility | 2 wks |
| **5** | Compliance Evidence Export | The revenue bridge | 3–4 wks |
| **6** | External Verifier SDK | Removes Python-only barrier | 4–6 wks |
| **7** | Agent Identity & Delegation | Enables multi-agent deals | 3–4 wks |
| **8** | Rollback / Reversal Proof | Operational safety | 2 wks |
| **9** | Incident Reconstruction | High demo value; wait for replay hardening | 4–6 wks |
| **10** | Simulation / Dry-Run | Policy team utility; not proof-critical | 3–4 wks |

### Wait For
- Proof Redaction — until concrete multi-party governance customer
- Multi-agent Graph — until Agent Identity proven

### Never Build
- ML Anomaly Detection, Auto-Healing, NL Policy Engine, Generic Workflow Engine, Policy Drift Detector, Governance Scorecard, Customer Invariants, Auditor Portal

---

## E. Feature Flag Mapping

| Module | Flag | Default | Dependencies |
|---|---|---|---|
| Policy Snapshot | `v2_policy_snapshot_enabled` | false | none |
| Tool Invocation Proof | `v2_tool_invocation_proof_enabled` | false | none |
| Human Approval Ceremony | `v2_approval_ceremony_enabled` | false | `v2_operator_approval_enabled` |
| Environment Fingerprint | `v2_env_fingerprint_enabled` | false | none |
| Compliance Export | `v2_compliance_export_enabled` | false | none |
| Incident Reconstruction | `v2_incident_reconstruction_enabled` | false | `v2_replay_engine_enabled` |
| Rollback Proof | `v2_rollback_proof_enabled` | false | none |
| External Verifier SDK | `v2_external_verifier_sdk_enabled` | false | none |
| Agent Identity | `v2_agent_identity_enabled` | false | `v2_federation_enabled` |

---

## F. Summary

**Build first:** Policy Snapshot, Tool Invocation Proof, Human Approval Ceremony, Environment Fingerprint, Compliance Export.

**These five modules transform ExoArmur from "a deterministic replay engine" into "the verifiable AI agent governance platform"—with each module creating a new proof artifact category that compliance officers, security teams, and auditors can consume without reading Python.**

Everything else waits or is rejected.
