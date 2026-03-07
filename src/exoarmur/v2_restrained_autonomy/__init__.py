"""
ExoArmur ADMO V2 Restrained Autonomy Pipeline
Minimal belief->policy->action pipeline with operator approval
"""

from .pipeline import RestrainedAutonomyPipeline, RestrainedAutonomyConfig, ActionOutcome
from .mock_executor import MockActionExecutor

__all__ = ['RestrainedAutonomyPipeline', 'RestrainedAutonomyConfig', 'ActionOutcome', 'MockActionExecutor']

# Import demo script for CLI access
from ..scripts.demo_v2_restrained_autonomy import main as demo_main

# Export main function for module entry point
def demo():
    """Demo entry point for CLI access"""
    import sys
    sys.exit(demo_main())
