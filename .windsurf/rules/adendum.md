---
trigger: model_decision
---

ADDENDUM: STATUS & EVIDENCE STRICTNESS

- Gate status may not be set to YELLOW or GREEN unless an artifacts/<run_id>/ directory exists.
- GREEN requires artifacts/<run_id>/PASS_FAIL.txt showing PASS for the targeted gate.
- YELLOW is permitted ONLY when:
  a) A verifier script exists and is runnable, AND
  b) The last run produced artifacts/<run_id>/ showing partial progress but not a PASS.
- If no artifacts exist for the current cycle, status MUST be RED and output MUST be UNPROVEN.
