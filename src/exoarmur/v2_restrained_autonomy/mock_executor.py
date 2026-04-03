"""
Mock Action Executor for V2 Restrained Autonomy - V2 GOVERNED ONLY
Safe, non-destructive action execution for testing and demos
ALL execution must pass through V2 Entry Gate - NO direct execution allowed
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from exoarmur.execution_boundary_v2.entry.v2_entry_gate import execute_module, ExecutionRequest

logger = logging.getLogger(__name__)


class MockActionExecutor:
    """Mock action executor for safe, non-destructive actions - V2 GOVERNED ONLY"""
    
    def __init__(self):
        self._executed_actions: Dict[str, Dict[str, Any]] = {}
    
    def execute_isolate_endpoint(
        self,
        endpoint_id: str,
        correlation_id: str,
        approval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute endpoint isolation through V2 Entry Gate - ONLY ALLOWED PATH
        NO direct execution allowed outside V2 governance
        """
        try:
            # Create V2 ExecutionRequest for mock isolation
            from exoarmur.execution_boundary_v2.core.core_types import ModuleID, ExecutionID, DeterministicSeed, ModuleExecutionContext
            
            execution_request = ExecutionRequest(
                module_id=ModuleID("mock_isolate_endpoint"),
                execution_context=ModuleExecutionContext(
                    execution_id=ExecutionID(str(uuid.uuid4())[:26]),
                    module_id=ModuleID("mock_isolate_endpoint"),
                    module_version=ModuleVersion(1, 0, 0),
                    deterministic_seed=DeterministicSeed(hash(endpoint_id + correlation_id) % (2**63)),
                    logical_timestamp=int(datetime.now(timezone.utc).timestamp()),
                    dependency_hash="mock_execution"
                ),
                action_data={
                    'action_class': 'mock_containment',
                    'action_type': 'isolate_endpoint',
                    'subject': endpoint_id,
                    'parameters': {
                        'endpoint_id': endpoint_id,
                        'correlation_id': correlation_id,
                        'approval_id': approval_id
                    }
                },
                correlation_id=correlation_id
            )

            # Execute through V2 Entry Gate - ONLY ALLOWED PATH
            result = execute_module(execution_request)
            
            if not result.success:
                logger.error(f"V2 Entry Gate blocked mock isolation: {result.error}")
                return {
                    "success": False,
                    "error": result.error,
                    "v2_enforced": True
                }
            
            # Create mock execution record (only after V2 validation)
            execution_record = {
                "execution_id": result.execution_id,
                "action_type": "isolate_endpoint",
                "endpoint_id": endpoint_id,
                "correlation_id": correlation_id,
                "approval_id": approval_id,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "mock": True,
                "v2_enforced": True,
                "v2_audit_trail": result.audit_trail_id
            }
            
            self._executed_actions[result.execution_id] = execution_record
            logger.info(f"Mock executed isolate_endpoint for {endpoint_id} via V2 Entry Gate (execution_id: {result.execution_id})")
            
            return execution_record
            
        except Exception as e:
            logger.error(f"Failed to execute mock isolation through V2 Entry Gate: {e}")
            return {
                "success": False,
                "error": str(e),
                "v2_enforced": True
            }
    
    def get_execution_record(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution record by ID"""
        return self._executed_actions.get(execution_id)
    
    def has_executed_recently(self, endpoint_id: str, correlation_id: str, time_window_seconds: int = 300) -> bool:
        """Check if same action was executed recently for idempotency"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - time_window_seconds
        
        for record in self._executed_actions.values():
            if (record.get("endpoint_id") == endpoint_id and 
                record.get("correlation_id") == correlation_id):
                exec_time = datetime.fromisoformat(record["executed_at"].replace('Z', '+00:00')).timestamp()
                if exec_time > cutoff_time:
                    return True
        
        return False
