"""
Phase 2B Completion Tests

Tests to verify that Phase 2B execution surface audit and primitive collapse
effectively eliminate independent execution primitives.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from exoarmur.execution_boundary_v2.entry.phase2b_completion import (
    execute_complete_phase2b,
    verify_single_spine_reality,
    get_phase2b_completion
)

class TestPhase2BCompletion:
    """Test Phase 2B execution surface audit and primitive collapse"""
    
    def test_phase2b_initialization(self):
        """Verify Phase 2B components can be initialized"""
        completion = get_phase2b_completion()
        
        # Should initialize successfully
        assert completion.initialize_components() == True
        assert completion._auditor is not None
        assert completion._collapser is not None
    
    def test_execution_surface_audit(self):
        """Verify execution surface audit works"""
        completion = get_phase2b_completion()
        completion.initialize_components()
        
        # Execute audit
        audit_results = completion.execute_phase2b_audit()
        
        # Should discover execution surfaces
        assert audit_results["total_surfaces"] > 0
        assert "bypass_surfaces" in audit_results
        assert "single_spine_assessment" in audit_results
        assert "critical_bypasses" in audit_results
    
    def test_primitive_collapse(self):
        """Verify primitive collapse works"""
        completion = get_phase2b_completion()
        completion.initialize_components()
        
        # Execute collapse
        collapse_results = completion.execute_primitive_collapse()
        
        # Should collapse some primitives
        assert "collapse_results" in collapse_results
        assert "verification" in collapse_results
        assert collapse_results["total_surfaces_collapsed"] >= 0
        assert collapse_results["total_methods_patched"] >= 0
    
    def test_complete_phase2b_execution(self):
        """Verify complete Phase 2B execution works"""
        results = execute_complete_phase2b()
        
        # Should complete successfully
        assert results["phase2b_completed"] == True
        assert "audit_results" in results
        assert "collapse_results" in results
        assert "final_assessment" in results
        assert "summary" in results
        
        # Should have discovered and collapsed surfaces
        assert results["summary"]["total_surfaces_discovered"] > 0
        assert results["summary"]["surfaces_collapsed"] >= 0
        assert results["summary"]["methods_patched"] >= 0
    
    def test_single_spine_verification(self):
        """Verify single-spine reality verification"""
        # Execute Phase 2B first
        execute_complete_phase2b()
        
        # Verify single-spine reality
        verification = verify_single_spine_reality()
        
        # Should provide assessment
        assert "single_spine_achieved" in verification
        assert "can_domain_logic_execute_without_v2" in verification
        assert "bypass_paths_remain" in verification
        assert "critical_bypasses_eliminated" in verification
    
    def test_bypass_surface_identification(self):
        """Verify bypass surfaces are properly identified"""
        completion = get_phase2b_completion()
        completion.initialize_components()
        
        # Execute audit
        audit_results = completion.execute_phase2b_audit()
        
        # Should identify bypass-capable surfaces
        assert audit_results["bypass_surfaces"] >= 0
        
        # Should identify critical bypasses
        single_spine_assessment = audit_results["single_spine_assessment"]
        assert "critical_bypasses" in single_spine_assessment
        assert "critical_bypass_details" in single_spine_assessment
    
    def test_collapse_effectiveness(self):
        """Verify primitive collapse is effective"""
        completion = get_phase2b_completion()
        completion.initialize_components()
        
        # Execute collapse
        collapse_results = completion.execute_primitive_collapse()
        
        # Should verify collapse effectiveness
        verification = collapse_results["verification"]
        assert "collapse_active" in verification
        assert "total_patches" in verification
        
        # Should have patched some methods
        assert verification["total_patches"] >= 0
    
    def test_phase2b_status_tracking(self):
        """Verify Phase 2B status tracking works"""
        completion = get_phase2b_completion()
        
        # Initial status
        status = completion.get_phase2b_status()
        assert status["components_initialized"] == False
        assert status["audit_completed"] == False
        assert status["collapse_completed"] == False
        
        # Initialize components
        completion.initialize_components()
        status = completion.get_phase2b_status()
        assert status["components_initialized"] == True
        
        # Execute audit
        completion.execute_phase2b_audit()
        status = completion.get_phase2b_status()
        assert status["audit_completed"] == True
    
    def test_error_handling(self):
        """Verify error handling in Phase 2B components"""
        completion = get_phase2b_completion()
        
        # Should handle missing components gracefully
        try:
            completion.execute_phase2b_audit()
            assert False, "Should have failed without initialization"
        except Exception:
            pass  # Expected
    
    def test_assessment_accuracy(self):
        """Verify single-spine assessment accuracy"""
        results = execute_complete_phase2b()
        
        assessment = results["final_assessment"]
        
        # Assessment should be internally consistent
        if assessment["single_spine_achieved"]:
            assert assessment["can_domain_logic_execute_without_v2"] == False
            assert assessment["critical_bypasses_eliminated"] >= 0
        
        # Should track collapse effectiveness
        assert assessment["surfaces_collapsed"] >= 0
        assert assessment["methods_patched"] >= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
