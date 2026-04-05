"""
Counterfactual Engine for replay analysis.

Provides the main interface for running counterfactual experiments
on ExoArmur audit trails.
"""

from typing import Dict, Any, List
from .intervention import Intervention, apply_intervention
from .counterfactual_report import CounterfactualReport
from exoarmur.replay.replay_engine import ReplayEngine, ReplayReport


class CounterfactualEngine:
    """Engine for running counterfactual replay experiments."""
    
    def __init__(self, replay_engine: ReplayEngine):
        """
        Initialize counterfactual engine with a replay engine.
        
        Args:
            replay_engine: Existing ReplayEngine instance to use
        """
        self.replay_engine = replay_engine
    
    def run_counterfactual(
        self,
        correlation_id: str,
        intervention: Intervention
    ) -> CounterfactualReport:
        """
        Run a counterfactual experiment.
        
        Args:
            correlation_id: Correlation ID to replay
            intervention: Intervention to apply
            
        Returns:
            CounterfactualReport with results
        """
        # Get original records from replay engine
        original_records = self.replay_engine.audit_store.get(correlation_id, [])
        if not original_records:
            raise ValueError(f"No audit records found for correlation_id: {correlation_id}")
        
        # Apply intervention to create modified records
        modified_records = []
        for record in original_records:
            modified_record = apply_intervention(record, intervention)
            modified_records.append(modified_record)
        
        # Create temporary replay engines for original and counterfactual
        original_engine = ReplayEngine(
            audit_store={correlation_id: original_records},
            intent_store=self.replay_engine.intent_store,
            approval_service=self.replay_engine.approval_service
        )
        
        counterfactual_engine = ReplayEngine(
            audit_store={correlation_id: modified_records},
            intent_store=self.replay_engine.intent_store,
            approval_service=self.replay_engine.approval_service
        )
        
        # Run both replays
        original_report = original_engine.replay_correlation(correlation_id)
        counterfactual_report = counterfactual_engine.replay_correlation(correlation_id)
        
        # Determine if outcome changed
        outcome_changed = self._did_outcome_change(original_report, counterfactual_report)
        
        # Generate verdict
        verdict = self._generate_verdict(original_report, counterfactual_report, outcome_changed)
        
        # Create counterfactual report
        return CounterfactualReport(
            correlation_id=correlation_id,
            intervention=intervention,
            original_result=original_report.result,
            counterfactual_result=counterfactual_report.result,
            outcome_changed=outcome_changed,
            original_summary=self._generate_summary(original_report),
            counterfactual_summary=self._generate_summary(counterfactual_report),
            verdict=verdict
        )
    
    def _did_outcome_change(self, original: ReplayReport, counterfactual: ReplayReport) -> bool:
        """Determine if the outcome changed between original and counterfactual."""
        # Different result status indicates change
        if original.result != counterfactual.result:
            return True
        
        # Different number of failures indicates change
        if len(original.failures) != len(counterfactual.failures):
            return True
        
        # Different safety gate verdicts indicate change
        if original.safety_gate_verdicts != counterfactual.safety_gate_verdicts:
            return True
        
        return False
    
    def _generate_verdict(self, original: ReplayReport, counterfactual: ReplayReport, outcome_changed: bool) -> str:
        """Generate a verdict for the counterfactual experiment."""
        if original.result.value == "failure" and counterfactual.result.value == "failure":
            return "INCONCLUSIVE"  # Both failed, can't determine difference
        
        if outcome_changed:
            return "DIFFERENT_OUTCOME"
        
        return "SAME_OUTCOME"
    
    def _generate_summary(self, report: ReplayReport) -> str:
        """Generate a human-readable summary of a replay report."""
        if report.result.value == "success":
            return f"SUCCESS: {report.processed_events} events processed, no failures"
        elif report.result.value == "failure":
            failure_summary = ", ".join(report.failures[:2])  # Show first 2 failures
            if len(report.failures) > 2:
                failure_summary += f" and {len(report.failures) - 2} more"
            return f"FAILURE: {failure_summary}"
        else:  # partial
            return f"PARTIAL: {report.processed_events} events processed, {len(report.warnings)} warnings"
