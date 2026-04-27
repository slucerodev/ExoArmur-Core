# ExoArmur ADMO Governance

## Binary Green Definition

**Green means exactly:**
- 0 failed tests
- 0 errors
- 0 **unexpected** skipped tests (see Allowed Skip Catalog below)

Any failure or unexplained skip is **red** and blocks deployment.

## Allowed Skip Catalog

The following skips are **explicitly permitted** because they gate on external
components that are intentionally optional:

| Test file | Skip reason | Activation |
|---|---|---|
| `tests/integration/test_core_dpo_integration.py` | `exoarmur_dpo` package not installed | `pip install exoarmur-dpo` |
| `tests/test_execution_boundary_v2_http_executor_integration.py` | HTTP Executor Plugin not available | Install external plugin |
| `tests/test_execution_boundary_v2_filesystem_executor_integration.py` | Filesystem executor package not available | Install external plugin |
| `tests/test_golden_demo_live.py` | Requires `EXOARMUR_LIVE_DEMO=1` + NATS JetStream | `docker compose up -d && EXOARMUR_LIVE_DEMO=1 pytest ...` |
| `tests/test_plugin_registry.py` | PoD provider not installed | Install PoD provider |
| `tests/test_schema_snapshots.py` | No schema change waivers file found | Only runs when waivers file is committed |

**Current expected counts:** 1166 passing, **10 skipped (all from catalog above)**, 3 xfailed.
Any new skip reason that is not in this catalog is a governance violation
and must either be added here (with approval) or eliminated.

## No Unannounced pytest.skip Policy

**Any `pytest.skip` or `pytest.importorskip` introduced by a PR must:**
- Appear in the Allowed Skip Catalog above, **or**
- Be converted to `pytest.xfail(strict=True, reason="...")`, **or**
- Be removed and the test rewritten to execute unconditionally

No conditional skips based on undocumented environment assumptions.
No silent `try/except ImportError → skip` without a corresponding catalog entry.

## xfail(strict=True) Policy

**Allowed only for future acceptance gates:**
- Must use `xfail(strict=True, reason="Explicit reason")`
- Reason must clearly indicate this is a future implementation gate
- When implementation causes XPASS, the xfail must be removed immediately
- No xfail for "todo" items, "nice to have", or convenience

**Valid xfail reasons:**
- "V2 federation not yet implemented (Phase 2)"
- "V2 operator approval not yet implemented (Phase 2)"
- "Requires live NATS JetStream - mock implementation is NOT acceptance"

**Invalid xfail reasons:**
- "TODO: implement this feature"
- "Not ready yet"
- "Works on my machine"

## No Masking Policy

**Zero tolerance for error masking:**
- No try/except blocks that hide failures
- No conditional test execution that skips validation
- No environment-based test exclusion
- All failures must surface immediately

## Governance Exception Process

**When an exception is needed:**
1. Document the specific requirement in a GitHub issue
2. Propose the exception with clear rationale and impact assessment
3. Request review from architecture team
4. If approved, document the decision in this file with:
   - Exception description
   - Approval date and reviewer
   - Sunset condition (when exception expires)
   - Monitoring requirements

**Example exception documentation:**
```markdown
## Exception: Temporary Test Infrastructure Limitation
- **Approved**: 2025-01-20 by @architecture-lead
- **Reason**: CI environment lacks NATS JetStream cluster
- **Sunset**: When CI JetStream is provisioned (Q2 2025)
- **Monitoring**: Weekly review of CI test coverage
```

## Enforcement

**Automated checks:**
- CI pipeline validates zero pytest.skip occurrences
- CI pipeline validates zero skipped tests
- CI pipeline validates all xfail have proper reasons
- CI pipeline runs Golden Demo as mandatory gate

**Manual reviews:**
- Pull requests must maintain binary green
- Architecture team reviews any governance changes
- Monthly audit of compliance metrics

## Violation Consequences

**First occurrence:**
- Immediate rollback of violating changes
- Team education on governance requirements
- Documentation of violation in team records

**Repeated occurrences:**
- Elevated review requirements for team
- Mandatory governance training
- Potential access restrictions to critical paths

## Compliance Verification

**Run these commands to verify compliance:**
```bash
# Check for pytest.skip (must return no results)
grep -R "pytest\.skip" -n . --exclude-dir=venv

# Check for allow_module_level=True (must return no results)  
grep -R "allow_module_level=True" -n . --exclude-dir=venv

# Verify test counts (must show exactly the cataloged skips, 0 failures)
pytest -q

# Verify xfail reasons are appropriate
pytest -q -rxX
```

**Expected output:**
- `pytest.skip` grep: only inside tests listed in the Allowed Skip Catalog
- `allow_module_level=True` grep: no results
- pytest summary: `1166 passed, 10 skipped, 3 xfailed, 0 failed, 0 errors`
- Each skip message must match one of the reasons in the Allowed Skip Catalog
- xfail reasons: only future implementation gates

## Philosophy

ExoArmur governance exists to ensure:
- **Reliability**: Binary green means system works
- **Safety**: No masking means problems are visible
- **Predictability**: Locked core means behavior is preserved by regression gates and release policy
- **Accountability**: Strict policies mean clear ownership
- **Authority Clarity**: Control plane coordinates but never executes V1 actions
- **Policy Integrity**: Signed V1 policy bundles cannot be mutated by V2 layers

## Control Plane Authority Boundaries

**The control plane may:**
- Coordinate multi-cell workflows
- Request human operator approval
- Orchestrate external approval procedures
- Distribute policy bundles (unchanged)
- Coordinate emergency response

**The control plane may NEVER:**
- Directly execute actions inside V1 cognition pipeline
- Mutate signed V1 policy bundles
- Override V1 safety gate decisions
- Modify V1 audit trails

## Reversible Action Guarantees (Doctrine Claim 3)

Per The ExoArmur Doctrine, every autonomous action requires:
- **Precomputed reversal plan** — rollback steps defined before execution
- **Bounded rollback window** — time limit within which rollback must complete
- **Post-rollback verification** — proof that state matches pre-action state

### Action Classification System

All actions are classified by reversibility level:

| Class | Name | Reversible | Rollback | Approval Required |
|-------|------|------------|----------|-------------------|
| A0 | OBSERVE | ✅ Always | N/A (no side effects) | No |
| A1 | SOFT_CONTAINMENT | ✅ Yes | Within 300s window | No |
| A2 | HARD_CONTAINMENT | ⚠️ Difficult | Limited recovery | Yes |
| A3 | IRREVERSIBLE | ❌ Never | N/A | Explicit approval |

### Implementation Requirements

**For A1 (Reversible) Actions:**
1. Pre-action state snapshot captured and hashed
2. Reversal plan generated with explicit rollback steps
3. Action executed with audit trail
4. Post-action state captured
5. Rollback executed within bounded window (300s default)
6. Post-rollback state verified against pre-action hash

**Verification Command:**
```bash
python examples/reversible_action_demo.py
# Expected: REVERSIBILITY_CLAIM=VERIFIED
```

### Lifecycle State Machine Integration

The `LifecycleStateMachine` includes explicit rollback states:
- `START_ROLLBACK` — Initiated on commit failure or explicit rollback request
- `ROLLING_BACK` — Rollback steps executing
- `ROLLBACK_COMPLETE` — All steps finished
- `ROLLED_BACK` — Final state, ready for finalization

### Governance Enforcement

- No A2 or A3 action executes without explicit approval record
- All A1 actions have automatically generated reversal plans
- Rollback window violations trigger audit alerts
- State hash mismatches after rollback escalate to incident

See `examples/reversible_action_demo.py` for complete demonstration.

## Phase Completion Records

### Phase 2A: Federation Identity Handshake - COMPLETED ✅

**Status:** ACCEPTED and LOCKED
**Date:** 2026-01-22
**Test Evidence:** 166 passed, 2 skipped, 12 xfailed, 0 failed, 0 errors

**Key Deliverables:**
- Deterministic identity handshake state machine
- Replay-capable audit trail with integrity validation
- Feature-flag isolated V2 federation modules
- V1/V2 architectural boundary via AuditInterface adapter pattern
- 104 Phase 2A tests with comprehensive negative-path coverage

**Safety Guarantees:**
- Identity handshake is deterministic and replayable
- All V2 modules inert when federation=False
- No direct V1 imports in V2 modules
- Audit trail integrity validation prevents tampering
- Phase Gate enforcement prevents unauthorized activation

**Critical Issues Resolved:**
- ✅ Unused import pollution removed
- ✅ Feature flag isolation verified correct
- ✅ V1/V2 architectural boundary fixed via AuditInterface

This governance enables autonomous defense operations with confidence that the system behaves exactly as specified and tested.
