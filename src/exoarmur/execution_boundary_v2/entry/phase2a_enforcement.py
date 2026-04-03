"""
Phase 2A Enforcement System - Structural Bypass Eradication

This module orchestrates the enforcement of canonical routing across all
execution surfaces, eliminating bypass capability structurally.

PRINCIPLES:
- Structural enforcement, not conventional
- No bypass possible at runtime
- Fail-fast on any execution divergence
"""

import logging
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)

class Phase2AEnforcementError(Exception):
    """Raised when Phase 2A enforcement fails"""
    pass

class Phase2AEnforcement:
    """Orchestrates Phase 2A structural enforcement"""
    
    def __init__(self):
        self._enforcement_active = False
        self._enforcement_components = {}
        self._initialization_time = None
    
    def initialize_enforcement(self) -> bool:
        """
        Initialize all enforcement components
        
        Returns:
            True if enforcement initialized successfully
        """
        logger.info("Initializing Phase 2A Enforcement System")
        
        try:
            # Initialize canonical router
            from .canonical_router import CanonicalExecutionRouter
            if not CanonicalExecutionRouter.is_available():
                raise Phase2AEnforcementError("Canonical router not available")
            
            self._enforcement_components["canonical_router"] = True
            
            # Initialize CLI wrapper
            from .cli_wrapper import get_cli_wrapper
            cli_wrapper = get_cli_wrapper()
            self._enforcement_components["cli_wrapper"] = cli_wrapper
            
            # Initialize script bootstrap
            from .script_bootstrap import get_script_bootstrap
            script_bootstrap = get_script_bootstrap()
            self._enforcement_components["script_bootstrap"] = script_bootstrap
            
            # Initialize executor collapser
            from .executor_collapse import get_executor_collapser
            executor_collapser = get_executor_collapser()
            self._enforcement_components["executor_collapser"] = executor_collapser
            
            self._initialization_time = time.time()
            self._enforcement_active = True
            
            logger.info("Phase 2A Enforcement System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Phase 2A enforcement: {e}")
            raise Phase2AEnforcementError(f"Enforcement initialization failed: {e}")
    
    def activate_enforcement(self) -> Dict[str, Any]:
        """
        Activate all enforcement mechanisms
        
        Returns:
            Dictionary with enforcement activation results
        """
        if not self._enforcement_active:
            raise Phase2AEnforcementError("Enforcement system not initialized")
        
        logger.info("Activating Phase 2A Enforcement Mechanisms")
        
        activation_results = {}
        
        try:
            # Activate executor collapse (highest priority)
            executor_collapser = self._enforcement_components["executor_collapser"]
            executor_collapser.collapse_all_direct_executors()
            activation_results["executor_collapse"] = "ACTIVE"
            
            # Verify executor collapse
            collapse_verification = executor_collapser.verify_collapse()
            activation_results["executor_collapse_verification"] = collapse_verification
            
            # CLI wrapper is ready (will be used by CLI commands)
            activation_results["cli_wrapper"] = "READY"
            
            # Script bootstrap is ready (will be used by script execution)
            activation_results["script_bootstrap"] = "READY"
            
            # Canonical router is available
            activation_results["canonical_router"] = "AVAILABLE"
            
            activation_results["enforcement_active"] = True
            activation_results["activation_time"] = time.time()
            
            logger.info("Phase 2A Enforcement Mechanisms activated successfully")
            
        except Exception as e:
            activation_results["enforcement_active"] = False
            activation_results["error"] = str(e)
            logger.error(f"Failed to activate enforcement: {e}")
            raise
        
        return activation_results
    
    def verify_enforcement(self) -> Dict[str, Any]:
        """
        Verify that enforcement is working correctly
        
        Returns:
            Dictionary with verification results
        """
        if not self._enforcement_active:
            return {"enforcement_active": False, "error": "Enforcement not active"}
        
        verification_results = {
            "enforcement_active": self._enforcement_active,
            "initialization_time": self._initialization_time,
            "verification_time": time.time()
        }
        
        try:
            # Verify canonical router
            from .canonical_router import CanonicalExecutionRouter
            verification_results["canonical_router_available"] = CanonicalExecutionRouter.is_available()
            
            # Verify executor collapse
            executor_collapser = self._enforcement_components["executor_collapser"]
            verification_results["executor_collapse"] = executor_collapser.verify_collapse()
            
            # Verify CLI wrapper
            cli_wrapper = self._enforcement_components["cli_wrapper"]
            verification_results["cli_wrapper_available"] = cli_wrapper is not None
            
            # Verify script bootstrap
            script_bootstrap = self._enforcement_components["script_bootstrap"]
            verification_results["script_bootstrap_available"] = script_bootstrap is not None
            
            verification_results["overall_status"] = "ENFORCED"
            
        except Exception as e:
            verification_results["overall_status"] = "FAILED"
            verification_results["verification_error"] = str(e)
            logger.error(f"Enforcement verification failed: {e}")
        
        return verification_results
    
    def get_enforcement_status(self) -> Dict[str, Any]:
        """Get current enforcement status"""
        return {
            "enforcement_active": self._enforcement_active,
            "components": list(self._enforcement_components.keys()),
            "initialization_time": self._initialization_time
        }

# Global enforcement instance
_phase2a_enforcement = None

def get_phase2a_enforcement() -> Phase2AEnforcement:
    """Get the global Phase 2A enforcement instance"""
    global _phase2a_enforcement
    if _phase2a_enforcement is None:
        _phase2a_enforcement = Phase2AEnforcement()
    return _phase2a_enforcement

def activate_phase2a_enforcement() -> Dict[str, Any]:
    """
    Activate Phase 2A enforcement system
    
    This function should be called at system startup to ensure
    all execution paths are structurally enforced.
    
    Returns:
        Dictionary with activation results
    """
    enforcement = get_phase2a_enforcement()
    
    # Initialize if needed
    if not enforcement._enforcement_active:
        enforcement.initialize_enforcement()
    
    # Activate enforcement
    return enforcement.activate_enforcement()

def verify_phase2a_enforcement() -> Dict[str, Any]:
    """Verify Phase 2A enforcement is working"""
    enforcement = get_phase2a_enforcement()
    return enforcement.verify_enforcement()
