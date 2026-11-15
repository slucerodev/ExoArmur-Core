# ExoArmur Pilot — Governed File-Write Workflow

This guide runs the bounded pilot: **one authenticated, policy-controlled
file-write workflow** with human approval of the exact proposed action,
durable global/tenant execution pauses, durable evidence with integrity
verification, and a server-served operator GUI.

Scope: local PostgreSQL + local workspace only. This is a reference
implementation, not a production deployment. See
[Known Limitations](KNOWN_LIMITATIONS.md) for precise guarantees.

Operational semantics worth stating plainly:

- ExoArmur governs only actions submitted through `/api/pilot/*`. An agent
  must be integrated to route its file writes through this API — ExoArmur
  does not automatically intercept an agent's other filesystem access.
- Trust scores and safety inputs are **operator-configured values** in the
  policy file, not measured or verified signals.
- Pauses block **subsequent dispatch**: they prevent pending/approved
  actions from executing, but do not interrupt an effect already running.
- Evidence verification is stored-content hash consistency — it detects
  altered stored records, not signer authenticity or a compromised database.

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

The pilot is installed **from source**. The published PyPI package
(`exoarmur-core` 2.1.0 at time of writing) predates the pilot and does not
contain `create_pilot_app` or the pilot routes — do not use it for this
guide.

Operator install (runtime dependencies only):

```bash
git clone https://github.com/slucerodev/ExoArmur-Core
cd ExoArmur-Core
git checkout main
python -m venv .venv && source .venv/bin/activate
pip install -e ".[postgres,demo-api]"
```

- `postgres` provides `asyncpg` (required — the pilot stores all state in PostgreSQL)
- `demo-api` provides FastAPI/uvicorn/httpx (required — the pilot is an HTTP service)
- Add `dev` (`pip install -e ".[dev]"`) only if you intend to run the test suite

Requires Python 3.10+ and a reachable PostgreSQL 12+ database.
Create a disposable database, e.g.:

```bash
createdb exoarmur_pilot   # or: psql -c "CREATE DATABASE exoarmur_pilot;"
```

Migrations (`api/migrations/001_init.sql`–`003_session_key_binding.sql`) apply
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
  --permission action:submit --permission action:read --permission action:resume
```

This first run creates the **agent** principal (submitter) plus the
operator policy file. Approval, pause, and evidence permissions belong
to the approver principal created next.

The script prints the raw API key **once** (only its SHA-256 hash is
stored), the policy file path, and the pinned policy digest. **Save the
agent key and the printed digest** — the digest is what
`EXOARMUR_POLICY_SHA256` must be set to.

Create the approver as a **credential-only** principal so the agent's
policy rule is preserved (this writes only an `api_keys` row — no policy
file is created or overwritten):

```bash
python examples/bootstrap_pilot.py \
  --credentials-only \
  --database-url "postgresql://USER:PASS@HOST:5432/exoarmur_pilot" \
  --principal-id operator-1 --tenant-id tenant-1 \
  --permission approval:grant --permission approval:deny \
  --permission action:read --permission pause:control --permission evidence:read
```

Keep `action:submit`/`action:resume` on the agent key and
`approval:grant`/`approval:deny` on the approver key. The service keeps
using the **agent policy file and its original digest** — the approver
needs no policy rule because approvals re-validate the action's stored
principal against that policy.

## 3. Start the service

```bash
export EXOARMUR_DATABASE_URL="postgresql://USER:PASS@HOST:5432/exoarmur_pilot"
export EXOARMUR_WORKSPACE_ROOT=/tmp/exoarmur_pilot_ws
export EXOARMUR_POLICY_FILE=/tmp/exoarmur_pilot/policy.json
export EXOARMUR_POLICY_SHA256=<digest printed by bootstrap>
export EXOARMUR_APPROVAL_TTL_HOURS=24   # optional, default 24

uvicorn "exoarmur.api.server:create_pilot_app" --factory --host 127.0.0.1 --port 8000
```

`create_pilot_app` is the **supported pilot surface**: it mounts only
`/health` and `/api/pilot/*`. The legacy/demo routers (`/v1/*`,
`/api/v2/*`, `/api/cli/*`) are not exposed there; they remain available
separately and unauthenticated via `exoarmur.api.server:create_app` for
the deterministic demo/CLI surface — do not use `create_app` for pilot
deployments.

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
  -d '{"scope":"tenant","tenant_id":"tenant-1","paused":true}'
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

Open `http://127.0.0.1:8000/api/pilot/gui` (served by the pilot app). Enter an API key to log in
(the key is kept in memory for the session only — never in browser
storage). The console shows:

- an approval queue with a review panel displaying the exact frozen
  content, requester, target, expiry, and approval requirement before
  "Approve & execute" (which dispatches immediately after re-checks);
- action history with readable outcomes, blocking reasons, an execution
  timeline, evidence verification scope, and collapsible raw records;
- independent global/tenant pause controls with scoped resume
  confirmation, disabled when the principal lacks `pause:control` or the
  pause is already in the requested state;
- a plain-language policy summary with the raw rules expandable;
- connection freshness and automatic refresh every 15s while the tab is
  visible (manual refresh always available; failures are shown explicitly).

Controls are permission-aware for usability only — the backend enforces
every permission regardless of the GUI.

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
