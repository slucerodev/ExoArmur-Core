"""
Trust evaluator interface.

This is a formal interface that raises NotImplementedError.
The actual trust evaluation implementation is not part of the kernel.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TrustEvaluation:
    """Result of trust evaluation."""
    trust_score: float
    rationale: str
    evidence: Dict[str, Any]


class TrustEvaluator:
    """
    Trust evaluator interface for evaluating emitter trustworthiness.
    
    This is a formal interface that defines the contract for trust evaluation.
    Implementations should evaluate the trustworthiness of an emitter based on
    historical behavior, reputation, and other signals.
    
    The kernel does not provide a concrete implementation. This interface is
    provided for type checking and documentation purposes.
    """
    
    def evaluate_trust(
        self,
        event_source: Dict[str, Any],
        emitter_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        cell_id: Optional[str] = None
    ) -> float:
        """
        Evaluate trust score for an emitter.
        
        Args:
            event_source: Source information for the event
            emitter_id: Identifier for the emitter
            tenant_id: Tenant identifier
            cell_id: Cell identifier
            
        Returns:
            Trust score between 0.0 (untrusted) and 1.0 (fully trusted)
            
        Raises:
            NotImplementedError: This interface does not provide a concrete implementation
        """
        raise NotImplementedError(
            "TrustEvaluator is an interface. "
            "Concrete implementations must be provided by the consuming system."
        )
