"""
Canonicalization utilities for execution proof bundles.

Provides deterministic JSON serialization and hash computation
for execution artifacts to enable verifiable replay with
comprehensive governance verdict tracking and executor sandboxing.
Enhanced with forensic-grade replay verification support and schema versioning.
"""

import hashlib
import json
from typing import Any, Dict, List, Union, Optional

from pydantic import BaseModel

from ..models.action_intent import ActionIntent
from ..models.policy_decision import PolicyDecision
from ..models.execution_trace import ExecutionTrace
from ..utils.verdict_resolution import FinalVerdict
from ..schema_migrations import SchemaMigrations, MigrationError


def to_canonical_dict(obj: Any) -> Dict[str, Any]:
    """Convert object to canonical dictionary with enhanced verification support.
    
    Handles Pydantic models, dataclasses, and primitive types with datetime
    and enum serialization for forensic-grade replay verification.
    """
    if hasattr(obj, 'model_dump'):
        result = obj.model_dump(exclude_none=True, exclude_unset=True)
    elif hasattr(obj, '__dict__'):
        result = obj.__dict__.copy()
    elif isinstance(obj, dict):
        result = obj.copy()
    else:
        result = {"value": obj}
    
    # Handle datetime objects and enums recursively
    def serialize_value(value):
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        elif hasattr(value, 'value'):  # Handle enum objects
            return value.value
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        else:
            return value
    
    return {k: serialize_value(v) for k, v in result.items()}


def canonical_json(data: Dict[str, Any]) -> bytes:
    """Generate canonical JSON bytes with deterministic serialization.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        UTF-8 encoded JSON bytes with sorted keys and consistent formatting
    """
    # Custom serializer for datetime and enum objects
    def json_serializer(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, 'value'):  # Handle enum objects
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=json_serializer
    ).encode('utf-8')


def compute_replay_hash(data: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of canonical JSON data for replay verification.
    
    Args:
        data: Dictionary to hash
        
    Returns:
        Hexadecimal SHA-256 hash
    """
    canonical_bytes = canonical_json(data)
    return hashlib.sha256(canonical_bytes).hexdigest()


def bundle_inputs_hash(
    intent: Union[ActionIntent, Dict[str, Any]],
    policy_decision: Union[PolicyDecision, Dict[str, Any]],
    safety_verdict: Dict[str, Any],
    final_verdict: FinalVerdict,
    execution_trace: Optional[Union[ExecutionTrace, Dict[str, Any]]] = None,
    executor_result: Optional[Dict[str, Any]] = None,
    governance_evidence: Optional[Dict[str, Any]] = None,
    resolution_evidence: Optional[Dict[str, Any]] = None,
    executor_capabilities: Optional[Dict[str, Any]] = None,
    validation_evidence: Optional[Dict[str, Any]] = None,
    executor_failure_evidence: Optional[Dict[str, Any]] = None
) -> str:
    """Compute deterministic hash of bundle inputs for replay verification.
    
    Enhanced with comprehensive governance verdict tracking and executor sandboxing.
    
    Args:
        intent: Action intent or canonical dictionary
        policy_decision: Policy decision or canonical dictionary
        safety_verdict: Safety gate verdict dictionary
        final_verdict: Final resolved verdict
        execution_trace: Execution trace or canonical dictionary (optional)
        executor_result: Executor result dictionary (optional)
        governance_evidence: Governance decision evidence (optional)
        resolution_evidence: Verdict resolution evidence (optional)
        executor_capabilities: Executor capabilities and constraints (optional)
        validation_evidence: Target validation evidence (optional)
        executor_failure_evidence: Executor failure evidence (optional)
        
    Returns:
        Hexadecimal SHA-256 hash of canonical bundle inputs
    """
    # Convert all inputs to canonical form
    canonical_intent = to_canonical_dict(intent)
    canonical_policy_decision = to_canonical_dict(policy_decision)
    canonical_safety_verdict = to_canonical_dict(safety_verdict)
    canonical_final_verdict = to_canonical_dict(final_verdict)
    canonical_execution_trace = to_canonical_dict(execution_trace) if execution_trace else {}
    canonical_executor_result = to_canonical_dict(executor_result) if executor_result else {}
    canonical_governance_evidence = to_canonical_dict(governance_evidence) if governance_evidence else {}
    canonical_resolution_evidence = to_canonical_dict(resolution_evidence) if resolution_evidence else {}
    canonical_executor_capabilities = to_canonical_dict(executor_capabilities) if executor_capabilities else {}
    canonical_validation_evidence = to_canonical_dict(validation_evidence) if validation_evidence else {}
    canonical_executor_failure_evidence = to_canonical_dict(executor_failure_evidence) if executor_failure_evidence else {}
    
    # Create canonical bundle data structure
    bundle_data = {
        "schema_version": "2.0",
        "bundle_version": "v1",
        "intent": canonical_intent,
        "policy_decision": canonical_policy_decision,
        "safety_verdict": canonical_safety_verdict,
        "final_verdict": canonical_final_verdict,
        "execution_trace": canonical_execution_trace,
        "executor_result": canonical_executor_result,
        "governance_evidence": canonical_governance_evidence,
        "resolution_evidence": canonical_resolution_evidence,
        "executor_capabilities": canonical_executor_capabilities,
        "validation_evidence": canonical_validation_evidence,
        "executor_failure_evidence": canonical_executor_failure_evidence,
    }
    
    return compute_replay_hash(bundle_data)


def canonicalize_bundle_with_migration(bundle_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Canonicalize bundle with automatic schema migration.
    
    Args:
        bundle_dict: Bundle dictionary to canonicalize
        
    Returns:
        Migrated and canonicalized bundle dictionary
        
    Raises:
        MigrationError: If migration fails or version unsupported
    """
    # Detect and migrate schema version
    try:
        migrated_bundle = SchemaMigrations.migrate_bundle(bundle_dict)
    except MigrationError as e:
        raise MigrationError(f"Bundle migration failed: {e.message}", e.from_version, e.to_version)
    
    # Validate schema compliance
    validation_report = SchemaMigrations.validate_schema_compliance(migrated_bundle)
    if not validation_report["is_supported"]:
        raise MigrationError(
            f"Unsupported schema version: {validation_report['schema_version']}",
            validation_report["schema_version"]
        )
    
    return to_canonical_dict(migrated_bundle)


def compute_replay_hash_with_migration(bundle_dict: Dict[str, Any]) -> str:
    """Compute replay hash with automatic schema migration.
    
    Args:
        bundle_dict: Bundle dictionary to hash
        
    Returns:
        Hexadecimal SHA-256 hash of migrated canonical bundle
        
    Raises:
        MigrationError: If migration fails or version unsupported
    """
    migrated_bundle = canonicalize_bundle_with_migration(bundle_dict)
    return compute_replay_hash(migrated_bundle)


def verify_canonicalization(data: Dict[str, Any]) -> bool:
    """Verify that data follows canonicalization rules for replay.
    
    Args:
        data: Data to verify
        
    Returns:
        True if data is properly canonicalized
    """
    try:
        # Check for NaN values
        json_str = json.dumps(data, allow_nan=False)
        
        # Parse back and compare
        parsed = json.loads(json_str)
        
        # Check for nested None values that should be excluded
        def check_none_values(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value is None:
                        return False, f"None value found at {path}.{key}"
                    result, msg = check_none_values(value, f"{path}.{key}")
                    if not result:
                        return False, msg
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    if value is None:
                        return False, f"None value found at {path}[{i}]"
                    result, msg = check_none_values(value, f"{path}[{i}]")
                    if not result:
                        return False, msg
            return True, ""
        
        return check_none_values(parsed)[0]
        
    except (ValueError, TypeError):
        return False


def compute_integrity_checksum(data: Dict[str, Any]) -> str:
    """Compute integrity checksum for enhanced replay verification.
    
    Args:
        data: Data to checksum
        
    Returns:
        Hexadecimal SHA-256 checksum
    """
    # Create a simplified version for integrity checking
    integrity_data = {
        "keys": sorted(data.keys()),
        "hashes": {k: compute_replay_hash(v) if isinstance(v, dict) else str(v) 
                 for k, v in data.items()}
    }
    
    return compute_replay_hash(integrity_data)


def canonical_diff(original: Dict[str, Any], modified: Dict[str, Any]) -> Dict[str, Any]:
    """Generate deterministic diff between two canonical dictionaries.
    
    Args:
        original: Original canonical dictionary
        modified: Modified canonical dictionary
        
    Returns:
        Deterministic diff structure
    """
    def _diff_recursive(orig: Any, mod: Any, path: str = "") -> Dict[str, Any]:
        diff = {
            "added": [],
            "removed": [],
            "modified": {},
            "unchanged": []
        }
        
        if isinstance(orig, dict) and isinstance(mod, dict):
            orig_keys = set(orig.keys())
            mod_keys = set(mod.keys())
            
            # Added keys
            for key in sorted(mod_keys - orig_keys):
                diff["added"].append(f"{path}.{key}" if path else key)
            
            # Removed keys
            for key in sorted(orig_keys - mod_keys):
                diff["removed"].append(f"{path}.{key}" if path else key)
            
            # Common keys
            for key in sorted(orig_keys & mod_keys):
                key_path = f"{path}.{key}" if path else key
                orig_val = orig[key]
                mod_val = mod[key]
                
                if orig_val != mod_val:
                    if isinstance(orig_val, dict) and isinstance(mod_val, dict):
                        nested_diff = _diff_recursive(orig_val, mod_val, key_path)
                        diff["modified"][key] = nested_diff
                    else:
                        diff["modified"][key] = {
                            "original": orig_val,
                            "modified": mod_val
                        }
                else:
                    diff["unchanged"].append(key_path)
        
        elif orig != mod:
            diff["modified"] = {
                "original": orig,
                "modified": mod
            }
        
        return diff
    
    return _diff_recursive(original, modified)


def validate_replay_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data for replay compliance.
    
    Args:
        data: Data to validate
        
    Returns:
        Validation results with any issues found
    """
    issues = []
    warnings = []
    
    # Check canonicalization
    if not verify_canonicalization(data):
        issues.append("Data is not properly canonicalized")
    
    # Check for required fields in bundle data
    if "bundle_version" not in data:
        issues.append("Missing bundle_version field")
    elif data["bundle_version"] not in ["v1"]:
        issues.append(f"Unsupported bundle version: {data['bundle_version']}")
    
    # Check for deterministic patterns
    if "bundle_id" in data:
        bundle_id = data["bundle_id"]
        if not isinstance(bundle_id, str) or len(bundle_id) != 26:
            issues.append("Invalid bundle_id format")
    
    # Check for timestamps (should be None for determinism)
    if "bundle_created_at" in data and data["bundle_created_at"] is not None:
        warnings.append("bundle_created_at should be None for deterministic replay")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }
