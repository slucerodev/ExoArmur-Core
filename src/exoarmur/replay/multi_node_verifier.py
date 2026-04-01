"""
Multi-Node Replay Verifier for deterministic consensus validation

Implements isolation guarantees and deterministic hash comparison across
independent replay node executions.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from .canonical_utils import canonical_json, stable_hash
from .event_envelope import CanonicalEvent
from .replay_engine import ReplayEngine, ReplayReport

logger = logging.getLogger(__name__)


class ConsensusResult(Enum):
    """Consensus outcome status"""
    CONSENSUS = "consensus"
    DIVERGENCE = "divergence"
    ERROR = "error"


class VerificationError(Exception):
    """Exception raised when verification fails due to invalid data or state"""
    pass


@dataclass(frozen=True)
class NodeResult:
    """Deterministic result from a single replay node execution"""
    
    node_id: str
    correlation_id: str
    replay_report: ReplayReport
    canonical_output: str
    output_hash: str
    
    def __post_init__(self):
        # Ensure canonical output is deterministic
        if not isinstance(object.__getattribute__(self, 'canonical_output'), str):
            raise ValueError("canonical_output must be a string")
        
        # Verify hash matches canonical output
        computed_hash = stable_hash(object.__getattribute__(self, 'canonical_output'))
        stored_hash = object.__getattribute__(self, 'output_hash')
        if computed_hash != stored_hash:
            raise ValueError(f"Hash mismatch: computed {computed_hash}, stored {stored_hash}")


@dataclass(frozen=True)
class DivergenceReport:
    """Structured divergence analysis report"""
    
    consensus_result: ConsensusResult
    node_hashes: Dict[str, str]
    divergent_nodes: List[str]
    canonical_outputs: Dict[str, str]
    divergence_details: Dict[str, Any] = field(default_factory=dict)
    
    def has_divergence(self) -> bool:
        """Check if any divergence was detected"""
        return self.consensus_result == ConsensusResult.DIVERGENCE
    
    def get_consensus_nodes(self) -> List[str]:
        """Get nodes that agree with the majority hash"""
        if not self.node_hashes:
            return []
        
        # Count hash frequencies
        hash_counts = {}
        for node_id, node_hash in self.node_hashes.items():
            hash_counts[node_hash] = hash_counts.get(node_hash, 0) + 1
        
        # Find majority hash
        majority_hash = max(hash_counts.items(), key=lambda x: x[1])[0]
        
        # Return nodes with majority hash
        return [node_id for node_id, node_hash in self.node_hashes.items() 
                if node_hash == majority_hash]


@dataclass
class MultiNodeReplayVerifier:
    """Deterministic multi-node replay verifier with isolation guarantees"""
    
    def __init__(self, node_count: int = 3):
        """
        Initialize multi-node verifier
        
        Args:
            node_count: Number of independent replay nodes to simulate
        """
        if node_count < 2:
            raise ValueError("node_count must be at least 2 for consensus validation")
        
        self.node_count = node_count
        self.logger = logging.getLogger(__name__)
    
    def verify_consensus(self, 
                        canonical_events: List[CanonicalEvent],
                        correlation_id: str,
                        node_inputs: Optional[Dict[str, List[CanonicalEvent]]] = None) -> DivergenceReport:
        """
        Run replay on multiple independent nodes and verify consensus
        
        Args:
            canonical_events: List of canonical replay events (base input)
            correlation_id: Correlation ID for replay
            node_inputs: Optional per-node input variations for testing divergence
            
        Returns:
            DivergenceReport with consensus analysis
        """
        try:
            # Generate node inputs (base or modified)
            if node_inputs is None:
                node_inputs = self._generate_identical_inputs(canonical_events)
            else:
                # Validate node_inputs structure
                if len(node_inputs) != self.node_count:
                    raise ValueError(f"node_inputs must have exactly {self.node_count} entries")
                
                # Verify all inputs are lists of CanonicalEvent
                for node_id, events in node_inputs.items():
                    if not isinstance(events, list):
                        raise ValueError(f"Node {node_id} inputs must be a list")
                    for event in events:
                        if not isinstance(event, CanonicalEvent):
                            raise ValueError(f"Node {node_id} contains non-CanonicalEvent input")
            
            # Execute replay on each node independently
            node_results = self._execute_isolated_replays(node_inputs, correlation_id)
            
            # Analyze consensus
            divergence_report = self._analyze_consensus(node_results)
            
            self.logger.info(f"Multi-node verification complete for {correlation_id}: "
                           f"Result={divergence_report.consensus_result.value}")
            
            return divergence_report
            
        except Exception as e:
            self.logger.error(f"Multi-node verification failed for {correlation_id}: {e}")
            # Return error report
            return DivergenceReport(
                consensus_result=ConsensusResult.ERROR,
                node_hashes={},
                divergent_nodes=[],
                canonical_outputs={},
                divergence_details={"error": str(e)}
            )
    
    def _generate_identical_inputs(self, canonical_events: List[CanonicalEvent]) -> Dict[str, List[CanonicalEvent]]:
        """Generate identical inputs for all nodes (consensus test)"""
        node_inputs = {}
        for i in range(self.node_count):
            node_id = f"node-{i+1}"
            # Create deep copies to ensure no shared mutable state
            node_inputs[node_id] = [
                CanonicalEvent(**event.to_dict()) for event in canonical_events
            ]
        return node_inputs
    
    def _execute_isolated_replays(self, 
                                  node_inputs: Dict[str, List[CanonicalEvent]], 
                                  correlation_id: str) -> List[NodeResult]:
        """Execute replay on each node with complete isolation"""
        node_results = []
        
        for node_id, events in node_inputs.items():
            try:
                # Create isolated replay engine for this node
                audit_store = {correlation_id: events}
                replay_engine = ReplayEngine(audit_store=audit_store)
                
                # Execute replay
                replay_report = replay_engine.replay_correlation(correlation_id)
                
                # Generate canonical output
                canonical_output = canonical_json(replay_report.to_dict())
                output_hash = stable_hash(canonical_output)
                
                # Create node result
                node_result = NodeResult(
                    node_id=node_id,
                    correlation_id=correlation_id,
                    replay_report=replay_report,
                    canonical_output=canonical_output,
                    output_hash=output_hash
                )
                
                node_results.append(node_result)
                
                self.logger.debug(f"Node {node_id} replay completed: hash={output_hash[:8]}...")
                
            except Exception as e:
                self.logger.error(f"Node {node_id} replay failed: {e}")
                # Continue with other nodes but record the error
                raise RuntimeError(f"Node {node_id} execution failed: {e}") from e
        
        return node_results
    
    def _analyze_consensus(self, node_results: List[NodeResult]) -> DivergenceReport:
        """Analyze consensus across node results"""
        if not node_results:
            return DivergenceReport(
                consensus_result=ConsensusResult.ERROR,
                node_hashes={},
                divergent_nodes=[],
                canonical_outputs={},
                divergence_details={"error": "No node results available"}
            )
        
        # Collect hashes and outputs
        node_hashes = {}
        canonical_outputs = {}
        
        for result in node_results:
            node_hashes[result.node_id] = result.output_hash
            canonical_outputs[result.node_id] = result.canonical_output
        
        # Check if all hashes are identical
        unique_hashes = set(node_hashes.values())
        
        if len(unique_hashes) == 1:
            # Consensus achieved
            consensus_hash = list(unique_hashes)[0]
            self.logger.info(f"Consensus achieved: {len(node_results)} nodes agree on hash {consensus_hash[:8]}...")
            
            return DivergenceReport(
                consensus_result=ConsensusResult.CONSENSUS,
                node_hashes=node_hashes,
                divergent_nodes=[],  # No divergence
                canonical_outputs=canonical_outputs,
                divergence_details={"consensus_hash": consensus_hash}
            )
        
        else:
            # Divergence detected
            self.logger.warning(f"Divergence detected: {len(unique_hashes)} different hashes across {len(node_results)} nodes")
            
            # Find divergent nodes (nodes not in majority)
            hash_counts = {}
            for node_hash in node_hashes.values():
                hash_counts[node_hash] = hash_counts.get(node_hash, 0) + 1
            
            majority_hash = max(hash_counts.items(), key=lambda x: x[1])[0]
            divergent_nodes = [
                node_id for node_id, node_hash in node_hashes.items()
                if node_hash != majority_hash
            ]
            
            # Detailed divergence analysis
            divergence_details = {
                "majority_hash": majority_hash,
                "hash_distribution": hash_counts,
                "divergent_hash_count": len(unique_hashes) - 1,
                "majority_node_count": hash_counts[majority_hash],
                "divergent_node_count": len(divergent_nodes)
            }
            
            return DivergenceReport(
                consensus_result=ConsensusResult.DIVERGENCE,
                node_hashes=node_hashes,
                divergent_nodes=divergent_nodes,
                canonical_outputs=canonical_outputs,
                divergence_details=divergence_details
            )
    
    def inject_divergence(self, 
                         base_events: List[CanonicalEvent], 
                         target_node: str,
                         divergence_type: str = "payload") -> Dict[str, List[CanonicalEvent]]:
        """
        Inject controlled divergence for testing
        
        Args:
            base_events: Base canonical events
            target_node: Node ID to inject divergence into
            divergence_type: Type of divergence to inject ("payload", "event_type", "sequence")
            
        Returns:
            Modified node inputs with injected divergence
        """
        node_inputs = self._generate_identical_inputs(base_events)
        
        if target_node not in node_inputs:
            raise ValueError(f"Target node {target_node} not found")
        
        # Create modified events for target node
        modified_events = []
        for i, event in enumerate(node_inputs[target_node]):
            event_dict = event.to_dict()
            
            if divergence_type == "payload" and event_dict.get("payload"):
                # Modify payload slightly in a way that affects replay processing
                payload = event_dict["payload"].copy()
                if isinstance(payload, dict):
                    # Add a divergence marker that will be preserved in replay output
                    payload["divergence_marker"] = f"modified_for_{target_node}"
                    # Also modify a field that replay engine actually processes
                    if "ref" in payload and isinstance(payload["ref"], dict):
                        payload["ref"]["divergence_injected"] = True
                    event_dict["payload"] = payload
                    # Recompute payload hash
                    event_dict["payload_hash"] = stable_hash(canonical_json(payload))
            
            elif divergence_type == "event_type" and event_dict.get("event_type"):
                # Modify event type to something that will be processed differently
                original_type = event_dict["event_type"]
                # Change to a different known event type
                if original_type == "telemetry_ingested":
                    event_dict["event_type"] = "safety_gate_evaluated"
                elif original_type == "safety_gate_evaluated":
                    event_dict["event_type"] = "approval_requested"
                else:
                    event_dict["event_type"] = f"{original_type}_modified"
            
            elif divergence_type == "sequence" and event_dict.get("sequence_number") is not None:
                # Modify sequence number to affect ordering
                event_dict["sequence_number"] = event_dict["sequence_number"] + 1000
            
            # Also modify event_id to ensure uniqueness and divergence
            event_dict["event_id"] = f"{event_dict['event_id']}_divergent_{target_node}"
            
            modified_events.append(CanonicalEvent(**event_dict))
        
        node_inputs[target_node] = modified_events
        
        self.logger.info(f"Injected {divergence_type} divergence into node {target_node}")
        
        return node_inputs
