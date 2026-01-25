# V2 Restrained Autonomy Demo - Developer Runbook

## Quick Troubleshooting

### PYTHONPATH Issues

The demo requires proper Python path setup to import modules without package installation:

```bash
# Set PYTHONPATH to include src and spec/contracts
export PYTHONPATH="/path/to/ExoArmur/src:/path/to/ExoArmur/spec/contracts"

# Or inline with command:
PYTHONPATH=/path/to/ExoArmur/src:/path/to/ExoArmur/spec/contracts python3 scripts/demo_v2_restrained_autonomy.py
```

**Common Error**: `ModuleNotFoundError: No module named 'spec'`
**Solution**: Ensure PYTHONPATH includes both `src` and `spec/contracts` directories.

### Feature Flag Issues

All V2 features are disabled by default. Enable required flags:

```bash
# Required flags for V2 demo
export EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true
export EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true  
export EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true
```

**Common Error**: "❌ V2 restrained autonomy is disabled"
**Solution**: Set all three required environment variables to `true`.

### Dependency Issues

The demo requires specific Python packages:

```bash
# Install required dependencies
pip install python-ulid
pip install pydantic==2.5.0
```

**Common Error**: `ModuleNotFoundError: No module named 'ulid'`
**Solution**: Install `python-ulid` package.

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|--------|----------|
| `AttributeError: 'ApprovalService' object has no attribute` | Wrong method name | Check ApprovalService interface in `src/control_plane/approval_service.py` |
| `ValidationError: belief_type Field required` | Wrong BeliefV1 model used | Ensure using first BeliefV1 definition (line ~99 in models_v1.py) |
| `REPLAY_VERIFIED=false` | Audit records not found by stream ID | Replay implementation needs enhancement (TODO) |

## Adding New Actions Safely

### Mock Executor Pattern

All actions must use the mock executor pattern to ensure safety:

```python
# In src/v2_restrained_autonomy/mock_executor.py
class MockActionExecutor:
    def execute_new_action(self, target_id: str, correlation_id: str) -> Dict[str, Any]:
        """Execute new safe action"""
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        
        # Record execution for idempotency
        self._executions[execution_id] = {
            "execution_id": execution_id,
            "action_type": "new_action",
            "target_id": target_id,
            "status": "completed",
            "mock": True,
            "executed_at": datetime.now(timezone.utc).isoformat()
        }
        
        return self._executions[execution_id]
```

### Key Safety Principles

1. **Mock by Default**: All actions should be mock implementations
2. **Idempotency**: Check `has_executed_recently()` before executing
3. **Audit Trail**: Emit audit events for all actions
4. **Approval Required**: A2/A3 actions require operator approval

### Integration Steps

1. **Add Action Type** to mock executor
2. **Update Pipeline** to call new action
3. **Add Audit Events** for action lifecycle
4. **Write Tests** for new action
5. **Update Demo** if needed for demonstration

## Extending Audit Fields

### Maintaining Replay Determinism

When adding audit fields, ensure replay compatibility:

```python
# Safe field addition (backward compatible)
new_payload = {
    "existing_field": "value",
    "new_field": "new_value"  # New fields are safe
}

# Avoid breaking changes:
# - Don't change field names/types
# - Don't remove required fields  
# - Don't change field order in deterministic ID generation
```

### Deterministic ID Generation

The `create_deterministic_id()` method ensures reproducible audit IDs:

```python
def create_deterministic_id(self, seed_data: Dict[str, Any]) -> str:
    """Create deterministic ID from seed data"""
    if self.config.deterministic_seed:
        seed_data["pipeline_seed"] = self.config.deterministic_seed
    
    # Sort keys for deterministic ordering
    seed_string = json.dumps(seed_data, sort_keys=True, separators=(',', ':'))
    hash_digest = hashlib.sha256(seed_string.encode()).hexdigest()
    
    # Convert to ULID format
    return str(ulid.ULID.from_bytes(hash_int.to_bytes(16, 'big')[:16]))
```

**Rules for Safe Extension**:
- Always use `sort_keys=True` in JSON dumps
- Include `pipeline_seed` for reproducibility
- Don't modify the hash algorithm
- Maintain ULID format compatibility

## Debug Mode

Enable verbose logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in demo script:
python3 scripts/demo_v2_restrained_autonomy.py --operator-decision deny --verbose
```

## Test Commands

### Unit Tests
```bash
# V2 demo tests only
python3 -m pytest tests/test_v2_restrained_autonomy.py -v

# With coverage
python3 -m pytest tests/test_v2_restrained_autonomy.py -v --cov=src/v2_restrained_autonomy
```

### Integration Tests
```bash
# Full test suite
python3 -m pytest tests/ -v

# Boundary gate tests (sensitive)
python3 -m pytest tests/ -v -m "sensitive"
```

### Manual Testing
```bash
# Test flags OFF (should refuse)
python3 scripts/demo_v2_restrained_autonomy.py

# Test flags ON + deny (safe)
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
PYTHONPATH=/path/to/ExoArmur/src:/path/to/ExoArmur/spec/contracts \
python3 scripts/demo_v2_restrained_autonomy.py --operator-decision deny

# Test flags ON + approve (unsafe, only for development)
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
PYTHONPATH=/path/to/ExoArmur/src:/path/to/ExoArmur/spec/contracts \
python3 scripts/demo_v2_restrained_autonomy.py --operator-decision approve
```

## CI/CD Integration

### GitHub Actions Markers

The CI job checks for these exact markers:

```bash
# Required markers for CI success
grep -q "DEMO_RESULT=DENIED" output.txt
grep -q "ACTION_EXECUTED=false" output.txt  
grep -q "AUDIT_STREAM_ID=" output.txt
grep -q "REPLAY_VERIFIED=true" replay.txt
```

### Local CI Simulation

```bash
# Simulate CI smoke test locally
EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true \
EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true \
EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true \
PYTHONPATH=/path/to/ExoArmur/src:/path/to/ExoArmur/spec/contracts \
python3 scripts/demo_v2_restrained_autonomy.py --operator-decision deny > demo_output.txt 2>&1

# Extract audit ID and test replay
AUDIT_ID=$(grep "AUDIT_STREAM_ID=" demo_output.txt | cut -d'=' -f2)
python3 scripts/demo_v2_restrained_autonomy.py --replay "$AUDIT_ID" > replay_output.txt 2>&1

# Verify markers
grep -q "DEMO_RESULT=DENIED" demo_output.txt && echo "✅ Demo marker OK"
grep -q "ACTION_EXECUTED=false" demo_output.txt && echo "✅ Action marker OK"
grep -q "AUDIT_STREAM_ID=" demo_output.txt && echo "✅ Audit ID marker OK"
```

## Performance Considerations

- **Deterministic IDs**: Hash computation is O(1) but uses crypto functions
- **Audit Storage**: In-memory storage suitable for demos, consider persistence for production
- **Feature Flag Checks**: Minimal overhead, cached after first load
- **Mock Actions**: No external dependencies, fast execution

## Security Notes

- **No Real Actions**: All actions are mocked for safety
- **Operator Approval**: Human-in-the-loop required for A2/A3 actions
- **Audit Trail**: Complete immutable record of all decisions
- **Feature Flags**: V2 capabilities disabled by default
- **Idempotency**: Prevents duplicate executions

## Getting Help

1. **Check logs**: Enable debug logging for detailed error information
2. **Verify flags**: Ensure all required environment variables are set
3. **Check dependencies**: Verify required Python packages are installed
4. **Test imports**: Manually test imports with your PYTHONPATH setup
5. **Review artifacts**: Check `docs/artifacts/v2_restrained_autonomy_demo.txt` for expected output
