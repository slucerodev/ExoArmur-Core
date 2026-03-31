"""
Byzantine Replay Stress & Fault Injection Layer

Module 3: Deterministic fault injection for validating system resilience
under adversarial or corrupted execution conditions.

This module is strictly additive - it injects faults without altering
canonical execution logic or MultiNodeReplayVerifier behavior.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import hashlib
import json

from .canonical_utils import canonical_json, stable_hash
from .event_envelope import CanonicalEvent
from .multi_node_verifier import MultiNodeReplayVerifier, DivergenceReport, ConsensusResult

logger = logging.getLogger(__name__)


class FaultType(Enum):
    """Types of deterministic faults that can be injected"""
    PAYLOAD_MUTATION = "payload_mutation"
    EVENT_TYPE_SUBSTITUTION = "event_type_substitution"
    SEQUENCE_MANIPULATION = "sequence_manipulation"
    FIELD_DELETION = "field_deletion"
    FIELD_ALTERATION = "field_alteration"
    HASH_CORRUPTION = "hash_corruption"
    STRUCTURED_CORRUPTION = "structured_corruption"


class ByzantineScenario(Enum):
    """Predefined Byzantine fault scenarios"""
    CLEAN = "clean"  # No faults
    SINGLE_NODE = "single_node"  # 1 faulty node
    PARTIAL = "partial"  # f < n/3 faulty nodes
    MAJORITY = "majority"  # f >= n/2 faulty nodes


@dataclass(frozen=True)
class FaultConfig:
    """Configuration for deterministic fault injection"""
    
    fault_type: FaultType
    target_nodes: List[str]
    severity: float = 1.0  # 0.0 to 1.0, affects fault intensity
    deterministic_seed: Optional[int] = None
    fault_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not 0.0 <= object.__getattribute__(self, 'severity') <= 1.0:
            raise ValueError("severity must be between 0.0 and 1.0")
        
        if not object.__getattribute__(self, 'target_nodes'):
            raise ValueError("target_nodes cannot be empty")


@dataclass(frozen=True)
class FaultInjectionResult:
    """Result of fault injection on a node"""
    
    node_id: str
    fault_type: FaultType
    original_events: List[CanonicalEvent]
    corrupted_events: List[CanonicalEvent]
    injection_details: Dict[str, Any] = field(default_factory=dict)
    
    def corruption_summary(self) -> Dict[str, Any]:
        """Get summary of corruption applied"""
        return {
            "node_id": self.node_id,
            "fault_type": self.fault_type.value,
            "events_corrupted": len(self.corrupted_events),
            "original_count": len(self.original_events),
            "corruption_ratio": len(self.corrupted_events) / len(self.original_events) if self.original_events else 0.0,
            "injection_details": self.injection_details
        }


@dataclass(frozen=True)
class ByzantineTestResult:
    """Complete result of Byzantine fault testing"""
    
    scenario: ByzantineScenario
    fault_configs: List[FaultConfig]
    injection_results: List[FaultInjectionResult]
    divergence_report: DivergenceReport
    baseline_hash: Optional[str] = None
    
    def test_summary(self) -> Dict[str, Any]:
        """Get comprehensive test summary"""
        return {
            "scenario": self.scenario.value,
            "consensus_result": self.divergence_report.consensus_result.value,
            "total_nodes": len(self.divergence_report.node_hashes),
            "faulty_nodes": len(self.fault_configs),
            "divergent_nodes": len(self.divergence_report.divergent_nodes),
            "consensus_achieved": self.divergence_report.consensus_result == ConsensusResult.CONSENSUS,
            "fault_types": [config.fault_type.value for config in self.fault_configs],
            "baseline_hash": self.baseline_hash,
            "node_hashes": self.divergence_report.node_hashes,
            "divergence_detected": self.divergence_report.has_divergence()
        }


class ByzantineFaultInjector:
    """Deterministic fault injection engine for Byzantine testing"""
    
    def __init__(self, deterministic_seed: Optional[int] = None):
        """
        Initialize fault injector
        
        Args:
            deterministic_seed: Seed for deterministic fault behavior
        """
        self.deterministic_seed = deterministic_seed
        self.logger = logging.getLogger(__name__)
        
        # Initialize deterministic random generator if seed provided
        if deterministic_seed is not None:
            self._rng_seed = deterministic_seed
        else:
            self._rng_seed = 42  # Default deterministic seed
    
    def inject_faults(self, 
                     base_events: List[CanonicalEvent], 
                     fault_configs: List[FaultConfig]) -> Dict[str, FaultInjectionResult]:
        """
        Inject deterministic faults into node inputs
        
        Args:
            base_events: Base canonical events to corrupt
            fault_configs: List of fault configurations to apply
            
        Returns:
            Dict mapping node_id to fault injection results
        """
        results = {}
        
        for fault_config in fault_configs:
            for target_node in fault_config.target_nodes:
                if target_node in results:
                    self.logger.warning(f"Node {target_node} already has faults applied")
                    continue
                
                # Apply fault based on type
                corrupted_events = self._apply_fault(
                    base_events.copy(), 
                    fault_config,
                    target_node
                )
                
                result = FaultInjectionResult(
                    node_id=target_node,
                    fault_type=fault_config.fault_type,
                    original_events=base_events,
                    corrupted_events=corrupted_events,
                    injection_details={
                        "severity": fault_config.severity,
                        "seed": fault_config.deterministic_seed or self._rng_seed,
                        "parameters": fault_config.fault_parameters
                    }
                )
                
                results[target_node] = result
                
                self.logger.info(f"Injected {fault_config.fault_type.value} fault into node {target_node}")
        
        return results
    
    def _apply_fault(self, 
                     events: List[CanonicalEvent], 
                     fault_config: FaultConfig,
                     node_id: str) -> List[CanonicalEvent]:
        """Apply specific fault type to events"""
        
        if fault_config.fault_type == FaultType.PAYLOAD_MUTATION:
            return self._apply_payload_mutation(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.EVENT_TYPE_SUBSTITUTION:
            return self._apply_event_type_substitution(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.SEQUENCE_MANIPULATION:
            return self._apply_sequence_manipulation(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.FIELD_DELETION:
            return self._apply_field_deletion(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.FIELD_ALTERATION:
            return self._apply_field_alteration(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.HASH_CORRUPTION:
            return self._apply_hash_corruption(events, fault_config, node_id)
        elif fault_config.fault_type == FaultType.STRUCTURED_CORRUPTION:
            return self._apply_structured_corruption(events, fault_config, node_id)
        else:
            raise ValueError(f"Unsupported fault type: {fault_config.fault_type}")
    
    def _apply_payload_mutation(self, 
                               events: List[CanonicalEvent], 
                               fault_config: FaultConfig,
                               node_id: str) -> List[CanonicalEvent]:
        """Apply payload mutation fault"""
        corrupted_events = []
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            # Apply mutation based on severity
            if self._should_apply_fault(i, fault_config.severity):
                if event_dict.get("payload"):
                    payload = event_dict["payload"].copy()
                    if isinstance(payload, dict):
                        # Mutate payload in deterministic way
                        mutation_key = f"byzantine_mutation_{node_id}_{i}"
                        payload[mutation_key] = f"corrupted_by_{node_id}"
                        
                        # If kind.ref exists, corrupt it too
                        if "kind" in payload and isinstance(payload["kind"], dict):
                            if "ref" in payload["kind"] and isinstance(payload["kind"]["ref"], dict):
                                payload["kind"]["ref"]["byzantine_corruption"] = True
                                payload["kind"]["ref"]["corruption_source"] = node_id
                        
                        event_dict["payload"] = payload
                        # Recompute payload hash
                        event_dict["payload_hash"] = stable_hash(canonical_json(payload))
            
            # Always modify event_id to ensure uniqueness
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_event_type_substitution(self, 
                                      events: List[CanonicalEvent], 
                                      fault_config: FaultConfig,
                                      node_id: str) -> List[CanonicalEvent]:
        """Apply event type substitution fault"""
        corrupted_events = []
        
        # Deterministic event type mapping
        type_mappings = fault_config.fault_parameters.get("type_mappings", {
            "telemetry_ingested": "safety_gate_evaluated",
            "safety_gate_evaluated": "approval_requested", 
            "approval_requested": "action_executed",
            "action_executed": "telemetry_ingested"
        })
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                original_type = event_dict.get("event_type")
                if original_type in type_mappings:
                    event_dict["event_type"] = type_mappings[original_type]
                else:
                    # Default corruption
                    event_dict["event_type"] = f"{original_type}_corrupted_by_{node_id}"
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_sequence_manipulation(self, 
                                    events: List[CanonicalEvent], 
                                    fault_config: FaultConfig,
                                    node_id: str) -> List[CanonicalEvent]:
        """Apply sequence manipulation fault"""
        corrupted_events = []
        
        manipulation_type = fault_config.fault_parameters.get("manipulation_type", "offset")
        offset = fault_config.fault_parameters.get("offset", 1000)
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                if event_dict.get("sequence_number") is not None:
                    if manipulation_type == "offset":
                        event_dict["sequence_number"] += offset
                    elif manipulation_type == "reverse":
                        event_dict["sequence_number"] = len(events) - i
                    elif manipulation_type == "random":
                        # Deterministic pseudo-random based on seed and node
                        seed_value = hash(f"{self._rng_seed}_{node_id}_{i}")
                        event_dict["sequence_number"] = abs(seed_value) % (len(events) * 2)
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_field_deletion(self, 
                             events: List[CanonicalEvent], 
                             fault_config: FaultConfig,
                             node_id: str) -> List[CanonicalEvent]:
        """Apply field deletion fault"""
        corrupted_events = []
        
        fields_to_delete = fault_config.fault_parameters.get("fields_to_delete", ["tenant_id", "cell_id"])
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                for field in fields_to_delete:
                    if field in event_dict and field != "payload":  # Never delete required payload
                        del event_dict[field]
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_field_alteration(self, 
                               events: List[CanonicalEvent], 
                               fault_config: FaultConfig,
                               node_id: str) -> List[CanonicalEvent]:
        """Apply field alteration fault"""
        corrupted_events = []
        
        alterations = fault_config.fault_parameters.get("alterations", {
            "tenant_id": f"corrupted_{node_id}",
            "cell_id": f"byzantine_{node_id}"
        })
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                for field, new_value in alterations.items():
                    if field in event_dict:
                        event_dict[field] = new_value
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_hash_corruption(self, 
                              events: List[CanonicalEvent], 
                              fault_config: FaultConfig,
                              node_id: str) -> List[CanonicalEvent]:
        """Apply hash corruption fault"""
        corrupted_events = []
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                # Corrupt payload_hash to make it inconsistent
                if "payload_hash" in event_dict:
                    event_dict["payload_hash"] = f"corrupted_hash_{node_id}_{i}"
                
                # Corrupt event_id hash
                if "event_id" in event_dict:
                    event_dict["event_id"] = f"{event_dict['event_id']}_hash_corrupted"
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _apply_structured_corruption(self, 
                                    events: List[CanonicalEvent], 
                                    fault_config: FaultConfig,
                                    node_id: str) -> List[CanonicalEvent]:
        """Apply structured corruption - combination of multiple fault types"""
        corrupted_events = []
        
        for i, event in enumerate(events):
            event_dict = event.to_dict()
            
            if self._should_apply_fault(i, fault_config.severity):
                # Apply multiple corruption types
                corruption_level = fault_config.fault_parameters.get("corruption_level", "medium")
                
                if corruption_level in ["medium", "high"]:
                    # Corrupt payload
                    if event_dict.get("payload"):
                        payload = event_dict["payload"].copy()
                        if isinstance(payload, dict):
                            payload["structured_corruption"] = {
                                "source": node_id,
                                "level": corruption_level,
                                "event_index": i
                            }
                        event_dict["payload"] = payload
                
                if corruption_level == "high":
                    # Corrupt event type
                    if event_dict.get("event_type"):
                        event_dict["event_type"] = f"corrupted_{event_dict['event_type']}"
                    
                    # Corrupt sequence
                    if event_dict.get("sequence_number") is not None:
                        event_dict["sequence_number"] += 10000
            
            event_dict["event_id"] = f"{event_dict['event_id']}_byzantine_{node_id}"
            
            corrupted_events.append(CanonicalEvent(**event_dict))
        
        return corrupted_events
    
    def _should_apply_fault(self, event_index: int, severity: float) -> bool:
        """Deterministically decide whether to apply fault to an event"""
        if severity >= 1.0:
            return True
        elif severity <= 0.0:
            return False
        else:
            # Deterministic decision based on event index and severity
            # Use modulo to ensure deterministic behavior
            threshold = int(severity * 100)
            return (event_index % 100) < threshold


class ByzantineScenarioGenerator:
    """Generator for predefined Byzantine fault scenarios"""
    
    @staticmethod
    def create_scenario(scenario: ByzantineScenario, 
                       node_count: int,
                       deterministic_seed: int = 42) -> List[FaultConfig]:
        """
        Create fault configuration for a given scenario
        
        Args:
            scenario: Byzantine scenario type
            node_count: Total number of nodes in the system
            deterministic_seed: Seed for deterministic behavior
            
        Returns:
            List of fault configurations
        """
        if scenario == ByzantineScenario.CLEAN:
            return []
        
        elif scenario == ByzantineScenario.SINGLE_NODE:
            # Corrupt 1 node
            target_node = f"node-{(deterministic_seed % node_count) + 1}"
            return [
                FaultConfig(
                    fault_type=FaultType.PAYLOAD_MUTATION,
                    target_nodes=[target_node],
                    severity=1.0,
                    deterministic_seed=deterministic_seed
                )
            ]
        
        elif scenario == ByzantineScenario.PARTIAL:
            # Corrupt f < n/3 nodes
            faulty_count = max(1, node_count // 3 - 1)
            target_nodes = []
            for i in range(faulty_count):
                node_id = f"node-{((deterministic_seed + i) % node_count) + 1}"
                target_nodes.append(node_id)
            
            return [
                FaultConfig(
                    fault_type=FaultType.STRUCTURED_CORRUPTION,
                    target_nodes=target_nodes,
                    severity=0.8,
                    deterministic_seed=deterministic_seed,
                    fault_parameters={"corruption_level": "medium"}
                )
            ]
        
        elif scenario == ByzantineScenario.MAJORITY:
            # Corrupt f >= n/2 nodes
            faulty_count = (node_count // 2) + 1
            target_nodes = []
            used_nodes = set()
            for i in range(faulty_count):
                node_id = f"node-{((deterministic_seed + i) % node_count) + 1}"
                # Ensure we don't duplicate nodes
                while node_id in used_nodes:
                    node_id = f"node-{((deterministic_seed + i + node_count) % node_count) + 1}"
                used_nodes.add(node_id)
                target_nodes.append(node_id)
            
            return [
                FaultConfig(
                    fault_type=FaultType.STRUCTURED_CORRUPTION,
                    target_nodes=target_nodes,
                    severity=1.0,
                    deterministic_seed=deterministic_seed,
                    fault_parameters={"corruption_level": "high"}
                )
            ]
        
        else:
            raise ValueError(f"Unsupported scenario: {scenario}")


class ByzantineTestRunner:
    """Complete Byzantine fault testing framework"""
    
    def __init__(self, node_count: int = 3, deterministic_seed: int = 42):
        """
        Initialize Byzantine test runner
        
        Args:
            node_count: Number of nodes to simulate
            deterministic_seed: Seed for deterministic behavior
        """
        self.node_count = node_count
        self.deterministic_seed = deterministic_seed
        self.verifier = MultiNodeReplayVerifier(node_count=node_count)
        self.fault_injector = ByzantineFaultInjector(deterministic_seed)
        self.logger = logging.getLogger(__name__)
    
    def run_byzantine_test(self,
                          base_events: List[CanonicalEvent],
                          scenario: ByzantineScenario,
                          custom_fault_configs: Optional[List[FaultConfig]] = None) -> ByzantineTestResult:
        """
        Run complete Byzantine fault test
        
        Args:
            base_events: Base canonical events
            scenario: Byzantine scenario to test
            custom_fault_configs: Optional custom fault configurations
            
        Returns:
            Complete Byzantine test result
        """
        # Get fault configurations
        if custom_fault_configs:
            fault_configs = custom_fault_configs
        else:
            fault_configs = ByzantineScenarioGenerator.create_scenario(
                scenario, self.node_count, self.deterministic_seed
            )
        
        # Generate baseline hash for clean execution
        baseline_report = self.verifier.verify_consensus(base_events, "baseline")
        baseline_hash = None
        if baseline_report.consensus_result == ConsensusResult.CONSENSUS:
            baseline_hash = list(baseline_report.node_hashes.values())[0]
        
        # Inject faults
        injection_results = self.fault_injector.inject_faults(base_events, fault_configs)
        
        # Prepare node inputs for verifier
        node_inputs = {}
        for i in range(self.node_count):
            node_id = f"node-{i+1}"
            if node_id in injection_results:
                node_inputs[node_id] = injection_results[node_id].corrupted_events
            else:
                # Use original events for non-faulty nodes
                node_inputs[node_id] = [
                    CanonicalEvent(**event.to_dict()) for event in base_events
                ]
        
        # Run consensus verification with faults
        divergence_report = self.verifier.verify_consensus(
            base_events, "byzantine_test", node_inputs
        )
        
        # Create comprehensive result
        result = ByzantineTestResult(
            scenario=scenario,
            fault_configs=fault_configs,
            injection_results=list(injection_results.values()),
            divergence_report=divergence_report,
            baseline_hash=baseline_hash
        )
        
        self.logger.info(f"Byzantine test complete: {scenario.value} -> {divergence_report.consensus_result.value}")
        
        return result
    
    def validate_byzantine_correctness(self, result: ByzantineTestResult) -> bool:
        """
        Validate that Byzantine test results are correct
        
        Args:
            result: Byzantine test result to validate
            
        Returns:
            True if test behaved correctly
        """
        scenario = result.scenario
        consensus_achieved = result.divergence_report.consensus_result == ConsensusResult.CONSENSUS
        faulty_nodes = len(result.fault_configs)
        total_nodes = len(result.divergence_report.node_hashes)
        
        if scenario == ByzantineScenario.CLEAN:
            # Clean scenario should always achieve consensus
            return consensus_achieved
        
        elif scenario == ByzantineScenario.SINGLE_NODE:
            # Single faulty node should cause divergence
            expected_divergence = faulty_nodes < (total_nodes - faulty_nodes)
            return consensus_achieved == (not expected_divergence)
        
        elif scenario == ByzantineScenario.PARTIAL:
            # Partial corruption (f < n/3) should cause divergence
            expected_divergence = faulty_nodes >= 1
            return consensus_achieved == (not expected_divergence)
        
        elif scenario == ByzantineScenario.MAJORITY:
            # Majority corruption should never achieve consensus
            return not consensus_achieved
        
        return False
