#!/usr/bin/env python3
"""
Test Delta Script for Phase -0.5 Regression Control
Tracks failing test count changes over time
"""

import subprocess
import sys
from pathlib import Path

def get_failing_tests():
    """Get current failing tests using canonical command"""
    cmd = [
        "python3", "-m", "pytest",
        "--ignore=tests/test_icw_api.py",
        "--ignore=tests/test_identity_containment.py", 
        "--ignore=tests/test_protocol_enforcer.py",
        "--tb=no", "-q"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    
    if result.returncode != 0 and result.returncode != 1:
        print(f"Error running pytest: {result.stderr}")
        sys.exit(1)
    
    # Extract failing tests
    failing_tests = []
    for line in result.stdout.split('\n'):
        if line.startswith('FAILED'):
            test_name = line.split(' ', 1)[1]
            failing_tests.append(test_name)
    
    return sorted(failing_tests)

def write_failing_set(tests, filename):
    """Write failing set to file"""
    with open(filename, 'w') as f:
        for test in tests:
            f.write(f"{test}\n")

def main():
    """Main script entry point"""
    print("🔍 Running canonical test command...")
    failing_tests = get_failing_tests()
    
    print(f"📊 Found {len(failing_tests)} failing tests")
    
    # Write current failing set
    output_file = Path(__file__).parent.parent / "FAILING_SET_NOW.txt"
    write_failing_set(failing_tests, output_file)
    
    print(f"✅ Wrote failing set to {output_file}")
    
    # Show summary
    if failing_tests:
        print("\n📋 Current failing tests:")
        for test in failing_tests:
            print(f"  ❌ {test}")
    else:
        print("\n🎉 All tests passing!")

if __name__ == "__main__":
    main()
