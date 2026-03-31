#!/usr/bin/env python3
"""
Core Determinism Enforcement for ExoArmur Replay System

This script enforces determinism for critical core components:
- Replay engine and related modules
- Multi-node verifier
- Byzantine fault injection
- Canonical utilities and event handling

These components MUST remain deterministic at all times.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_core_determinism_check():
    """Run determinism check only on core replay components"""
    core_paths = [
        "src/exoarmur/replay",
        "src/exoarmur/clock.py",
        "src/exoarmur/main.py", 
        "tests/test_invariants.py"
    ]
    
    print("🔒 CORE DETERMINISM ENFORCEMENT")
    print("=" * 50)
    
    violations_found = False
    
    for path in core_paths:
        if Path(path).exists():
            print(f"📁 Checking: {path}")
            result = subprocess.run([
                "python3", "scripts/check_determinism.py", path
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            if result.returncode != 0:
                print(f"❌ VIOLATIONS FOUND in {path}")
                print(result.stdout)
                violations_found = True
            else:
                print(f"✅ {path} - PASSED")
    
    # Check environment
    hash_seed = os.environ.get('PYTHONHASHSEED')
    if hash_seed is None:
        print("⚠️  WARNING: PYTHONHASHSEED not set")
        print("   Set PYTHONHASHSEED=0 for deterministic hashing")
        violations_found = True
    else:
        print(f"✅ PYTHONHASHSEED={hash_seed}")
    
    if violations_found:
        print("\n❌ CORE DETERMINISM VIOLATIONS DETECTED")
        print("The core replay system must remain 100% deterministic")
        print("Fix violations before proceeding")
        sys.exit(1)
    else:
        print("\n✅ CORE DETERMINISM VERIFIED")
        print("All critical components pass determinism checks")
        sys.exit(0)

if __name__ == "__main__":
    run_core_determinism_check()
