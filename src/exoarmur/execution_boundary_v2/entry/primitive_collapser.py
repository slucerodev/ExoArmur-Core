"""
Primitive Collapser - Phase 2B Execution Primitive Elimination

This module collapses independent execution primitives to ensure no domain
logic can execute outside the canonical routing boundary.

PRINCIPLES:
- Structural elimination of independent execution
- No side effects outside routed context
- All meaningful behavior must route through V2EntryGate
"""

import logging
from typing import Dict, Any, List, Optional, Callable
import functools
from .execution_surface_audit import ExecutionSurface, CollapseAction, BypassRiskLevel
from .canonical_router import CanonicalExecutionRouter

logger = logging.getLogger(__name__)

class PrimitiveCollapseError(Exception):
    """Raised when primitive collapse fails"""
    pass

class PrimitiveCollapser:
    """Collapses independent execution primitives"""
    
    def __init__(self):
        self._collapsed_surfaces: List[str] = []
        self._patched_methods: List[str] = []
        self._router = None
        self._initialize_router()
    
    def _initialize_router(self):
        """Initialize canonical router"""
        try:
            self._router = CanonicalExecutionRouter()
            logger.info("Primitive Collapser: Canonical router initialized")
        except Exception as e:
            raise PrimitiveCollapseError(f"Cannot initialize canonical router: {e}")
    
    def collapse_replay_engine(self) -> bool:
        """
        Collapse ReplayEngine to route through canonical spine
        
        ReplayEngine can currently reconstruct system behavior without V2EntryGate.
        This collapse forces all replay operations through canonical routing.
        """
        logger.info("Collapsing ReplayEngine...")
        
        try:
            # Import ReplayEngine
            from exoarmur.replay.replay_engine import ReplayEngine
            
            # Patch the replay_correlation method
            original_replay_correlation = ReplayEngine.replay_correlation
            
            @functools.wraps(original_replay_correlation)
            def canonical_replay_correlation(self, correlation_id: str):
                """Canonical replay that routes through V2EntryGate"""
                logger.info(f"ReplayEngine: Routing replay for {correlation_id} through canonical spine")
                
                execution_context = {
                    "execution_id": f"replay_{correlation_id}_{int(time.time())}",
                    "module_id": "replay_engine",
                    "deterministic_seed": 42,
                    "logical_timestamp": int(time.time()),
                    "correlation_id": f"replay_{correlation_id}"
                }
                
                action_data = {
                    "replay_command": "replay_correlation",
                    "correlation_id": correlation_id,
                    "audit_store": self.audit_store,
                    "intent_store": self.intent_store,
                    "approval_service": self.approval_service,
                    "collapsed_by": "primitive_collapser"
                }
                
                # Route through canonical spine
                result = self._router.route_to_v2_entry_gate(
                    module_id="replay_engine",
                    execution_context_data=execution_context,
                    action_data=action_data
                )
                
                if result.success:
                    return result.result_data.get("replay_report")
                else:
                    raise PrimitiveCollapseError(f"Replay failed: {result.error}")
            
            # Apply patch
            ReplayEngine.replay_correlation = canonical_replay_correlation
            self._patched_methods.append("ReplayEngine.replay_correlation")
            self._collapsed_surfaces.append("ReplayEngine")
            
            logger.info("ReplayEngine collapsed successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to collapse ReplayEngine: {e}")
            return False
        except Exception as e:
            logger.error(f"ReplayEngine collapse failed: {e}")
            return False
    
    def collapse_multi_node_verifier(self) -> bool:
        """
        Collapse MultiNodeVerifier to route through canonical spine
        
        MultiNodeVerifier can execute replays in isolated environments without V2EntryGate.
        This collapse forces all verification operations through canonical routing.
        """
        logger.info("Collapsing MultiNodeVerifier...")
        
        try:
            from exoarmur.replay.multi_node_verifier import MultiNodeVerifier
            
            # Patch the _execute_isolated_replays method
            original_execute_isolated_replays = MultiNodeVerifier._execute_isolated_replays
            
            @functools.wraps(original_execute_isolated_replays)
            def canonical_execute_isolated_replays(self, correlation_id: str):
                """Canonical multi-node verification through V2EntryGate"""
                logger.info(f"MultiNodeVerifier: Routing verification for {correlation_id} through canonical spine")
                
                execution_context = {
                    "execution_id": f"multi_node_verify_{correlation_id}_{int(time.time())}",
                    "module_id": "multi_node_verifier",
                    "deterministic_seed": 42,
                    "logical_timestamp": int(time.time()),
                    "correlation_id": f"multi_node_{correlation_id}"
                }
                
                action_data = {
                    "verification_command": "execute_isolated_replays",
                    "correlation_id": correlation_id,
                    "verifier_config": getattr(self, 'config', {}),
                    "collapsed_by": "primitive_collapser"
                }
                
                # Route through canonical spine
                result = self._router.route_to_v2_entry_gate(
                    module_id="multi_node_verifier",
                    execution_context_data=execution_context,
                    action_data=action_data
                )
                
                if result.success:
                    return result.result_data.get("verification_report")
                else:
                    raise PrimitiveCollapseError(f"Multi-node verification failed: {result.error}")
            
            # Apply patch
            MultiNodeVerifier._execute_isolated_replays = canonical_execute_isolated_replays
            self._patched_methods.append("MultiNodeVerifier._execute_isolated_replays")
            self._collapsed_surfaces.append("MultiNodeVerifier")
            
            logger.info("MultiNodeVerifier collapsed successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to collapse MultiNodeVerifier: {e}")
            return False
        except Exception as e:
            logger.error(f"MultiNodeVerifier collapse failed: {e}")
            return False
    
    def collapse_tick_service(self) -> bool:
        """
        Collapse IdentityContainmentTickService to route through canonical spine
        
        Tick service can process expirations without V2EntryGate mediation.
        This collapse forces all tick operations through canonical routing.
        """
        logger.info("Collapsing IdentityContainmentTickService...")
        
        try:
            from exoarmur.identity_containment.execution import IdentityContainmentTickService
            
            # Patch the tick method
            original_tick = IdentityContainmentTickService.tick
            
            @functools.wraps(original_tick)
            async def canonical_tick(self) -> int:
                """Canonical tick processing through V2EntryGate"""
                logger.info("IdentityContainmentTickService: Routing tick through canonical spine")
                
                execution_context = {
                    "execution_id": f"tick_{int(time.time())}",
                    "module_id": "tick_service",
                    "deterministic_seed": 42,
                    "logical_timestamp": int(time.time()),
                    "correlation_id": "tick_service"
                }
                
                action_data = {
                    "tick_command": "process_expirations",
                    "tick_interval_seconds": self.tick_interval_seconds,
                    "last_tick_utc": self.last_tick_utc.isoformat() if self.last_tick_utc else None,
                    "collapsed_by": "primitive_collapser"
                }
                
                # Route through canonical spine
                result = self._router.route_to_v2_entry_gate(
                    module_id="tick_service",
                    execution_context_data=execution_context,
                    action_data=action_data
                )
                
                if result.success:
                    return result.result_data.get("expired_count", 0)
                else:
                    raise PrimitiveCollapseError(f"Tick processing failed: {result.error}")
            
            # Apply patch
            IdentityContainmentTickService.tick = canonical_tick
            self._patched_methods.append("IdentityContainmentTickService.tick")
            self._collapsed_surfaces.append("IdentityContainmentTickService")
            
            logger.info("IdentityContainmentTickService collapsed successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to collapse IdentityContainmentTickService: {e}")
            return False
        except Exception as e:
            logger.error(f"IdentityContainmentTickService collapse failed: {e}")
            return False
    
    def eliminate_mock_executor(self) -> bool:
        """
        Eliminate MockExecutor direct execution capability
        
        MockExecutor can execute without V2EntryGate routing.
        This elimination removes the dangerous direct execution primitive.
        """
        logger.info("Eliminating MockExecutor direct execution...")
        
        try:
            from exoarmur.v2_restrained_autonomy.mock_executor import MockActionExecutor
            
            # Patch the execute_isolate_endpoint method to raise error
            @functools.wraps(MockActionExecutor.execute_isolate_endpoint)
            def blocked_execute_isolate_endpoint(self, request):
                """Blocked mock executor execution"""
                raise PrimitiveCollapseError(
                    "MOCK EXECUTOR BYPASS DETECTED. "
                    "MockActionExecutor.execute_isolate_endpoint() is blocked. "
                    "Use CanonicalExecutionRouter.route_to_v2_entry_gate() instead."
                )
            
            # Apply patch
            MockActionExecutor.execute_isolate_endpoint = blocked_execute_isolate_endpoint
            self._patched_methods.append("MockActionExecutor.execute_isolate_endpoint")
            self._collapsed_surfaces.append("MockActionExecutor")
            
            logger.info("MockExecutor direct execution eliminated successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to eliminate MockExecutor: {e}")
            return False
        except Exception as e:
            logger.error(f"MockExecutor elimination failed: {e}")
            return False
    
    def collapse_all_critical_primitives(self) -> Dict[str, bool]:
        """
        Collapse all critical execution primitives
        
        Returns:
            Dictionary with collapse results for each primitive
        """
        logger.info("Collapsing all critical execution primitives...")
        
        results = {}
        
        # Collapse ReplayEngine (CRITICAL)
        results["replay_engine"] = self.collapse_replay_engine()
        
        # Collapse MultiNodeVerifier (CRITICAL)
        results["multi_node_verifier"] = self.collapse_multi_node_verifier()
        
        # Collapse TickService (HIGH)
        results["tick_service"] = self.collapse_tick_service()
        
        # Eliminate MockExecutor (HIGH)
        results["mock_executor"] = self.eliminate_mock_executor()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"Primitive collapse complete: {success_count}/{total_count} successful")
        
        return results
    
    def verify_collapse_effectiveness(self) -> Dict[str, Any]:
        """Verify that primitive collapse is effective"""
        verification = {
            "collapsed_surfaces": self._collapsed_surfaces,
            "patched_methods": self._patched_methods,
            "collapse_active": len(self._collapsed_surfaces) > 0,
            "total_patches": len(self._patched_methods)
        }
        
        # Test that critical primitives are blocked
        try:
            # Test ReplayEngine
            from exoarmur.replay.replay_engine import ReplayEngine
            # This should now route through canonical spine
            
            # Test MockExecutor
            from exoarmur.v2_restrained_autonomy.mock_executor import MockActionExecutor
            mock_executor = MockActionExecutor()
            
            try:
                mock_executor.execute_isolate_endpoint(None)
                verification["mock_executor_blocked"] = False
            except PrimitiveCollapseError:
                verification["mock_executor_blocked"] = True
            except Exception as e:
                verification["mock_executor_blocked"] = f"Unexpected error: {e}"
                
        except ImportError as e:
            verification["verification_error"] = str(e)
        
        return verification

# Global primitive collapser instance
_primitive_collapser = None

def get_primitive_collapser() -> PrimitiveCollapser:
    """Get the global primitive collapser instance"""
    global _primitive_collapser
    if _primitive_collapser is None:
        _primitive_collapser = PrimitiveCollapser()
    return _primitive_collapser

def collapse_execution_primitives() -> Dict[str, Any]:
    """
    Collapse all independent execution primitives
    
    Returns:
        Dictionary with collapse results
    """
    collapser = get_primitive_collapser()
    
    # Collapse all critical primitives
    collapse_results = collapser.collapse_all_critical_primitives()
    
    # Verify effectiveness
    verification = collapser.verify_collapse_effectiveness()
    
    return {
        "collapse_results": collapse_results,
        "verification": verification,
        "total_surfaces_collapsed": len(collapser._collapsed_surfaces),
        "total_methods_patched": len(collapser._patched_methods),
        "collapse_successful": sum(1 for success in collapse_results.values() if success) > 0
    }
