"""
Counterfactual Replay Module

Minimal implementation for counterfactual analysis of ExoArmur audit trails.
"""

__version__ = "0.1.0"

from .intervention import Intervention, apply_intervention
from .counterfactual_engine import CounterfactualEngine
from .counterfactual_report import CounterfactualReport

__all__ = [
    "Intervention",
    "apply_intervention", 
    "CounterfactualEngine",
    "CounterfactualReport"
]
