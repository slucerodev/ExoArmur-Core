"""
Execution Surface Audit - Phase 2B Primitive Collapse

This module audits and collapses all remaining execution surfaces that can
trigger domain logic without passing through V2EntryGate.

PRINCIPLES:
- No independent execution primitives
- All domain logic must route through canonical spine
- Structural elimination of bypass capability
"""

import logging
from typing import Dict, Any, List, Set, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ExecutionSurfaceType(Enum):
    """Types of execution surfaces"""
    DOMAIN_LOGIC = "domain_logic"
    DIRECT_PRIMITIVE = "direct_primitive"
    ASYNC_BACKGROUND = "async_background"
    SERVICE_LAYER = "service_layer"
    TEST_UTILITIES = "test_utilities"
    DEBUG_HOOKS = "debug_hooks"

class BypassRiskLevel(Enum):
    """Risk levels for bypass capability"""
    CRITICAL = "critical"  # Can execute domain logic without V2EntryGate
    HIGH = "high"         # Likely bypass path
    MEDIUM = "medium"     # Possible bypass path
    LOW = "low"           # Read-only or limited impact

class CollapseAction(Enum):
    """Required action for execution surface"""
    MUST_ROUTE = "must_route"           # Must route through V2EntryGate
    MUST_WRAP = "must_wrap"             # Must be wrapped for routing
    MUST_REFACTOR = "must_refactor"     # Must be refactored into routed service
    MUST_ELIMINATE = "must_eliminate"   # Dangerous direct primitive - remove

@dataclass
class ExecutionSurface:
    """Represents an execution surface that could bypass canonical routing"""
    name: str
    location: str
    surface_type: ExecutionSurfaceType
    bypass_risk: BypassRiskLevel
    collapse_action: CollapseAction
    description: str
    bypass_mechanism: str
    dependencies: List[str]
    
class ExecutionSurfaceAuditor:
    """Audits execution surfaces for bypass capability"""
    
    def __init__(self):
        self.discovered_surfaces: List[ExecutionSurface] = []
        self.bypass_surfaces: List[ExecutionSurface] = []
        self.collapse_plan: Dict[CollapseAction, List[ExecutionSurface]] = {
            action: [] for action in CollapseAction
        }
    
    def discover_execution_surfaces(self) -> List[ExecutionSurface]:
        """Discover all execution surfaces in the codebase"""
        logger.info("Discovering execution surfaces...")
        
        surfaces = []
        
        # A) DOMAIN LOGIC ENTRYPOINTS
        surfaces.extend(self._discover_domain_logic_surfaces())
        
        # B) DIRECT EXECUTION PRIMITIVES
        surfaces.extend(self._discover_direct_primitives())
        
        # C) ASYNC/BACKGROUND SURFACES
        surfaces.extend(self._discover_async_surfaces())
        
        # D) SERVICE LAYER METHODS
        surfaces.extend(self._discover_service_surfaces())
        
        # E) TEST UTILITIES
        surfaces.extend(self._discover_test_surfaces())
        
        # F) DEBUG HOOKS
        surfaces.extend(self._discover_debug_surfaces())
        
        self.discovered_surfaces = surfaces
        logger.info(f"Discovered {len(surfaces)} execution surfaces")
        
        return surfaces
    
    def _discover_domain_logic_surfaces(self) -> List[ExecutionSurface]:
        """Discover domain logic entrypoints"""
        surfaces = []
        
        # ReplayEngine - Direct replay capability
        surfaces.append(ExecutionSurface(
            name="ReplayEngine.replay_correlation",
            location="src/exoarmur/replay/replay_engine.py",
            surface_type=ExecutionSurfaceType.DOMAIN_LOGIC,
            bypass_risk=BypassRiskLevel.CRITICAL,
            collapse_action=CollapseAction.MUST_ROUTE,
            description="Replay engine can reconstruct system behavior without V2EntryGate",
            bypass_mechanism="Direct event processing without canonical routing",
            dependencies=["audit_store", "intent_store"]
        ))
        
        # MultiNodeVerifier - Direct verification
        surfaces.append(ExecutionSurface(
            name="MultiNodeVerifier._execute_isolated_replays",
            location="src/exoarmur/replay/multi_node_verifier.py",
            surface_type=ExecutionSurfaceType.DOMAIN_LOGIC,
            bypass_risk=BypassRiskLevel.CRITICAL,
            collapse_action=CollapseAction.MUST_ROUTE,
            description="Multi-node verifier can execute replays without V2EntryGate",
            bypass_mechanism="Direct replay execution in isolated environments",
            dependencies=["replay_engine", "audit_store"]
        ))
        
        # ByzantineFaultInjection - Direct fault injection
        surfaces.append(ExecutionSurface(
            name="ByzantineFaultInjection",
            location="src/exoarmur/replay/byzantine_fault_injection.py",
            surface_type=ExecutionSurfaceType.DOMAIN_LOGIC,
            bypass_risk=BypassRiskLevel.HIGH,
            collapse_action=CollapseAction.MUST_WRAP,
            description="Byzantine fault injection can execute test scenarios without V2EntryGate",
            bypass_mechanism="Direct fault scenario execution",
            dependencies=["replay_engine", "test_scenarios"]
        ))
        
        return surfaces
    
    def _discover_direct_primitives(self) -> List[ExecutionSurface]:
        """Discover direct execution primitives"""
        surfaces = []
        
        # IdentityContainmentTickService.tick() - Background processing
        surfaces.append(ExecutionSurface(
            name="IdentityContainmentTickService.tick",
            location="src/exoarmur/identity_containment/execution.py",
            surface_type=ExecutionSurfaceType.ASYNC_BACKGROUND,
            bypass_risk=BypassRiskLevel.HIGH,
            collapse_action=CollapseAction.MUST_ROUTE,
            description="Tick service can process expirations without V2EntryGate mediation",
            bypass_mechanism="Direct executor.process_expirations() call",
            dependencies=["executor", "clock", "audit_service"]
        ))
        
        # MockExecutor.execute_isolate_endpoint - Direct execution
        surfaces.append(ExecutionSurface(
            name="MockExecutor.execute_isolate_endpoint",
            location="src/exoarmur/v2_restrained_autonomy/mock_executor.py",
            surface_type=ExecutionSurfaceType.DIRECT_PRIMITIVE,
            bypass_risk=BypassRiskLevel.HIGH,
            collapse_action=CollapseAction.MUST_ELIMINATE,
            description="Mock executor can execute without V2EntryGate routing",
            bypass_mechanism="Direct execute_module call without enforcement",
            dependencies=["execution_request"]
        ))
        
        return surfaces
    
    def _discover_async_surfaces(self) -> List[ExecutionSurface]:
        """Discover async/background execution surfaces"""
        surfaces = []
        
        # NATS Consumer - Background message processing
        surfaces.append(ExecutionSurface(
            name="CollectiveAggregator.start_consumer",
            location="src/exoarmur/main.py (background task)",
            surface_type=ExecutionSurfaceType.ASYNC_BACKGROUND,
            bypass_risk=BypassRiskLevel.MEDIUM,
            collapse_action=CollapseAction.MUST_WRAP,
            description="Background consumer can process messages without V2EntryGate",
            bypass_mechanism="Async task creation without canonical routing",
            dependencies=["nats_client", "message_handler"]
        ))
        
        return surfaces
    
    def _discover_service_surfaces(self) -> List[ExecutionSurface]:
        """Discover service layer methods"""
        surfaces = []
        
        # AuthService - Authentication logic
        surfaces.append(ExecutionSurface(
            name="AuthService methods",
            location="src/exoarmur/auth/auth_service.py",
            surface_type=ExecutionSurfaceType.SERVICE_LAYER,
            bypass_risk=BypassRiskLevel.LOW,
            collapse_action=CollapseAction.MUST_WRAP,
            description="Auth service methods (read-only verification)",
            bypass_mechanism="Direct auth logic execution",
            dependencies=["user_store", "token_validation"]
        ))
        
        # ApprovalService - Approval logic
        surfaces.append(ExecutionSurface(
            name="ApprovalService methods",
            location="src/exoarmur/control_plane/approval_service.py",
            surface_type=ExecutionSurfaceType.SERVICE_LAYER,
            bypass_risk=BypassRiskLevel.MEDIUM,
            collapse_action=CollapseAction.MUST_WRAP,
            description="Approval service can modify approval state without V2EntryGate",
            bypass_mechanism="Direct approval state modification",
            dependencies=["approval_store", "policy_engine"]
        ))
        
        return surfaces
    
    def _discover_test_surfaces(self) -> List[ExecutionSurface]:
        """Discover test utilities"""
        surfaces = []
        
        # Test helpers and utilities
        surfaces.append(ExecutionSurface(
            name="Test execution helpers",
            location="tests/ (various test files)",
            surface_type=ExecutionSurfaceType.TEST_UTILITIES,
            bypass_risk=BypassRiskLevel.MEDIUM,
            collapse_action=CollapseAction.MUST_WRAP,
            description="Test helpers can execute domain logic without V2EntryGate",
            bypass_mechanism="Direct test execution without canonical routing",
            dependencies=["test_fixtures", "mock_objects"]
        ))
        
        return surfaces
    
    def _discover_debug_surfaces(self) -> List[ExecutionSurface]:
        """Discover debug hooks"""
        surfaces = []
        
        # Debug utilities and development hooks
        surfaces.append(ExecutionSurface(
            name="Debug execution hooks",
            location="src/ (various debug utilities)",
            surface_type=ExecutionSurfaceType.DEBUG_HOOKS,
            bypass_risk=BypassRiskLevel.LOW,
            collapse_action=CollapseAction.MUST_ELIMINATE,
            description="Debug hooks can execute without V2EntryGate",
            bypass_mechanism="Direct debug execution",
            dependencies=["debug_tools", "development_utilities"]
        ))
        
        return surfaces
    
    def analyze_bypass_capability(self) -> List[ExecutionSurface]:
        """Analyze which surfaces can bypass canonical routing"""
        logger.info("Analyzing bypass capability...")
        
        bypass_surfaces = []
        
        for surface in self.discovered_surfaces:
            if surface.bypass_risk in [BypassRiskLevel.CRITICAL, BypassRiskLevel.HIGH]:
                bypass_surfaces.append(surface)
        
        self.bypass_surfaces = bypass_surfaces
        logger.info(f"Found {len(bypass_surfaces)} bypass-capable surfaces")
        
        return bypass_surfaces
    
    def create_collapse_plan(self) -> Dict[CollapseAction, List[ExecutionSurface]]:
        """Create collapse plan for execution surfaces"""
        logger.info("Creating collapse plan...")
        
        collapse_plan = {action: [] for action in CollapseAction}
        
        for surface in self.discovered_surfaces:
            collapse_plan[surface.collapse_action].append(surface)
        
        self.collapse_plan = collapse_plan
        
        # Log summary
        for action, surfaces in collapse_plan.items():
            logger.info(f"{action.value}: {len(surfaces)} surfaces")
        
        return collapse_plan
    
    def assess_single_spine_reality(self) -> Dict[str, Any]:
        """Assess whether single-spine execution is reality"""
        logger.info("Assessing single-spine reality...")
        
        critical_bypasses = [s for s in self.bypass_surfaces if s.bypass_risk == BypassRiskLevel.CRITICAL]
        high_bypasses = [s for s in self.bypass_surfaces if s.bypass_risk == BypassRiskLevel.HIGH]
        
        assessment = {
            "single_spine_achieved": len(critical_bypasses) == 0,
            "total_surfaces": len(self.discovered_surfaces),
            "bypass_surfaces": len(self.bypass_surfaces),
            "critical_bypasses": len(critical_bypasses),
            "high_bypasses": len(high_bypasses),
            "can_domain_logic_execute_without_v2": len(critical_bypasses) > 0,
            "bypass_paths_exist": len(self.bypass_surfaces) > 0,
            "critical_bypass_details": [(s.name, s.location) for s in critical_bypasses],
            "high_bypass_details": [(s.name, s.location) for s in high_bypasses]
        }
        
        logger.info(f"Single-spine assessment: {assessment['single_spine_achieved']}")
        
        return assessment

# Global auditor instance
_execution_surface_auditor = None

def get_execution_surface_auditor() -> ExecutionSurfaceAuditor:
    """Get the global execution surface auditor instance"""
    global _execution_surface_auditor
    if _execution_surface_auditor is None:
        _execution_surface_auditor = ExecutionSurfaceAuditor()
    return _execution_surface_auditor

def audit_execution_surfaces() -> Dict[str, Any]:
    """
    Perform complete execution surface audit
    
    Returns:
        Dictionary with audit results
    """
    auditor = get_execution_surface_auditor()
    
    # Discover surfaces
    surfaces = auditor.discover_execution_surfaces()
    
    # Analyze bypass capability
    bypass_surfaces = auditor.analyze_bypass_capability()
    
    # Create collapse plan
    collapse_plan = auditor.create_collapse_plan()
    
    # Assess single-spine reality
    assessment = auditor.assess_single_spine_reality()
    
    return {
        "total_surfaces": len(surfaces),
        "bypass_surfaces": len(bypass_surfaces),
        "collapse_plan": {action.value: len(surfaces) for action, surfaces in collapse_plan.items()},
        "single_spine_assessment": assessment,
        "critical_bypasses": assessment["critical_bypasses"],
        "single_spine_achieved": assessment["single_spine_achieved"]
    }
