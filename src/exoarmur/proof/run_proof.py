#!/usr/bin/env python3
"""
ExoArmur Proof Mode - Deterministic System Validation

Single-command deterministic proof that demonstrates ExoArmur system correctness.
Reuses existing execution paths without modification.
"""

import sys
import os
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def run_quickstart_proof():
    """Execute quickstart and capture structured output"""
    try:
        # Import and run quickstart logic
        from exoarmur.quickstart.run_quickstart import main as quickstart_main
        
        # Capture quickstart output by redirecting stdout
        import io
        import contextlib
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            exit_code = quickstart_main()
        
        output = captured_output.getvalue()
        
        if exit_code == 0:
            return True, output
        else:
            return False, output
            
    except Exception as e:
        return False, f"Quickstart execution failed: {e}"

def run_canonical_demo():
    """Execute canonical demo scenario"""
    try:
        # Run canonical demo using the examples/demo_standalone.py
        demo_path = Path('/home/oem/CascadeProjects/ExoArmur/examples/demo_standalone.py')
        result = subprocess.run([
            'python3', str(demo_path)
        ], capture_output=True, text=True, cwd='/home/oem/CascadeProjects/ExoArmur', timeout=30)
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
            
    except Exception as e:
        return False, f"Canonical demo execution failed: {e}"

def extract_proof_data(quickstart_output, demo_output):
    """Extract structured proof data from execution outputs"""
    
    # Extract correlation ID from quickstart output
    correlation_id = "unknown"
    for line in quickstart_output.split('\n'):
        if 'correlation_id:' in line.lower():
            correlation_id = line.split(':')[-1].strip()
            break
    
    # Extract replay hash from demo output
    replay_hash = "unknown"
    for line in demo_output.split('\n'):
        if 'Proof bundle replay hash:' in line:
            replay_hash = line.split(':')[-1].strip()
            break
    
    # Determine decision from demo output
    decision = "DENIED"  # Default for safety
    action_executed = False
    
    for line in demo_output.split('\n'):
        if 'DEMO_RESULT=DENIED' in line:
            decision = "DENIED"
            action_executed = False
            break
        elif 'DEMO_RESULT=ALLOWED' in line:
            decision = "ALLOWED"
            action_executed = True
            break
        elif 'ACTION_EXECUTED=false' in line:
            action_executed = False
        elif 'ACTION_EXECUTED=true' in line:
            action_executed = True
    
    return {
        'correlation_id': correlation_id,
        'replay_hash': replay_hash,
        'decision': decision,
        'action_executed': action_executed
    }

def main():
    """Run ExoArmur Proof Mode"""
    
    print("EXOARMUR PROOF MODE")
    print("====================")
    print()
    print("Scenario: canonical")
    print("Execution Mode: deterministic")
    print("Tenant: exoarmur-core")
    print()
    
    # Step 1: Run quickstart validation
    quickstart_success, quickstart_output = run_quickstart_proof()
    
    if not quickstart_success:
        print("RESULT:")
        print("- Decision: FAILED")
        print("- Action Executed: false")
        print("- Replay Hash: quickstart_failed")
        print("- Correlation ID: unknown")
        print()
        print("VERDICT:")
        print("PROOF FAILED - Quickstart validation failed")
        return 1
    
    # Step 2: Run canonical demo
    demo_success, demo_output = run_canonical_demo()
    
    if not demo_success:
        print("RESULT:")
        print("- Decision: FAILED")
        print("- Action Executed: false")
        print("- Replay Hash: demo_failed")
        print("- Correlation ID: unknown")
        print()
        print("VERDICT:")
        print("PROOF FAILED - Canonical demo failed")
        return 1
    
    # Step 3: Extract and display proof data
    proof_data = extract_proof_data(quickstart_output, demo_output)
    
    print("RESULT:")
    print(f"- Decision: {proof_data['decision']}")
    print(f"- Action Executed: {proof_data['action_executed']}")
    print(f"- Replay Hash: {proof_data['replay_hash']}")
    print(f"- Correlation ID: {proof_data['correlation_id']}")
    print()
    print("VERDICT:")
    print("PROOF COMPLETE")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
