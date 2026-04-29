"""
Enterprise Simulation Harness Test Suite

Tests verify that the EnterpriseSimulationHarness correctly:
- Registers and runs scenarios
- Produces deterministic hashes
- Verifies reproducibility across runs
"""

import pytest
from exoarmur.execution_boundary_v2.simulation.enterprise_simulation_harness import (
    ScenarioDefinition,
    ScenarioResult,
    SimulationReport,
    EnterpriseSimulationHarness,
    create_default_scenarios,
)


class TestScenarioDefinition:
    """Test ScenarioDefinition initialization and validation"""
    
    def test_scenario_definition_valid(self):
        """Verify valid ScenarioDefinition can be created"""
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
            tags=("test",),
        )
        
        assert scenario.scenario_id == "SCENARIO_001"
        assert scenario.name == "Test Scenario"
        assert scenario.description == "A test scenario"
        assert scenario.input_data == {"action": "execute", "x": 10}
        assert scenario.expected_behavior == "Success"
        assert scenario.tags == ("test",)
    
    def test_scenario_definition_frozen(self):
        """Verify ScenarioDefinition is frozen (immutable)"""
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        with pytest.raises(Exception):  # FrozenInstanceError
            scenario.scenario_id = "SCENARIO_002"


class TestScenarioResult:
    """Test ScenarioResult initialization and properties"""
    
    def test_scenario_result_valid(self):
        """Verify valid ScenarioResult can be created"""
        result = ScenarioResult(
            scenario_id="SCENARIO_001",
            pass_result=True,
            execution_hash="abc123",
            execution_metadata={"runtime": 100},
            failure_reason=None,
            stage_hashes={"stage1": "hash1"},
        )
        
        assert result.scenario_id == "SCENARIO_001"
        assert result.pass_result is True
        assert result.execution_hash == "abc123"
        assert result.execution_metadata == {"runtime": 100}
        assert result.failure_reason is None
        assert result.stage_hashes == {"stage1": "hash1"}
    
    def test_scenario_result_failure(self):
        """Verify ScenarioResult can represent failure"""
        result = ScenarioResult(
            scenario_id="SCENARIO_001",
            pass_result=False,
            execution_hash="xyz789",
            execution_metadata={"error": "test error"},
            failure_reason="Test failure",
            stage_hashes={},
        )
        
        assert result.pass_result is False
        assert result.failure_reason == "Test failure"


class TestSimulationReport:
    """Test SimulationReport initialization and properties"""
    
    def test_simulation_report_empty(self):
        """Verify empty SimulationReport can be created"""
        report = SimulationReport()
        
        assert report.scenario_results == {}
        assert report.overall_hash == ""
        assert report.reproducibility_score == 0.0
        assert report.failure_count == 0
        assert report.success_count == 0
    
    def test_simulation_report_all_hashes_property(self):
        """Verify all_hashes property returns all scenario hashes"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=True,
                execution_hash="hash2",
            ),
        }
        
        hashes = report.all_hashes
        assert len(hashes) == 2
        assert "hash1" in hashes
        assert "hash2" in hashes
    
    def test_simulation_report_unique_hash_count_property(self):
        """Verify unique_hash_count property returns count of unique hashes"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=True,
                execution_hash="hash1",  # Same hash
            ),
            "SCENARIO_003": ScenarioResult(
                scenario_id="SCENARIO_003",
                pass_result=True,
                execution_hash="hash2",  # Different hash
            ),
        }
        
        assert report.unique_hash_count == 2
    
    def test_simulation_report_overall_status_all_passed(self):
        """Verify overall_status returns ALL SCENARIOS PASSED when all pass"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=True,
                execution_hash="hash2",
            ),
        }
        report.success_count = 2
        report.failure_count = 0
        
        assert report.overall_status == "ALL SCENARIOS PASSED"
    
    def test_simulation_report_overall_status_partial_failure(self):
        """Verify overall_status returns PARTIAL FAILURE when some fail"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=False,
                execution_hash="hash2",
            ),
        }
        report.success_count = 1
        report.failure_count = 1
        
        assert report.overall_status == "PARTIAL FAILURE (1/2 failed)"
    
    def test_simulation_report_overall_status_all_failed(self):
        """Verify overall_status returns ALL SCENARIOS FAILED when all fail"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=False,
                execution_hash="hash1",
            ),
        }
        report.success_count = 0
        report.failure_count = 1
        
        assert report.overall_status == "ALL SCENARIOS FAILED"
    
    def test_simulation_report_compute_overall_hash(self):
        """Verify compute_overall_hash produces deterministic hash"""
        report = SimulationReport()
        report.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=True,
                execution_hash="hash2",
            ),
        }
        
        hash1 = report.compute_overall_hash()
        hash2 = report.compute_overall_hash()
        
        assert hash1 == hash2  # Deterministic
        assert len(hash1) == 64  # SHA256 hex string


class TestEnterpriseSimulationHarness:
    """Test EnterpriseSimulationHarness initialization and methods"""
    
    def test_harness_initialization(self):
        """Verify EnterpriseSimulationHarness can be initialized"""
        harness = EnterpriseSimulationHarness(seed=42)
        
        assert harness.seed == 42
        assert harness.scenarios == {}
    
    def test_register_scenario(self):
        """Verify register_scenario adds scenario to harness"""
        harness = EnterpriseSimulationHarness()
        
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        harness.register_scenario(scenario)
        
        assert "SCENARIO_001" in harness.scenarios
        assert harness.scenarios["SCENARIO_001"] == scenario
    
    def test_register_scenarios(self):
        """Verify register_scenarios adds multiple scenarios to harness"""
        harness = EnterpriseSimulationHarness()
        
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
        
        harness.register_scenarios(scenarios)
        
        assert len(harness.scenarios) == 2
        assert "SCENARIO_001" in harness.scenarios
        assert "SCENARIO_002" in harness.scenarios
    
    def test_run_scenario(self):
        """Verify run_scenario executes scenario and returns result"""
        harness = EnterpriseSimulationHarness()
        
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        result = harness.run_scenario(scenario, executor)
        
        assert result.scenario_id == "SCENARIO_001"
        assert result.pass_result is True
        assert result.execution_hash is not None
        assert len(result.execution_hash) == 64  # SHA256
    
    def test_run_scenario_failure(self):
        """Verify run_scenario handles executor failure"""
        harness = EnterpriseSimulationHarness()
        
        scenario = ScenarioDefinition(
            scenario_id="SCENARIO_001",
            name="Test Scenario",
            description="A test scenario",
            input_data={"action": "execute", "x": 10},
            expected_behavior="Success",
        )
        
        def executor(input_data):
            raise ValueError("Test error")
        
        result = harness.run_scenario(scenario, executor)
        
        assert result.scenario_id == "SCENARIO_001"
        assert result.pass_result is False
        assert result.failure_reason == "Test error"
        assert result.execution_hash is not None
    
    def test_run_scenarios_sequential(self):
        """Verify run_scenarios executes scenarios sequentially"""
        harness = EnterpriseSimulationHarness()
        
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
        
        harness.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report = harness.run_scenarios(executor, parallel=False)
        
        assert len(report.scenario_results) == 2
        assert report.success_count == 2
        assert report.failure_count == 0
        assert report.overall_hash is not None
    
    def test_run_scenarios_parallel(self):
        """Verify run_scenarios executes scenarios in parallel"""
        harness = EnterpriseSimulationHarness()
        
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
        
        harness.register_scenarios(scenarios)
        
        def executor(input_data):
            return {"success": True, "result": input_data["x"] * 2}
        
        report = harness.run_scenarios(executor, parallel=True, max_workers=2)
        
        assert len(report.scenario_results) == 2
        assert report.success_count == 2
        assert report.failure_count == 0
        assert report.overall_hash is not None
    
    def test_verify_reproducibility_true(self):
        """Verify verify_reproducibility returns True for identical reports"""
        harness = EnterpriseSimulationHarness()
        
        report1 = SimulationReport()
        report1.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
        }
        report1.overall_hash = "abc123"
        
        report2 = SimulationReport()
        report2.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
        }
        report2.overall_hash = "abc123"
        
        assert harness.verify_reproducibility(report1, report2) is True
    
    def test_verify_reproducibility_false_hash_mismatch(self):
        """Verify verify_reproducibility returns False on hash mismatch"""
        harness = EnterpriseSimulationHarness()
        
        report1 = SimulationReport()
        report1.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
        }
        report1.overall_hash = "abc123"
        
        report2 = SimulationReport()
        report2.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
        }
        report2.overall_hash = "xyz789"  # Different overall hash
        
        assert harness.verify_reproducibility(report1, report2) is False
    
    def test_verify_reproducibility_false_scenario_mismatch(self):
        """Verify verify_reproducibility returns False on scenario mismatch"""
        harness = EnterpriseSimulationHarness()
        
        report1 = SimulationReport()
        report1.scenario_results = {
            "SCENARIO_001": ScenarioResult(
                scenario_id="SCENARIO_001",
                pass_result=True,
                execution_hash="hash1",
            ),
        }
        report1.overall_hash = "abc123"
        
        report2 = SimulationReport()
        report2.scenario_results = {
            "SCENARIO_002": ScenarioResult(
                scenario_id="SCENARIO_002",
                pass_result=True,
                execution_hash="hash2",
            ),
        }
        report2.overall_hash = "abc123"
        
        assert harness.verify_reproducibility(report1, report2) is False


class TestCreateDefaultScenarios:
    """Test create_default_scenarios function"""
    
    def test_create_default_scenarios_returns_list(self):
        """Verify create_default_scenarios returns list of scenarios"""
        scenarios = create_default_scenarios()
        
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
        
        for scenario in scenarios:
            assert isinstance(scenario, ScenarioDefinition)
    
    def test_create_default_scenarios_has_expected_scenarios(self):
        """Verify create_default_scenarios includes expected scenarios"""
        scenarios = create_default_scenarios()
        
        scenario_ids = [s.scenario_id for s in scenarios]
        assert "SCENARIO_001" in scenario_ids
        assert "SCENARIO_002" in scenario_ids
        assert "SCENARIO_003" in scenario_ids
        assert "SCENARIO_004" in scenario_ids
        assert "SCENARIO_005" in scenario_ids
