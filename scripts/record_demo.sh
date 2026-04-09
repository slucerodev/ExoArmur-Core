#!/usr/bin/env bash
# ExoArmur demo recording script for asciinema
# Usage:
#   pip install asciinema
#   bash scripts/record_demo.sh          # records to demo.cast
#   asciinema play demo.cast             # play back
#   # To convert to GIF: pip install agg && agg demo.cast demo.gif

set -euo pipefail

CAST_FILE="${1:-demo.cast}"

echo "Recording ExoArmur governance demo to: $CAST_FILE"
echo "Press Ctrl+D to stop recording."
echo ""

asciinema rec "$CAST_FILE" \
  --title "ExoArmur — Deterministic AI Governance" \
  --command "bash scripts/demo_steps.sh" \
  --overwrite
