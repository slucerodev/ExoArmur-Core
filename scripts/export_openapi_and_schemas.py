#!/usr/bin/env python3
"""
Export OpenAPI spec and schemas from the running FastAPI application
"""

import json
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def main():
    """Export OpenAPI spec to artifacts directory"""
    # Import the app
    import main
    
    # Generate OpenAPI spec
    openapi_spec = main.app.openapi()
    
    # Write to artifacts directory
    artifacts_dir = Path(__file__).parent.parent / 'artifacts'
    openapi_file = artifacts_dir / 'openapi_v1.json'
    
    # Ensure artifacts directory exists
    artifacts_dir.mkdir(exist_ok=True)
    
    # Write OpenAPI spec with proper formatting
    with open(openapi_file, 'w') as f:
        json.dump(openapi_spec, f, indent=2, sort_keys=True)
    
    print(f"✅ OpenAPI spec exported to {openapi_file}")
    print(f"📊 Generated {len(openapi_spec.get('paths', {}))} API paths")
    
    # Show summary of new paths
    paths = openapi_spec.get('paths', {})
    icw_paths = [p for p in paths.keys() if 'identity_containment' in p]
    if icw_paths:
        print(f"🔧 ICW API paths: {len(icw_paths)}")
        for path in sorted(icw_paths):
            print(f"   - {path}")

if __name__ == "__main__":
    main()
