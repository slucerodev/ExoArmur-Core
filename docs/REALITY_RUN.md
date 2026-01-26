# ExoArmur Reality Runbook

## Cold Reviewer Reproduction Steps

### Prerequisites
- Docker and docker-compose installed
- Python 3.8+ with asyncio support
- Git repository checked out

### Single Command Reality Test

```bash
# Run complete reality scenario (Gate 4)
./scripts/reality.sh reality_run_006
```

This command:
1. Starts NATS JetStream with docker-compose
2. Runs ExoArmur injection scenario
3. Exports audit records for replay
4. Verifies replay equivalence
5. Captures all evidence artifacts
6. Produces PASS/FAIL result

### Evidence Bundle Location

All artifacts are emitted to: `artifacts/reality_run_006/`

Required artifacts for Gate 4:
- `PASS_FAIL.txt` - Explicit PASS/FAIL result
- `storage_state.json` - Storage configuration
- `audit_export.jsonl` - Durable audit export
- `replay_report.json` - Replay equivalence verification
- `docker_compose.log` - Docker execution logs
- `service.log` - Service execution logs

### Verification Steps

1. **Check PASS/FAIL status:**
   ```bash
   cat artifacts/reality_run_006/PASS_FAIL.txt
   ```

2. **Verify replay equivalence:**
   ```bash
   jq .pass artifacts/reality_run_006/replay_report.json
   ```

3. **Check evidence completeness:**
   ```bash
   ls -la artifacts/reality_run_006/
   ```

### Expected Results

For a successful Gate 4 run:
- PASS_FAIL.txt should show "FINAL STATUS: GREEN"
- replay_report.json should show `"pass": true`
- All required artifacts should be present
- Docker logs should show successful service startup

### Troubleshooting

If the test fails:
1. Check `docker_compose.log` for container issues
2. Check `service.log` for application errors
3. Verify NATS health: `docker compose logs nats`
4. Ensure no port conflicts (4222, 8222)

### Clean Environment Test

To verify from a completely clean state:
```bash
# Remove any existing volumes
docker volume ls | grep jetstream_data | awk '{print $2}' | xargs docker volume rm || true

# Run reality test
./scripts/reality.sh reality_run_clean
```

This ensures the test works from a fresh deployment without any cached state.
