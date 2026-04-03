"""
Phase 2B Completion - Execution Surface Audit + Primitive Collapse

This module orchestrates the complete Phase 2B process:
1. Audit all execution surfaces
2. Analyze bypass capability
3. Collapse independent execution primitives
4. Verify single-spine reality

PRINCIPLES:
- No domain logic can execute outside canonical routing
- Structural elimination of independent execution primitives
- Complete bypass capability eradication
"""

import logging
from typing import Dict, Any, List
import time

logger = logging.getLogger(__name__)

class Phase2BCompletionError(Exception):
    """Raised when Phase 2B completion fails"""
    pass

class Phase2BCompletion:
    """Orchestrates Phase 2B execution surface audit and primitive collapse"""
    
    def __init__(self):
        self._auditor = None
        self._collapser = None
        self._completion_time = None
        self._audit_results = None
        self._collapse_results = None
        self._final_assessment = None
    
    def initialize_components(self) -> bool:
        """Initialize Phase 2B components"""
        logger.info("Initializing Phase 2B components...")
        
        try:
            # Initialize auditor
            from .execution_surface_audit import get_execution_surface_auditor
            self._auditor = get_execution_surface_auditor()
            
            # Initialize collapser
            from .primitive_collapser import get_primitive_collapser
            self._collapser = get_primitive_collapser()
            
            logger.info("Phase 2B components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Phase 2B components: {e}")
            raise Phase2BCompletionError(f"Component initialization failed: {e}")
    
    def execute_phase2b_audit(self) -> Dict[str, Any]:
        """Execute complete Phase 2B audit"""
        if not self._auditor:
            raise Phase2BCompletionError("Auditor not initialized")
        
        logger.info("Executing Phase 2B execution surface audit...")
        
        # Perform complete audit
        audit_results = audit_execution_surfaces()
        
        self._audit_results = audit_results
        
        logger.info(f"Phase 2B audit complete: {audit_results['total_surfaces']} surfaces, {audit_results['bypass_surfaces']} bypass surfaces")
        
        return audit_results
    
    def execute_primitive_collapse(self) -> Dict[str, Any]:
        """Execute primitive collapse"""
        if not self._collapser:
            raise Phase2BCompletionError("Collapser not initialized")
        
        logger.info("Executing Phase 2B primitive collapse...")
        
        # Collapse all independent execution primitives
        collapse_results = collapse_execution_primitives()
        
        self._collapse_results = collapse_results
        
        logger.info(f"Phase 2B collapse complete: {collapse_results['total_surfaces_collapsed']} surfaces collapsed")
        
        return collapse_results
    
    def assess_single_spine_achievement(self) -> Dict[str, Any]:
        """Assess whether single-spine execution is achieved"""
        logger.info("Assessing single-spine achievement...")
        
        if not self._audit_results or not self._collapse_results:
            raise Phase2BCompletionError("Audit and collapse must be completed first")
        
        # Get single-spine assessment from audit
        single_spine_assessment = self._audit_results.get("single_spine_assessment", {})
        
        # Add collapse results to assessment
        assessment = {
            "phase2b_completion_time": self._completion_time,
            "audit_results": self._audit_results,
            "collapse_results": self._collapse_results,
            "single_spine_before_collapse": not single_spine_assessment.get("single_spine_achieved", False),
            "critical_bypasses_before": single_spine_assessment.get("critical_bypasses", 0),
            "surfaces_collapsed": self._collapse_results.get("total_surfaces_collapsed", 0),
            "methods_patched": self._collapse_results.get("total_methods_patched", 0),
            "collapse_successful": self._collapse_results.get("collapse_successful", False)
        }
        
        # Determine final single-spine status
        critical_bypasses_remaining = single_spine_assessment.get("critical_bypasses", 0)
        collapse_successful = self._collapse_results.get("collapse_successful", False)
        
        assessment["single_spine_achieved"] = (
            critical_bypasses_remaining == 0 and collapse_successful
        )
        
        assessment["can_domain_logic_execute_without_v2"] = (
            critical_bypasses_remaining > 0 or not collapse_successful
        )
        
        assessment["bypass_paths_remain"] = (
            self._audit_results.get("bypass_surfaces", 0) > self._collapse_results.get("total_surfaces_collapsed", 0)
        )
        
        self._final_assessment = assessment
        
        logger.info(f"Single-spine assessment: {assessment['single_spine_achieved']}")
        
        return assessment
    
    def execute_complete_phase2b(self) -> Dict[str, Any]:
        """Execute complete Phase 2B process"""
        logger.info("Starting complete Phase 2B execution...")
        
        try:
            # Initialize components
            if not self.initialize_components():
                raise Phase2BCompletionError("Component initialization failed")
            
            # Execute audit
            audit_results = self.execute_phase2b_audit()
            
            # Execute primitive collapse
            collapse_results = self.execute_primitive_collapse()
            
            # Assess single-spine achievement
            final_assessment = self.assess_single_spine_achievement()
            
            self._completion_time = time.time()
            
            # Prepare final results
            phase2b_results = {
                "phase2b_completed": True,
                "completion_time": self._completion_time,
                "audit_results": audit_results,
                "collapse_results": collapse_results,
                "final_assessment": final_assessment,
                "success": final_assessment["single_spine_achieved"],
                "summary": {
                    "total_surfaces_discovered": audit_results["total_surfaces"],
                    "bypass_surfaces_found": audit_results["bypass_surfaces"],
                    "critical_bypasses_eliminated": audit_results["single_spine_assessment"]["critical_bypasses"],
                    "surfaces_collapsed": collapse_results["total_surfaces_collapsed"],
                    "methods_patched": collapse_results["total_methods_patched"],
                    "single_spine_achieved": final_assessment["single_spine_achieved"]
                }
            }
            
            logger.info(f"Phase 2B completed successfully: {phase2b_results['success']}")
            
            return phase2b_results
            
        except Exception as e:
            logger.error(f"Phase 2B execution failed: {e}")
            raise Phase2BCompletionError(f"Phase 2B execution failed: {e}")
    
    def get_phase2b_status(self) -> Dict[str, Any]:
        """Get current Phase 2B status"""
        return {
            "components_initialized": self._auditor is not None and self._collapser is not None,
            "audit_completed": self._audit_results is not None,
            "collapse_completed": self._collapse_results is not None,
            "assessment_completed": self._final_assessment is not None,
            "completion_time": self._completion_time
        }

# Global Phase 2B completion instance
_phase2b_completion = None

def get_phase2b_completion() -> Phase2BCompletion:
    """Get the global Phase 2B completion instance"""
    global _phase2b_completion
    if _phase2b_completion is None:
        _phase2b_completion = Phase2BCompletion()
    return _phase2b_completion

def execute_complete_phase2b() -> Dict[str, Any]:
    """
    Execute complete Phase 2B process
    
    Returns:
        Dictionary with complete Phase 2B results
    """
    completion = get_phase2b_completion()
    return completion.execute_complete_phase2b()

def verify_single_spine_reality() -> Dict[str, Any]:
    """
    Verify that single-spine execution reality is achieved
    
    Returns:
        Dictionary with verification results
    """
    completion = get_phase2b_completion()
    
    if not completion._final_assessment:
        # Execute Phase 2B if not already completed
        results = execute_complete_phase2b()
        return results["final_assessment"]
    
    return completion._final_assessment
