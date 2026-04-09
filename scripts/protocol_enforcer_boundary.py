#!/usr/bin/env python3
"""
Protocol Enforcer Boundary Check
Ensures the protocol enforcer failing set remains exactly bounded
"""

import subprocess
import sys
from pathlib import Path

from typing import Set, Dict

def load_known_failing() -> Set[str]:
    """Load the known failing test list"""
    known_failing_file = Path(__file__).parent.parent / "tests" / "KNOWN_FAILING_PROTOCOL_ENFORCER.txt"
    known_failing = set()
    
    # If the file doesn't exist, it means all tests should pass
    if not known_failing_file.exists():
        return known_failing
    
    with open(known_failing_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '|' in line:
                test_nodeid = line.split('|')[0].strip()
                known_failing.add(test_nodeid)
    
    return known_failing

def parse_failures_from_stdout(stdout: str) -> Dict[str, str]:
    """Parse pytest stdout for failing nodeids"""
    failures: Dict[str, str] = {}
    for line in stdout.split('\n'):
        if line.startswith('FAILED') or line.startswith('ERROR'):
            test_nodeid = line.split(' ', 1)[1].strip()
            if '::' not in test_nodeid:
                continue
            failures[test_nodeid] = "FAILED" if line.startswith('FAILED') else "ERROR"
    return failures


def run_protocol_enforcer_tests() -> Dict[str, str]:
    """Run protocol enforcer tests and return failures"""
    print("🔍 Running protocol enforcer tests...")
    
    cmd = [
        sys.executable, '-m', 'pytest',
        'tests/test_protocol_enforcer.py',
        '--tb=no', '-q'
    ]
    
    print(f"🧪 Pytest command: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    failures = parse_failures_from_stdout(result.stdout)

    if result.returncode != 0 and not failures:
        print("\nPYTEST INFRA/COLLECTION ERROR (not a test failure set expansion)")
        if result.stderr:
            print(result.stderr.rstrip())
        elif result.stdout:
            print(result.stdout.rstrip())
        raise RuntimeError("Pytest infra/collection error without test failures")

    return failures

def compare_failing_sets(known_failing: Set[str], actual_failing: Dict[str, str], infra_error: bool) -> bool:
    """Compare known failing set with actual failures"""
    actual_failing_set = set(actual_failing.keys())
    
    print(f"\n📊 Comparison:")
    print(f"  Known failing: {len(known_failing)} tests")
    print(f"  Actual failing: {len(actual_failing_set)} tests")
    print(f"  Infra error: {'true' if infra_error else 'false'}")
    
    # Check for new failures
    new_failures = actual_failing_set - known_failing
    if new_failures:
        print(f"\n❌ NEW FAILURES DETECTED:")
        for test in sorted(new_failures):
            print(f"  {test}")
        print(f"\n🚨 BOUNDARY VIOLATION: {len(new_failures)} new failures appeared!")
        print("   This indicates uncontrolled failure set expansion.")
        return False
    
    # Check for fixed tests (good, but requires explicit update)
    fixed_tests = known_failing - actual_failing_set
    if fixed_tests:
        print(f"\n✅ TESTS FIXED:")
        for test in sorted(fixed_tests):
            print(f"  {test}")
        print(f"\n📝 ACTION REQUIRED: Update KNOWN_FAILING_PROTOCOL_ENFORCER.txt")
        print("   Remove the fixed tests from the known failing list.")
        print("   This prevents silent behavior drift.")
        return False
    
    # Check for exact match
    if actual_failing_set == known_failing:
        print(f"\n✅ BOUNDARY CHECK PASSED")
        print(f"  Failing set is exactly bounded ({len(known_failing)} tests)")
        return True
    
    print(f"\n❌ UNEXPECTED STATE")
    print(f"  Known and actual failing sets don't match but no new failures detected")
    return False

def main():
    """Main protocol enforcer boundary check"""
    print("🚀 Protocol Enforcer Boundary Check")
    print("Ensuring failing set remains exactly bounded")
    
    # Load known failing tests
    try:
        known_failing = load_known_failing()
    except FileNotFoundError:
        print("❌ KNOWN_FAILING_PROTOCOL_ENFORCER.txt not found")
        sys.exit(1)
    
    # Run tests
    try:
        actual_failing = run_protocol_enforcer_tests()
        infra_error = False
    except RuntimeError:
        actual_failing = {}
        infra_error = True
    
    # Compare
    if compare_failing_sets(known_failing, actual_failing, infra_error):
        print("✅ Protocol enforcer boundary check passed")
        sys.exit(0)
    else:
        print("❌ Protocol enforcer boundary check failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
