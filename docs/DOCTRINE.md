# THE EXOARMUR DOCTRINE (KERNEL VERSION)
## Deterministic Autonomous Defense with Verifiable Governance

**Version 2.0 — May 2026**

> **How to read this document:** sections 1–7 state the *doctrine* — the
> design claims and minimum requirements ExoArmur is built around. They
> are goals and falsifiable criteria, not a statement of what the current
> codebase delivers. The **VERIFICATION STATUS** section at the end is the
> authoritative account of what is actually implemented and internally
> evaluated on the current baseline, including known gaps. Where the two
> differ, the verification status controls.

---

## Executive Summary — The Line in the Sand

This doctrine makes three falsifiable claims:

1. **Any autonomous security system that cannot produce deterministic replay of its decisions is not auditable.**

2. **Any system that cannot prove reversibility of its actions is not safe to operate autonomously.**

3. **Any system that places machine learning in the authority path cannot guarantee decision integrity.**

These claims can be disproven with:
- reproducible multi‑run test harnesses
- byte‑identical decision traces
- verifiable action rollback
- independently validated audit chains

If they cannot be disproven, the implication is unavoidable:

> **Most current EDR, XDR, SIEM, SOAR, and AI‑driven SOC platforms do not meet minimum requirements for autonomous operation in regulated or adversarial environments.**

This doctrine defines those minimum requirements.

---

## What ExoArmur Is Designed to Demonstrate

*The following are the doctrine's design claims. Each is a requirement the
kernel architecture targets; current implementation status for each is
reported in the VERIFICATION STATUS section at the end of this document —
several are only partially met today.*

ExoArmur is a minimal deterministic governance kernel validated under the following conditions:

### 1. Deterministic Replay Verification

- Identical inputs → byte‑identical outputs
- Full decision trace reproducibility
- Independent replay validation

**Test:**  
Run the same event stream 3× → outputs hash‑identical.

### 2. Cryptographic Decision Attestation

- Hash‑linked decision chain
- Canonicalized execution records
- External anchoring capability

**Verification:**  
A third party can validate integrity without trusting the system.

### 3. Reversible Action Guarantees

Every autonomous action requires:
- a precomputed reversal plan
- a bounded rollback window
- post‑action verification

**Test:**  
Execute → rollback → system returns to pre‑action state within defined bounds.

### 4. ML Isolation from the Authority Path

The kernel has **zero ML in the authority path**:
- No ML imports in kernel modules
- No ML dependencies in core execution path
- All decision-making is deterministic and rule-based

**Verification:**  
Kernel has no ML imports; decision pipeline uses deterministic rules only.

### 5. Counterfactual Replay Capability

The system can answer, deterministically:
> "What would have happened if this action had not been taken?"

**Test:**  
Replay with action removed → divergence must be consistent across runs.

### 6. Air-Gap Integrity

The kernel has **zero network dependencies**:
- No network calls in execution path
- Zero web interfaces
- Importable as a pure Python library

**Verification:**  
Dependency audit shows zero network imports in kernel.

---

## Minimum Requirements for Autonomous Defense (Proposed Standard)

Any system claiming "autonomous response" must demonstrate:

| Requirement | Verification Method |
|-------------|---------------------|
| deterministic replay (multi-run parity) | reproducible test harness |
| cryptographic audit chain integrity | independent third-party validation |
| action reversibility guarantees | rollback demonstration |
| isolation of non-deterministic components | component disable test |
| counterfactual explainability | replay divergence analysis |
| ML isolation from authority path | dependency audit |

If a system cannot meet these requirements:

> **It is not autonomous defense.**  
> **It is probabilistic automation with limited accountability.**

---

## Deterministic Autonomy Compliance Test (DACT v0.2)

A system satisfies minimum autonomous defense criteria **only if** it passes all of the following:

### Test 1 — Replay Parity
- **Input:** identical event stream (N ≥ 3 runs)
- **Requirement:** outputs must produce identical hashes
- **Fail:** any divergence

### Test 2 — Action Reversibility
- **Input:** executed autonomous action
- **Requirement:** system returns to pre‑action state within defined bounds
- **Fail:** residual state divergence

### Test 3 — Audit Verification
- **Input:** exported audit chain
- **Requirement:** independent verifier validates integrity without system trust
- **Fail:** unverifiable or mutable records

### Test 4 — ML Isolation
- **Input:** disable all ML components
- **Requirement:** decision pipeline remains valid and deterministic
- **Fail:** degraded correctness or undefined behavior

### Test 5 — Counterfactual Consistency
- **Input:** remove action and replay
- **Requirement:** divergence analysis must be deterministic across runs
- **Fail:** inconsistent counterfactual outcomes

### Test 6 — Air-Gap Integrity
- **Input:** operate without network access
- **Requirement:** core functionality remains operational
- **Fail:** network dependencies in execution path

---

## Why This Matters (Immediate Operational Impact)

### Incident Response
- **Current:** "We think this is what happened."
- **Deterministic:** "We can prove exactly what happened."

### Legal / Compliance
- **Current:** narrative reconstruction
- **Deterministic:** cryptographically verifiable decision record

### Autonomous Action Risk
- **Current:** irreversible actions justified probabilistically
- **Deterministic:** bounded, reversible, provable actions

### Multi‑Org Coordination
- **Current:** trust‑based sharing
- **Deterministic:** verifiable, signed state exchange

### Regulatory and Liability Implications

In environments subject to audit, breach disclosure, or legal review:

- Non‑reproducible decisions may be classified as non‑verifiable controls
- Irreversible automated actions may introduce unbounded operational risk
- Unverifiable audit logs may be considered insufficient forensic evidence

As autonomous response systems proliferate, the ability to prove decision integrity will shift from differentiator to baseline expectation.

---

## Immediate Operator Action

Security teams can evaluate their current stack within 48 hours:

1. Select a recent high‑severity incident
2. Attempt deterministic replay across 3 runs
3. Attempt full action rollback
4. Attempt independent audit validation

**If any step fails:**

> The system is operating with unquantified autonomous risk that cannot be independently verified or bounded.

---

## Failure Modes of Non‑Deterministic Autonomous Systems

Systems that cannot meet the above requirements exhibit the following failure classes:

### 1. Non‑Reproducible Incidents
Identical inputs produce different outcomes.  
→ Root cause cannot be proven  
→ Incident reports are non‑verifiable

### 2. Irreversible Action Risk
Actions cannot be safely undone.  
→ Containment may introduce additional damage  
→ Autonomous response increases blast radius

### 3. Audit Chain Breakage
Logs cannot be independently validated.  
→ Forensic evidence becomes disputable  
→ Legal and regulatory exposure increases

### 4. ML‑Induced Decision Drift
Probabilistic components alter behavior over time.  
→ Same scenario yields different outcomes  
→ No stable policy baseline exists

### 5. Cross‑Org Trust Failure
No verifiable state exchange.  
→ Shared intelligence cannot be trusted  
→ Federation collapses into manual coordination

---


## What Comes Next — Future Extensions

ExoArmur Core is the single‑node proof.

Future reserved extension surfaces may include:
- federated deterministic nodes
- signed belief propagation
- sovereignty‑preserving coordination
- cross‑domain verifiable defense behavior

These are **planned, not implemented** on the current baseline.

---

## Challenge to Vendors and Operators

You do not need to agree with this doctrine.

You only need to answer four questions:

1. Can your system replay decisions deterministically?
2. Can you prove every autonomous action is reversible?
3. Can an external party verify your audit chain independently?
4. Can you remove ML and still guarantee correct operation?

**If the answer to any is "no," then:**

> Your system is not autonomous.  
> It is automation with unverifiable risk.

---

## Closing

This is not a proposal.

This is a testable boundary condition for autonomous defense.

Systems will either meet it,  
or they will be measured against it.

And once measured:

> **Systems that cannot prove their decisions will not be trusted to make them.**

---

## VERIFICATION STATUS — 2.2.0 BASELINE

*Scope: internal evaluation only. DACT v0.2 is ExoArmur's own evaluation
framework (see `docs/DACT_STANDARD_v0.2.md`), not an independent standard or
certification. No third-party audit or formal verification has been conducted.*

### Internally Evaluated Claims

| Doctrine Claim | Internal Status | Evidence / Caveat |
|---------------|-----------------|-------------------|
| 1. Deterministic Replay | Internally evaluated | Canonical JSON + deterministic IDs/clock; CI three-run stability gate. Recomputing hashes detects stored-field inconsistency, not proof that original content was preserved. |
| 2. Cryptographic Attestation | Partially supported | Canonical SHA-256 hashes over evidence payloads. `evidence_signature` is stored but signature verification is **not implemented** (`NOT_CHECKED` in `kernel/replay_verification.py`). No Ed25519 or signer verification exists on this baseline. |
| 3. Reversible Actions | Internally evaluated | FileSystemExecutor and DatabaseExecutor implement rollback plans with state-hash checks; not all executors/action classes are reversible. |
| 4. ML Isolation | Internally evaluated | Kernel packages contain no ML imports; advisory ML guidance in `docs/ML_ISOLATION.md`. |
| 5. Counterfactual Replay | Not implemented on this baseline | No counterfactual engine exists in the 2.2.0 architecture. |
| 6. Air-Gap Integrity | Internally evaluated (kernel scope) | `kernel/` and `executors/` have no network dependencies. The optional `exoarmur.api` FastAPI layer is outside this scope. |

### DACT v0.2 Self-Assessment

DACT is ExoArmur's own evaluation framework, not an independent standard
or certification. Current status per level:

- **Levels 1, 4, 5** — internally evaluated within their documented scope
  by dedicated compliance tests (`tests/compliance/`).
- **Level 2 (Cryptographic Attestation)** — partial: canonical hashes are
  computed and checked for consistency; evidence signatures are stored but
  not verified (`NOT_CHECKED`).
- **Level 3 (Counterfactual Analysis)** — not implemented; no
  counterfactual engine exists on this baseline.
- **Level 6 (Formal Verification)** — pending external/formal review.

This is self-assessment against our own framework, not certification.

### Known Gaps on This Baseline

The bounded pilot (merged on `main`, served by
`exoarmur.api.server:create_pilot_app`) now provides authenticated
API-key principals bound to server-side permissions and tenants,
digest-pinned operator policy, operator-configured (not measured) trust
inputs, durable global/tenant execution pauses enforced immediately
before dispatch, approval-bound resume of the exact frozen action, and
persisted evidence with hash-consistency verification. An operator GUI is
served at `/api/pilot/gui`.

Remaining gaps:

- The legacy `create_app` routes (`/v1/*`, `/api/v2/*`, `/api/cli/*`) and
  `/admin/consistency` remain **unauthenticated**; approval endpoints
  there accept self-asserted `operator_id` headers. They are not part of
  the supported pilot surface.
- `kernel/trust_evaluator.py` remains interface-only; pilot trust scores
  are operator-configured assertions.
- Evidence signatures are stored but not verified (`NOT_CHECKED`); the
  pilot's `verify` endpoint checks stored-content hash consistency only.
- No counterfactual engine exists on this baseline.
- Vendor executors (OpenAI, Anthropic, HuggingFace, LangChain) are scaffolds
  returning mock data.
- Pilot scope is local PostgreSQL + local workspace, filesystem
  create/modify only, unpaginated history, and ambiguous `EXECUTING`
  states are reported rather than retried.

See `docs/KNOWN_LIMITATIONS.md` for the full disclosure.

### Verification Commands

```bash
# Run tests
python -m pytest tests/ -q

# ML isolation check (kernel + executors only)
grep -r "import torch\|import transformers\|import sklearn\|import tensorflow" \
  src/exoarmur/kernel src/exoarmur/executors || echo "ML ISOLATION CLEAN"

# Air-gap check (kernel + executors only)
grep -r "import urllib\|import requests\|import socket\|import nats" \
  src/exoarmur/kernel src/exoarmur/executors || echo "AIRGAP CLEAN"
```

---

*This document pairs the theoretical framework (the Doctrine) with an honest account of what the current baseline implements. It does **not** claim that ExoArmur satisfies all stated requirements — counterfactual replay is not implemented, evidence signatures are unverified, and several doctrine properties hold only in scoped or partial form (see VERIFICATION STATUS and KNOWN_LIMITATIONS).*
