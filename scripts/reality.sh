#!/usr/bin/env bash
set -euo pipefail

# ExoArmur Reality Command
# Single command to run full reality scenario with docker-compose

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts"

RUN_ID="${1:-reality_run_$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_DIR="${ARTIFACTS_DIR}/${RUN_ID}"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "${RUN_DIR}/service.log" ; }

mkdir -p "${RUN_DIR}"

main() {
    log "Starting ExoArmur reality deployment: ${RUN_ID}"
    
    # Bring up docker-compose stack
    log "Starting docker-compose stack"
    docker-compose -f "${ROOT_DIR}/docker-compose.yml" up -d
    
    # Wait for NATS to be healthy
    log "Waiting for NATS to be healthy"
    timeout 60 bash -c 'until docker-compose -f "'"${ROOT_DIR}"'/docker-compose.yml" ps -q nats | xargs -I {} docker inspect {} --format="{{.State.Health.Status}}" | grep -q healthy; do sleep 2; done'
    
    # Additional wait for NATS to be fully ready
    log "Waiting additional time for NATS to be ready"
    sleep 5
    
    # Run injection scenario from host
    log "Running injection scenario"
    python3 "${ROOT_DIR}/scripts/reality_inject.py" \
        --nats "nats://127.0.0.1:4222" \
        --stream "EXOARMUR_AUDIT_V1" \
        --out "${RUN_DIR}/audit_record.json"
    
    # Export audit records
    log "Exporting audit records"
    python3 "${ROOT_DIR}/scripts/reality_export_simple.py" \
        --injection "${RUN_DIR}/audit_record.json" \
        --out "${RUN_DIR}/audit_export.jsonl"
    
    # Run replay verification
    log "Running replay verification"
    python3 "${ROOT_DIR}/scripts/reality_replay_verify.py" \
        --audit-export "${RUN_DIR}/audit_export.jsonl" \
        --out "${RUN_DIR}/replay_report.json"
    
    # Capture storage state
    log "Capturing storage state"
    {
        echo "STORAGE_TYPE: docker_volume"
        echo "STREAM_NAME: EXOARMUR_AUDIT_V1"
        echo "STORE_DIR: /data/jetstream (docker volume)"
        echo "CAPTURED_AT: $(date -u +%FT%TZ)"
    } >"${RUN_DIR}/storage_state.json"
    
    # Capture docker logs
    log "Capturing docker logs"
    docker-compose -f "${ROOT_DIR}/docker-compose.yml" logs >"${RUN_DIR}/docker_compose.log" 2>&1
    
    # Determine pass/fail status
    if python3 -c "import json; r=json.load(open('${RUN_DIR}/replay_report.json')); raise SystemExit(0 if r.get('pass') is True else 1)"; then
        cat >"${RUN_DIR}/PASS_FAIL.txt" <<EOF
TARGET GATE: 4
FINAL STATUS: GREEN
GATE 4: PASS (docker-compose deployment and replay verified).
EOF
        log "Gate 4: PASS - Docker deployment and replay verified"
    else
        cat >"${RUN_DIR}/PASS_FAIL.txt" <<EOF
TARGET GATE: 4
FINAL STATUS: RED
GATE 4: FAIL (docker-compose deployment or replay failed).
EOF
        log "Gate 4: FAIL - See replay_report.json"
    fi
    
    # Bring down stack
    log "Bringing down docker-compose stack"
    docker-compose -f "${ROOT_DIR}/docker-compose.yml" down -v || true
    
    log "Reality deployment completed: ${RUN_ID}"
    echo "Evidence bundle: ${RUN_DIR}"
}

trap 'docker-compose -f "'"${ROOT_DIR}"'/docker-compose.yml" down -v || true' EXIT
main
