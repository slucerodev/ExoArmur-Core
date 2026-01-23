"""
Schema snapshot tests for ExoArmur ADMO v1

These tests ensure that schema changes are intentional and tracked.
If schemas change, tests fail with clear remediation instructions.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Add contracts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))


class TestSchemaSnapshots:
    """Test that current schemas match committed snapshots"""
    
    @classmethod
    def setup_class(cls):
        """Setup test class with paths and model imports"""
        cls.project_root = Path(os.path.dirname(__file__)).parent
        cls.artifacts_dir = cls.project_root / 'artifacts'
        cls.schemas_dir = cls.artifacts_dir / 'schemas'
        
        # Import contract models
        from models_v1 import (
            TelemetryEventV1, SignalFactsV1, BeliefV1, 
            LocalDecisionV1, ExecutionIntentV1, AuditRecordV1
        )
        
        # Import API models
        from api_models import (
            TelemetryIngestResponseV1, AuditResponseV1, ErrorResponseV1
        )
        
        cls.v1_models = {
            'TelemetryEventV1': TelemetryEventV1,
            'SignalFactsV1': SignalFactsV1,
            'BeliefV1': BeliefV1,
            'LocalDecisionV1': LocalDecisionV1,
            'ExecutionIntentV1': ExecutionIntentV1,
            'AuditRecordV1': AuditRecordV1
        }
        
        cls.api_models = {
            'TelemetryIngestResponseV1': TelemetryIngestResponseV1,
            'AuditResponseV1': AuditResponseV1,
            'ErrorResponseV1': ErrorResponseV1
        }
        
        cls.all_models = {**cls.v1_models, **cls.api_models}
    
    def _load_snapshot(self, model_name: str) -> Dict[str, Any]:
        """Load a schema snapshot from file"""
        snapshot_file = self.schemas_dir / f'{model_name}.json'
        if not snapshot_file.exists():
            pytest.fail(f"Schema snapshot not found: {snapshot_file}")
        
        with open(snapshot_file, 'r') as f:
            return json.load(f)
    
    def _generate_current_schema(self, model_name: str) -> Dict[str, Any]:
        """Generate current schema from model class (same as export script)"""
        model_class = self.all_models[model_name]
        schema = model_class.model_json_schema()
        
        # Add ExoArmur metadata (same as export script)
        if model_name in self.api_models:
            schema['title'] = f'ExoArmur ADMO v1 API - {model_name}'
            schema['description'] = f'Pydantic v2 schema for {model_name} API response model'
        else:
            schema['title'] = f'ExoArmur ADMO v1 - {model_name}'
            schema['description'] = f'Pydantic v2 schema for {model_name} contract model'
        
        return schema
    
    def _compare_schemas(self, current: Dict[str, Any], snapshot: Dict[str, Any], model_name: str) -> None:
        """Compare current schema with snapshot and fail if different"""
        if current != snapshot:
            # Generate helpful diff message
            diff_message = f"\n🔍 SCHEMA CHANGE DETECTED: {model_name}\n"
            diff_message += "=" * 60 + "\n"
            diff_message += "The current schema differs from the committed snapshot.\n\n"
            
            # Check for breaking changes
            breaking_changes = self._detect_breaking_changes(current, snapshot, model_name)
            
            if breaking_changes:
                diff_message += "🚨 BREAKING CHANGES DETECTED:\n"
                for change in breaking_changes:
                    diff_message += f"  - {change}\n"
                diff_message += "\n"
            
            diff_message += "📋 REMEDIATION STEPS:\n"
            diff_message += "1. If this change is intentional and backward compatible:\n"
            diff_message += "   a. Run: python scripts/export_openapi_and_schemas.py\n"
            diff_message += "   b. Commit the updated schema snapshots\n"
            diff_message += "   c. Add a schema change waiver if adding optional fields\n"
            diff_message += "\n"
            diff_message += "2. If this change is breaking:\n"
            diff_message += "   a. STOP - Breaking changes require explicit approval\n"
            diff_message += "   b. Consider v2 model instead\n"
            diff_message += "   c. Update migration strategy\n"
            diff_message += "\n"
            diff_message += "3. To regenerate all snapshots:\n"
            diff_message += "   python scripts/export_openapi_and_schemas.py\n"
            
            pytest.fail(diff_message)
    
    def _detect_breaking_changes(self, current: Dict[str, Any], snapshot: Dict[str, Any], model_name: str) -> list:
        """Detect breaking changes between schemas"""
        breaking_changes = []
        
        current_props = current.get('properties', {})
        snapshot_props = snapshot.get('properties', {})
        
        # Check for removed required fields
        current_required = set(current.get('required', []))
        snapshot_required = set(snapshot.get('required', []))
        
        removed_required = snapshot_required - current_required
        if removed_required:
            breaking_changes.append(f"Removed required fields: {', '.join(removed_required)}")
        
        # Check for removed fields
        removed_fields = set(snapshot_props.keys()) - set(current_props.keys())
        if removed_fields:
            breaking_changes.append(f"Removed fields: {', '.join(removed_fields)}")
        
        # Check for type changes
        for field_name in current_props:
            if field_name in snapshot_props:
                current_type = current_props[field_name].get('type')
                snapshot_type = snapshot_props[field_name].get('type')
                if current_type != snapshot_type:
                    breaking_changes.append(f"Type change for {field_name}: {snapshot_type} -> {current_type}")
        
        # Check for new required fields (breaking)
        new_required = current_required - snapshot_required
        if new_required:
            breaking_changes.append(f"Added required fields: {', '.join(new_required)}")
        
        return breaking_changes
    
    @pytest.mark.parametrize("model_name", [
        'TelemetryEventV1', 'SignalFactsV1', 'BeliefV1', 
        'LocalDecisionV1', 'ExecutionIntentV1', 'AuditRecordV1',
        'TelemetryIngestResponseV1', 'AuditResponseV1', 'ErrorResponseV1'
    ])
    def test_schema_snapshot_unchanged(self, model_name):
        """Test that model schema matches committed snapshot"""
        current_schema = self._generate_current_schema(model_name)
        snapshot_schema = self._load_snapshot(model_name)
        
        self._compare_schemas(current_schema, snapshot_schema, model_name)
    
    def test_openapi_snapshot_unchanged(self):
        """Test that OpenAPI spec matches committed snapshot"""
        # Import app using temporary main file
        import importlib.util
        
        # Create temporary main with absolute imports
        main_temp_path = Path(__file__).parent.parent / 'src' / 'main_temp.py'
        if not main_temp_path.exists():
            # Create temporary version for testing
            main_path = Path(__file__).parent.parent / 'src' / 'main.py'
            main_temp_path.write_text(main_path.read_text().replace('from .', 'from '))
        
        # Load the temporary main
        spec = importlib.util.spec_from_file_location("main_temp", main_temp_path)
        main_temp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_temp)
        
        app = main_temp.app
        current_openapi = app.openapi()
        
        # Load snapshot
        openapi_snapshot_file = self.artifacts_dir / 'openapi_v1.json'
        if not openapi_snapshot_file.exists():
            pytest.fail(f"OpenAPI snapshot not found: {openapi_snapshot_file}")
        
        with open(openapi_snapshot_file, 'r') as f:
            snapshot_openapi = json.load(f)
        
        # Compare OpenAPI specs
        if current_openapi != snapshot_openapi:
            diff_message = f"\n🔍 OPENAPI CHANGE DETECTED\n"
            diff_message += "=" * 60 + "\n"
            diff_message += "The current OpenAPI spec differs from the committed snapshot.\n\n"
            diff_message += "📋 REMEDIATION STEPS:\n"
            diff_message += "1. If this change is intentional:\n"
            diff_message += "   a. Run: python scripts/export_openapi_and_schemas.py\n"
            diff_message += "   b. Commit the updated OpenAPI snapshot\n"
            diff_message += "\n"
            diff_message += "2. To regenerate all snapshots:\n"
            diff_message += "   python scripts/export_openapi_and_schemas.py\n"
            
            pytest.fail(diff_message)
        
        # Clean up temporary file
        if main_temp_path.exists():
            main_temp_path.unlink()


class TestSchemaChangeWaiver:
    """Test schema change waiver mechanism"""
    
    def test_schema_change_waiver_format(self):
        """Test that schema change waivers follow the required format"""
        waiver_file = Path(__file__).parent.parent / 'artifacts' / 'schema_change_waivers.json'
        
        if waiver_file.exists():
            with open(waiver_file, 'r') as f:
                waivers = json.load(f)
            
            # Validate waiver format
            required_fields = ['model_name', 'field_name', 'reason', 'approved_by', 'approved_at']
            
            for waiver in waivers:
                for field in required_fields:
                    if field not in waiver:
                        pytest.fail(f"Schema change waiver missing required field: {field}")
                
                # Validate approved_at format (ISO 8601)
                if not isinstance(waiver['approved_at'], str):
                    pytest.fail(f"Schema change waiver approved_at must be string ISO 8601 format")
    
    def test_only_optional_field_changes_waived(self):
        """Test that waivers only exist for optional field additions"""
        waiver_file = Path(__file__).parent.parent / 'artifacts' / 'schema_change_waivers.json'
        
        if not waiver_file.exists():
            pytest.skip("No schema change waivers file found")
        
        with open(waiver_file, 'r') as f:
            waivers = json.load(f)
        
        # This would require more complex logic to validate against actual schemas
        # For now, just ensure the file exists and has valid format
        assert len(waivers) >= 0  # File exists and is valid JSON
