#!/usr/bin/env bash
set -euo pipefail

# ExoArmur Reality Batch Harness (Gate-aware)
# Goals:
# - Standardize evidence bundles
# - Allow running Gate 3+ without redoing earlier gates
# - Produce cold-review artifacts with explicit PASS/FAIL

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"

RUN_ID="${1:-reality_run_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="${ARTIFACTS_DIR}/${RUN_ID}"

# Gate control:
#   GATE=3 bash scripts/reality_batch.sh reality_run_005
#   GATE=4 bash scripts/reality_batch.sh reality_run_006
GATE="${GATE:-3}"

# Stable durable store dir (MUST NOT be ephemeral if you want Gate 2+4)
STORE_DIR="${STORE_DIR:-${ROOT_DIR}/data/jetstream}"

NATS_URL="${NATS_URL:-nats://127.0.0.1:4222}"
STREAM_NAME_AUDIT="${STREAM_NAME_AUDIT:-EXOARMUR_AUDIT_V1}"
KV_BUCKET_IDEM="${KV_BUCKET_IDEM:-EXOARMUR_IDEMPOTENCY_V1}"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${RUN_DIR}/service.log" ; }
require_bin() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required binary: $1" >&2; exit 2; }; }

mkdir -p "${RUN_DIR}"
mkdir -p "${STORE_DIR}"

# --- NATS lifecycle (local) ---------------------------------------------------
start_nats() {
  require_bin nats-server
  log "Starting NATS JetStream with store_dir=${STORE_DIR}"
  nohup nats-server -js -sd "${STORE_DIR}" -p 4222 >"${RUN_DIR}/nats.log" 2>&1 &
  echo $! >"${RUN_DIR}/nats.pid"
  sleep 1
}

stop_nats() {
  if [[ -f "${RUN_DIR}/nats.pid" ]]; then
    local pid; pid="$(cat "${RUN_DIR}/nats.pid")"
    log "Stopping NATS pid=${pid}"
    kill "${pid}" || true
    sleep 1
  fi
}

capture_store_listing() {
  log "Capturing store_dir listing"
  {
    echo "STORE_DIR=${STORE_DIR}"
    ls -la "${STORE_DIR}" || true
    echo
    find "${STORE_DIR}" -maxdepth 6 -type f -print -exec ls -la {} \; 2>/dev/null || true
    echo
    du -ah "${STORE_DIR}" 2>/dev/null || true
  } >"${RUN_DIR}/store_dir_listing.txt"
}

capture_storage_state() {
  # Use nats CLI if present for authoritative stream info.
  if command -v nats >/dev/null 2>&1; then
    log "Capturing JetStream state via nats CLI"
    # Stream info
    nats --server "${NATS_URL}" stream info "${STREAM_NAME_AUDIT}" --json \
      >"${RUN_DIR}/storage_state.json" || true
    # KV info (if it exists)
    nats --server "${NATS_URL}" kv info "${KV_BUCKET_IDEM}" --json \
      >"${RUN_DIR}/kv_state.json" || true
  else
    log "nats CLI not found; writing minimal storage_state.json"
    cat >"${RUN_DIR}/storage_state.json" <<EOF
{
  "storage_type": "file",
  "stream_name": "${STREAM_NAME_AUDIT}",
  "store_dir": "${STORE_DIR}",
  "captured_at_utc": "$(date -u +%FT%TZ)"
}
EOF
  fi
}

write_passfail() {
  local gate="$1" status="$2" reason="${3:-}"
  cat >"${RUN_DIR}/PASS_FAIL.txt" <<EOF
TARGET GATE: ${gate}
FINAL STATUS: ${status}
${reason}
EOF
}

# --- Repo-provided python entrypoints ----------------------------------------
# These MUST exist in-repo. If they don't, that is the next required work item.
inject_once() {
  log "Injecting known scenario (once)"
  python3 "${ROOT_DIR}/scripts/reality_inject.py" \
    --nats "${NATS_URL}" \
    --stream "${STREAM_NAME_AUDIT}" \
    --out "${RUN_DIR}/audit_record.json"
}

export_audit() {
  log "Exporting audit stream for cold replay"
  python3 "${ROOT_DIR}/scripts/reality_export_simple.py" \
    --injection "${RUN_DIR}/audit_record.json" \
    --out "${RUN_DIR}/audit_export.jsonl"
}

replay_and_verify_gate3() {
  log "Replaying from durable export and verifying equivalence (Gate 3)"
  python3 "${ROOT_DIR}/scripts/reality_replay_verify.py" \
    --audit-export "${RUN_DIR}/audit_export.jsonl" \
    --out "${RUN_DIR}/replay_report.json"
}

verify_gate2_state() {
  # Optional sanity only; Gate 2 is already GREEN in your stated timeline.
  log "Running Gate 2 verifier (sanity only)"
  python3 "${ROOT_DIR}/scripts/reality_verify.py" \
    --nats "${NATS_URL}" \
    --stream "${STREAM_NAME_AUDIT}" \
    --store-dir "${STORE_DIR}" \
    --out "${RUN_DIR}/evidence.json" \
    --idempotency-out "${RUN_DIR}/idempotency_check.json" \
    --gate "2"
}

compose_up() {
  require_bin docker
  require_bin docker-compose || true
  log "Bringing up docker-compose stack (Gate 4)"
  docker compose -f "${ROOT_DIR}/docker-compose.yml" up -d --build
}

compose_down() {
  if [[ -f "${ROOT_DIR}/docker-compose.yml" ]]; then
    log "Bringing down docker-compose stack"
    docker compose -f "${ROOT_DIR}/docker-compose.yml" down -v || true
  fi
}

main() {
  log "Reality batch run started: ${RUN_ID}"
  log "RUN_DIR=${RUN_DIR}"
  log "GATE=${GATE}"

  # For Gate 3 runs, we still need a broker; for Gate 4, prefer compose.
  if [[ "${GATE}" == "4" ]]; then
    compose_up
    # In compose mode, NATS_URL likely differs; allow override by env.
    capture_storage_state
    inject_once
    export_audit
    replay_and_verify_gate3
    capture_store_listing
    # Pass/fail is written by verifier scripts; this file is still required
    write_passfail "4" "SEE replay_report.json / evidence.json" "Gate 4 verification is via artifacts."
    log "Gate 4 run completed: ${RUN_ID}"
    return 0
  fi

  # Default: local broker (Gate 3)
  start_nats
  capture_storage_state
  inject_once

  # OPTIONAL sanity: verify gate 2 mechanics are still intact
  # Comment this out if you want Gate 3 only.
  verify_gate2_state

  export_audit
  replay_and_verify_gate3
  capture_storage_state
  capture_store_listing

  # Gate 3 pass/fail must be explicit. If replay_report.json has "pass": true, mark pass.
  if python3 -c "import json; r=json.load(open('${RUN_DIR}/replay_report.json')); raise SystemExit(0 if r.get('pass') is True else 1)"; then
    write_passfail "3" "GREEN" "GATE 3: PASS (replay equivalence verified)."
  else
    write_passfail "3" "RED" "GATE 3: FAIL (replay equivalence not verified)."
    log "Gate 3 failed; see replay_report.json"
    exit 1
  fi

  log "Gate 3 run completed: ${RUN_ID}"
}

trap 'stop_nats || true; compose_down || true' EXIT
main
