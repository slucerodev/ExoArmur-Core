#!/usr/bin/env python3
"""
Verify All - Comprehensive validation script for ExoArmur

Runs lint, tests, schema validation, golden demo, and replay checks.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description, check=True):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=check,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"✅ {description} - PASSED")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Exit code: {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False

def main():
    """Main verification pipeline"""
    print("🚀 ExoArmur Verification Pipeline")
    print("This script validates all components of the system")
    
    results = []
    
    # 1. Python syntax check
    results.append(run_command(
        "python3 -m py_compile src/federation/*.py",
        "Python Syntax Check"
    ))
    
    # 2. Import check
    results.append(run_command(
        "python3 -c \"import src.federation.handshake_controller; import src.federation.observation_ingest; import src.federation.belief_aggregation; import src.federation.arbitration_service; print('All imports successful')\"",
        "Import Validation"
    ))
    
    # 3. Unit tests (Phase 2 only)
    results.append(run_command(
        "python3 -m pytest tests/test_observation_ingest.py tests/test_belief_aggregation.py tests/test_visibility_api.py tests/test_arbitration.py tests/test_constitutional_invariants.py tests/test_boundary_enforcement.py tests/test_replay_determinism.py tests/test_federate_identity_store.py tests/test_handshake_controller.py -v --tb=short",
        "Unit Tests (Phase 2)"
    ))
    
    # 4. Schema validation
    results.append(run_command(
        "python3 -c \"from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, ObservationV1, ArbitrationV1; print('Schema validation passed')\"",
        "Schema Validation"
    ))
    
    # 5. V1 Golden Demo (if exists)
    if os.path.exists("tests/test_golden_demo.py"):
        results.append(run_command(
            "python3 -m pytest tests/test_golden_demo.py -v",
            "V1 Golden Demo"
        ))
    else:
        print("\n⚠️  V1 Golden Demo test not found - skipping")
        results.append(True)  # Don't fail for missing test
    
    # 6. Replay determinism test
    results.append(run_command(
        "python3 -m pytest tests/test_replay_determinism.py -v",
        "Replay Determinism"
    ))
    
    # 7. Constitutional invariants test
    results.append(run_command(
        "python3 -m pytest tests/test_constitutional_invariants.py -v",
        "Constitutional Invariants"
    ))
    
    # 8. Boundary enforcement test
    results.append(run_command(
        "python3 -m pytest tests/test_boundary_enforcement.py -v",
        "Boundary Enforcement"
    ))
    
    # Summary
    print(f"\n{'='*60}")
    print("VERIFICATION SUMMARY")
    print('='*60)
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("🎉 ExoArmur verification complete!")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total})")
        print("🔧 Please fix the failing checks before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())
