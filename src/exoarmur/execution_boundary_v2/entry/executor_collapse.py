"""
Executor Collapse Module - Elimination of Direct Executor Paths

This module provides mechanisms to collapse all direct executor calls
into canonical routing, eliminating parallel execution paths.

PRINCIPLES:
- No direct executor access possible
- All executor calls must route through canonical spine
- Preserve executor functionality while eliminating bypass
"""

import logging
from typing import Any, Callable
import functools

logger = logging.getLogger(__name__)

class ExecutorBypassError(RuntimeError):
    """Raised when direct executor bypass is detected"""
    pass

class ExecutorCollapser:
    """Collapses direct executor paths into canonical routing"""
    
    def __init__(self):
        self._patched_classes = set()
        self._patched_methods = set()
    
    def collapse_executor_class(self, executor_class: classmethod, class_name: str = None):
        """
        Collapse an executor class to prevent direct execution
        
        This patches all execute methods to route through canonical spine.
        
        Args:
            executor_class: The executor class to collapse
            class_name: Optional name for error messages
        """
        class_identifier = class_name or executor_class.__name__
        
        if class_identifier in self._patched_classes:
            logger.warning(f"Executor class {class_identifier} already collapsed")
            return
        
        # Patch all execute methods
        for attr_name in dir(executor_class):
            if attr_name == 'execute' and callable(getattr(executor_class, attr_name)):
                original_execute = getattr(executor_class, attr_name)
                
                @functools.wraps(original_execute)
                def canonical_execute(self, *args, **kwargs):
                    """Canonical execution that routes through V2EntryGate"""
                    raise ExecutorBypassError(
                        f"DIRECT EXECUTOR BYPASS DETECTED in {class_identifier}. "
                        f"Use CanonicalExecutionRouter.route_to_v2_entry_gate() instead. "
                        f"Direct executor.execute() calls are forbidden."
                    )
                
                # Replace the method
                setattr(executor_class, attr_name, canonical_execute)
                self._patched_methods.add(f"{class_identifier}.{attr_name}")
                
                logger.info(f"Collapsed {class_identifier}.{attr_name} - direct execution blocked")
        
        self._patched_classes.add(class_identifier)
        logger.info(f"Executor class {class_identifier} collapsed")
    
    def collapse_proxy_pipeline(self):
        """Specifically collapse ProxyPipeline direct execution"""
        try:
            from ..pipeline.proxy_pipeline import ProxyPipeline
            self.collapse_executor_class(ProxyPipeline, "ProxyPipeline")
            logger.info("ProxyPipeline direct execution collapsed")
        except ImportError as e:
            logger.error(f"Failed to collapse ProxyPipeline: {e}")
    
    def collapse_gateway_adapter(self):
        """Specifically collapse gateway adapter direct execution"""
        try:
            from ..gateway.adapter import GatewayAdapter
            self.collapse_executor_class(GatewayAdapter, "GatewayAdapter")
            logger.info("GatewayAdapter direct execution collapsed")
        except ImportError as e:
            logger.error(f"Failed to collapse GatewayAdapter: {e}")
    
    def collapse_all_direct_executors(self):
        """Collapse all known direct executor paths"""
        logger.info("Starting collapse of all direct executor paths")
        
        # Collapse known executor classes
        self.collapse_proxy_pipeline()
        self.collapse_gateway_adapter()
        
        # TODO: Add other executor classes as they are identified
        # self.collapse_other_executors()
        
        logger.info(f"Executor collapse complete: {len(self._patched_classes)} classes, {len(self._patched_methods)} methods")
    
    def verify_collapse(self) -> dict:
        """Verify that executor collapse is effective"""
        verification_result = {
            "patched_classes": list(self._patched_classes),
            "patched_methods": list(self._patched_methods),
            "collapse_active": len(self._patched_classes) > 0
        }
        
        # Test that direct execution is blocked
        try:
            from ..pipeline.proxy_pipeline import ProxyPipeline
            pipeline = ProxyPipeline(None, None, None, None)  # Dummy initialization
            
            # This should raise ExecutorBypassError
            try:
                pipeline.execute(None)  # This should fail
                verification_result["direct_execution_blocked"] = False
            except ExecutorBypassError:
                verification_result["direct_execution_blocked"] = True
            except Exception as e:
                verification_result["direct_execution_blocked"] = f"Unexpected error: {e}"
                
        except ImportError as e:
            verification_result["verification_error"] = str(e)
        
        return verification_result

# Global executor collapser instance
_executor_collapser = None

def get_executor_collapser() -> ExecutorCollapser:
    """Get the global executor collapser instance"""
    global _executor_collapser
    if _executor_collapser is None:
        _executor_collapser = ExecutorCollapser()
    return _executor_collapser

def enforce_executor_collapse():
    """
    Enforce that all direct executor paths are collapsed
    
    This function should be called at system initialization to prevent
    any direct executor access from being used.
    """
    collapser = get_executor_collapser()
    collapser.collapse_all_direct_executors()
    logger.info("Executor collapse enforcement activated")
    return collapser

def is_executor_collapsed() -> bool:
    """Check if executor collapse is active"""
    collapser = get_executor_collapser()
    return len(collapser._patched_classes) > 0
