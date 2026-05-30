#!/usr/bin/env python3
"""
Generate demo artifacts from real ExoArmur-Core E2E flows.

This script creates realistic demo JSON artifacts for use by ExoArmur-Web-UI
as local demo data. All artifacts are generated from real Core objects using
deterministic flows where possible.
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from exoarmur.kernel.boundary import (
    ActionIntent,
    PolicyDecision,
    PolicyVerdict,
    PolicyDecisionPoint,
    SafetyGate,
    V2AuditEmitter,
    ProxyPipeline,
    DispatchStatus,
    ExecutionDispatch,
    ExecutorResult,
)
from exoarmur.kernel.external_effect import (
    ExternalEffectEvidence,
    RollbackStrategy,
    ReplayVerificationStatus,
    ExecutionMode,
)
from exoarmur.kernel.canonicalization import canonical_hash
from exoarmur.executors.file_system_executor import FileSystemExecutor
from exoarmur.executors.database_executor import DatabaseExecutor


# Output directory
OUTPUT_DIR = Path(__file__).parent / "demo_artifacts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class MockPolicyDecisionPoint(PolicyDecisionPoint):
    """Mock policy decision point for demo artifact generation."""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=PolicyVerdict.ALLOW,
            rationale="Demo policy allows all"
        )
    
    def approval_status(self, intent_id: str):
        from exoarmur.kernel.boundary import ApprovalStatus
        return ApprovalStatus.NOT_REQUIRED


class DenyPolicyDecisionPoint(PolicyDecisionPoint):
    """Mock policy decision point that denies for demo artifact generation."""
    
    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        return PolicyDecision.create(
            intent_id=intent.intent_id,
            verdict=PolicyVerdict.DENY,
            rationale="Demo policy denies this operation"
        )
    
    def approval_status(self, intent_id: str):
        from exoarmur.kernel.boundary import ApprovalStatus
        return ApprovalStatus.NOT_REQUIRED


def sanitize_path(path: str) -> str:
    """Sanitize local paths for public demo artifacts."""
    return path.replace(str(Path.home()), "/home/demo").replace("/tmp", "/tmp/demo")


def serialize_to_json(data: Any, output_path: Path) -> None:
    """Serialize data to JSON with sorted keys and indentation."""
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)


def generate_manifest() -> Dict[str, Any]:
    """Generate manifest.json with artifact metadata."""
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "description": "Demo artifacts generated from ExoArmur-Core E2E flows",
        "artifacts": [
            {
                "name": "filesystem_allow_trace.json",
                "description": "Trace from allowed filesystem execution showing successful file creation"
            },
            {
                "name": "filesystem_deny_trace.json",
                "description": "Trace from denied filesystem execution showing blocked operation"
            },
            {
                "name": "database_allow_trace.json",
                "description": "Trace from allowed database execution showing successful table creation and insert"
            },
            {
                "name": "external_effect_replay_verified.json",
                "description": "External effect evidence with verified replay status"
            },
            {
                "name": "external_effect_tamper_detected.json",
                "description": "External effect evidence with tamper detection failure"
            }
        ]
    }


def generate_filesystem_allow_trace() -> Dict[str, Any]:
    """Generate filesystem_allow_trace.json from real Core execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        authorized_root = tmp_path / "authorized"
        authorized_root.mkdir()
        
        executor = FileSystemExecutor(authorized_root=str(authorized_root))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        target_file = authorized_root / "test.txt"
        intent = ActionIntent.create(
            actor_id="demo_actor",
            actor_type="human",
            action_type="file_create",
            target=str(target_file),
            parameters={
                "operation": "create",
                "payload": {"content": "demo content"}
            }
        )
        
        result, trace = pipeline.execute_with_trace(intent)
        
        # Serialize to dict and sanitize paths
        trace_dict = {
            "intent_id": trace.intent_id,
            "trace_id": trace.trace_id,
            "events": [
                {
                    "event_id": event.event_id,
                    "stage": event.stage.value if hasattr(event.stage, 'value') else str(event.stage),
                    "ok": event.ok,
                    "code": event.code,
                    "details": event.details,
                    "timestamp": event.timestamp,
                    "sequence": event.sequence
                }
                for event in trace.events
            ],
            "final_verdict": trace.final_verdict,
            "executor_result": {
                "success": result.success if isinstance(result, ExecutorResult) else None,
                "error": result.error if isinstance(result, ExecutorResult) else None,
                "evidence": result.evidence if isinstance(result, ExecutorResult) else None
            }
        }
        
        # Sanitize paths in trace data
        trace_dict = json.loads(json.dumps(trace_dict).replace(str(tmp_path), "/tmp/demo"))
        
        return trace_dict


def generate_filesystem_deny_trace() -> Dict[str, Any]:
    """Generate filesystem_deny_trace.json from real Core execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        authorized_root = tmp_path / "authorized"
        authorized_root.mkdir()
        
        executor = FileSystemExecutor(authorized_root=str(authorized_root))
        policy = DenyPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        # Try to create file outside authorized root
        target_file = tmp_path / "unauthorized" / "test.txt"
        intent = ActionIntent.create(
            actor_id="demo_actor",
            actor_type="human",
            action_type="file_create",
            target=str(target_file),
            parameters={
                "operation": "create",
                "payload": {"content": "unauthorized content"}
            }
        )
        
        result, trace = pipeline.execute_with_trace(intent)
        
        # Serialize to dict and sanitize paths
        trace_dict = {
            "intent_id": trace.intent_id,
            "trace_id": trace.trace_id,
            "events": [
                {
                    "event_id": event.event_id,
                    "stage": event.stage.value if hasattr(event.stage, 'value') else str(event.stage),
                    "ok": event.ok,
                    "code": event.code,
                    "details": event.details,
                    "timestamp": event.timestamp,
                    "sequence": event.sequence
                }
                for event in trace.events
            ],
            "final_verdict": trace.final_verdict,
            "dispatch_status": result.status.value if isinstance(result, ExecutionDispatch) else None
        }
        
        # Sanitize paths in trace data
        trace_dict = json.loads(json.dumps(trace_dict).replace(str(tmp_path), "/tmp/demo"))
        
        return trace_dict


def generate_database_allow_trace() -> Dict[str, Any]:
    """Generate database_allow_trace.json from real Core execution."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        executor = DatabaseExecutor(authorized_db_dir=str(tmp_path))
        policy = MockPolicyDecisionPoint()
        safety_gate = SafetyGate()
        audit_emitter = V2AuditEmitter()
        
        pipeline = ProxyPipeline(policy, safety_gate, executor, audit_emitter)
        
        # Create table intent
        db_path = tmp_path / "demo.db"
        intent = ActionIntent.create(
            actor_id="demo_actor",
            actor_type="human",
            action_type="database_execute",
            target=str(db_path),
            parameters={
                "operation": "create_table",
                "sql": "CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)"
            }
        )
        
        result, trace = pipeline.execute_with_trace(intent)
        
        # Serialize to dict and sanitize paths
        trace_dict = {
            "intent_id": trace.intent_id,
            "trace_id": trace.trace_id,
            "events": [
                {
                    "event_id": event.event_id,
                    "stage": event.stage.value if hasattr(event.stage, 'value') else str(event.stage),
                    "ok": event.ok,
                    "code": event.code,
                    "details": event.details,
                    "timestamp": event.timestamp,
                    "sequence": event.sequence
                }
                for event in trace.events
            ],
            "final_verdict": trace.final_verdict,
            "executor_result": {
                "success": result.success if isinstance(result, ExecutorResult) else None,
                "error": result.error if isinstance(result, ExecutorResult) else None,
                "evidence": result.evidence if isinstance(result, ExecutorResult) else None
            }
        }
        
        # Sanitize paths in trace data
        trace_dict = json.loads(json.dumps(trace_dict).replace(str(tmp_path), "/tmp/demo"))
        
        return trace_dict


def generate_external_effect_replay_verified() -> Dict[str, Any]:
    """Generate external_effect_replay_verified.json."""
    # Create a sample external effect evidence
    request_data = {"method": "POST", "url": "https://api.example.com/data", "body": {"key": "value"}}
    response_data = {"status": 200, "body": {"result": "success"}}
    
    request_hash = canonical_hash(json.dumps(request_data, sort_keys=True))
    response_hash = canonical_hash(json.dumps(response_data, sort_keys=True))
    
    evidence = ExternalEffectEvidence(
        execution_id="demo_execution_001",
        intent_id="demo_intent_001",
        trace_id="demo_trace_001",
        provider="demo_provider",
        operation_type="demo_operation",
        request_canonical_hash=request_hash,
        response_canonical_hash=response_hash,
        normalized_request=request_data,
        normalized_response=response_data,
        evidence_timestamp=datetime.now(timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
        replay_verification_status=ReplayVerificationStatus.VERIFIED
    )
    
    # Serialize to dict
    evidence_dict = evidence.to_dict()
    
    return evidence_dict


def generate_external_effect_tamper_detected() -> Dict[str, Any]:
    """Generate external_effect_tamper_detected.json by tampering with verified evidence."""
    # Start with verified evidence
    request_data = {"method": "POST", "url": "https://api.example.com/data", "body": {"key": "value"}}
    response_data = {"status": 200, "body": {"result": "success"}}
    
    request_hash = canonical_hash(json.dumps(request_data, sort_keys=True))
    response_hash = canonical_hash(json.dumps(response_data, sort_keys=True))
    
    # Tamper with the response data
    tampered_response_data = {"status": 200, "body": {"result": "tampered"}}
    
    evidence = ExternalEffectEvidence(
        execution_id="demo_execution_002",
        intent_id="demo_intent_002",
        trace_id="demo_trace_002",
        provider="demo_provider",
        operation_type="demo_operation",
        request_canonical_hash=request_hash,
        response_canonical_hash=response_hash,  # Original hash (mismatch!)
        normalized_request=request_data,
        normalized_response=tampered_response_data,
        evidence_timestamp=datetime.now(timezone.utc),
        irreversible_effect=True,
        rollback_strategy=RollbackStrategy.RECORD_ONLY,
        replay_verification_status=ReplayVerificationStatus.MISMATCH
    )
    
    # Serialize to dict
    evidence_dict = evidence.to_dict()
    
    return evidence_dict


def main():
    """Generate all demo artifacts."""
    print("Generating demo artifacts...")
    
    # Generate manifest
    manifest = generate_manifest()
    serialize_to_json(manifest, OUTPUT_DIR / "manifest.json")
    print(f"Generated: manifest.json")
    
    # Generate filesystem allow trace
    fs_allow = generate_filesystem_allow_trace()
    serialize_to_json(fs_allow, OUTPUT_DIR / "filesystem_allow_trace.json")
    print(f"Generated: filesystem_allow_trace.json")
    
    # Generate filesystem deny trace
    fs_deny = generate_filesystem_deny_trace()
    serialize_to_json(fs_deny, OUTPUT_DIR / "filesystem_deny_trace.json")
    print(f"Generated: filesystem_deny_trace.json")
    
    # Generate database allow trace
    db_allow = generate_database_allow_trace()
    serialize_to_json(db_allow, OUTPUT_DIR / "database_allow_trace.json")
    print(f"Generated: database_allow_trace.json")
    
    # Generate external effect replay verified
    ext_verified = generate_external_effect_replay_verified()
    serialize_to_json(ext_verified, OUTPUT_DIR / "external_effect_replay_verified.json")
    print(f"Generated: external_effect_replay_verified.json")
    
    # Generate external effect tamper detected
    ext_tampered = generate_external_effect_tamper_detected()
    serialize_to_json(ext_tampered, OUTPUT_DIR / "external_effect_tamper_detected.json")
    print(f"Generated: external_effect_tamper_detected.json")
    
    print(f"\nAll artifacts generated in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
