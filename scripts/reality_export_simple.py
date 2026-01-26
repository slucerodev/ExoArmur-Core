#!/usr/bin/env python3
"""
Simple audit export using existing injection records
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone


def create_audit_export(injection_record_file: str, output_file: str):
    """Create audit export from injection record"""
    print(f"Creating audit export from {injection_record_file}")
    
    # Read injection record
    injection_path = Path(injection_record_file)
    if not injection_path.exists():
        raise FileNotFoundError(f"Injection record not found: {injection_record_file}")
    
    with open(injection_path, 'r') as f:
        injection_record = json.load(f)
    
    # Extract audit records from injection
    audit_records = injection_record.get("injected_records", [])
    
    # Create export entries
    export_entries = []
    
    for i, record in enumerate(audit_records):
        export_entry = {
            "sequence": i + 1,
            "timestamp": datetime.fromisoformat(record["recorded_at"].replace('Z', '+00:00')).timestamp(),
            "subject": "exoarmur.audit.append.v1",
            "data": record,
            "headers": {}
        }
        export_entries.append(export_entry)
    
    # Write export file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        for entry in export_entries:
            f.write(json.dumps(entry) + '\n')
    
    # Write metadata
    metadata = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "injection_record",
        "total_messages": len(export_entries),
        "injection_scenarios": injection_record.get("scenarios_injected", 0)
    }
    
    metadata_file = output_path.with_suffix('.metadata.json')
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Exported {len(export_entries)} messages to {output_path}")
    return len(export_entries)


def main():
    parser = argparse.ArgumentParser(description='Create audit export from injection record')
    parser.add_argument('--injection', required=True, help='Injection record file')
    parser.add_argument('--out', required=True, help='Output export file (JSONL)')
    
    args = parser.parse_args()
    
    count = create_audit_export(args.injection, args.out)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
