#!/usr/bin/env bash
# ExoArmur live demo steps — runs automatically inside asciinema recording
# This script is meant to be driven by record_demo.sh

set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

pause() { sleep "${1:-1.5}"; }

banner() {
  echo ""
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD}  $1${RESET}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  pause 1
}

clear
echo -e "${BOLD}ExoArmur — Deterministic Execution Governance for AI Agents${RESET}"
echo -e "${CYAN}github.com/slucerodev/ExoArmur-Core${RESET}"
pause 2

# ── Step 1: Install ──────────────────────────────────────────────
banner "Step 1 — Install from source"
echo -e "${YELLOW}\$ pip install -e .${RESET}"
pause 1
pip install -e . -q
echo -e "${GREEN}✅ Installed${RESET}"
pause 1

# ── Step 2: Version check ────────────────────────────────────────
banner "Step 2 — CLI version check"
echo -e "${YELLOW}\$ exoarmur --version${RESET}"
pause 0.5
exoarmur --version
pause 1

# ── Step 3: Health check ─────────────────────────────────────────
banner "Step 3 — Governed runtime health check"
echo -e "${YELLOW}\$ exoarmur health${RESET}"
pause 0.5
exoarmur health
pause 1.5

# ── Step 4: Governance demo — policy DENIES the action ──────────
banner "Step 4 — AI action hits governance boundary → DENIED"
echo -e "${YELLOW}\$ exoarmur demo${RESET}"
pause 0.5
exoarmur demo
pause 2

# ── Step 5: Cryptographic proof bundle ──────────────────────────
banner "Step 5 — Generate cryptographic proof of decision"
echo -e "${YELLOW}\$ exoarmur proof${RESET}"
pause 0.5
exoarmur proof
pause 2

# ── Step 6: Full canonical truth reconstruction demo ─────────────
banner "Step 6 — Canonical truth reconstruction + replay verification"
echo -e "${YELLOW}\$ python demos/canonical_truth_reconstruction_demo.py${RESET}"
pause 0.5
python demos/canonical_truth_reconstruction_demo.py 2>/dev/null | grep -E "DEMO_RESULT|ACTION_EXECUTED|AUDIT_STREAM_ID|REPLAY_VERDICT|✅|❌"
pause 2

echo ""
echo -e "${GREEN}${BOLD}Every action governed. Every decision replayable. Every denial provable.${RESET}"
echo -e "${CYAN}github.com/slucerodev/ExoArmur-Core${RESET}"
pause 3
