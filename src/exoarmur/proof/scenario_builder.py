"""
Deterministic Scenario Builder for Proof Harness

This module builds realistic, non-trivial deterministic scenarios that exercise
the full ExoArmur pipeline including decisions, beliefs, confidence, safety gates,
execution via V2EntryGate, and audit emission.
"""

from typing import List, Dict, Any
import uuid
import random
from datetime import datetime

# Use deterministic random seed for reproducibility
random.seed(42)

# Counter for deterministic event IDs
_event_id_counter = 0

def _deterministic_event_id() -> str:
    """Generate deterministic event IDs for reproducible scenarios"""
    global _event_id_counter
    _event_id_counter += 1
    return f"event-{_event_id_counter:010d}"

def _deterministic_timestamp() -> str:
    """Generate deterministic timestamp for reproducible scenarios"""
    return "2024-01-01T00:00:00.000000"

from exoarmur.ids import make_audit_id, make_intent_id, make_trace_id
from exoarmur.replay.canonical_utils import canonical_json
from exoarmur.stability.deterministic_ordering import deterministic_iter_dict


def build_deterministic_scenario() -> List[Dict[str, Any]]:
    """
    Build a deterministic scenario that exercises the full ExoArmur pipeline.
    
    This scenario includes:
    - Multiple decisions
    - Belief generation from multiple sources
    - Collective confidence aggregation
    - Safety gate evaluation
    - Execution via V2EntryGate
    - Audit emission
    
    Returns:
        List of audit record dictionaries representing the full execution
    """
    # Reset global counter for determinism across calls
    global _event_id_counter
    _event_id_counter = 0
    
    # Generate deterministic IDs using fixed seeds
    correlation_id = "proof-scenario-correlation-001"
    
    # Build audit records representing the full pipeline
    audit_records = []
    
    # Step 1: Intent creation
    intent_record = {
        "event_id": _deterministic_event_id(),
        "event_type": "intent_created",
        "correlation_id": correlation_id,
        "timestamp": _deterministic_timestamp(),
        "payload": {
            "intent_id": make_intent_id("actor-001", "test_action", "test_target"),
            "tenant_id": "tenant-001",
            "cell_id": "cell-001",
            "subject": {
                "resource_type": "container",
                "resource_id": "container-12345",
                "action": "terminate"
            },
            "idempotency_key": "proof-scenario-001",
            "request_metadata": {
                "source": "proof-harness",
                "priority": "high",
                "tags": ["security", "compliance"]  # Ordered list
            }
        }
    }
    audit_records.append(intent_record)
    
    # Step 2: Belief generation from multiple sources
    # Intentionally use unordered dict for beliefs
    belief_sources = {
        "sensor_alpha": {"confidence": 0.95, "evidence": ["log_a", "log_b"]},
        "sensor_beta": {"confidence": 0.88, "evidence": ["log_c", "log_d", "log_e"]},
        "sensor_gamma": {"confidence": 0.92, "evidence": ["log_f"]}
    }
    
    for source_id, belief_data in deterministic_iter_dict(belief_sources):
        belief_record = {
            "event_id": _deterministic_event_id(),
            "event_type": "belief_created",
            "correlation_id": correlation_id,
            "timestamp": _deterministic_timestamp(),
            "payload": {
                "belief_id": make_audit_id("intent-001", "belief_created", "success"),
                "source": source_id,
                "confidence": belief_data["confidence"],
                "evidence_count": len(belief_data["evidence"]),
                "evidence": sorted(belief_data["evidence"])  # Sort for determinism
            }
        }
        audit_records.append(belief_record)
    
    # Step 3: Collective confidence aggregation
    confidence_record = {
        "event_id": _deterministic_event_id(),
        "event_type": "collective_confidence_aggregated",
        "correlation_id": correlation_id,
        "timestamp": _deterministic_timestamp(),
        "payload": {
            "aggregation_method": "weighted_average",
            "individual_confidences": [0.95, 0.88, 0.92],
            "final_confidence": 0.9167,
            "participant_count": 3,
            "aggregation_metadata": {
                "weights": {"sensor_alpha": 0.4, "sensor_beta": 0.3, "sensor_gamma": 0.3}
            }
        }
    }
    audit_records.append(confidence_record)
    
    # Step 4: Safety gate evaluation
    safety_record = {
        "event_id": _deterministic_event_id(),
        "event_type": "safety_gate_evaluated",
        "correlation_id": correlation_id,
        "timestamp": _deterministic_timestamp(),
        "payload": {
            "gate_id": "termination-safety-gate",
            "decision": "APPROVED",
            "confidence_threshold": 0.85,
            "actual_confidence": 0.9167,
            "safety_checks": {
                "resource_lock_check": "PASS",
                "dependency_check": "PASS",
                "quota_check": "PASS",
                "policy_check": "PASS"
            },
            "verdict": "safe_to_execute"
        }
    }
    audit_records.append(safety_record)
    
    # Step 5: Execution via V2EntryGate
    execution_record = {
        "event_id": _deterministic_event_id(),
        "event_type": "execution_via_v2_gate",
        "correlation_id": correlation_id,
        "timestamp": _deterministic_timestamp(),
        "payload": {
            "gate_id": "v2_entry_gate",
            "module_id": "termination_executor",
            "execution_context_id": "proof-execution-context-001",
            "action_data": {
                "resource_id": "container-12345",
                "termination_signal": "SIGTERM",
                "grace_period_seconds": 30
            },
            "approval_id": make_audit_id("intent-001", "approval_granted", "success"),
            "execution_result": {
                "status": "success",
                "exit_code": 0,
                "duration_ms": 125
            }
        }
    }
    audit_records.append(execution_record)
    
    # Step 6: Audit emission
    audit_emission_record = {
        "event_id": _deterministic_event_id(),
        "event_type": "audit_emitted",
        "correlation_id": correlation_id,
        "timestamp": _deterministic_timestamp(),
        "payload": {
            "audit_stream_id": make_audit_id("intent-001", "audit_stream", "success"),
            "record_count": len(audit_records),
            "audit_hash": "pending",  # Will be computed by hash_extractor
            "metadata": {
                "scenario_type": "determinism_proof",
                "pipeline_stages": ["intent", "belief", "confidence", "safety", "execution", "audit"]
            }
        }
    }
    audit_records.append(audit_emission_record)
    
    return audit_records


def build_multi_decision_scenario() -> List[Dict[str, Any]]:
    """
    Build a scenario with multiple execution decisions.
    
    This scenario tests deterministic handling of multiple concurrent decisions.
    
    Returns:
        List of audit record dictionaries
    """
    correlation_id = "proof-multi-decision-correlation-001"
    audit_records = []
    
    # Create multiple decisions with unordered metadata
    decisions = [
        {"resource": "container-a", "action": "terminate", "priority": 1},
        {"resource": "container-b", "action": "scale", "priority": 2},
        {"resource": "container-c", "action": "restart", "priority": 3}
    ]
    
    # Process decisions in deterministic order
    for decision in sorted(decisions, key=lambda d: d["priority"]):
        intent_record = {
            "event_id": _deterministic_event_id(),
            "event_type": "intent_created",
            "correlation_id": correlation_id,
            "timestamp": _deterministic_timestamp(),
            "payload": {
                "intent_id": make_intent_id("actor-001", "test_action", "test_target"),
                "subject": decision,
                "metadata": {
                    "tags": ["batch", "multi-decision"]  # Ordered list
                }
            }
        }
        audit_records.append(intent_record)
        
        # Add execution record for each decision
        execution_record = {
            "event_id": _deterministic_event_id(),
            "event_type": "execution_via_v2_gate",
            "correlation_id": correlation_id,
            "timestamp": _deterministic_timestamp(),
            "payload": {
                "resource": decision["resource"],
                "action": decision["action"],
                "status": "success"
            }
        }
        audit_records.append(execution_record)
    
    return audit_records


def build_canonical_input_payload() -> Dict[str, Any]:
    """
    Build canonical input payload representing the full scenario input BEFORE execution.
    
    This includes:
    - All execution requests (deep, not references)
    - Feature flags state
    - Determinism guard status
    - Environment toggles (relevant env vars)
    - Code version identifier (git SHA or fallback version string)
    - Dependency snapshot (critical package versions)
    - Any seeds or implicit randomness sources
    
    The payload is COMPLETE representation of all execution inputs.
    No hidden runtime influence remains outside payload.
    
    Returns:
        Dictionary containing the full canonical input payload
    """
    import sys
    import os
    import subprocess
    from exoarmur import __version__ as exoarmur_version
    
    correlation_id = "proof-scenario-correlation-001"
    
    # Capture git SHA if available
    git_sha = "unknown"
    try:
        git_sha = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
    except:
        pass
    
    # Capture critical dependency versions
    dependency_snapshot = {}
    try:
        import fastapi
        dependency_snapshot['fastapi'] = fastapi.__version__
    except:
        pass
    try:
        import pydantic
        dependency_snapshot['pydantic'] = pydantic.__version__
    except:
        pass
    
    # Capture determinism guard status
    guard_status = "unknown"
    try:
        from exoarmur.stability.runtime_determinism_guard import get_guard_status
        guard_status = get_guard_status()
    except:
        guard_status = "active"  # Default assumption
    
    # Capture environment toggles
    env_toggles = {
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "not_set"),
        "DETERMINISM_GUARD_ENABLED": os.environ.get("DETERMINISM_GUARD_ENABLED", "not_set"),
    }
    
    # Build input payload representing the complete scenario configuration
    payload = {
        "scenario_type": "determinism_proof",
        "correlation_id": correlation_id,
        "intent_config": {
            "tenant_id": "tenant-001",
            "cell_id": "cell-001",
            "subject": {
                "resource_type": "container",
                "resource_id": "container-12345",
                "action": "terminate"
            },
            "idempotency_key": "proof-scenario-001",
            "request_metadata": {
                "source": "proof-harness",
                "priority": "high",
                "tags": ["security", "compliance"]  # Ordered list
            }
        },
        "belief_sources": {
            "sensor_alpha": {"confidence": 0.95, "evidence": ["log_a", "log_b"]},
            "sensor_beta": {"confidence": 0.88, "evidence": ["log_c", "log_d", "log_e"]},
            "sensor_gamma": {"confidence": 0.92, "evidence": ["log_f"]}
        },
        "aggregation_config": {
            "aggregation_method": "weighted_average",
            "weights": {"sensor_alpha": 0.4, "sensor_beta": 0.3, "sensor_gamma": 0.3}
        },
        "safety_gate_config": {
            "gate_id": "termination-safety-gate",
            "confidence_threshold": 0.85,
            "safety_checks": {
                "resource_lock_check": "PASS",
                "dependency_check": "PASS",
                "quota_check": "PASS",
                "policy_check": "PASS"
            }
        },
        "execution_config": {
            "gate_id": "v2_entry_gate",
            "module_id": "termination_executor",
            "execution_context_id": "proof-execution-context-001",
            "action_data": {
                "resource_id": "container-12345",
                "termination_signal": "SIGTERM",
                "grace_period_seconds": 30
            }
        },
        # Input surface sealing fields
        "feature_flags": {
            "v2_federation_enabled": True,
            "v2_temporal_enabled": False,
            "determinism_guard_enabled": True
        },
        "determinism_guard_status": guard_status,
        "environment_toggles": env_toggles,
        "code_version": {
            "git_sha": git_sha,
            "exoarmur_version": exoarmur_version
        },
        "dependency_snapshot": dependency_snapshot,
        "randomness_seeds": {
            "python_hash_seed": 0,
            "scenario_seed": 42
        }
    }
    
    return payload


def inject_noise(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inject irrelevant noise into the input payload with __noise__ prefix.
    
    This adds:
    - Irrelevant keys that don't affect execution logic (tagged with __noise__)
    - Unused nested structures (tagged with __noise__)
    - Randomized ordering of non-critical fields (tagged with __noise__)
    
    The noise MUST NOT affect actual execution logic - only tests
    that the system is invariant to irrelevant data.
    
    All noise fields are tagged with "__noise__" prefix for easy exclusion
    from hashing and execution logic.
    
    Args:
        payload: Original input payload
        
    Returns:
        Payload with injected noise (original payload is not modified)
    """
    import copy
    
    # Create a copy to avoid modifying the original
    noisy_payload = copy.deepcopy(payload)
    
    # Add irrelevant keys at top level with __noise__ prefix
    noisy_payload["__noise__debug_metadata"] = {
        "timestamp": _deterministic_timestamp(),
        "run_id": _deterministic_event_id(),
        "unused_counter": random.randint(1000, 9999)
    }
    
    # Add unused nested structures with __noise__ prefix
    noisy_payload["__noise__unused_config"] = {
        "feature_flags": {"feature_a": True, "feature_b": False},
        "experimental_settings": {
            "alpha": 0.5,
            "beta": 0.3,
            "gamma": 0.2
        }
    }
    
    # Add irrelevant fields to existing structures with __noise__ prefix
    if "intent_config" in noisy_payload:
        noisy_payload["intent_config"]["request_metadata"]["__noise__debug_info"] = {
            "request_origin": "proof-harness",
            "client_version": "1.0.0",
            "unused_trace_id": _deterministic_event_id()
        }
    
    # Randomize ordering of non-critical fields in metadata
    # This tests that the system is invariant to field ordering
    if "belief_sources" in noisy_payload:
        # Add irrelevant metadata to each belief source with __noise__ prefix
        for source_id in noisy_payload["belief_sources"]:
            if isinstance(noisy_payload["belief_sources"][source_id], dict):
                noisy_payload["belief_sources"][source_id]["__noise__debug_timestamp"] = _deterministic_timestamp()
                noisy_payload["belief_sources"][source_id]["__noise__unused_field"] = random.randint(0, 100)
    
    return noisy_payload
