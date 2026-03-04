"""
ExoArmur Execution Governance Boundary V2

Additive scaffolding for execution governance without modifying V1 contracts.
All V2 functionality is feature-gated and inert by default.
"""

from .flags.feature_flags import EXECUTION_BOUNDARY_V2_ENABLED

__all__ = ["EXECUTION_BOUNDARY_V2_ENABLED"]
