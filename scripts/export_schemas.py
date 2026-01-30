#!/usr/bin/env python3
"""
Export model schemas to artifacts directory
"""

import json
import sys
import os
from pathlib import Path

# Add repo root and contracts to path for imports
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

def main():
    """Export model schemas to artifacts directory"""
    # Import contract models
    from models_v1 import (
        TelemetryEventV1, SignalFactsV1, BeliefV1, 
        LocalDecisionV1, ExecutionIntentV1, AuditRecordV1
    )
    
    # Import API models
    from exoarmur.api_models import (
        TelemetryIngestResponseV1, AuditResponseV1, ErrorResponseV1
    )
    
    # All models to export
    v1_models = {
        'TelemetryEventV1': TelemetryEventV1,
        'SignalFactsV1': SignalFactsV1,
        'BeliefV1': BeliefV1,
        'LocalDecisionV1': LocalDecisionV1,
        'ExecutionIntentV1': ExecutionIntentV1,
        'AuditRecordV1': AuditRecordV1
    }
    
    api_models = {
        'TelemetryIngestResponseV1': TelemetryIngestResponseV1,
        'AuditResponseV1': AuditResponseV1,
        'ErrorResponseV1': ErrorResponseV1
    }
    
    all_models = {**v1_models, **api_models}
    
    # Create artifacts directory
    artifacts_dir = Path(__file__).parent.parent / 'artifacts'
    schemas_dir = artifacts_dir / 'schemas'
    schemas_dir.mkdir(exist_ok=True)
    
    # Export each model schema
    for model_name, model_class in all_models.items():
        schema = model_class.model_json_schema()
        
        # Add ExoArmur metadata
        if model_name in api_models:
            schema['title'] = f'ExoArmur ADMO v1 API - {model_name}'
            schema['description'] = f'Pydantic v2 schema for {model_name} API response model'
        else:
            schema['title'] = f'ExoArmur ADMO v1 - {model_name}'
            schema['description'] = f'Pydantic v2 schema for {model_name} contract model'
        
        # Write schema to file
        schema_file = schemas_dir / f'{model_name}.json'
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2, sort_keys=True)
        
        print(f"✅ Exported {model_name} schema to {schema_file}")
    
    print(f"📊 Exported {len(all_models)} model schemas to {schemas_dir}")

if __name__ == "__main__":
    main()
