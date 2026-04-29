"""
Enterprise Simulation Harness

This module provides a reproducible multi-scenario simulation harness for
enterprise-scale validation of ExoArmur governance boundaries. It runs
multiple deterministic scenarios and produces stable hashes for certification.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

from exoarmur.stability.deterministic_ordering import deterministic_iter_dict


@dataclass(frozen=True)
class ScenarioDefinition:
    """Definition of a simulation scenario."""
    scenario_id: str
    name: str
    description: str
    input_data: Dict[str, Any]
    expected_behavior: str
    tags: tuple = field(default_factory=tuple)


@dataclass
class ScenarioResult:
    """Result of running a single scenario."""
    scenario_id: str
    pass_result: bool
    execution_hash: str
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    stage_hashes: Dict[str, str] = field(default_factory=dict)


@dataclass
class SimulationReport:
    """Report from running multiple scenarios."""
    scenario_results: Dict[str, ScenarioResult] = field(default_factory=dict)
    overall_hash: str = ""
    reproducibility_score: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def all_hashes(self) -> List[str]:
        """Get all scenario execution hashes."""
        return [result.execution_hash for result in self.scenario_results.values()]
    
    @property
    def unique_hash_count(self) -> int:
        """Get count of unique hashes across all scenarios."""
        return len(set(self.all_hashes))
    
    @property
    def overall_status(self) -> str:
        """Get overall pass/fail status."""
        if self.failure_count == 0 and self.success_count > 0:
            return "ALL SCENARIOS PASSED"
        elif self.success_count > 0:
            return f"PARTIAL FAILURE ({self.failure_count}/{len(self.scenario_results)} failed)"
        else:
            return "ALL SCENARIOS FAILED"
    
    def compute_overall_hash(self) -> str:
        """Compute overall hash from all scenario results."""
        # Sort scenario IDs for deterministic ordering
        sorted_ids = sorted(self.scenario_results.keys())
        
        # Collect all hashes in deterministic order
        hash_components = []
        for scenario_id in sorted_ids:
            result = self.scenario_results[scenario_id]
            hash_components.append({
                "scenario_id": scenario_id,
                "execution_hash": result.execution_hash,
                "pass_result": result.pass_result,
            })
        
        # Compute deterministic hash
        hash_input = json.dumps(hash_components, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()


class EnterpriseSimulationHarness:
    """
    Harness for running reproducible multi-scenario enterprise simulations.
    
    This harness runs multiple scenarios in a deterministic manner and produces
    stable hashes for certification validation.
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize the simulation harness.
        
        Args:
            seed: Random seed for deterministic execution
        """
        self.seed = seed
        self.scenarios: Dict[str, ScenarioDefinition] = {}
    
    def register_scenario(self, scenario: ScenarioDefinition) -> None:
        """
        Register a scenario for simulation.
        
        Args:
            scenario: Scenario definition to register
        """
        self.scenarios[scenario.scenario_id] = scenario
    
    def register_scenarios(self, scenarios: List[ScenarioDefinition]) -> None:
        """
        Register multiple scenarios for simulation.
        
        Args:
            scenarios: List of scenario definitions to register
        """
        for scenario in scenarios:
            self.register_scenario(scenario)
    
    def run_scenario(
        self,
        scenario: ScenarioDefinition,
        executor: Callable[[Dict[str, Any]], Dict[str, Any]]
    ) -> ScenarioResult:
        """
        Run a single scenario.
        
        Args:
            scenario: Scenario to run
            executor: Function that executes the scenario and returns result
            
        Returns:
            Scenario result with execution hash and metadata
        """
        try:
            # Execute scenario
            execution_result = executor(scenario.input_data)
            
            # Compute execution hash from result
            # Convert deterministic_iter_dict result to dict for JSON serialization
            ordered_result = dict(deterministic_iter_dict(execution_result))
            hash_input = json.dumps(ordered_result, sort_keys=True)
            execution_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            # Determine pass/fail
            pass_result = execution_result.get("success", True)
            failure_reason = execution_result.get("failure_reason")
            
            # Extract stage hashes if present
            stage_hashes = execution_result.get("stage_hashes", {})
            
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                pass_result=pass_result,
                execution_hash=execution_hash,
                execution_metadata=execution_result.get("metadata", {}),
                failure_reason=failure_reason,
                stage_hashes=stage_hashes,
            )
        except Exception as e:
            # Return failure result on exception
            hash_input = json.dumps({"error": str(e)}, sort_keys=True)
            execution_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                pass_result=False,
                execution_hash=execution_hash,
                execution_metadata={"error": str(e)},
                failure_reason=str(e),
            )
    
    def run_scenarios(
        self,
        executor: Callable[[Dict[str, Any]], Dict[str, Any]],
        parallel: bool = False,
        max_workers: int = 4
    ) -> SimulationReport:
        """
        Run all registered scenarios.
        
        Args:
            executor: Function that executes scenarios
            parallel: Whether to run scenarios in parallel
            max_workers: Maximum number of parallel workers
            
        Returns:
            Simulation report with all scenario results
        """
        report = SimulationReport()
        
        if parallel:
            # Run scenarios in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor_pool:
                futures = {
                    executor_pool.submit(
                        self.run_scenario,
                        scenario,
                        executor
                    ): scenario.scenario_id
                    for scenario in self.scenarios.values()
                }
                
                for future in futures:
                    scenario_id = futures[future]
                    result = future.result()
                    report.scenario_results[scenario_id] = result
        else:
            # Run scenarios sequentially
            for scenario in self.scenarios.values():
                result = self.run_scenario(scenario, executor)
                report.scenario_results[scenario.scenario_id] = result
        
        # Compute statistics
        report.success_count = sum(
            1 for result in report.scenario_results.values() if result.pass_result
        )
        report.failure_count = len(report.scenario_results) - report.success_count
        
        # Compute overall hash
        report.overall_hash = report.compute_overall_hash()
        
        # Compute reproducibility score
        if len(report.scenario_results) > 0:
            report.reproducibility_score = report.success_count / len(report.scenario_results)
        
        return report
    
    def verify_reproducibility(
        self,
        report1: SimulationReport,
        report2: SimulationReport
    ) -> bool:
        """
        Verify that two simulation reports are reproducible.
        
        Args:
            report1: First simulation report
            report2: Second simulation report
            
        Returns:
            True if reports are reproducible (same overall hash and results)
        """
        # Check overall hash
        if report1.overall_hash != report2.overall_hash:
            return False
        
        # Check scenario results
        if set(report1.scenario_results.keys()) != set(report2.scenario_results.keys()):
            return False
        
        for scenario_id in report1.scenario_results:
            result1 = report1.scenario_results[scenario_id]
            result2 = report2.scenario_results[scenario_id]
            
            if result1.execution_hash != result2.execution_hash:
                return False
            if result1.pass_result != result2.pass_result:
                return False
        
        return True


def create_default_scenarios() -> List[ScenarioDefinition]:
    """
    Create a set of default enterprise scenarios for simulation.
    
    Returns:
        List of default scenario definitions
    """
    return [
        ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Basic Module Execution",
            description="Basic module execution with valid input",
            input_data={"action": "execute", "module": "test_module", "params": {"x": 10}},
            expected_behavior="Successful execution with deterministic output",
            tags=("basic", "execution"),
        ),
        ScenarioDefinition(
            scenario_id="SCENARIO_002",
            name="Capability Enforcement",
            description="Module execution with capability check",
            input_data={"action": "execute", "module": "test_module", "params": {"x": 10}, "capabilities": ["read"]},
            expected_behavior="Successful execution with capability enforcement",
            tags=("capability", "enforcement"),
        ),
        ScenarioDefinition(
            scenario_id="SCENARIO_003",
            name="Budget Limit",
            description="Module execution with budget limit",
            input_data={"action": "execute", "module": "test_module", "params": {"x": 10}, "budget": {"steps": 100}},
            expected_behavior="Successful execution within budget",
            tags=("budget", "limit"),
        ),
        ScenarioDefinition(
            scenario_id="SCENARIO_004",
            name="Provenance Audit",
            description="Module execution with provenance tracking",
            input_data={"action": "execute", "module": "test_module", "params": {"x": 10}, "provenance": True},
            expected_behavior="Successful execution with provenance audit",
            tags=("provenance", "audit"),
        ),
        ScenarioDefinition(
            scenario_id="SCENARIO_005",
            name="Policy Simulation",
            description="Module execution with policy simulation",
            input_data={"action": "execute", "module": "test_module", "params": {"x": 10}, "policy": "allow_all"},
            expected_behavior="Successful execution with policy simulation",
            tags=("policy", "simulation"),
        ),
    ]
