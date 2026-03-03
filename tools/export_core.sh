#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: tools/export_core.sh <output-dir>" >&2
  exit 1
fi

OUTPUT_DIR="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"
MANIFEST="${REPO_ROOT}/tools/export_manifest_core.json"

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Output directory already exists: ${OUTPUT_DIR}" >&2
  exit 1
fi


mapfile -t PATHS < <(
  python3 - "${MANIFEST}" <<'PY'
import json
import sys
manifest_path = sys.argv[1]
with open(manifest_path, "r", encoding="utf-8") as handle:
    manifest = json.load(handle)
for path in manifest.get("paths", []):
    print(path)
PY
)

args=()
for path in "${PATHS[@]}"; do
  args+=(--path "${path}")
done

printf "Exporting core to %s\n" "${OUTPUT_DIR}"
git clone --no-local "${REPO_ROOT}" "${OUTPUT_DIR}"

if command -v git-filter-repo >/dev/null 2>&1; then
  (
    cd "${OUTPUT_DIR}"
    git filter-repo --force "${args[@]}"
  )
else
  echo "git-filter-repo not found; using legacy git filter-branch fallback." >&2
  KEEP_FILE="$(mktemp)"
  printf "%s\n" "${PATHS[@]}" > "${KEEP_FILE}"
  (
    cd "${OUTPUT_DIR}"
    KEEP_FILE="${KEEP_FILE}" git filter-branch --force --prune-empty --index-filter '
      git rm -r --cached -q .
      while IFS= read -r path; do
        git reset -q "$GIT_COMMIT" -- "$path" >/dev/null 2>&1 || true
      done < "$KEEP_FILE"
    ' -- --all
  )
  rm -f "${KEEP_FILE}"
fi

printf "Core export complete: %s\n" "${OUTPUT_DIR}"
