"""
ExoArmur ADMO Replay System
Deterministic audit replay for organism verification
"""

from .canonical_utils import canonical_json, stable_hash
from .event_envelope import AuditEventEnvelope, EventTypePriority, CanonicalEvent
from .replay_engine import ReplayEngine, ReplayReport, ReplayResult
from .multi_node_verifier import (
    MultiNodeReplayVerifier,
    ConsensusResult,
    NodeResult,
    DivergenceReport
)
from .byzantine_fault_injection import (
    FaultInjector,
    CorruptionScenarioGenerator,
    FaultInjectionTestRunner,
    FaultType,
    CorruptionScenario,
    FaultConfig,
    FaultInjectionResult,
    FaultInjectionTestResult
)

# Backward compatibility aliases (deprecated)
ByzantineFaultInjector = FaultInjector
ByzantineScenarioGenerator = CorruptionScenarioGenerator
ByzantineTestRunner = FaultInjectionTestRunner
ByzantineScenario = CorruptionScenario
ByzantineTestResult = FaultInjectionTestResult

__all__ = [
    'canonical_json',
    'stable_hash',
    'AuditEventEnvelope',
    'EventTypePriority',
    'CanonicalEvent',
    'ReplayEngine',
    'ReplayReport',
    'ReplayResult',
    'MultiNodeReplayVerifier',
    'ConsensusResult',
    'NodeResult',
    'DivergenceReport',
    # New names (preferred)
    'FaultInjector',
    'CorruptionScenarioGenerator',
    'FaultInjectionTestRunner',
    'FaultType',
    'CorruptionScenario',
    'FaultConfig',
    'FaultInjectionResult',
    'FaultInjectionTestResult',
    # Deprecated aliases for backward compatibility
    'ByzantineFaultInjector',
    'ByzantineScenarioGenerator',
    'ByzantineTestRunner',
    'ByzantineScenario',
    'ByzantineTestResult',
]
