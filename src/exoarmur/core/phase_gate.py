"""
ExoArmur ADMO Phase Gate Mechanism
Ensures strict Phase isolation while allowing prototype development
"""

import os
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class SystemPhase(Enum):
    """System Phase enumeration for ADMO development"""
    PHASE_1 = 1  # Core ADMO loop only - production safe
    PHASE_2 = 2  # Federation and advanced features - prototype


class PhaseGate:
    """
    Phase Gate enforcement mechanism.
    
    ADMO Organism Law Compliance:
    - LAW-01: No Central Brain - Phase gate is local decision
    - LAW-06: Evidence-Backed Decisions - Phase changes are explicit and auditable
    - LAW-09: Graceful Degradation - Phase 1 remains fully functional without Phase 2
    
    Purpose:
    Prevents governance contradiction where enabled=True alone activates
    prototype behavior before Phase 2 acceptance criteria are met.
    """
    
    _current_phase: Optional[SystemPhase] = None
    
    @classmethod
    def current_phase(cls) -> SystemPhase:
        """Determine current system phase from environment"""
        if cls._current_phase is None:
            # Check explicit phase environment variable
            phase_env = os.getenv("EXOARMUR_PHASE", "1")
            try:
                phase_int = int(phase_env)
                cls._current_phase = SystemPhase(phase_int)
            except (ValueError, KeyError):
                logger.warning(f"Invalid EXOARMUR_PHASE '{phase_env}', defaulting to Phase 1")
                cls._current_phase = SystemPhase.PHASE_1
            
            logger.info(f"PhaseGate: Operating in Phase {cls._current_phase.value}")
        
        return cls._current_phase
    
    @classmethod
    def check_phase_2_eligibility(cls, component_name: str) -> None:
        """
        Check if component may activate Phase 2 behavior.
        
        Args:
            component_name: Name of component requesting Phase 2 activation
            
        Raises:
            NotImplementedError: If Phase 2 gate is not explicitly enabled
            
        Governance Rule:
        - enabled=True + Phase gate NOT present → raise NotImplementedError
        - enabled=True + Phase gate present → allow prototype behavior  
        - enabled=False → inert (handled by component logic)
        """
        current_phase = cls.current_phase()
        
        if current_phase != SystemPhase.PHASE_2:
            raise NotImplementedError(
                f"{component_name}: Phase 2 behavior requires EXOARMUR_PHASE=2. "
                f"Current phase: {current_phase.value}. "
                f"This protects Phase 1 isolation until acceptance criteria are met."
            )
        
        logger.debug(f"PhaseGate: {component_name} approved for Phase 2 behavior")
    
    @classmethod
    def is_phase_2_enabled(cls) -> bool:
        """Check if Phase 2 is explicitly enabled"""
        return cls.current_phase() == SystemPhase.PHASE_2


def require_phase_2(component_name: str):
    """
    Decorator for Phase 2 methods.
    
    Usage:
        @require_phase_2("FederationManager")
        async def advanced_federation_behavior(self):
            # Phase 2 implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            PhaseGate.check_phase_2_eligibility(component_name)
            return func(*args, **kwargs)
        return wrapper
    return decorator
