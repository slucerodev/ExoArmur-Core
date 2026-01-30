#!/usr/bin/env python3
"""
Verify All - Comprehensive validation script for ExoArmur

Runs verify_all test suite (full suite, no ignores) as defined in docs/TEST_SUITES.md
"""

import os
import subprocess
import sys
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
    
    # 1. Import sanity check
    results.append(run_command(
        """python3 -c "
# V1 Core imports
from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, LocalDecisionV1, ExecutionIntentV1, AuditRecordV1

# Core system imports  
from exoarmur.audit import AuditLogger, NoOpAuditInterface, FederationAuditInterface
from exoarmur.replay import ReplayEngine
from exoarmur.safety import SafetyGate

# Federation interface imports
from exoarmur.federation import FederateIdentityStore, HandshakeStateMachine

# Approval/safety gate imports
from exoarmur.analysis import FactsDeriver
from exoarmur.beliefs import BeliefGenerator
from exoarmur.collective_confidence import CollectiveConfidenceAggregator

print('✅ All core imports successful')
print('✅ V1 Core: TelemetryEventV1, BeliefV1, LocalDecisionV1, ExecutionIntentV1, AuditRecordV1')
print('✅ Audit: AuditLogger, NoOpAuditInterface, FederationAuditInterface, ReplayEngine')  
print('✅ Safety: SafetyGate')
print('✅ Federation: FederateIdentityStore, HandshakeStateMachine')
print('✅ Analysis: FactsDeriver, BeliefGenerator, CollectiveConfidenceAggregator')
" """,
        "Import Sanity Check"
    ))
    
    # 2. verify_all test suite (full suite, no ignores)
    results.append(run_command(
        "python3 -m pytest tests/ --tb=short -W error::pytest.PytestUnraisableExceptionWarning -W error::RuntimeWarning",
        "verify_all Test Suite with Strict Warnings"
    ))
    
    # 3. Schema validation
    results.append(run_command(
        "python3 -c \"from spec.contracts.models_v1 import TelemetryEventV1, BeliefV1, ObservationV1, ArbitrationV1; print('Schema validation passed')\"",
        "Schema Validation"
    ))
    
    # 4. V1 Golden Demo (if exists)
    if os.path.exists("tests/test_golden_demo.py"):
        results.append(run_command(
            "python3 -m pytest tests/test_golden_demo.py -v",
            "V1 Golden Demo"
        ))
    else:
        print("\n⚠️  V1 Golden Demo test not found - skipping")
        results.append(True)  # Don't fail for missing test
    
    # 5. Replay determinism test
    results.append(run_command(
        "python3 -m pytest tests/test_replay_determinism.py -v",
        "Replay Determinism"
    ))
    
    # 6. Constitutional invariants test
    results.append(run_command(
        "python3 -m pytest tests/test_constitutional_invariants.py -v",
        "Constitutional Invariants"
    ))
    
    # 7. Boundary enforcement test
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
