#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

UNTRACKED=$(git ls-files --others --exclude-standard src/exoarmur)
if [[ -z "$UNTRACKED" ]]; then
  echo "[guard] OK: no untracked content under src/exoarmur"
  exit 0
fi

echo "[guard] ERROR: untracked paths detected under src/exoarmur" >&2
echo "$UNTRACKED" >&2

mkdir -p artifacts
MANIFEST="artifacts/untracked_src_exoarmur.json"
UNTRACKED="$UNTRACKED" python3 - <<'PY'
import hashlib, json, os, subprocess, sys, datetime
untracked = os.environ.get("UNTRACKED", "").strip().splitlines()
if not untracked:
    sys.exit(0)

def file_info(path: str):
    p = os.path.abspath(path)
    if os.path.isdir(p):
        return {"path": path, "type": "dir"}
    try:
        size = os.path.getsize(p)
    except OSError:
        size = None
    sha256 = None
    if os.path.isfile(p):
        h = hashlib.sha256()
        try:
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            sha256 = h.hexdigest()
        except OSError:
            sha256 = None
    return {"path": path, "type": "file" if os.path.isfile(p) else "other", "size": size, "sha256": sha256}

def capture(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except subprocess.CalledProcessError:
        return ""

manifest = {
    "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
    "git_head": capture("git rev-parse HEAD"),
    "branch": capture("git rev-parse --abbrev-ref HEAD"),
    "paths": [file_info(p) for p in untracked],
}
with open("artifacts/untracked_src_exoarmur.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
print(json.dumps(manifest, indent=2))
PY

exit 1
