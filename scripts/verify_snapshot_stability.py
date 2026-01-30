#!/usr/bin/env python3
"""
Verify Snapshot Stability Script
CI gate to ensure schema snapshots are stable
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def run_schema_snapshot_tests():
    """Run schema snapshot tests"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_shared_primitives_snapshots.py", "-v"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        print(f"Error running snapshot tests: {e}")
        return 1, "", str(e)


def extract_schemas_from_test_output(output):
    """Extract schema information from test output"""
    schemas = {}
    
    # Look for schema assertions in test output
    lines = output.split('\n')
    current_schema = None
    
    for line in lines:
        if 'schema_snapshot' in line.lower() and 'test_' in line.lower():
            current_schema = line.strip()
            schemas[current_schema] = []
        elif current_schema and ('PASSED' in line or 'FAILED' in line):
            schemas[current_schema].append(line.strip())
    
    return schemas


def calculate_schema_hash():
    """Calculate hash of current shared primitives schemas"""
    try:
        # Import and get schemas
        sys.path.insert(0, str(Path(__file__).parent.parent / "spec" / "contracts"))
        
        from shared_primitives_v1 import (
            BeliefDeltaV1,
            ConflictV1,
            EvidenceRefV1,
            FindingV1,
            HypothesisV1,
            NarrativeV1,
            TimelineEventV1,
            TimelineV1,
        )
        
        schemas = {
            'EvidenceRefV1': EvidenceRefV1.model_json_schema(),
            'BeliefDeltaV1': BeliefDeltaV1.model_json_schema(),
            'HypothesisV1': HypothesisV1.model_json_schema(),
            'NarrativeV1': NarrativeV1.model_json_schema(),
            'FindingV1': FindingV1.model_json_schema(),
            'TimelineEventV1': TimelineEventV1.model_json_schema(),
            'TimelineV1': TimelineV1.model_json_schema(),
            'ConflictV1': ConflictV1.model_json_schema()
        }
        
        # Calculate hash for each schema
        schema_hashes = {}
        for name, schema in schemas.items():
            schema_json = json.dumps(schema, sort_keys=True, separators=(',', ':'))
            schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()
            schema_hashes[name] = schema_hash
        
        return schema_hashes
        
    except Exception as e:
        print(f"Error calculating schema hashes: {e}")
        return {}


def load_baseline_hashes():
    """Load baseline schema hashes from file"""
    baseline_file = Path(__file__).parent.parent / "tests" / "golden_scenarios" / "schema_hashes.json"
    
    if baseline_file.exists():
        try:
            with open(baseline_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading baseline hashes: {e}")
    
    return {}


def save_baseline_hashes(hashes):
    """Save current schema hashes as baseline"""
    baseline_file = Path(__file__).parent.parent / "tests" / "golden_scenarios" / "schema_hashes.json"
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(baseline_file, 'w') as f:
            json.dump(hashes, f, indent=2)
        print(f"✅ Baseline hashes saved to {baseline_file}")
        return True
    except Exception as e:
        print(f"Error saving baseline hashes: {e}")
        return False


def compare_hashes(current, baseline):
    """Compare current hashes with baseline"""
    if not baseline:
        print("📝 No baseline found - will create new baseline")
        return True, "No baseline"
    
    differences = []
    
    for schema_name in current:
        current_hash = current[schema_name]
        baseline_hash = baseline.get(schema_name)
        
        if baseline_hash is None:
            differences.append(f"NEW: {schema_name}")
        elif current_hash != baseline_hash:
            differences.append(f"CHANGED: {schema_name}")
    
    # Check for removed schemas
    for schema_name in baseline:
        if schema_name not in current:
            differences.append(f"REMOVED: {schema_name}")
    
    return len(differences) == 0, differences


def main():
    """Main verification function"""
    print("🔍 Verifying schema snapshot stability...")
    
    # Run the snapshot tests
    returncode, stdout, stderr = run_schema_snapshot_tests()
    
    if returncode != 0:
        print(f"❌ Schema snapshot tests failed (exit code: {returncode})")
        print(f"STDOUT:\n{stdout}")
        print(f"STDERR:\n{stderr}")
        return 1
    
    print("✅ Schema snapshot tests passed")
    
    # Calculate current schema hashes
    current_hashes = calculate_schema_hash()
    if not current_hashes:
        print("❌ Failed to calculate schema hashes")
        return 1
    
    print(f"📊 Calculated hashes for {len(current_hashes)} schemas")
    
    # Load baseline
    baseline_hashes = load_baseline_hashes()
    
    # Compare hashes
    is_stable, differences = compare_hashes(current_hashes, baseline_hashes)
    
    if is_stable:
        print("✅ Schema snapshots are stable")
        
        # Save baseline if it didn't exist
        if not baseline_hashes:
            save_baseline_hashes(current_hashes)
        
        return 0
    else:
        print("❌ Schema snapshots have CHANGED")
        print("\nDifferences:")
        for diff in differences:
            print(f"   {diff}")
        
        print("\n💡 If this change is intentional:")
        print("   1. Review the schema changes")
        print("   2. Update the baseline with: python scripts/verify_snapshot_stability.py --update-baseline")
        print("   3. Ensure all tests still pass")
        
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--update-baseline":
        print("📝 Updating baseline hashes...")
        current_hashes = calculate_schema_hash()
        if current_hashes and save_baseline_hashes(current_hashes):
            print("✅ Baseline updated successfully")
            sys.exit(0)
        else:
            print("❌ Failed to update baseline")
            sys.exit(1)
    else:
        sys.exit(main())
