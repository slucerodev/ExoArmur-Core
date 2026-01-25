"""
Mock Action Executor for V2 Restrained Autonomy
Safe, non-destructive action execution for testing and demos
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


class MockActionExecutor:
    """Mock action executor for safe, non-destructive actions"""
    
    def __init__(self):
        self._executed_actions: Dict[str, Dict[str, Any]] = {}
    
    def execute_isolate_endpoint(
        self,
        endpoint_id: str,
        correlation_id: str,
        approval_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Mock isolation of an endpoint (safe implementation)"""
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        
        execution_record = {
            "execution_id": execution_id,
            "action_type": "isolate_endpoint",
            "endpoint_id": endpoint_id,
            "correlation_id": correlation_id,
            "approval_id": approval_id,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "mock": True
        }
        
        self._executed_actions[execution_id] = execution_record
        logger.info(f"Mock executed isolate_endpoint for {endpoint_id} (execution_id: {execution_id})")
        
        return execution_record
    
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
