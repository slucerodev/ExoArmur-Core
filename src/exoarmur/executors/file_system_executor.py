"""
FileSystemExecutor - Production-grade file system executor for ExoArmur.

Implements ExecutorPlugin interface with rollback capabilities, state verification,
and deterministic audit emission for file operations.
"""

import os
import shutil
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from datetime import datetime

from exoarmur.kernel.boundary import (
    ExecutorPlugin,
    ExecutorResult,
    ExecutorCapabilities,
    TargetValidationResult,
    ValidationResult,
    ActionIntent,
    ActionClass
)
from exoarmur.kernel.clock import utc_now


class RollbackPlan:
    """Rollback plan for reversible file operations."""
    
    def __init__(
        self,
        action_type: str,
        original_state_path: Optional[str],
        target_path: str,
        expiration_timestamp: datetime,
        rollback_command: Optional[Callable[[], bool]] = None,
        rollback_instruction: Optional[Dict[str, Any]] = None
    ):
        self.action_type = action_type
        self.original_state_path = original_state_path
        self.target_path = target_path
        # Ensure expiration_timestamp is timezone-aware (convert if naive, preserve if aware)
        if expiration_timestamp.tzinfo is None:
            from datetime import timezone
            self.expiration_timestamp = expiration_timestamp.replace(tzinfo=timezone.utc)
        else:
            self.expiration_timestamp = expiration_timestamp
        self.rollback_command = rollback_command
        self.rollback_instruction = rollback_instruction or {}
        self.plan_id = self._generate_plan_id()
    
    def _generate_plan_id(self) -> str:
        """Generate deterministic plan ID."""
        seed = f"{self.action_type}:{self.target_path}:{self.expiration_timestamp.isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]
    
    def is_expired(self) -> bool:
        """Check if rollback plan has expired."""
        now = utc_now()
        # Ensure both datetimes are timezone-aware for comparison
        if now.tzinfo is None:
            from datetime import timezone
            now = now.replace(tzinfo=timezone.utc)
        if self.expiration_timestamp.tzinfo is None:
            from datetime import timezone
            self.expiration_timestamp = self.expiration_timestamp.replace(tzinfo=timezone.utc)
        return now > self.expiration_timestamp


class RollbackResult:
    """Result of rollback operation."""
    
    def __init__(
        self,
        success: bool,
        restored_state_hash: Optional[str],
        hash_match: bool,
        time_to_rollback_ms: int,
        error: Optional[str] = None
    ):
        self.success = success
        self.restored_state_hash = restored_state_hash
        self.hash_match = hash_match
        self.time_to_rollback_ms = time_to_rollback_ms
        self.error = error


class FileSystemExecutor(ExecutorPlugin):
    """Production-grade file system executor with rollback capabilities.
    
    Executes file operations through ProxyPipeline governance boundary with:
    - Pre-execution rollback plan computation
    - State hash verification
    - 300-second rollback window for A1/A2 actions
    - Deterministic audit emission
    - Safety gate integration
    """
    
    ROLLBACK_WINDOW_SECONDS = 300
    
    def __init__(self, authorized_root: str = "/tmp"):
        """Initialize FileSystemExecutor.
        
        Args:
            authorized_root: Root directory for allowed file operations
        """
        self.authorized_root = Path(authorized_root).resolve()
        self._rollback_plans: Dict[str, RollbackPlan] = {}
        self._trash_dir = Path(tempfile.mkdtemp(prefix="exoarmur_trash_"))
    
    def name(self) -> str:
        """Return executor name."""
        return "FileSystemExecutor"
    
    def capabilities(self) -> Dict[str, Any]:
        """Return executor capabilities."""
        return {
            "executor_name": self.name(),
            "version": "1.0.0",
            "capabilities": [
                "file_create",
                "file_delete",
                "file_rename",
                "file_modify",
                "file_read",
                "file_stat"
            ],
            "constraints": {
                "authorized_root": str(self.authorized_root),
                "rollback_window_seconds": self.ROLLBACK_WINDOW_SECONDS
            },
            "supported_targets": [str(self.authorized_root)],
            "required_parameters": ["operation"]
        }
    
    def validate_target(self, intent: ActionIntent) -> TargetValidationResult:
        """Validate target against authorized root.
        
        Args:
            intent: Action intent to validate
            
        Returns:
            TargetValidationResult with validation evidence
        """
        target_path = Path(intent.target).resolve()
        
        # Check if path is within authorized root
        try:
            target_path.relative_to(self.authorized_root)
            return TargetValidationResult(
                result=ValidationResult.VALID,
                evidence={
                    "target": str(target_path),
                    "authorized_root": str(self.authorized_root),
                    "is_authorized": True
                },
                validation_id=self._generate_validation_id(intent)
            )
        except ValueError:
            return TargetValidationResult(
                result=ValidationResult.VIOLATES_CONSTRAINTS,
                evidence={
                    "target": str(target_path),
                    "authorized_root": str(self.authorized_root),
                    "is_authorized": False,
                    "reason": "Path outside authorized root"
                },
                validation_id=self._generate_validation_id(intent)
            )
    
    def execute(
        self,
        intent: ActionIntent,
        policy_decision: Any,
        governance_context: Dict[str, Any]
    ) -> ExecutorResult:
        """Execute file operation with rollback plan.
        
        Args:
            intent: Action intent to execute
            policy_decision: Policy decision authorizing execution
            governance_context: Additional governance context
            
        Returns:
            ExecutorResult with execution evidence
        """
        # Extract operation from parameters
        operation = intent.parameters.get("operation", "unknown")
        payload = intent.parameters.get("payload", {})
        
        # Classify action
        action_class = self.classify_file_action(operation, payload)
        
        # Check safety gate from governance context
        final_verdict = governance_context.get("final_verdict")
        if final_verdict and str(final_verdict) == "DENY":
            return ExecutorResult(
                success=False,
                output={},
                error="SAFETY_GATE_DENY",
                evidence={
                    "action_class": action_class.value,
                    "operation": operation,
                    "reason": "Safety gate denied execution"
                },
                execution_id=self._generate_execution_id(intent)
            )
        
        # Compute pre-execution state hash
        target_path = Path(intent.target)
        pre_hash = self.compute_state_hash(target_path) if target_path.exists() else None
        
        # Compute rollback plan before execution
        rollback_plan = None
        if action_class in [ActionClass.A1_SOFT_CONTAINMENT, ActionClass.A2_HARD_CONTAINMENT]:
            rollback_plan = self.compute_rollback(intent, action_class)
            if rollback_plan:
                self._rollback_plans[rollback_plan.plan_id] = rollback_plan
        
        # Execute the operation
        try:
            execution_start = utc_now()
            
            if operation == "create":
                self._execute_create(target_path, payload)
            elif operation == "delete":
                self._execute_delete(target_path, rollback_plan)
            elif operation == "rename":
                self._execute_rename(target_path, payload, rollback_plan)
            elif operation == "modify":
                self._execute_modify(target_path, payload, rollback_plan)
            elif operation == "read":
                result = self._execute_read(target_path)
            elif operation == "stat":
                result = self._execute_stat(target_path)
            else:
                return ExecutorResult(
                    success=False,
                    output={},
                    error=f"Unsupported operation: {operation}",
                    evidence={"action_class": action_class.value},
                    execution_id=self._generate_execution_id(intent)
                )
            
            # Compute post-execution state hash
            post_hash = self.compute_state_hash(target_path) if target_path.exists() else None
            
            # Calculate execution time
            execution_time_ms = int((utc_now() - execution_start).total_seconds() * 1000)
            
            # Build output
            output = {
                "operation": operation,
                "target": str(target_path),
                "action_class": action_class.value,
                "pre_hash": pre_hash,
                "post_hash": post_hash,
                "execution_time_ms": execution_time_ms
            }
            
            if rollback_plan:
                output["rollback_plan_id"] = rollback_plan.plan_id
            
            # Emit audit event
            self._emit_audit_event(
                intent=intent,
                operation_type=operation,
                target_path=str(target_path),
                action_class=action_class,
                pre_hash=pre_hash,
                post_hash=post_hash,
                rollback_plan_id=rollback_plan.plan_id if rollback_plan else None,
                outcome="executed"
            )
            
            return ExecutorResult(
                success=True,
                output=output,
                evidence=output,
                execution_id=self._generate_execution_id(intent)
            )
            
        except PermissionError as e:
            # Permission error - state unchanged, no rollback needed
            self._emit_audit_event(
                intent=intent,
                operation_type=operation,
                target_path=str(target_path),
                action_class=action_class,
                pre_hash=pre_hash,
                post_hash=pre_hash,
                rollback_plan_id=None,
                outcome="failed",
                error=str(e)
            )
            return ExecutorResult(
                success=False,
                output={},
                error=f"Permission denied: {e}",
                evidence={"action_class": action_class.value},
                execution_id=self._generate_execution_id(intent)
            )
            
        except Exception as e:
            # Other exception - attempt rollback if A1/A2
            self._emit_audit_event(
                intent=intent,
                operation_type=operation,
                target_path=str(target_path),
                action_class=action_class,
                pre_hash=pre_hash,
                post_hash=None,
                rollback_plan_id=rollback_plan.plan_id if rollback_plan else None,
                outcome="failed",
                error=str(e)
            )
            
            if rollback_plan and action_class in [ActionClass.A1_SOFT_CONTAINMENT, ActionClass.A2_HARD_CONTAINMENT]:
                rollback_result = self.rollback(rollback_plan)
                return ExecutorResult(
                    success=False,
                    output={"rollback_attempted": True, "rollback_success": rollback_result.success},
                    error=str(e),
                    evidence={
                        "action_class": action_class.value,
                        "rollback_result": {
                            "success": rollback_result.success,
                            "hash_match": rollback_result.hash_match
                        }
                    },
                    execution_id=self._generate_execution_id(intent)
                )
            
            return ExecutorResult(
                success=False,
                output={},
                error=str(e),
                evidence={"action_class": action_class.value},
                execution_id=self._generate_execution_id(intent)
            )
    
    def compute_rollback(self, intent: ActionIntent, action_class: ActionClass) -> Optional[RollbackPlan]:
        """Compute rollback plan before execution.
        
        Args:
            intent: Action intent
            action_class: Classified action class
            
        Returns:
            RollbackPlan or None if not applicable
        """
        operation = intent.parameters.get("operation", "unknown")
        target_path = Path(intent.target)
        
        from datetime import timedelta
        expiration_dt = utc_now() + timedelta(seconds=self.ROLLBACK_WINDOW_SECONDS)
        
        if operation == "delete":
            # Copy file to trash before deleting
            if target_path.exists():
                trash_path = self._trash_dir / f"{target_path.name}_{intent.intent_id}"
                shutil.copy2(target_path, trash_path)
                return RollbackPlan(
                    action_type="delete",
                    original_state_path=str(trash_path),
                    target_path=str(target_path),
                    expiration_timestamp=expiration_dt,
                    rollback_instruction={"operation": "restore_from_trash", "trash_path": str(trash_path)}
                )
        
        elif operation == "rename":
            # Store original and new paths
            new_path = Path(intent.parameters.get("payload", {}).get("new_path", ""))
            return RollbackPlan(
                action_type="rename",
                original_state_path=str(target_path),
                target_path=str(new_path),
                expiration_timestamp=expiration_dt,
                rollback_instruction={"operation": "rename_back", "original_path": str(target_path), "new_path": str(new_path)}
            )
        
        elif operation == "modify":
            # Create backup of original content
            if target_path.exists():
                backup_path = self._trash_dir / f"{target_path.name}_backup_{intent.intent_id}"
                shutil.copy2(target_path, backup_path)
                return RollbackPlan(
                    action_type="modify",
                    original_state_path=str(backup_path),
                    target_path=str(target_path),
                    expiration_timestamp=expiration_dt,
                    rollback_instruction={"operation": "restore_from_backup", "backup_path": str(backup_path)}
                )
        
        elif operation == "create":
            # Store created path for removal
            return RollbackPlan(
                action_type="create",
                original_state_path=None,
                target_path=str(target_path),
                expiration_timestamp=expiration_dt,
                rollback_instruction={"operation": "delete_created", "target_path": str(target_path)}
            )
        
        return None
    
    def rollback(self, plan: RollbackPlan) -> RollbackResult:
        """Execute rollback operation.
        
        Args:
            plan: Rollback plan to execute
            
        Returns:
            RollbackResult with rollback evidence
        """
        # Check if plan expired
        if plan.is_expired():
            return RollbackResult(
                success=False,
                restored_state_hash=None,
                hash_match=False,
                time_to_rollback_ms=0,
                error="Rollback plan expired"
            )
        
        rollback_start = utc_now()
        
        try:
            instruction = plan.rollback_instruction
            operation = instruction.get("operation")
            
            if operation == "restore_from_trash":
                trash_path = Path(instruction["trash_path"])
                target_path = Path(plan.target_path)
                if trash_path.exists():
                    # Ensure parent directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(trash_path, target_path)
                else:
                    return RollbackResult(
                        success=False,
                        restored_state_hash=None,
                        hash_match=False,
                        time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                        error=f"Trash backup not found: {trash_path}"
                    )
            
            elif operation == "rename_back":
                original_path = Path(instruction["original_path"])
                new_path = Path(instruction["new_path"])
                if new_path.exists():
                    # Ensure parent directory exists
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(new_path, original_path)
                else:
                    return RollbackResult(
                        success=False,
                        restored_state_hash=None,
                        hash_match=False,
                        time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                        error=f"Renamed file not found: {new_path}"
                    )
            
            elif operation == "restore_from_backup":
                backup_path = Path(instruction["backup_path"])
                target_path = Path(plan.target_path)
                if backup_path.exists():
                    # Ensure parent directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, target_path)
                else:
                    return RollbackResult(
                        success=False,
                        restored_state_hash=None,
                        hash_match=False,
                        time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                        error=f"Backup not found: {backup_path}"
                    )
            
            elif operation == "delete_created":
                target_path = Path(plan.target_path)
                if target_path.exists():
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()
                else:
                    return RollbackResult(
                        success=False,
                        restored_state_hash=None,
                        hash_match=False,
                        time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                        error=f"Created file not found: {target_path}"
                    )
            
            # Verify restored state
            target_path = Path(plan.target_path)
            restored_hash = self.compute_state_hash(target_path) if target_path.exists() else None
            
            # Compute hash match if original state exists
            hash_match = False
            if plan.original_state_path:
                original_path = Path(plan.original_state_path)
                if original_path.exists():
                    original_hash = self.compute_state_hash(original_path)
                    hash_match = restored_hash == original_hash
            
            rollback_time_ms = int((utc_now() - rollback_start).total_seconds() * 1000)
            
            return RollbackResult(
                success=True,
                restored_state_hash=restored_hash,
                hash_match=hash_match,
                time_to_rollback_ms=rollback_time_ms
            )
            
        except FileNotFoundError as e:
            return RollbackResult(
                success=False,
                restored_state_hash=None,
                hash_match=False,
                time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                error=f"File not found during rollback: {e}"
            )
        
        except Exception as e:
            return RollbackResult(
                success=False,
                restored_state_hash=None,
                hash_match=False,
                time_to_rollback_ms=int((utc_now() - rollback_start).total_seconds() * 1000),
                error=str(e)
            )
    
    def verify_state(self, path: str, expected_hash: str) -> bool:
        """Verify file state matches expected hash.
        
        Args:
            path: File path to verify
            expected_hash: Expected SHA-256 hash
            
        Returns:
            True if state matches, False otherwise
        """
        actual_hash = self.compute_state_hash(Path(path))
        return actual_hash == expected_hash
    
    def classify_file_action(self, operation: str, payload: Dict[str, Any]) -> ActionClass:
        """Classify file operation by action class.
        
        Args:
            operation: File operation type
            payload: Operation payload
            
        Returns:
            ActionClass classification
        """
        if operation in ["read", "stat"]:
            return ActionClass.A0_OBSERVE
        
        elif operation in ["delete", "rename", "create"]:
            return ActionClass.A1_SOFT_CONTAINMENT
        
        elif operation in ["modify", "append"]:
            return ActionClass.A2_HARD_CONTAINMENT
        
        elif operation == "chmod" and payload.get("mode") == "000":
            return ActionClass.A3_IRREVERSIBLE
        
        elif operation == "overwrite" and payload.get("content") == "random":
            return ActionClass.A3_IRREVERSIBLE
        
        # Default to A2 for unknown operations
        return ActionClass.A2_HARD_CONTAINMENT
    
    def compute_state_hash(self, path: Path) -> Optional[str]:
        """Compute SHA-256 hash of file content + metadata.
        
        Args:
            path: File path to hash
            
        Returns:
            SHA-256 hash or None if file doesn't exist
        """
        if not path.exists():
            return None
        
        stat = path.stat()
        
        # Hash file content if it's a regular file
        if path.is_file():
            sha256 = hashlib.sha256()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            content_hash = sha256.hexdigest()
        else:
            content_hash = "directory"
        
        # Combine with metadata for state hash (exclude mtime for determinism)
        state_data = {
            "content_hash": content_hash,
            "size": stat.st_size,
            "mode": stat.st_mode
        }
        
        canonical = json.dumps(state_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def supports_capability(self, capability: str) -> bool:
        """Check if executor supports a specific capability."""
        return capability in self.capabilities()["capabilities"]
    
    # Private helper methods
    
    def _execute_create(self, target_path: Path, payload: Dict[str, Any]) -> None:
        """Execute file create operation."""
        content = payload.get("content", "")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content)
    
    def _execute_delete(self, target_path: Path, rollback_plan: Optional[RollbackPlan]) -> None:
        """Execute file delete operation."""
        if target_path.exists():
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
    
    def _execute_rename(self, target_path: Path, payload: Dict[str, Any], rollback_plan: Optional[RollbackPlan]) -> None:
        """Execute file rename operation."""
        new_path = Path(payload.get("new_path", ""))
        if target_path.exists():
            target_path.rename(new_path)
    
    def _execute_modify(self, target_path: Path, payload: Dict[str, Any], rollback_plan: Optional[RollbackPlan]) -> None:
        """Execute file modify operation."""
        if target_path.exists():
            if "content" in payload:
                target_path.write_text(payload["content"])
            elif "append" in payload:
                with open(target_path, 'a') as f:
                    f.write(payload["append"])
    
    def _execute_read(self, target_path: Path) -> Dict[str, Any]:
        """Execute file read operation."""
        if target_path.exists() and target_path.is_file():
            return {"content": target_path.read_text()}
        return {"error": "File not found or not a regular file"}
    
    def _execute_stat(self, target_path: Path) -> Dict[str, Any]:
        """Execute file stat operation."""
        if target_path.exists():
            stat = target_path.stat()
            return {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "mode": stat.st_mode,
                "is_file": target_path.is_file(),
                "is_dir": target_path.is_dir()
            }
        return {"error": "Path not found"}
    
    def _emit_audit_event(
        self,
        intent: ActionIntent,
        operation_type: str,
        target_path: str,
        action_class: ActionClass,
        pre_hash: Optional[str],
        post_hash: Optional[str],
        rollback_plan_id: Optional[str],
        outcome: str,
        error: Optional[str] = None
    ) -> None:
        """Emit audit event for file operation.
        
        Args:
            intent: Action intent
            operation_type: Operation type
            target_path: Target file path
            action_class: Action classification
            pre_hash: Pre-execution state hash
            post_hash: Post-execution state hash
            rollback_plan_id: Rollback plan ID
            outcome: Execution outcome
            error: Optional error message
        """
        # Build event details
        details = {
            "operation_type": operation_type,
            "target_path": target_path,
            "action_class": action_class.value,
            "pre_hash": pre_hash,
            "post_hash": post_hash,
            "rollback_plan_id": rollback_plan_id,
            "outcome": outcome
        }
        
        if error:
            details["error"] = error
        
        # Compute outcome hash
        canonical = json.dumps(details, sort_keys=True, separators=(",", ":"))
        outcome_hash = hashlib.sha256(canonical.encode()).hexdigest()
        details["outcome_hash"] = outcome_hash
        
        # In production, this would emit to the audit emitter
        # For now, we'll log it (audit emission will be integrated through ProxyPipeline)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"FileSystemExecutor audit event: {outcome} - {operation_type} on {target_path}")
    
    def _generate_execution_id(self, intent: ActionIntent) -> str:
        """Generate execution ID."""
        seed = f"{intent.intent_id}:{utc_now().isoformat()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]
    
    def _generate_validation_id(self, intent: ActionIntent) -> str:
        """Generate validation ID."""
        seed = f"validation:{intent.intent_id}:{intent.target}"
        return hashlib.sha256(seed.encode()).hexdigest()[:32]
