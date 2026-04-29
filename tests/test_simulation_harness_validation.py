"""
Simulation Harness Validation Test Suite

Tests verify that the EnterpriseSimulationHarness produces:
- Stable hashes across sequential runs
- Stable hashes across parallel runs
- Deterministic individual scenario hashes
- Reproducible results across instances
"""

import pytest
from exoarmur.execution_boundary_v2.simulation.enterprise_simulation_harness import (
    ScenarioDefinition,
    EnterpriseSimulationHarness,
    create_default_scenarios,
)


class TestHashStabilitySequential:
    """Test hash stability in sequential execution"""
    
    def test_hash_stability_sequential_runs(self):
        """Verify sequential runs produce identical hashes"""
        harness1 = EnterpriseSimulationHarness(seed=42)
        
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario 1",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
            ScenarioDefinition(
                scenario_id="SCENARIO_002",
                name="Test Scenario 2",
                description="Another test scenario",
                input_data={"action": "execute", "x": 20},
                expected_behavior="Success",
            ),
        ]
        
        harness1.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report1 = harness1.run_scenarios(executor, parallel=False)
        
        # Run again with new harness instance
        harness2 = EnterpriseSimulationHarness(seed=42)
        harness2.register_scenarios(scenarios)
        report2 = harness2.run_scenarios(executor, parallel=False)
        
        # Hashes should be identical
        assert report1.overall_hash == report2.overall_hash
        assert report1.unique_hash_count == report2.unique_hash_count
    
    def test_hash_stability_sequential_multiple_runs(self):
        """Verify multiple sequential runs produce identical hashes"""
        harness = EnterpriseSimulationHarness(seed=42)
        
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
        ]
        
        harness.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        hashes = []
        for _ in range(5):
            report = harness.run_scenarios(executor, parallel=False)
            hashes.append(report.overall_hash)
        
        # All hashes should be identical
        assert len(set(hashes)) == 1


class TestHashStabilityParallel:
    """Test hash stability in parallel execution"""
    
    def test_hash_stability_parallel_runs(self):
        """Verify parallel runs produce identical hashes"""
        harness1 = EnterpriseSimulationHarness(seed=42)
        
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario 1",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
            ScenarioDefinition(
                scenario_id="SCENARIO_002",
                name="Test Scenario 2",
                description="Another test scenario",
                input_data={"action": "execute", "x": 20},
                expected_behavior="Success",
            ),
        ]
        
        harness1.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report1 = harness1.run_scenarios(executor, parallel=True, max_workers=2)
        
        # Run again with new harness instance
        harness2 = EnterpriseSimulationHarness(seed=42)
        harness2.register_scenarios(scenarios)
        report2 = harness2.run_scenarios(executor, parallel=True, max_workers=2)
        
        # Hashes should be identical
        assert report1.overall_hash == report2.overall_hash
        assert report1.unique_hash_count == report2.unique_hash_count
    
    def test_hash_stability_parallel_multiple_runs(self):
        """Verify multiple parallel runs produce identical hashes"""
        harness = EnterpriseSimulationHarness(seed=42)
        
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
        ]
        
        harness.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        hashes = []
        for _ in range(5):
            report = harness.run_scenarios(executor, parallel=True, max_workers=2)
            hashes.append(report.overall_hash)
        
        # All hashes should be identical
        assert len(set(hashes)) == 1


class TestIndividualScenarioHashDeterminism:
    """Test individual scenario hash determinism"""
    
    def test_individual_scenario_hash_deterministic(self):
        """Verify individual scenario hash is deterministic"""
        harness1 = EnterpriseSimulationHarness(seed=42)
        
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        harness1.register_scenario(scenario)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        result1 = harness1.run_scenario(scenario, executor)
        
        # Run again with new harness instance
        harness2 = EnterpriseSimulationHarness(seed=42)
        harness2.register_scenario(scenario)
        result2 = harness2.run_scenario(scenario, executor)
        
        # Hashes should be identical
        assert result1.execution_hash == result2.execution_hash
    
    def test_individual_scenario_hash_stable_across_runs(self):
        """Verify individual scenario hash is stable across multiple runs"""
        harness = EnterpriseSimulationHarness(seed=42)
        
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        harness.register_scenario(scenario)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        hashes = []
        for _ in range(5):
            result = harness.run_scenario(scenario, executor)
            hashes.append(result.execution_hash)
        
        # All hashes should be identical
        assert len(set(hashes)) == 1


class TestReproducibilityAcrossInstances:
    """Test reproducibility across different harness instances"""
    
    def test_reproducibility_different_instances(self):
        """Verify different harness instances produce reproducible results"""
        harness1 = EnterpriseSimulationHarness(seed=42)
        harness2 = EnterpriseSimulationHarness(seed=42)
        
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
        ]
        
        harness1.register_scenarios(scenarios)
        harness2.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report1 = harness1.run_scenarios(executor, parallel=False)
        report2 = harness2.run_scenarios(executor, parallel=False)
        
        # Results should be reproducible
        assert report1.overall_hash == report2.overall_hash
        assert harness1.verify_reproducibility(report1, report2) is True
    
    def test_reproducibility_with_default_scenarios(self):
        """Verify reproducibility with default scenarios"""
        harness1 = EnterpriseSimulationHarness(seed=42)
        harness2 = EnterpriseSimulationHarness(seed=42)
        
        default_scenarios = create_default_scenarios()
        harness1.register_scenarios(default_scenarios)
        harness2.register_scenarios(default_scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data.get("x", 0) * 2}
        
        report1 = harness1.run_scenarios(executor, parallel=False)
        report2 = harness2.run_scenarios(executor, parallel=False)
        
        # Results should be reproducible
        assert report1.overall_hash == report2.overall_hash
        assert harness1.verify_reproducibility(report1, report2) is True
    
    def test_reproducibility_registration_order_independence(self):
        """Verify registration order does not affect reproducibility"""
        scenarios = [
            ScenarioDefinition(
                scenario_id="SCENARIO_001",
                name="Test Scenario 1",
                description="A test scenario",
                input_data={"action": "execute", "x": 10},
                expected_behavior="Success",
            ),
            ScenarioDefinition(
                scenario_id="SCENARIO_002",
                name="Test Scenario 2",
                description="Another test scenario",
                input_data={"action": "execute", "x": 20},
                expected_behavior="Success",
            ),
        ]
        
        harness1 = EnterpriseSimulationHarness(seed=42)
        harness1.register_scenarios(scenarios)  # Original order
        
        harness2 = EnterpriseSimulationHarness(seed=42)
        harness2.register_scenarios(list(reversed(scenarios)))  # Reversed order
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report1 = harness1.run_scenarios(executor, parallel=False)
        report2 = harness2.run_scenarios(executor, parallel=False)
        
        # Results should be reproducible (hash computation uses sorted scenario IDs)
        assert report1.overall_hash == report2.overall_hash
