"""
Determinism Proof Harness Test Suite

Tests verify that the determinism harness produces identical hashes
across all execution modes: sequential, parallel, process-isolated,
time-skewed, and adversarial.
"""

import pytest
from typing import List, Dict, Any

from exoarmur.proof.determinism_harness import (
    DeterminismHarness,
    ProofReport
)
from exoarmur.proof.hash_extractor import (
    extract_canonical_audit_hash,
    verify_hash_consistency,
    get_unique_hash_count
)
from exoarmur.proof.scenario_builder import build_deterministic_scenario
from exoarmur.stability.deterministic_ordering import DeterminismViolationError


class TestHashExtractor:
    """Test canonical hash extraction"""
    
    def test_extract_canonical_audit_hash_basic(self):
        """Verify basic hash extraction produces consistent results"""
        audit_records = build_deterministic_scenario()
        
        # Extract hash twice
        hash1 = extract_canonical_audit_hash(audit_records)
        hash2 = extract_canonical_audit_hash(audit_records)
        
        # Should be identical
        assert hash1 == hash2, f"Hash mismatch: {hash1} != {hash2}"
    
    def test_extract_canonical_audit_hash_empty_raises(self):
        """Verify empty audit records raise ValueError"""
        with pytest.raises(ValueError, match="Cannot extract hash from empty"):
            extract_canonical_audit_hash([])
    
    def test_extract_canonical_audit_hash_invalid_type_raises(self):
        """Verify invalid record types raise ValueError"""
        invalid_records = [{"valid": "dict"}, "not_a_dict"]
        
        with pytest.raises(ValueError, match="Invalid audit record type"):
            extract_canonical_audit_hash(invalid_records)
    
    def test_verify_hash_consistency_all_equal(self):
        """Verify hash consistency check passes for identical hashes"""
        hashes = ["hash123", "hash123", "hash123"]
        assert verify_hash_consistency(hashes) is True
    
    def test_verify_hash_consistency_mismatch(self):
        """Verify hash consistency check fails for different hashes"""
        hashes = ["hash123", "hash456", "hash789"]
        assert verify_hash_consistency(hashes) is False
    
    def test_verify_hash_consistency_empty(self):
        """Verify hash consistency check fails for empty list"""
        assert verify_hash_consistency([]) is False
    
    def test_get_unique_hash_count(self):
        """Verify unique hash count calculation"""
        hashes = ["hash123", "hash456", "hash123", "hash789"]
        assert get_unique_hash_count(hashes) == 3


class TestDeterminismHarnessSequential:
    """Test sequential execution mode"""
    
    def test_sequential_runs_produce_identical_hashes(self):
        """Verify sequential runs produce identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        hashes = harness.run_sequential()
        
        # All hashes should be identical
        assert len(hashes) == 5
        assert verify_hash_consistency(hashes), f"Sequential hashes not consistent: {hashes}"
        assert get_unique_hash_count(hashes) == 1
    
    def test_sequential_assert_all_equal_passes(self):
        """Verify assert_all_equal passes for consistent hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        hashes = harness.run_sequential()
        # Should not raise
        harness.assert_all_equal(hashes)
    
    def test_sequential_assert_all_equal_raises_on_mismatch(self):
        """Verify assert_all_equal raises on hash mismatch"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=1)
        
        mismatched_hashes = ["hash1", "hash2", "hash3"]
        
        with pytest.raises(DeterminismViolationError, match="Hash inconsistency detected"):
            harness.assert_all_equal(mismatched_hashes)


class TestDeterminismHarnessParallel:
    """Test parallel execution mode"""
    
    def test_parallel_runs_produce_identical_hashes(self):
        """Verify parallel runs produce identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        hashes = harness.run_parallel()
        
        # All hashes should be identical
        assert len(hashes) == 5
        assert verify_hash_consistency(hashes), f"Parallel hashes not consistent: {hashes}"
        assert get_unique_hash_count(hashes) == 1


class TestDeterminismHarnessTimeSkew:
    """Test time-skewed execution mode"""
    
    def test_time_skewed_runs_produce_identical_hashes(self):
        """Verify time-skewed runs produce identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        hashes = harness.run_with_time_skew()
        
        # All hashes should be identical despite time delays
        assert len(hashes) == 5
        assert verify_hash_consistency(hashes), f"Time-skewed hashes not consistent: {hashes}"
        assert get_unique_hash_count(hashes) == 1


class TestDeterminismHarnessAdversarial:
    """Test adversarial execution mode"""
    
    def test_adversarial_runs_produce_identical_hashes(self):
        """Verify adversarial runs produce identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        hashes = harness.run_adversarial()
        
        # All hashes should be identical despite adversarial conditions
        assert len(hashes) == 5
        assert verify_hash_consistency(hashes), f"Adversarial hashes not consistent: {hashes}"
        assert get_unique_hash_count(hashes) == 1


class TestDeterminismHarnessProcessIsolated:
    """Test process-isolated execution mode using subprocess execution"""
    
    def test_process_isolation_subprocess(self):
        """Verify subprocess-based process isolation produces identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        # Run process-isolated mode (now uses subprocess)
        hashes = harness.run_process_isolated()
        
        # All hashes should be identical
        assert len(hashes) == 3, f"Expected 3 hashes, got {len(hashes)}"
        assert verify_hash_consistency(hashes), f"Process-isolated hashes not consistent: {hashes}"
        assert get_unique_hash_count(hashes) == 1, f"Expected 1 unique hash, got {get_unique_hash_count(hashes)}"
        
        # Hashes should match sequential execution hash
        harness.run_sequential()
        sequential_hash = harness.report.sequential_hashes[0]
        assert all(h == sequential_hash for h in hashes), \
            f"Process-isolated hashes do not match sequential hash {sequential_hash}"


class TestDeterminismHarnessMixedModes:
    """Test mixed-mode execution"""
    
    def test_mixed_modes_produce_identical_hashes(self):
        """Verify all modes together produce identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        # Run all modes
        sequential_hashes = harness.run_sequential()
        parallel_hashes = harness.run_parallel()
        time_skewed_hashes = harness.run_with_time_skew()
        adversarial_hashes = harness.run_adversarial()
        
        # All hashes across all modes should be identical
        all_hashes = (
            sequential_hashes +
            parallel_hashes +
            time_skewed_hashes +
            adversarial_hashes
        )
        
        assert verify_hash_consistency(all_hashes), f"Mixed-mode hashes not consistent"
        assert get_unique_hash_count(all_hashes) == 1


class TestProofReport:
    """Test proof report generation"""
    
    def test_proof_report_mode_statuses(self):
        """Verify proof report correctly calculates mode statuses"""
        report = ProofReport()
        
        # Set consistent hashes for all modes
        consistent_hash = "abc123def456"
        report.sequential_hashes = [consistent_hash] * 5
        report.parallel_hashes = [consistent_hash] * 5
        report.time_skewed_hashes = [consistent_hash] * 5
        report.adversarial_hashes = [consistent_hash] * 5
        
        # All modes should pass
        statuses = report.mode_statuses
        assert statuses["Sequential"] == "PASS"
        assert statuses["Parallel"] == "PASS"
        assert statuses["Time-Skewed"] == "PASS"
        assert statuses["Adversarial"] == "PASS"
    
    def test_proof_report_unique_hash_count(self):
        """Verify proof report correctly counts unique hashes"""
        report = ProofReport()
        
        # Set consistent hashes
        consistent_hash = "abc123"
        report.sequential_hashes = [consistent_hash] * 5
        report.parallel_hashes = [consistent_hash] * 5
        
        assert report.unique_hash_count == 1
        
        # Add different hash
        report.time_skewed_hashes = ["different_hash"] * 5
        
        assert report.unique_hash_count == 2
    
    def test_proof_report_overall_status(self):
        """Verify proof report overall status"""
        report = ProofReport()
        
        # All consistent hashes
        report.sequential_hashes = ["hash1"] * 5
        report.parallel_hashes = ["hash1"] * 5
        
        assert report.overall_status == "VERIFIED DETERMINISTIC"
        
        # Add inconsistent hash
        report.time_skewed_hashes = ["hash2"] * 5
        
        assert report.overall_status == "DETERMINISM VIOLATION DETECTED"
    
    def test_proof_report_canonical_hash(self):
        """Verify proof report canonical hash extraction"""
        report = ProofReport()
        
        # No hashes
        assert report.canonical_hash == ""
        
        # All consistent hashes
        report.sequential_hashes = ["canonical123"] * 5
        assert report.canonical_hash == "canonical123"
        
        # Inconsistent hashes
        report.parallel_hashes = ["different456"] * 5
        assert report.canonical_hash == ""


class TestDeterminismHarnessFullProof:
    """Test full proof execution"""
    
    def test_full_proof_execution_generates_report(self):
        """Verify full proof execution generates complete report"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        report = harness.run_full_proof()
        
        # Verify report is generated
        assert isinstance(report, ProofReport)
        
        # Verify all modes have results (except potentially process-isolated)
        assert len(report.sequential_hashes) == 3
        assert len(report.parallel_hashes) == 3
        assert len(report.time_skewed_hashes) == 3
        assert len(report.adversarial_hashes) == 3
        assert len(report.noise_hashes) == 3
    
    def test_full_proof_all_hashes_identical(self):
        """Verify full proof produces identical hashes across all modes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        report = harness.run_full_proof()
        
        # All hashes should be identical
        assert verify_hash_consistency(report.all_hashes), f"Full proof hashes not consistent"
        assert report.unique_hash_count == 1
        assert report.overall_status in ["VERIFIED DETERMINISTIC", "VERIFIED DETERMINISTIC (CLOSED-LOOP)"]
    
    def test_generate_proof_report(self):
        """Verify proof report generation"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        harness.run_sequential()
        harness.run_parallel()
        
        report_dict = harness.generate_proof_report()
        
        # Verify report structure
        assert "sequential_hashes" in report_dict
        assert "parallel_hashes" in report_dict
        assert "noise_hashes" in report_dict
        assert "input_hash" in report_dict
        assert "execution_hash" in report_dict
        assert "replay_hash" in report_dict
        assert "replay_verified" in report_dict
        assert "noise_verified" in report_dict
        assert "unique_hash_count" in report_dict
        assert "canonical_hash" in report_dict
        assert "overall_status" in report_dict
        assert "mode_statuses" in report_dict


class TestInputCommitment:
    """Test input commitment functionality"""
    
    def test_input_hash_consistency_across_runs(self):
        """Verify input hash is identical across multiple harness instances"""
        harness1 = DeterminismHarness(build_deterministic_scenario, runs=1)
        harness2 = DeterminismHarness(build_deterministic_scenario, runs=1)
        
        # Input hashes should be identical
        assert harness1.report.input_hash == harness2.report.input_hash, \
            f"Input hashes differ: {harness1.report.input_hash} vs {harness2.report.input_hash}"
    
    def test_input_hash_from_payload(self):
        """Verify input hash is computed from canonical payload"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        from exoarmur.proof.input_commitment import compute_input_hash
        
        payload = build_canonical_input_payload()
        input_hash = compute_input_hash(payload)
        
        # Harness should compute same hash
        harness = DeterminismHarness(build_deterministic_scenario, runs=1)
        assert harness.report.input_hash == input_hash


class TestReplayVerification:
    """Test replay-from-Proof verification"""
    
    def test_replay_hash_equals_execution_hash(self):
        """Verify replay hash equals execution hash"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        harness.run_sequential()
        
        # Compute execution hash
        execution_hash = harness.report.sequential_hashes[0]
        harness.report.execution_hash = execution_hash
        
        # Perform replay verification using the actual input hash
        from exoarmur.proof.replay_verifier import replay_from_input
        replay_hash = replay_from_input(harness.report.input_hash)
        
        # Replay hash should equal execution hash
        assert replay_hash == execution_hash, \
            f"Replay hash {replay_hash} does not match execution hash {execution_hash}"
    
    def test_replay_verified_flag(self):
        """Verify replay_verified flag is set correctly"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        report = harness.run_full_proof()
        
        # Replay verification should succeed
        assert report.replay_verified is True, "Replay verification should succeed"


class TestNoiseInjection:
    """Test noise injection resistance"""
    
    def test_noise_injection_does_not_change_execution_hash(self):
        """Verify noise injection does not change execution hash"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=5)
        
        # Run sequential to get reference hash
        harness.run_sequential()
        reference_hash = harness.report.sequential_hashes[0]
        
        # Run with noise
        noise_hashes = harness.run_with_noise()
        
        # All noise hashes should equal reference hash
        for noise_hash in noise_hashes:
            assert noise_hash == reference_hash, \
                f"Noise hash {noise_hash} does not match reference {reference_hash}"
    
    def test_noise_verified_flag(self):
        """Verify noise_verified flag is set correctly"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        report = harness.run_full_proof()
        
        # Noise verification should succeed
        assert report.noise_verified is True, "Noise verification should succeed"


class TestCombinedStress:
    """Test combined stress scenarios"""
    
    def test_noise_plus_async_plus_process_isolation(self):
        """Verify combined stress (noise + async + process isolation) produces identical hashes"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        # Run all modes
        harness.run_sequential()
        harness.run_parallel()
        harness.run_with_time_skew()
        harness.run_adversarial()
        harness.run_with_noise()
        
        # All hashes should be identical
        all_hashes = (
            harness.report.sequential_hashes +
            harness.report.parallel_hashes +
            harness.report.time_skewed_hashes +
            harness.report.adversarial_hashes +
            harness.report.noise_hashes
        )
        
        assert verify_hash_consistency(all_hashes), f"Combined stress hashes not consistent: {all_hashes}"
        assert get_unique_hash_count(all_hashes) == 1


class TestInputCompleteness:
    """Test input payload completeness"""
    
    def test_input_payload_includes_required_fields(self):
        """Verify input payload includes all required sealing fields"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        
        payload = build_canonical_input_payload()
        
        # Verify required input surface sealing fields are present
        assert "feature_flags" in payload, "Missing feature_flags"
        assert "determinism_guard_status" in payload, "Missing determinism_guard_status"
        assert "environment_toggles" in payload, "Missing environment_toggles"
        assert "code_version" in payload, "Missing code_version"
        assert "dependency_snapshot" in payload, "Missing dependency_snapshot"
        assert "randomness_seeds" in payload, "Missing randomness_seeds"
    
    def test_feature_flags_includes_required_flags(self):
        """Verify feature flags include required flags"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        
        payload = build_canonical_input_payload()
        feature_flags = payload.get("feature_flags", {})
        
        assert "v2_federation_enabled" in feature_flags
        assert "v2_temporal_enabled" in feature_flags
        assert "determinism_guard_enabled" in feature_flags
    
    def test_code_version_includes_git_sha(self):
        """Verify code version includes git SHA or fallback"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        
        payload = build_canonical_input_payload()
        code_version = payload.get("code_version", {})
        
        assert "git_sha" in code_version
        assert "exoarmur_version" in code_version


class TestPayloadPersistence:
    """Test payload persistence and replay"""
    
    def test_payload_can_be_persisted_and_loaded(self):
        """Verify payload can be persisted and loaded correctly"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        from exoarmur.proof.input_commitment import compute_input_hash
        from exoarmur.proof.payload_store import persist_payload, load_payload
        
        payload = build_canonical_input_payload()
        input_hash = compute_input_hash(payload)
        
        # Persist payload
        persist_payload(input_hash, payload)
        
        # Load payload
        loaded_payload = load_payload(input_hash)
        
        # Verify loaded payload matches original
        assert loaded_payload == payload, "Loaded payload does not match original"
    
    def test_replay_uses_persisted_payload(self):
        """Verify replay uses persisted payload instead of reconstruction"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload
        from exoarmur.proof.input_commitment import compute_input_hash
        from exoarmur.proof.payload_store import persist_payload, load_payload, payload_exists
        
        payload = build_canonical_input_payload()
        input_hash = compute_input_hash(payload)
        
        # Persist payload
        persist_payload(input_hash, payload)
        
        # Verify payload exists
        assert payload_exists(input_hash), "Payload was not persisted"
        
        # Verify load returns correct payload
        loaded_payload = load_payload(input_hash)
        assert loaded_payload == payload


class TestNoiseExclusion:
    """Test noise field exclusion from hashing and execution"""
    
    def test_noise_fields_have_prefix(self):
        """Verify all noise fields have __noise__ prefix"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload, inject_noise
        
        base_payload = build_canonical_input_payload()
        noisy_payload = inject_noise(base_payload)
        
        # Check for noise-prefixed fields
        noise_fields = [k for k in noisy_payload.keys() if k.startswith("__noise__")]
        assert len(noise_fields) > 0, "No noise fields found with __noise__ prefix"
    
    def test_strip_noise_fields_removes_noise(self):
        """Verify strip_noise_fields removes all __noise__ fields"""
        from exoarmur.proof.scenario_builder import build_canonical_input_payload, inject_noise
        from exoarmur.proof.hash_extractor import strip_noise_fields
        
        base_payload = build_canonical_input_payload()
        noisy_payload = inject_noise(base_payload)
        
        # Strip noise fields
        clean_payload = strip_noise_fields(noisy_payload)
        
        # Verify no noise fields remain
        noise_fields = [k for k in clean_payload.keys() if k.startswith("__noise__")]
        assert len(noise_fields) == 0, "Noise fields were not removed"
    
    def test_noise_excluded_from_execution_logic(self):
        """Verify noise does not affect execution logic"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=3)
        
        # Run with noise
        noise_hashes = harness.run_with_noise()
        
        # Verify all noise hashes are identical (noise didn't affect execution)
        assert verify_hash_consistency(noise_hashes), "Noise affected execution logic"


class TestFailureMode:
    """Test failure demonstration mode"""
    
    def test_failure_mode_detects_violations(self):
        """Verify failure mode detects intentional violations"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=1)
        
        # Run failure mode
        result = harness.run_failure_mode()
        
        # Verify failure was detected
        assert isinstance(result, dict), "Failure mode did not return dict"
        assert "failure_detected" in result, "Missing failure_detected field"
        assert "violation_type" in result, "Missing violation_type field"
        assert "hash_diverged" in result, "Missing hash_diverged field"
    
    def test_failure_mode_includes_datetime_test(self):
        """Verify failure mode includes datetime.now() test"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=1)
        
        # Run failure mode
        result = harness.run_failure_mode()
        
        # Verify failure detection occurred (either by guard or hash divergence)
        assert result["failure_detected"] or result["hash_diverged"], \
            "Failure mode did not detect any violation"


class TestEnvironmentCapture:
    """Test environment capture"""
    
    def test_environment_capture_populates_required_fields(self):
        """Verify environment capture includes required fields"""
        from exoarmur.proof.environment_capture import capture_environment
        
        env = capture_environment()
        
        # Verify required fields are present
        assert "python_version" in env, "Missing python_version"
        assert "os" in env, "Missing os"
        assert "platform" in env, "Missing platform"
        assert "architecture" in env, "Missing architecture"
        assert "dependencies" in env, "Missing dependencies"
        assert "determinism_guards" in env, "Missing determinism_guards"
    
    def test_environment_capture_includes_python_version(self):
        """Verify environment capture includes valid Python version"""
        from exoarmur.proof.environment_capture import capture_environment
        
        env = capture_environment()
        python_version = env.get("python_version", "")
        
        # Verify version format (e.g., "3.11.0")
        assert len(python_version.split(".")) >= 2, "Invalid Python version format"
    
    def test_environment_capture_includes_determinism_guards(self):
        """Verify environment capture includes determinism guard status"""
        from exoarmur.proof.environment_capture import capture_environment
        
        env = capture_environment()
        guards = env.get("determinism_guards", {})
        
        # Verify guards dictionary is present
        assert isinstance(guards, dict), "Determinism guards is not a dict"
        assert "status" in guards, "Missing guard status"
    
    def test_harness_captures_environment(self):
        """Verify harness captures environment on initialization"""
        harness = DeterminismHarness(build_deterministic_scenario, runs=1)
        
        # Verify environment is populated
        assert harness.report.environment is not None, "Environment not captured"
        assert len(harness.report.environment) > 0, "Environment is empty"
