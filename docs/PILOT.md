# ExoArmur Pilot — Governed File-Write Workflow

This guide runs the bounded pilot: **one authenticated, policy-controlled
file-write workflow** with human approval of the exact proposed action,
durable global/tenant execution pauses, durable evidence with integrity
verification, and a server-served operator GUI.

Scope: local PostgreSQL + local workspace only. This is a reference
implementation, not a production deployment. See
[Known Limitations](KNOWN_LIMITATIONS.md) for precise guarantees.

## What is real vs. demo

| Component | Status |
|---|---|
| Authentication | Real — API keys verified by SHA-256 hash against `api_keys` table; permissions enforced server-side |
| Policy | Real — versioned JSON policy file pinned by an independently configured SHA-256 digest; default deny |
| Executor | Real — `FileSystemExecutor` restricted to `EXOARMUR_WORKSPACE_ROOT` (path-traversal and symlink checks) |
| Pauses | Real — durable `execution_pauses` rows re-checked immediately before dispatch |
| Evidence | Real — persisted request/decision/execution records; payload-hash consistency check (not signer verification) |
| GUI | Real — `/api/pilot/gui`, backed entirely by the pilot API |
| `/api/cli/ai-complete` | **Demo only** — allow-by-construction policy + mocked REPLAY executor; not a governed path |

## 1. Install

```bash
git clone https://github.com/slucerodev/ExoArmur-Core
cd ExoArmur-Core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,postgres,demo-api]"
```

Requires Python 3.10+ and a reachable PostgreSQL 12+ database.
Create a disposable database, e.g.:

```bash
createdb exoarmur_pilot   # or: psql -c "CREATE DATABASE exoarmur_pilot;"
```

Migrations (`api/migrations/001_init.sql`, `002_pilot.sql`) apply
automatically when the app starts.

## 2. Bootstrap principal, policy, workspace

```bash
python examples/bootstrap_pilot.py \
  --database-url "postgresql://USER:PASS@HOST:5432/exoarmur_pilot" \
  --workspace /tmp/exoarmur_pilot_ws \
  --policy-out /tmp/exoarmur_pilot/policy.json \
  --principal-id agent-1 --tenant-id tenant-1 \
  --operation fs.create_file --operation fs.modify_file \
  --action-class fs.create_file=A1_soft_containment \
  --action-class fs.modify_file=A2_hard_containment \
  --approval human --trust-score 0.9 \
  --permission action:submit --permission action:read --permission action:resume \
  --permission approval:grant --permission approval:deny \
  --permission pause:control --permission evidence:read
```

The script prints the raw API key **once** (only its SHA-256 hash is
stored), the policy file path, and the pinned policy digest. Run it a
second time with a different `--principal-id` (e.g. `operator-1`) to
create a separate approver principal — keep `approval:grant` /
`approval:deny` on the approver and `action:submit` on the agent.

## 3. Start the service

```bash
export EXOARMUR_DATABASE_URL="postgresql://USER:PASS@HOST:5432/exoarmur_pilot"
export EXOARMUR_WORKSPACE_ROOT=/tmp/exoarmur_pilot_ws
export EXOARMUR_POLICY_FILE=/tmp/exoarmur_pilot/policy.json
export EXOARMUR_POLICY_SHA256=<digest printed by bootstrap>
export EXOARMUR_APPROVAL_TTL_HOURS=24   # optional, default 24

uvicorn "exoarmur.api.server:create_app" --factory --host 127.0.0.1 --port 8000
```

The service fails closed: if the policy file is missing, altered, or the
digest does not match `EXOARMUR_POLICY_SHA256`, every governed action is
denied. If `EXOARMUR_WORKSPACE_ROOT` / policy env vars are unset, pilot
endpoints return 503.

## 4. Submit an action (agent key)

```bash
curl -X POST http://127.0.0.1:8000/api/pilot/actions \
  -H "X-API-Key: $AGENT_KEY" -H "x-exoarmur-request: 1" \
  -H "Content-Type: application/json" \
  -d '{"operation":"create_file","path":"out/hello.txt","content":"hello pilot"}'
```

Response: `{"created": true, "action": {...}}`. With `required_approval:
human` the action is `PENDING_APPROVAL` and **nothing is written yet**.
The `parameters` are frozen and hashed (`params_sha256`) at submission.

## 5. Approve / deny (approver key)

```bash
curl -X POST http://127.0.0.1:8000/api/pilot/actions/<action_id>/approve \
  -H "X-API-Key: $APPROVER_KEY" -H "x-exoarmur-request: 1"
```

On approval the stored action is re-validated (tenant, policy, pauses)
and dispatched through `ProxyPipeline` → `SafetyGate` →
`FileSystemExecutor`. The file appears under the workspace. `deny` takes
`{"reason": "..."}` and blocks execution permanently for that action.

## 6. Pause / resume execution

```bash
# Global pause (blocks every tenant)
curl -X PUT http://127.0.0.1:8000/api/pilot/pauses \
  -H "X-API-Key: $APPROVER_KEY" -H "x-exoarmur-request: 1" \
  -H "Content-Type: application/json" \
  -d '{"scope":"global","paused":true}'

# Tenant-scoped pause
curl -X PUT http://127.0.0.1:8000/api/pilot/pauses \
  -H "X-API-Key: $APPROVER_KEY" -H "x-exoarmur-request: 1" \
  -H "Content-Type: application/json" \
  -d '{"scope":"tenant","scope_key":"tenant-1","paused":true}'
```

Pauses are durable rows checked immediately before executor dispatch,
including approval resume. Resume with `"paused": false`.

## 7. Evidence and verification

```bash
curl http://127.0.0.1:8000/api/pilot/actions/<action_id> \
  -H "X-API-Key: $APPROVER_KEY"            # full record incl. evidence

curl http://127.0.0.1:8000/api/pilot/actions/<action_id>/verify \
  -H "X-API-Key: $APPROVER_KEY"            # integrity verdict
```

`verify` recomputes payload hashes against the evidence recorded at
write time. `overall: "VERIFIED"` means stored-content hash consistency;
`"MISMATCH"` means stored evidence was altered after recording.
Signature verification is reported `NOT_CHECKED` — hashes prove internal
consistency, not signer authenticity or protection against a compromised
database.

## 8. Operator GUI

Open `http://127.0.0.1:8000/api/pilot/gui`. Enter an API key to log in
(the key is kept in memory for the session only — never in browser
storage). The console shows pending approvals with exact parameters,
action history, evidence verification, active policy version, supported
operations, and pause controls. All controls call the same authenticated
API; the backend enforces permissions regardless of the GUI.

## 9. Restart durability

Stop and restart uvicorn against the same `EXOARMUR_DATABASE_URL`.
Pending approvals, completed evidence, and pause rows persist; no action
is re-dispatched on restart (an action stuck in `EXECUTING` is reported
as ambiguous, not silently retried).

## Tests

```bash
EXOARMUR_TEST_DATABASE_URL="postgresql://USER:PASS@HOST:5432/exoarmur_pilot_test" \
  python -m pytest tests/api/test_pilot.py -q
```

The suite requires a real disposable Postgres database; it is skipped
when the variable is unset and never substitutes mocks for the database
or executor.
