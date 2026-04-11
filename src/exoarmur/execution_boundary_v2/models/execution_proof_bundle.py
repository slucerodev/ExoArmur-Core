"""
Execution proof bundle model for deterministic replay verification.

# INTERNAL MODULE: Not part of the public SDK surface.
# Use exoarmur.sdk.public_api instead.
# This module is an implementation detail and may change without notice.

This model provides a canonical, versioned representation of execution
artifacts that can be deterministically replayed and verified with
comprehensive governance verdict tracking and executor sandboxing.
Enhanced with forensic-grade replay verification support.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from exoarmur.clock import utc_now
from exoarmur.ids import make_bundle_id
from ..utils.verdict_resolution import FinalVerdict


class ExecutionProofBundle(BaseModel):
    """Canonical execution proof bundle for deterministic replay verification.
    
    Contains all execution artifacts needed to replay and verify an execution
    with full determinism and cryptographic integrity guarantees. Enhanced
    with comprehensive governance verdict tracking and executor sandboxing.
    """
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    bundle_id: str = Field(description="Bundle identifier (deterministic ULID)")
    schema_version: str = Field(default="2.0", description="Schema version for migration compatibility")
    bundle_version: str = Field(default="v1", description="Bundle format version")
    intent: Dict[str, Any] = Field(description="Original intent (canonicalized)")
    policy_decision: Dict[str, Any] = Field(description="Policy decision (canonicalized)")
    safety_verdict: Dict[str, Any] = Field(description="Safety gate verdict (canonicalized)")
    final_verdict: FinalVerdict = Field(description="Final resolved verdict")
    approval_records: List[Dict[str, Any]] = Field(default_factory=list, description="Approval records (if any)")
    execution_trace: Dict[str, Any] = Field(description="Complete execution trace (canonicalized)")
    executor_result: Dict[str, Any] = Field(description="Executor result (canonicalized)")
    replay_hash: str = Field(description="SHA-256 hash of canonical bundle data")
    bundle_created_at: Optional[datetime] = Field(default=None, description="Bundle creation timestamp (optional for determinism)")
    
    # Governance evidence fields for comprehensive audit trails
    governance_evidence: Dict[str, Any] = Field(default_factory=dict, description="Governance decision evidence")
    resolution_evidence: Dict[str, Any] = Field(default_factory=dict, description="Verdict resolution evidence")
    
    # Executor sandboxing fields for capability enforcement
    executor_capabilities: Dict[str, Any] = Field(default_factory=dict, description="Executor capabilities and constraints")
    validation_evidence: Dict[str, Any] = Field(default_factory=dict, description="Target validation evidence")
    executor_failure_evidence: Dict[str, Any] = Field(default_factory=dict, description="Executor failure evidence")
    
    # Enhanced replay verification fields
    bundle_checksum: Optional[str] = Field(default=None, description="SHA-256 checksum of entire bundle")
    integrity_hash: Optional[str] = Field(default=None, description="Hash for integrity verification")
    replay_verification_timestamp: Optional[str] = Field(default=None, description="Replay verification timestamp")
    
    # Deterministic enforcement flags
    deterministic_timestamps: bool = Field(default=True, description="Whether timestamps are deterministic")
    deterministic_ids: bool = Field(default=True, description="Whether IDs are deterministic")
    canonicalization_verified: bool = Field(default=False, description="Whether canonicalization has been verified")
    
    # Audit linking
    audit_stream_id: Optional[str] = Field(default=None, description="Audit stream identifier")
    audit_event_count: int = Field(default=0, description="Number of audit events generated")

    @classmethod
    def create(cls, intent: Dict[str, Any], policy_decision: Dict[str, Any],
               safety_verdict: Dict[str, Any], final_verdict: FinalVerdict,
               approval_records: Optional[List[Dict[str, Any]]] = None,
               execution_trace: Optional[Dict[str, Any]] = None,
               executor_result: Optional[Dict[str, Any]] = None,
               governance_evidence: Optional[Dict[str, Any]] = None,
               resolution_evidence: Optional[Dict[str, Any]] = None,
               executor_capabilities: Optional[Dict[str, Any]] = None,
               validation_evidence: Optional[Dict[str, Any]] = None,
               executor_failure_evidence: Optional[Dict[str, Any]] = None,
               audit_stream_id: Optional[str] = None,
               audit_event_count: int = 0) -> "ExecutionProofBundle":
        """Create execution proof bundle with deterministic ID and enhanced verification."""
        
        # Helper function to convert datetime objects to ISO strings for JSON serialization
        def serialize_datetime(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, 'value'):  # Handle enum objects
                return obj.value
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            else:
                return obj
        
        # Create canonical representation for hash computation
        canonical_data = {
            "schema_version": "2.0",
            "bundle_version": "v1",
            "intent": serialize_datetime(intent),
            "policy_decision": serialize_datetime(policy_decision),
            "safety_verdict": serialize_datetime(safety_verdict),
            "final_verdict": final_verdict.value,
            "approval_records": serialize_datetime(approval_records or []),
            "execution_trace": serialize_datetime(execution_trace or {}),
            "executor_result": serialize_datetime(executor_result or {}),
            "governance_evidence": serialize_datetime(governance_evidence or {}),
            "resolution_evidence": serialize_datetime(resolution_evidence or {}),
            "executor_capabilities": serialize_datetime(executor_capabilities or {}),
            "validation_evidence": serialize_datetime(validation_evidence or {}),
            "executor_failure_evidence": serialize_datetime(executor_failure_evidence or {}),
        }
        
        # Generate canonical hash
        import json
        import hashlib
        canonical_json_bytes = json.dumps(canonical_data, sort_keys=True, separators=(",", ":")).encode()
        replay_hash = hashlib.sha256(canonical_json_bytes).hexdigest()
        
        # Generate bundle ID from intent_id only (not replay_hash to avoid circular dependency)
        intent_id = intent.get("intent_id", "unknown")
        bundle_id = make_bundle_id(intent_id, "deterministic-bundle")
        
        # Generate bundle checksum
        bundle_data = {
            "bundle_id": bundle_id,
            "bundle_version": "v1",
            "replay_hash": replay_hash,
            "final_verdict": final_verdict.value,
            "intent": intent_id,
            "correlation_id": intent.get("correlation_id", "unknown")
        }
        bundle_checksum = hashlib.sha256(
            json.dumps(bundle_data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        
        return cls(
            bundle_id=bundle_id,
            bundle_version="v1",
            intent=intent,
            policy_decision=policy_decision,
            safety_verdict=safety_verdict,
            final_verdict=final_verdict,
            approval_records=approval_records or [],
            execution_trace=execution_trace or {},
            executor_result=executor_result or {},
            replay_hash=replay_hash,
            governance_evidence=governance_evidence or {},
            resolution_evidence=resolution_evidence or {},
            executor_capabilities=executor_capabilities or {},
            validation_evidence=validation_evidence or {},
            executor_failure_evidence=executor_failure_evidence or {},
            bundle_checksum=bundle_checksum,
            bundle_created_at=utc_now(),  # Populated for audit trail; excluded from hash by canonicalization
            audit_stream_id=audit_stream_id,
            audit_event_count=audit_event_count
        )
    
    def verify_replay_hash(self) -> bool:
        """Verify replay hash matches canonical bundle data."""
        try:
            import json
            import hashlib
            
            # Must match the serialization used by create()
            def serialize_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif hasattr(obj, 'value'):
                    return obj.value
                elif isinstance(obj, dict):
                    return {k: serialize_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [serialize_datetime(item) for item in obj]
                else:
                    return obj
            
            # Create canonical representation (must match create() exactly)
            canonical_data = {
                "schema_version": self.schema_version,
                "bundle_version": self.bundle_version,
                "intent": serialize_datetime(self.intent),
                "policy_decision": serialize_datetime(self.policy_decision),
                "safety_verdict": serialize_datetime(self.safety_verdict),
                "final_verdict": self.final_verdict.value,
                "approval_records": serialize_datetime(self.approval_records),
                "execution_trace": serialize_datetime(self.execution_trace),
                "executor_result": serialize_datetime(self.executor_result),
                "governance_evidence": serialize_datetime(self.governance_evidence),
                "resolution_evidence": serialize_datetime(self.resolution_evidence),
                "executor_capabilities": serialize_datetime(self.executor_capabilities),
                "validation_evidence": serialize_datetime(self.validation_evidence),
                "executor_failure_evidence": serialize_datetime(self.executor_failure_evidence),
            }
            
            # Generate canonical hash
            canonical_json_bytes = json.dumps(canonical_data, sort_keys=True, separators=(",", ":")).encode()
            computed_hash = hashlib.sha256(canonical_json_bytes).hexdigest()
            
            return computed_hash == self.replay_hash
            
        except Exception:
            return False
    
    def verify_bundle_checksum(self) -> bool:
        """Verify bundle checksum matches core bundle data."""
        try:
            import json
            import hashlib
            
            # Generate bundle checksum
            bundle_data = {
                "bundle_id": self.bundle_id,
                "bundle_version": self.bundle_version,
                "replay_hash": self.replay_hash,
                "final_verdict": self.final_verdict.value,
                "intent": self.intent.get("intent_id", "unknown"),
                "correlation_id": self.intent.get("correlation_id", "unknown")
            }
            computed_checksum = hashlib.sha256(
                json.dumps(bundle_data, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            
            return computed_checksum == self.bundle_checksum
            
        except Exception:
            return False
    
    def verify_determinism(self) -> Dict[str, bool]:
        """Verify bundle follows deterministic patterns."""
        results = {
            "timestamps_deterministic": True,
            "ids_deterministic": True,
            "canonicalization_valid": True
        }
        
        # Check timestamp determinism
        if self.bundle_created_at is not None:
            results["timestamps_deterministic"] = False
        
        # Check ID determinism
        if not self._is_valid_ulid(self.bundle_id):
            results["ids_deterministic"] = False
        
        # Check canonicalization
        if not self.verify_replay_hash():
            results["canonicalization_valid"] = False
        
        return results
    
    def verify_integrity(self) -> bool:
        """Verify complete bundle integrity."""
        # Verify replay hash
        if not self.verify_replay_hash():
            return False
        
        # Verify bundle checksum
        if self.bundle_checksum and not self.verify_bundle_checksum():
            return False
        
        # Verify determinism
        determinism_results = self.verify_determinism()
        if not all(determinism_results.values()):
            return False
        
        return True
    
    def get_replay_summary(self) -> Dict[str, Any]:
        """Get summary for replay verification."""
        return {
            "bundle_id": self.bundle_id,
            "bundle_version": self.bundle_version,
            "correlation_id": self.intent.get("correlation_id", "unknown"),
            "intent_id": self.intent.get("intent_id", "unknown"),
            "final_verdict": self.final_verdict.value,
            "has_approval_records": len(self.approval_records) > 0,
            "has_execution_trace": bool(self.execution_trace),
            "has_executor_result": bool(self.executor_result),
            "has_governance_evidence": bool(self.governance_evidence),
            "has_executor_capabilities": bool(self.executor_capabilities),
            "audit_event_count": self.audit_event_count,
            "replay_hash_verified": self.verify_replay_hash(),
            "bundle_checksum_verified": self.verify_bundle_checksum() if self.bundle_checksum else None,
            "integrity_verified": self.verify_integrity(),
            "determinism_results": self.verify_determinism()
        }
    
    def _is_valid_ulid(self, ulid_string: str) -> bool:
        """Check if string is a valid ULID format."""
        if not isinstance(ulid_string, str):
            return False
        
        # Basic ULID format check: 26 characters, base32
        if len(ulid_string) != 26:
            return False
        
        # Check if all characters are valid base32
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        return all(c in valid_chars for c in ulid_string.upper())
