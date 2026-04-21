#!/bin/bash
# ExoArmur Codespace Welcome Script
# Shows available demo commands when the container starts

cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ███████╗██╗  ██╗ ██████╗  █████╗ ██████╗ ███╗   ███╗██╗   ██╗██████╗    ║
║   ██╔════╝╚██╗██╔╝██╔═══██╗██╔══██╗██╔══██╗████╗ ████║██║   ██║██╔══██╗   ║
║   █████╗   ╚███╔╝ ██║   ██║███████║██████╔╝██╔████╔██║██║   ██║██████╔╝   ║
║   ██╔══╝   ██╔██╗ ██║   ██║██╔══██║██╔══██╗██║╚██╔╝██║██║   ██║██╔══██╗   ║
║   ███████╗██╔╝ ██╗╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║╚██████╔╝██║  ██║   ║
║   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ║
║                                                                           ║
║                    AUTONOMOUS DEFENSE PLATFORM                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

🎯 QUICK DEMO COMMANDS
═══════════════════════════════════════════════════════════════════════════

1️⃣  VERIFY DETERMINISTIC REPLAY (The Core Guarantee)
    $ exoarmur proof
    # Run it 3 times - same hash proves determinism

2️⃣  VERIFY REVERSIBLE ACTIONS (Claim 3)
    $ python examples/reversible_action_demo.py
    # Shows: pre-action → action → rollback → identical state

3️⃣  VERIFY ML ISOLATION (Claim 4)
    $ python -m pytest tests/test_ml_isolation.py -v
    # All 6 tests should pass

4️⃣  RUN FULL TEST SUITE
    $ python -m pytest tests/ -q --tb=short
    # Expected: ~1000+ tests passing

5️⃣  VERIFY DOCTRINE CLAIMS
    $ cat docs/DOCTRINE_VERIFICATION.md | grep -A 5 "Overall Assessment"

📚 KEY DOCUMENTS
═══════════════════════════════════════════════════════════════════════════

📖 Doctrine (verified claims):     docs/DOCTRINE.md
📋 Verification details:           docs/DOCTRINE_VERIFICATION.md
🏗️  Architecture:                    docs/ARCHITECTURE.md
🔒 ML Isolation Policy:             docs/ML_ISOLATION.md
⚙️  Governance:                      docs/GOVERNANCE.md

🔧 EXPLORATION COMMANDS
═══════════════════════════════════════════════════════════════════════════

# Check the SDK API
$ python -c "from exoarmur.sdk.public_api import ActionClass; print([c.value for c in ActionClass])"

# Verify determinism environment
$ echo "PYTHONHASHSEED=$PYTHONHASHSEED"

# Check version
$ exoarmur --version

# Run the Golden Demo (if you have the key)
$ python tests/test_golden_demo.py

═══════════════════════════════════════════════════════════════════════════

Environment is ready. PYTHONHASHSEED=0 is set for deterministic operation.

Start with: exoarmur proof
EOF
