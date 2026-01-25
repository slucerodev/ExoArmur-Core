# ExoArmur Constitution

## GLOBAL GOVERNANCE (APPLIES TO ALL PHASES)

### G0 — V1 IMMUTABILITY
- V1 contracts, models, schemas, and Golden Demo behavior are immutable
- Any modification altering V1 behavior is forbidden
- V1 functionality must remain exactly as originally delivered

**Enforcing Tests:**
- `tests/test_api_models.py` - API model contract compliance
- `tests/test_integration.py` - V1 Golden Demo integration
- `scripts/demo_handshake.py` - Original V1 demo must pass unchanged

### G1 — BINARY GREEN ONLY
- No skipped tests allowed
- No temporary failures permitted
- Every phase must end with full green test suite + boundary gate
- If any test fails, fix immediately before proceeding

**Enforcing Tests:**
- `conftest.py` - Automatic test collection and boundary enforcement
- `python3 -m pytest tests/` - Full suite must pass
- `python3 -m pytest tests/ -m sensitive` - Boundary gate must pass

### G2 — ADDITIVE ONLY
- All new functionality must live in V2 modules or new packages
- Feature flags must default to OFF
- No replacement of working V1 paths

**Enforcing Tests:**
- `src/feature_flags/feature_flags.py` - All flags default to False
- `tests/test_v2_restrained_autonomy.py` - V2 functionality behind flags
- `python3 scripts/demo_v2_restrained_autonomy.py` - Refuses when flags OFF

### G3 — DETERMINISM
- No wall-clock dependence in core logic
- All randomness must be seeded and logged
- Replay must reproduce identical outcomes and hashes
- All time usage goes through injected Clock interface

**Enforcing Tests:**
- `src/v2_restrained_autonomy/pipeline_impl.py` - Deterministic ID generation
- `tests/test_v2_restrained_autonomy.py::TestDeterministicAuditAndReplay` - Replay verification
- `scripts/demo_v2_restrained_autonomy.py --replay` - Audit stream replay

### G4 — NO BACKWARDS MOVEMENT
- No removal of gates, tests, or enforcement mechanisms
- No refactors that reduce safety or coverage
- Do not rename files or concepts globally unless explicitly required

**Enforcing Tests:**
- All existing tests must continue to pass
- No test deletions allowed without phase roadmap justification
- Boundary gate tests must remain and strengthen over time

### G5 — SAFE DEFAULTS
- All demos and adapters default to deny / no-op / simulated behavior
- No destructive actions in default configuration
- Real effectors must be simulated first

**Enforcing Tests:**
- `scripts/demo_v2_restrained_autonomy.py` - Defaults to deny mode
- `src/v2_restrained_autonomy/mock_executor.py` - All actions are simulated
- Demo smoke test requires `DEMO_RESULT=DENIED` and `ACTION_EXECUTED=false`

## FORBIDDEN CHANGES (EXPLICITLY PROHIBITED)

### V1 Contract Changes
- ❌ Modifying any field in `spec/contracts/models_v1.py` V1 classes
- ❌ Changing V1 API response schemas
- ❌ Altering V1 Golden Demo behavior or outputs
- ❌ Removing or weakening V1 validation rules

### Safety Mechanism Removal
- ❌ Removing feature flag checks
- ❌ Disabling approval requirements
- ❌ Removing audit event emission
- ❌ Weakening idempotency checks

### Test Reduction
- ❌ Deleting existing tests
- ❌ Skipping test failures
- ❌ Weakening assertions
- ❌ Removing boundary gate enforcement

### Default Behavior Changes
- ❌ Making demos default to approve/execute
- ❌ Removing mock/simulation defaults
- ❌ Enabling V2 features by default

## INVARIANT ENFORCEMENT

### 1. Feature Flag Enforcement
```python
# All V2 functionality must check flags
if not self.feature_flags.is_v2_control_plane_enabled():
    return ActionOutcome(action_taken=False, refusal_reason="V2 disabled")
```

### 2. Audit Trail Completeness
```python
# Every state transition must emit audit events
self.emit_audit_event(correlation_id, trace_id, tenant_id, cell_id, 
                     "event_kind", payload_data, audit_stream_id)
```

### 3. Deterministic ID Generation
```python
# All IDs must be reproducible under same inputs
def create_deterministic_id(self, seed_data: Dict[str, Any]) -> str:
    seed_string = json.dumps(seed_data, sort_keys=True, separators=(',', ':'))
    hash_digest = hashlib.sha256(seed_string.encode()).hexdigest()
    return str(ulid.ULID.from_bytes(hash_int.to_bytes(16, 'big')[:16]))
```

### 4. Safe Default Enforcement
```python
# All actions must default to safe behavior
class MockActionExecutor:
    def execute_isolate_endpoint(self, endpoint_id: str, correlation_id: str):
        # Always simulated, never real
        return {"execution_id": f"exec-{uuid.uuid4().hex[:12]}", "mock": True}
```

## PHASE GATES

Each phase must pass these gates before proceeding:

### Gate Requirements
1. **Clean Environment**: `pip install -e .` works from fresh venv
2. **Full Test Suite**: `python3 -m pytest tests/` passes completely
3. **Boundary Gate**: `python3 -m pytest tests/ -m sensitive` passes
4. **Demo Verification**: `python3 src/cli.py demo --operator-decision deny` works
5. **Replay Proof**: Audit stream replay produces consistent results
6. **CLI verify_all**: `python3 src/cli.py verify-all` passes

### Gate Enforcement Commands
```bash
# Complete gate verification
python3 src/cli.py verify-all

# Individual gate components
python3 -m pytest tests/                    # Full suite
python3 -m pytest tests/ -m sensitive      # Boundary gate  
python3 src/cli.py demo --operator-decision deny  # Demo smoke
python3 src/cli.py health                   # Health check
```

## CONSTITUTIONAL VIOLATION RESPONSES

### Minor Violations
- Fix immediately without weakening tests
- Document root cause and prevention
- Add regression test if needed

### Major Violations
- Stop all work immediately
- Revert to last known good state
- Conduct constitutional review
- Require explicit approval before proceeding

### Repeat Violations
- Constitutional review required
- Process improvement mandatory
- Additional safeguards required

## AMENDMENT PROCESS

Constitutional amendments require:
1. Explicit justification in roadmap phase
2. Risk assessment and mitigation plan
3. Updated enforcement tests
4. Documentation of invariant changes
5. Review and approval from build engineer

## COMPLIANCE VERIFICATION

Use these commands to verify constitutional compliance:

```bash
# Verify all constitutional invariants
python3 src/cli.py verify-all

# Check specific invariants
python3 -m pytest tests/ -k "v2_disabled"     # V1 immutability
python3 -m pytest tests/ -m "sensitive"       # Boundary gate
python3 src/cli.py demo --operator-decision deny  # Safe defaults

# Verify deterministic behavior
python3 scripts/demo_v2_restrained_autonomy.py --replay <audit_id>
```

---

**This constitution is binding for all phases of the ExoArmur Max Build Roadmap.**  
**Violations must be corrected immediately before proceeding with any development work.**
