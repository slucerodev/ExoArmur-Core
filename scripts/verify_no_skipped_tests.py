#!/usr/bin/env python3
"""
Verify No Skipped Tests Script
CI gate to ensure no tests are skipped
"""

import re
import subprocess
import sys
from pathlib import Path


def run_pytest_with_detailed_output():
    """Run pytest and capture detailed output"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        print(f"Error running pytest: {e}")
        return 1, "", str(e)


def parse_skipped_tests(output):
    """Parse pytest output to find skipped tests"""
    skipped_tests = []
    
    # Look for skipped test summary
    skipped_section_match = re.search(r'=\s*short test summary info\s*=.*?SKIPPED\s+\[(\d+)\](.*?)(?=\s*=|$)', output, re.DOTALL)
    if skipped_section_match:
        skip_count = int(skipped_section_match.group(1))
        skipped_content = skipped_section_match.group(2)
        
        if skip_count > 0:
            # Extract individual skipped test lines
            skipped_lines = re.findall(r'(\S+)\s*::(\S+)\s*.*?SKIPPED.*?(?=\n\S|$)', skipped_content, re.DOTALL)
            for file, test in skipped_lines:
                skipped_tests.append(f"{file}::{test}")
    
    return skipped_tests


def check_pytest_warnings_for_skips(output):
    """Check for pytest warnings about async functions without plugins"""
    async_warnings = []
    
    # Look for async function warnings
    async_warning_pattern = r'(\S+)\s*::(\S+).*?async def function and no async plugin installed'
    async_matches = re.findall(async_warning_pattern, output)
    
    for file, test in async_matches:
        async_warnings.append(f"{file}::{test}")
    
    return async_warnings


def main():
    """Main verification function"""
    print("🔍 Verifying no skipped tests...")
    
    returncode, stdout, stderr = run_pytest_with_detailed_output()
    
    # Parse for skipped tests
    skipped_tests = parse_skipped_tests(stdout)
    async_warnings = check_pytest_warnings_for_skips(stdout)
    
    print(f"📊 Test execution completed")
    print(f"   Exit code: {returncode}")
    print(f"   Skipped tests found: {len(skipped_tests)}")
    print(f"   Async warnings (potential skips): {len(async_warnings)}")
    
    if skipped_tests:
        print("\n❌ SKIPPED TESTS DETECTED:")
        for skipped_test in skipped_tests:
            print(f"   - {skipped_test}")
        print("\n💡 All tests must run. Remove pytest.mark.skip decorators and fix async test issues.")
        return 1
    
    if async_warnings:
        print("\n⚠️  ASYNC TEST WARNINGS DETECTED:")
        for warning in async_warnings:
            print(f"   - {warning}")
        print("\n💡 These tests are being skipped due to missing async plugin configuration.")
        return 1
    
    # Check test summary for any other skip indicators
    summary_match = re.search(r'=\s*short test summary info\s*=.*?SKIPPED\s+\[(\d+)\]', stdout, re.DOTALL)
    if summary_match:
        skip_count = int(summary_match.group(1))
        if skip_count > 0:
            print(f"\n❌ {skip_count} SKIPPED TESTS DETECTED IN SUMMARY")
            print("Please review the full pytest output above.")
            return 1
    
    # Also check for the specific "SKIPPED" line in pytest output
    if "SKIPPED [" in stdout and "SKIPPED [0]" not in stdout:
        print("\n❌ SKIPPED TESTS DETECTED IN OUTPUT")
        print("Please review the full pytest output above.")
        return 1
    
    print("\n✅ No skipped tests detected!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
