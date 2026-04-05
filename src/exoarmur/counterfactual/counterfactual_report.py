"""
Counterfactual Report data structures.

Provides structured reporting for counterfactual analysis results.
"""

from typing import Any, Dict
from dataclasses import dataclass
from .intervention import Intervention
from exoarmur.replay.replay_engine import ReplayResult


@dataclass
class CounterfactualReport:
    """Report containing results of a counterfactual experiment."""
    
    correlation_id: str
    intervention: Intervention
    original_result: ReplayResult
    counterfactual_result: ReplayResult
    outcome_changed: bool
    original_summary: str
    counterfactual_summary: str
    verdict: str  # "SAME_OUTCOME", "DIFFERENT_OUTCOME", "INCONCLUSIVE"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "correlation_id": self.correlation_id,
            "intervention": {
                "field_path": self.intervention.field_path,
                "original_value": self.intervention.original_value,
                "counterfactual_value": self.intervention.counterfactual_value,
                "rationale": self.intervention.rationale
            },
            "original_result": self.original_result.value,
            "counterfactual_result": self.counterfactual_result.value,
            "outcome_changed": self.outcome_changed,
            "original_summary": self.original_summary,
            "counterfactual_summary": self.counterfactual_summary,
            "verdict": self.verdict
        }
