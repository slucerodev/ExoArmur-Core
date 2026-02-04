#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: tools/export_module.sh <module-name> <output-dir>" >&2
  exit 1
fi

MODULE_NAME="$1"
OUTPUT_DIR="$2"
REPO_ROOT="$(git rev-parse --show-toplevel)"
MANIFEST="${REPO_ROOT}/modules/${MODULE_NAME}/export_manifest.json"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Missing manifest: ${MANIFEST}" >&2
  exit 1
fi

if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Output directory already exists: ${OUTPUT_DIR}" >&2
  exit 1
fi

MODULE_PATH=$(python3 - "${MANIFEST}" <<'PY'
import json
import sys
manifest_path = sys.argv[1]
with open(manifest_path, "r", encoding="utf-8") as handle:
    manifest = json.load(handle)
print(manifest["module_path"])
PY
)

PATH_RENAME=$(python3 - "${MANIFEST}" <<'PY'
import json
import sys
manifest_path = sys.argv[1]
with open(manifest_path, "r", encoding="utf-8") as handle:
    manifest = json.load(handle)
print(manifest.get("path_rename", ""))
PY
)

if command -v git-filter-repo >/dev/null 2>&1; then
  printf "Exporting module %s to %s (git-filter-repo)\n" "${MODULE_NAME}" "${OUTPUT_DIR}"
  git clone --no-local "${REPO_ROOT}" "${OUTPUT_DIR}"
  (
    cd "${OUTPUT_DIR}"
    if [[ -n "${PATH_RENAME}" ]]; then
      git filter-repo --force --path "${MODULE_PATH}" --path-rename "${PATH_RENAME}:"
    else
      git filter-repo --force --path "${MODULE_PATH}"
    fi
  )
else
  printf "Exporting module %s to %s (git subtree split fallback)\n" "${MODULE_NAME}" "${OUTPUT_DIR}"
  SPLIT_BRANCH="split-${MODULE_NAME}"
  git -C "${REPO_ROOT}" subtree split --prefix "${MODULE_PATH}" -b "${SPLIT_BRANCH}"
  git clone --no-local --branch "${SPLIT_BRANCH}" "${REPO_ROOT}" "${OUTPUT_DIR}"
  git -C "${REPO_ROOT}" branch -D "${SPLIT_BRANCH}"
fi

printf "Module export complete: %s\n" "${OUTPUT_DIR}"
