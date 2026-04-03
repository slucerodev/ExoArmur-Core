"""
Canonical Execution Router - Thin routing layer for V2EntryGate convergence

This is a stateless routing layer that ensures ALL execution paths converge
through V2EntryGate without duplicating governance logic.

PRINCIPLES:
- Stateless routing only
- No validation logic duplication
- Always delegates to V2EntryGate
- Deterministic behavior
"""

from typing import Dict, Any
from .v2_entry_gate import execute_module, ExecutionRequest, ExecutionResult
from ..core.core_types import ModuleID, ExecutionID, DeterministicSeed, ModuleExecutionContext, ModuleVersion
import time
import logging

logger = logging.getLogger(__name__)

class CanonicalExecutionRouter:
    """
    Thin routing layer - NO VALIDATION LOGIC
    
    ONLY routes to V2EntryGate
    NO governance logic duplication
    STATELESS operation
    """
    
    @staticmethod
    def route_to_v2_entry_gate(
        module_id: str,
        execution_context_data: Dict[str, Any],
        action_data: Dict[str, Any]
    ) -> ExecutionResult:
        """
        SINGLE ROUTING POINT - NO VALIDATION
        
        ONLY routes to V2EntryGate
        NO governance logic duplication
        STATELESS operation
        
        Args:
            module_id: Module identifier for execution
            execution_context_data: Context data for execution
            action_data: Action payload data
            
        Returns:
            ExecutionResult from V2EntryGate
        """
        logger.info(f"Canonical router: Routing {module_id} to V2EntryGate")
        
        # Create standardized execution request
        request = ExecutionRequest(
            module_id=ModuleID(module_id),
            execution_context=ModuleExecutionContext(
                execution_id=ExecutionID(execution_context_data.get('execution_id', f"exec_{int(time.time())}")),
                module_id=ModuleID(module_id),
                module_version=ModuleVersion(1, 0, 0),
                deterministic_seed=DeterministicSeed(execution_context_data.get('deterministic_seed', 42)),
                logical_timestamp=execution_context_data.get('logical_timestamp', int(time.time())),
                dependency_hash=execution_context_data.get('dependency_hash', 'canonical_router')
            ),
            action_data=action_data,
            correlation_id=execution_context_data.get('correlation_id', '')
        )
        
        # Route to V2EntryGate - ONLY VALID PATH
        result = execute_module(request)
        
        logger.info(f"Canonical router: V2EntryGate result - success: {result.success}")
        return result
    
    @staticmethod
    def is_available() -> bool:
        """Check if V2EntryGate is available for routing"""
        try:
            from .v2_entry_gate import get_v2_entry_gate
            gate = get_v2_entry_gate()
            return gate is not None
        except ImportError:
            logger.error("V2EntryGate not available for canonical routing")
            return False
        except Exception as e:
            logger.error(f"Error checking V2EntryGate availability: {e}")
            return False

# Global router instance for convenience
_canonical_router = None

def get_canonical_router() -> CanonicalExecutionRouter:
    """Get the canonical router instance"""
    global _canonical_router
    if _canonical_router is None:
        _canonical_router = CanonicalExecutionRouter()
    return _canonical_router
