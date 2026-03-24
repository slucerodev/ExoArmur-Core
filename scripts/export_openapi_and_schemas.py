#!/usr/bin/env python3
"""
Export OpenAPI spec and schemas from the running FastAPI application
"""

import json
from pathlib import Path


def main():
    """Export OpenAPI spec to artifacts directory"""
    # Import the app from the installed package namespace
    from exoarmur.main import app

    openapi_spec = app.openapi()

    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    openapi_file = artifacts_dir / "openapi_v1.json"

    artifacts_dir.mkdir(exist_ok=True)

    with open(openapi_file, "w") as f:
        json.dump(openapi_spec, f, indent=2, sort_keys=True)

    print(f"✅ OpenAPI spec exported to {openapi_file}")
    print(f"📊 Generated {len(openapi_spec.get('paths', {}))} API paths")

    paths = openapi_spec.get("paths", {})
    icw_paths = [p for p in paths.keys() if "identity_containment" in p]
    if icw_paths:
        print(f"🔧 ICW API paths: {len(icw_paths)}")
        for path in sorted(icw_paths):
            print(f"   - {path}")

if __name__ == "__main__":
    main()
