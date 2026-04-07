"""
Schema migration layer for ExecutionProofBundle and related structures.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

Provides deterministic migration between schema versions with comprehensive
error handling and version validation for forensic-grade replay verification.
"""

from typing import Dict, Any, Optional
from enum import Enum

from exoarmur.clock import utc_now
from exoarmur.ids import make_id


class SchemaVersion(Enum):
    """Supported schema versions with migration paths."""
    V1_0 = "1.0"
    V2_0 = "2.0"
    
    @classmethod
    def current(cls) -> str:
        """Get current schema version."""
        return cls.V2_0.value
    
    @classmethod
    def is_supported(cls, version: str) -> bool:
        """Check if schema version is supported."""
        return version in [v.value for v in cls]
    
    @classmethod
    def requires_migration(cls, from_version: str, to_version: str) -> bool:
        """Check if migration is required between versions."""
        return from_version != to_version


class MigrationError(Exception):
    """Deterministic migration error with schema version context."""
    
    def __init__(self, message: str, from_version: str, to_version: Optional[str] = None):
        self.from_version = from_version
        self.to_version = to_version
        self.message = message
        self.timestamp = utc_now()
        self.error_id = make_id("migration_error")
        super().__init__(self.message)


class SchemaMigrations:
    """Deterministic schema migration engine for ExecutionProofBundle structures."""
    
    @staticmethod
    def detect_schema_version(bundle_dict: Dict[str, Any]) -> str:
        """Detect schema version from bundle dictionary.
        
        Args:
            bundle_dict: Bundle dictionary to analyze
            
        Returns:
            Detected schema version
            
        Raises:
            MigrationError: If version cannot be determined
        """
        if "schema_version" in bundle_dict:
            version = bundle_dict["schema_version"]
            if not isinstance(version, str):
                raise MigrationError(
                    f"schema_version must be string, got {type(version).__name__}",
                    "unknown"
                )
            return version
        
        # Detect V1.0 by absence of schema_version and presence of V1 fields
        if "bundle_version" in bundle_dict and bundle_dict.get("bundle_version") == "v1":
            return SchemaVersion.V1_0.value
        
        # Default to V1.0 for backward compatibility
        return SchemaVersion.V1_0.value
    
    @staticmethod
    def migrate_bundle(bundle_dict: Dict[str, Any], target_version: Optional[str] = None) -> Dict[str, Any]:
        """Migrate bundle dictionary to target schema version.
        
        Args:
            bundle_dict: Bundle dictionary to migrate
            target_version: Target version (defaults to current)
            
        Returns:
            Migrated bundle dictionary
            
        Raises:
            MigrationError: If migration fails or version unsupported
        """
        if target_version is None:
            target_version = SchemaVersion.current()
        
        if not SchemaVersion.is_supported(target_version):
            raise MigrationError(
                f"Target schema version '{target_version}' not supported",
                "unknown",
                target_version
            )
        
        # Detect current version
        current_version = SchemaMigrations.detect_schema_version(bundle_dict)
        
        if not SchemaVersion.is_supported(current_version):
            raise MigrationError(
                f"Source schema version '{current_version}' not supported",
                current_version,
                target_version
            )
        
        # No migration needed
        if current_version == target_version:
            migrated = bundle_dict.copy()
            migrated["schema_version"] = target_version
            return migrated
        
        # Perform migration
        if current_version == SchemaVersion.V1_0.value and target_version == SchemaVersion.V2_0.value:
            return SchemaMigrations._migrate_v1_to_v2(bundle_dict)
        
        raise MigrationError(
            f"No migration path from '{current_version}' to '{target_version}'",
            current_version,
            target_version
        )
    
    @staticmethod
    def _migrate_v1_to_v2(v1_bundle: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate V1.0 bundle to V2.0 format.
        
        Args:
            v1_bundle: V1.0 bundle dictionary
            
        Returns:
            V2.0 bundle dictionary
        """
        # Start with V1 bundle
        v2_bundle = v1_bundle.copy()
        
        # Update schema version
        v2_bundle["schema_version"] = SchemaVersion.V2_0.value
        
        # Add new V2.0 fields with defaults
        if "bundle_checksum" not in v2_bundle:
            v2_bundle["bundle_checksum"] = None
        
        if "integrity_hash" not in v2_bundle:
            v2_bundle["integrity_hash"] = None
        
        if "replay_verification_timestamp" not in v2_bundle:
            v2_bundle["replay_verification_timestamp"] = None
        
        if "deterministic_timestamps" not in v2_bundle:
            v2_bundle["deterministic_timestamps"] = True
        
        if "deterministic_ids" not in v2_bundle:
            v2_bundle["deterministic_ids"] = True
        
        if "canonicalization_verified" not in v2_bundle:
            v2_bundle["canonicalization_verified"] = False
        
        if "audit_stream_id" not in v2_bundle:
            v2_bundle["audit_stream_id"] = None
        
        if "audit_event_count" not in v2_bundle:
            v2_bundle["audit_event_count"] = 0
        
        # Migrate execution trace if present
        if "execution_trace" in v2_bundle and v2_bundle["execution_trace"]:
            v2_bundle["execution_trace"] = SchemaMigrations.migrate_trace(
                v2_bundle["execution_trace"], SchemaVersion.V2_0.value
            )
        
        return v2_bundle
    
    @staticmethod
    def migrate_trace(trace_dict: Dict[str, Any], target_version: Optional[str] = None) -> Dict[str, Any]:
        """Migrate execution trace to target schema version.
        
        Args:
            trace_dict: Trace dictionary to migrate
            target_version: Target version (defaults to current)
            
        Returns:
            Migrated trace dictionary
        """
        if target_version is None:
            target_version = SchemaVersion.current()
        
        # For now, traces follow bundle version
        # In future, traces might have independent versioning
        migrated = trace_dict.copy()
        
        # Add V2.0 fields if missing
        if target_version == SchemaVersion.V2_0.value:
            if "trace_hash" not in migrated:
                migrated["trace_hash"] = None
            
            if "integrity_checksum" not in migrated:
                migrated["integrity_checksum"] = None
            
            if "replay_timestamp" not in migrated:
                migrated["replay_timestamp"] = None
            
            if "audit_stream_id" not in migrated:
                migrated["audit_stream_id"] = None
            
            if "audit_event_count" not in migrated:
                migrated["audit_event_count"] = 0
        
        return migrated
    
    @staticmethod
    def migrate_event(event_dict: Dict[str, Any], target_version: Optional[str] = None) -> Dict[str, Any]:
        """Migrate trace event to target schema version.
        
        Args:
            event_dict: Event dictionary to migrate
            target_version: Target version (defaults to current)
            
        Returns:
            Migrated event dictionary
        """
        if target_version is None:
            target_version = SchemaVersion.current()
        
        # For now, events follow bundle version
        migrated = event_dict.copy()
        
        # Add V2.0 fields if missing
        if target_version == SchemaVersion.V2_0.value:
            if "checksum" not in migrated:
                migrated["checksum"] = None
            
            if "parent_event_id" not in migrated:
                migrated["parent_event_id"] = None
            
            if "event_hash" not in migrated:
                migrated["event_hash"] = None
        
        return migrated
    
    @staticmethod
    def validate_schema_compliance(bundle_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate bundle schema compliance and return validation report.
        
        Args:
            bundle_dict: Bundle dictionary to validate
            
        Returns:
            Validation report with compliance status
        """
        schema_version = SchemaMigrations.detect_schema_version(bundle_dict)
        
        report = {
            "schema_version": schema_version,
            "is_supported": SchemaVersion.is_supported(schema_version),
            "is_current": schema_version == SchemaVersion.current(),
            "validation_timestamp": utc_now(),
            "validation_id": make_id("schema_validation"),
            "issues": []
        }
        
        # Check required fields for current version
        if schema_version == SchemaVersion.V2_0.value:
            required_fields = [
                "schema_version", "bundle_id", "bundle_version", "replay_hash",
                "intent", "policy_decision", "safety_verdict", "final_verdict"
            ]
            
            for field in required_fields:
                if field not in bundle_dict:
                    report["issues"].append(f"Missing required field: {field}")
        
        return report