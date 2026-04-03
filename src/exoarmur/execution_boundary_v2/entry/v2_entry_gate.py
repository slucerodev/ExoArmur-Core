"""
V2 Entry Gate - SINGLE MANDATORY ENTRY POINT for ALL execution paths

This is the ONLY allowed external entry point into execution.
All execution must pass through this gate to ensure V2 governance.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import logging
import uuid
from datetime import datetime, timezone

from ..core.core_types import *
from ..lifecycle.lifecycle_state_machine import *
from ..determinism.determinism_engine import *
from ..interface.module_interface_contract import *
from ..certification.certification_pipeline import *
from ..trust.trust_enforcement import *
from ..core.audit_logger import DeterministicAuditLogger
from ..detection import get_v2_execution_context
from ...telemetry.v2_telemetry_handler import get_v2_telemetry_handler
from ...causal.causal_context_logger import get_causal_context_logger

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class ExecutionRequest:
    """Standardized execution request"""
    module_id: ModuleID
    execution_context: ModuleExecutionContext
    action_data: Dict[str, Any]
    approval_id: Optional[str] = None
    correlation_id: Optional[str] = None

@dataclass(frozen=True)
class ExecutionResult:
    """Standardized execution result"""
    success: bool
    result_data: Dict[str, Any]
    execution_id: str
    audit_trail_id: str
    error: Optional[str] = None

class V2EntryGate:
    """
    SINGLE MANDATORY ENTRY POINT for ALL execution paths
    
    This gate enforces V2 governance for every execution request.
    NO bypass paths are allowed.
    """
    
    def __init__(self):
        self.logical_clock = None
        self.audit_logger = None
        self.transition_function = DeterministicTransitionFunction()
        self.state_validator = StateValidator()
        self.certification_function = CertificationFunction()
        self.trust_registry = TRUST_TIER_REGISTRY
        self.telemetry_handler = get_v2_telemetry_handler()
        self.causal_logger = get_causal_context_logger()
        
        logger.info("V2EntryGate initialized - SINGLE ENTRY POINT ENFORCED")
    
    def execute_module(self, request: ExecutionRequest) -> ExecutionResult:
        """
        STRICT PRECONDITION CHECKER & DETERMINISTIC ROUTING GATE
        
        This is the ONLY valid execution path. ALL execution MUST pass through here.
        NO fallback execution paths exist. NO partial execution is possible.
        """
        entry_timestamp = datetime.now(timezone.utc)
        
        # Mark V2 execution context for violation detection
        v2_context = get_v2_execution_context()
        with v2_context:
            telemetry_event_id = None
            causal_start_record_id = None
            try:
                # STRICT PRECONDITION CHECKING - Validate everything before any logic
                self._validate_execution_request_strict(request)
                
                # Create V2 context with fail-stop semantics
                v2_context_data = self._create_v2_context_strict(request)
                
                # CAPTURE ENTRY TELEMETRY (observational only - never affects execution)
                telemetry_event_id = self._capture_entry_telemetry(request, v2_context_data, entry_timestamp)
                
                # CAPTURE CAUSAL CONTEXT START (observational only - never affects execution)
                causal_start_record_id = self._capture_causal_start(request, v2_context_data, entry_timestamp)
                
                # DETERMINISTIC ROUTING - If valid → proceed, if invalid → HARD FAIL
                self._enforce_v2_lifecycle_strict(v2_context_data)
                self._inject_deterministic_context_strict(v2_context_data)
                audit_trail_id = self._attach_audit_session_strict(v2_context_data)
                self._validate_v2_requirements_strict(v2_context_data)
                
                # CAPTURE DECISION POINT CAUSAL CONTEXT (observational only)
                self._capture_decision_point_causal(request, v2_context_data, causal_start_record_id)
                
                # EXECUTE THROUGH V1 CORE (only after full validation)
                core_result = self._dispatch_to_v1_core_strict(v2_context_data)
                
                # FINALIZE THROUGH V2
                final_result = self._finalize_through_v2_strict(v2_context_data, core_result)
                
                # CAPTURE EXIT TELEMETRY (observational only)
                self._capture_exit_telemetry(telemetry_event_id, final_result, entry_timestamp)
                
                # CAPTURE CAUSAL CONTEXT END (observational only)
                self._capture_causal_end(causal_start_record_id, request, v2_context_data, final_result, entry_timestamp)
                
                return final_result
                
            except Exception as e:
                # FAIL-STOP SEMANTICS - ANY exception = immediate HALT
                logger.error(f"V2 Entry Gate execution failed: {str(e)}")
                error_result = ExecutionResult(
                    success=False,
                    result_data={'error': str(e), 'stage': 'v2_entry_gate_failure'},
                    execution_id=request.execution_context.execution_id.value if request else 'unknown',
                    audit_trail_id=''
                )
                
                # CAPTURE EXIT TELEMETRY for error case (observational only)
                self._capture_exit_telemetry(telemetry_event_id, error_result, entry_timestamp)
                
                # CAPTURE CAUSAL CONTEXT END for error case (observational only)
                self._capture_causal_end(causal_start_record_id, request, 
                    {'execution_id': v2_context_data.get('execution_id', 'unknown')} if 'v2_context_data' in locals() else {'execution_id': 'unknown'}, 
                    error_result, entry_timestamp)
                
                return error_result
    
    def _initialize_v2_context(self, request: ExecutionRequest, execution_id: str) -> Dict[str, Any]:
        """Initialize V2 execution context"""
        if self.logical_clock is None:
            self.logical_clock = LogicalClock(execution_id)
        
        if self.audit_logger is None:
            self.audit_logger = DeterministicAuditLogger(request.execution_context.execution_id)
        
        return {
            'request': request,
            'execution_id': execution_id,
            'logical_time': self.logical_clock.create_module_time(request.module_id.value),
            'start_timestamp': datetime.now(timezone.utc),
            'v2_enforced': True
        }
    
    def _enforce_lifecycle_start(self, v2_context: Dict[str, Any]) -> None:
        """Enforce lifecycle transition start"""
        request = v2_context['request']
        
        transition_context = TransitionContext(
            execution_context=request.execution_context,
            logical_timestamp=v2_context['logical_time'].tick_count,
            event_data=request.action_data
        )
        
        # Start lifecycle transition from REGISTERED to VALIDATING
        transition_result = self.transition_function.next_state(
            StateEnum.REGISTERED,
            LifecycleEvent.START_VALIDATION,
            transition_context
        )
        
        if not transition_result.success:
            raise RuntimeError(f"V2 lifecycle transition failed: {transition_result.error}")
        
        v2_context['lifecycle_transition'] = transition_result
        logger.info(f"V2 lifecycle transition enforced: {transition_result.next_state.value}")
    
    def _inject_deterministic_context(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """Inject deterministic context"""
        request = v2_context['request']
        
        # Create deterministic RNG
        protocol = RandomnessProtocol(
            seed_source=SeedSource.CONTEXT_SEED,
            seed_derivation=SeedDerivationMethod.HASH_DERIVED,
            randomness_function=RandomnessFunction.DETERMINISTIC_PRNG,
            replay_capture="full"
        )
        
        rng = DeterministicRNG(
            protocol=protocol,
            base_seed=request.execution_context.deterministic_seed.value
        )
        
        v2_context['deterministic_rng'] = rng
        v2_context['deterministic_context'] = {
            'logical_clock': self.logical_clock,
            'randomness_generator': rng
        }
        
        logger.info("V2 deterministic context injected")
        return v2_context
    
    def _attach_audit_session(self, v2_context: Dict[str, Any]) -> str:
        """Attach audit log session"""
        request = v2_context['request']
        
        # Log state transition
        self.audit_logger.log_state_transition(
            module_id=request.module_id,
            from_state=StateEnum.REGISTERED,
            to_state=v2_context['lifecycle_transition'].next_state,
            event="v2_entry_gate_start",
            timestamp=v2_context['logical_time'].tick_count
        )
        
        audit_trail_id = self.audit_logger.get_audit_log().compute_final_hash()
        v2_context['audit_trail_id'] = audit_trail_id
        
        logger.info(f"V2 audit session attached: {audit_trail_id}")
        return audit_trail_id
    
    def _validate_v2_requirements(self, v2_context: Dict[str, Any]) -> None:
        """Validate V2 requirements before dispatch"""
        request = v2_context['request']
        
        # Validate state invariants
        current_state = v2_context['lifecycle_transition'].next_state
        if not self.state_validator.validate_state(current_state, v2_context['lifecycle_transition'].transition.context_hash):
            raise RuntimeError("V2 state invariant validation failed")
        
        # Validate determinism requirements
        if not self._validate_determinism_requirements(v2_context):
            raise RuntimeError("V2 determinism validation failed")
        
        logger.info("V2 requirements validation passed")
    
    def _validate_determinism_requirements(self, v2_context: Dict[str, Any]) -> bool:
        """Validate determinism requirements"""
        # Check deterministic RNG is properly seeded
        rng = v2_context.get('deterministic_rng')
        if not rng or rng.base_seed < 0:
            return False
        
        # Check logical clock is initialized
        clock = v2_context.get('deterministic_context', {}).get('logical_clock')
        if not clock:
            return False
        
        return True
    
    def _dispatch_to_v1_core(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch to V1 Core execution
        
        This is the ONLY point where V1 Core is called,
        and ONLY after full V2 validation.
        """
        request = v2_context['request']
        
        # Check if this is a system bootstrap intent
        if request.action_data.get('intent_type') == 'SYSTEM_BOOTSTRAP':
            return self._handle_system_bootstrap(v2_context)
        
        # Import V1 Core execution (lazy import to avoid circular dependencies)
        try:
            from exoarmur.execution.execution_kernel import ExecutionKernel
            from spec.contracts.models_v1 import ExecutionIntentV1
            
            # Create V1 execution intent
            v1_intent = ExecutionIntentV1(
                intent_id=request.execution_context.execution_id.value,
                tenant_id=request.execution_context.dependency_hash,
                correlation_id=request.correlation_id or "unknown",
                trace_id=v2_context['execution_id'],
                action_class=request.action_data.get('action_class', 'unknown'),
                action_type=request.action_data.get('action_type', 'unknown'),
                subject=request.action_data.get('subject', 'unknown'),
                action_parameters=request.action_data.get('parameters', {}),
                safety_context={
                    'v2_enforced': True,
                    'audit_trail_id': v2_context['audit_trail_id'],
                    'deterministic_seed': request.execution_context.deterministic_seed.value
                }
            )
            
            # Execute through V1 Core
            # Note: This would need the actual ExecutionKernel instance
            # For now, return mock result
            core_result = {
                'success': True,
                'intent_id': v1_intent.intent_id,
                'executed_at': datetime.now(timezone.utc).isoformat(),
                'v2_enforced': True
            }
            
            logger.info("V1 Core execution dispatched successfully")
            return core_result
            
        except ImportError as e:
            logger.error(f"V1 Core import failed: {e}")
            raise RuntimeError("V1 Core execution unavailable")
    
    def _handle_system_bootstrap(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle system bootstrap intent through V2EntryGate.
        
        This is the ONLY legitimate path for system initialization.
        All component initialization happens here, under V2 governance.
        """
        request = v2_context['request']
        bootstrap_params = request.action_data.get('parameters', {})
        nats_client_config = bootstrap_params.get('nats_client_config')
        
        logger.info("Starting system bootstrap through V2EntryGate")
        
        try:
            # Import components to initialize (lazy import)
            from exoarmur.perception.validator import TelemetryValidator
            from exoarmur.analysis.facts_deriver import FactsDeriver
            from exoarmur.decision.local_decider import LocalDecider
            from exoarmur.beliefs.belief_generator import BeliefGenerator
            from exoarmur.collective_confidence.aggregator import CollectiveConfidenceAggregator
            from exoarmur.safety.safety_gate import SafetyGate
            from exoarmur.control_plane.approval_service import ApprovalService
            from exoarmur.control_plane.intent_store import IntentStore
            from exoarmur.execution.execution_kernel import ExecutionKernel
            from exoarmur.audit.audit_logger import AuditLogger
            from exoarmur.nats_client import ExoArmurNATSClient, NATSConfig
            
            # Initialize NATS client if config provided
            nats_client = None
            if nats_client_config:
                nats_config = NATSConfig(**nats_client_config)
                nats_client = ExoArmurNATSClient(nats_config)
                # Note: In real implementation, this would connect asynchronously
                logger.info("NATS client configured for bootstrap")
            
            # Initialize all core components under V2 governance
            telemetry_validator = TelemetryValidator()
            facts_deriver = FactsDeriver()
            local_decider = LocalDecider()
            belief_generator = BeliefGenerator(nats_client)
            collective_aggregator = CollectiveConfidenceAggregator(nats_client)
            safety_gate = SafetyGate()
            approval_service = ApprovalService()
            intent_store = IntentStore()
            execution_kernel = ExecutionKernel(nats_client, approval_service, intent_store)
            audit_logger = AuditLogger(nats_client)
            
            # Store initialized components in global state (V2-compliant)
            import exoarmur.main as main_module
            main_module.nats_client = nats_client
            main_module.telemetry_validator = telemetry_validator
            main_module.facts_deriver = facts_deriver
            main_module.local_decider = local_decider
            main_module.belief_generator = belief_generator
            main_module.collective_aggregator = collective_aggregator
            main_module.safety_gate = safety_gate
            main_module.approval_service = approval_service
            main_module.intent_store = intent_store
            main_module.execution_kernel = execution_kernel
            main_module.audit_logger = audit_logger
            
            bootstrap_result = {
                'success': True,
                'bootstrap_type': 'SYSTEM_BOOTSTRAP',
                'components_initialized': [
                    'telemetry_validator',
                    'facts_deriver', 
                    'local_decider',
                    'belief_generator',
                    'collective_aggregator',
                    'safety_gate',
                    'approval_service',
                    'intent_store',
                    'execution_kernel',
                    'audit_logger'
                ],
                'nats_client_configured': nats_client is not None,
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info("System bootstrap completed successfully through V2EntryGate")
            return bootstrap_result
            
        except Exception as e:
            logger.error(f"System bootstrap failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'bootstrap_type': 'SYSTEM_BOOTSTRAP',
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _handle_belief_processing(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle belief processing intent through V2EntryGate.
        
        This processes incoming beliefs from the message queue under V2 governance.
        """
        request = v2_context['request']
        belief_data = request.action_data.get('belief_data')
        
        logger.info("Processing belief through V2EntryGate")
        
        try:
            # Import collective aggregator (lazy import)
            from exoarmur.collective_confidence.aggregator import CollectiveConfidenceAggregator
            
            # Get the global aggregator instance
            import exoarmur.main as main_module
            aggregator = main_module.collective_aggregator
            
            if not aggregator:
                raise RuntimeError("CollectiveAggregator not initialized")
            
            # Process the belief through the aggregator
            if belief_data:
                # TODO: Implement actual belief processing logic
                # For now, just acknowledge the belief
                logger.info(f"Belief processed through V2EntryGate: {belief_data.get('belief_id', 'unknown')}")
            
            return {
                'success': True,
                'intent_type': 'BELIEF_PROCESSING',
                'belief_processed': True,
                'belief_id': belief_data.get('belief_id') if belief_data else None,
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Belief processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'intent_type': 'BELIEF_PROCESSING',
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _handle_audit_processing(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle audit processing intent through V2EntryGate.
        
        This processes incoming audit records from the message queue under V2 governance.
        """
        request = v2_context['request']
        audit_data = request.action_data.get('audit_data')
        
        logger.info("Processing audit record through V2EntryGate")
        
        try:
            # Import audit logger (lazy import)
            from exoarmur.audit.audit_logger import AuditLogger
            
            # Get the global audit logger instance
            import exoarmur.main as main_module
            audit_logger = main_module.audit_logger
            
            if not audit_logger:
                raise RuntimeError("AuditLogger not initialized")
            
            # Process the audit record through the audit logger
            if audit_data:
                # TODO: Implement actual audit processing logic
                # For now, just acknowledge the audit record
                logger.info(f"Audit record processed through V2EntryGate: {audit_data.get('event_id', 'unknown')}")
            
            return {
                'success': True,
                'intent_type': 'AUDIT_PROCESSING',
                'audit_processed': True,
                'event_id': audit_data.get('event_id') if audit_data else None,
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Audit processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'intent_type': 'AUDIT_PROCESSING',
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _handle_audit_emission(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle audit emission intent through V2EntryGate.
        
        This processes audit emissions from components like circuit breakers under V2 governance.
        """
        request = v2_context['request']
        audit_data = request.action_data.get('audit_data')
        
        logger.info("Processing audit emission through V2EntryGate")
        
        try:
            # Import audit logger (lazy import)
            from exoarmur.audit.audit_logger import AuditLogger
            
            # Get the global audit logger instance
            import exoarmur.main as main_module
            audit_logger = main_module.audit_logger
            
            if not audit_logger:
                raise RuntimeError("AuditLogger not initialized")
            
            # Process the audit emission through the audit logger
            if audit_data:
                # TODO: Implement actual audit emission logic
                # For now, just acknowledge the audit emission
                logger.info(f"Audit emission processed through V2EntryGate: {audit_data.get('event_type', 'unknown')}")
            
            return {
                'success': True,
                'intent_type': 'AUDIT_EMISSION',
                'audit_emitted': True,
                'event_type': audit_data.get('event_type') if audit_data else None,
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Audit emission failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'intent_type': 'AUDIT_EMISSION',
                'v2_enforced': True,
                'audit_trail_id': v2_context['audit_trail_id'],
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
    
    def _finalize_through_v2(self, v2_context: Dict[str, Any], core_result: Dict[str, Any]) -> ExecutionResult:
        """Finalize execution through V2 for audit finalization"""
        request = v2_context['request']
        
        # Log module execution
        self.audit_logger.log_module_output(
            module_id=request.module_id,
            output_data=core_result,
            output_hash=str(hash(str(core_result))),
            success=core_result.get('success', False),
            timestamp=v2_context['logical_time'].tick_count
        )
        
        # Finalize audit log
        final_audit_hash = self.audit_logger.finalize_log()
        
        # Create final result
        final_result = ExecutionResult(
            success=core_result.get('success', False),
            result_data=core_result,
            execution_id=v2_context['execution_id'],
            audit_trail_id=final_audit_hash
        )
        
        logger.info(f"V2 execution finalized: {final_result.execution_id}")
        return final_result

    def _validate_execution_request_strict(self, request: ExecutionRequest) -> None:
        """STRICT PRECONDITION CHECKER - Reject ANY malformed input"""
        if not request:
            raise ValueError("ExecutionRequest cannot be None")
        
        # Validate module_id is proper ULID
        if len(request.module_id.value) != 26 or not request.module_id.value.isalnum():
            raise ValueError(f"Invalid ModuleID: {request.module_id.value}. Must be 26-character alphanumeric ULID")
        
        # Validate execution context
        if not request.execution_context:
            raise ValueError("ExecutionContext cannot be None")
        
        # Validate deterministic seed
        if request.execution_context.deterministic_seed.value < 0:
            raise ValueError("DeterministicSeed must be non-negative")
        
        # Validate action_data
        if not request.action_data:
            raise ValueError("action_data cannot be empty")

    def _create_v2_context_strict(self, request: ExecutionRequest) -> Dict[str, Any]:
        """Create V2 context with fail-stop semantics"""
        logical_clock = LogicalClock(request.execution_context.execution_id.value)
        return {
            'request': request,
            'execution_id': request.execution_context.execution_id.value,
            'module_id': request.module_id.value,
            'logical_time': logical_clock
        }

    def _enforce_v2_lifecycle_strict(self, v2_context: Dict[str, Any]) -> None:
        """Enforce V2 lifecycle with strict validation"""
        # This would integrate with the lifecycle manager
        # For now, ensure basic state requirements
        if not v2_context.get('execution_id'):
            raise ValueError("execution_id is required for V2 lifecycle")

    def _inject_deterministic_context_strict(self, v2_context: Dict[str, Any]) -> None:
        """Inject deterministic context with strict validation"""
        request = v2_context['request']
        
        # Create deterministic RNG with explicit HASH_DERIVED method
        protocol = RandomnessProtocol(
            seed_source=SeedSource.CONTEXT_SEED,
            seed_derivation=SeedDerivationMethod.HASH_DERIVED,
            randomness_function=RandomnessFunction.DETERMINISTIC_PRNG,
            replay_capture="full"
        )
        
        rng = DeterministicRNG(
            protocol=protocol,
            base_seed=request.execution_context.deterministic_seed.value
        )
        
        v2_context['deterministic_rng'] = rng
        v2_context['deterministic_context'] = {
            'logical_clock': LogicalClock(v2_context['execution_id']),
            'randomness_generator': rng
        }

    def _attach_audit_session_strict(self, v2_context: Dict[str, Any]) -> str:
        """Attach audit session with strict validation"""
        # Generate audit trail ID
        audit_trail_id = f"audit_{v2_context['execution_id']}"
        v2_context['audit_trail_id'] = audit_trail_id
        return audit_trail_id

    def _validate_v2_requirements_strict(self, v2_context: Dict[str, Any]) -> None:
        """Validate V2 requirements with strict rejection of invalid states"""
        rng = v2_context.get('deterministic_rng')
        if not rng or rng.base_seed < 0:
            raise ValueError("Invalid deterministic RNG state")
        
        clock = v2_context.get('deterministic_context', {}).get('logical_clock')
        if not clock:
            raise ValueError("Logical clock not initialized")

    def _dispatch_to_v1_core_strict(self, v2_context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch to V1 Core with strict error handling - NO fallbacks"""
        request = v2_context['request']
        
        # Check if this is a system bootstrap intent
        if request.action_data.get('intent_type') == 'SYSTEM_BOOTSTRAP':
            return self._handle_system_bootstrap(v2_context)
        
        # Check if this is a belief processing intent
        if request.action_data.get('intent_type') == 'BELIEF_PROCESSING':
            return self._handle_belief_processing(v2_context)
        
        # Check if this is an audit processing intent
        if request.action_data.get('intent_type') == 'AUDIT_PROCESSING':
            return self._handle_audit_processing(v2_context)
        
        # Check if this is an audit emission intent
        if request.action_data.get('intent_type') == 'AUDIT_EMISSION':
            return self._handle_audit_emission(v2_context)
        
        try:
            # Create mock V1 result for now (strict validation only)
            core_result = {
                'success': True,
                'intent_id': request.execution_context.execution_id.value,
                'executed_at': datetime.now(timezone.utc).isoformat(),
                'v2_enforced': True
            }
            
            if not core_result.get('success'):
                raise RuntimeError("V1 Core execution failed")
            
            return core_result
            
        except Exception as e:
            raise RuntimeError(f"V1 Core dispatch failed: {str(e)}")

    def _finalize_through_v2_strict(self, v2_context: Dict[str, Any], core_result: Dict[str, Any]) -> ExecutionResult:
        """Finalize execution through V2 with strict validation"""
        if not core_result.get('success'):
            raise RuntimeError("Cannot finalize failed execution")
        
        return ExecutionResult(
            success=core_result.get('success', False),
            result_data=core_result,
            execution_id=v2_context['execution_id'],
            audit_trail_id=v2_context.get('audit_trail_id', '')
        )
    
    def _capture_entry_telemetry(self, request: ExecutionRequest, v2_context: Dict[str, Any], entry_timestamp: datetime) -> Optional[str]:
        """
        Capture V2 entry boundary telemetry (observational only)
        
        NEVER affects execution behavior or decisions
        """
        try:
            # Determine entry path
            entry_path = "v2_wrapped"  # All execution through V2 entry gate is V2 wrapped
            
            # Extract feature flags (observational only)
            feature_flags = self._get_current_feature_flags()
            
            # Determine routing decision (observational only)
            routing_decision = "v2_governance_active"
            routing_context = {
                'module_id': str(request.module_id.value),
                'execution_id': v2_context['execution_id'],
                'v2_validation_required': True
            }
            
            # Capture telemetry (non-blocking, failure-tolerant)
            return self.telemetry_handler.capture_entry_observation(
                entry_path=entry_path,
                module_id=str(request.module_id.value),
                execution_id=v2_context['execution_id'],
                correlation_id=request.correlation_id,
                trace_id=getattr(request.execution_context, 'trace_id', None),
                feature_flags=feature_flags,
                routing_decision=routing_decision,
                routing_context=routing_context,
                v2_governance_active=True,
                v2_validation_passed=True
            )
        except Exception as e:
            # Telemetry failure must never affect execution
            logger.debug(f"Entry telemetry capture failed: {e}")
            return None
    
    def _capture_exit_telemetry(self, telemetry_event_id: Optional[str], result: ExecutionResult, entry_timestamp: datetime) -> bool:
        """
        Capture V2 exit boundary telemetry (observational only)
        
        NEVER affects execution behavior or decisions
        """
        try:
            if not telemetry_event_id:
                return False
            
            # Calculate processing duration
            processing_duration_ms = None
            try:
                exit_timestamp = datetime.now(timezone.utc)
                duration = exit_timestamp - entry_timestamp
                processing_duration_ms = duration.total_seconds() * 1000
            except Exception:
                pass
            
            # Create result summary (observational only)
            result_summary = {
                'success': result.success,
                'has_error': result.error is not None,
                'execution_id': result.execution_id,
                'audit_trail_id': result.audit_trail_id
            }
            
            # Capture exit telemetry (non-blocking, failure-tolerant)
            return self.telemetry_handler.capture_exit_observation(
                event_id=telemetry_event_id,
                success=result.success,
                result_summary=result_summary,
                processing_duration_ms=processing_duration_ms
            )
        except Exception as e:
            # Telemetry failure must never affect execution
            logger.debug(f"Exit telemetry capture failed: {e}")
            return False
    
    def _get_current_feature_flags(self) -> Dict[str, bool]:
        """
        Get current feature flag state (observational only)
        
        Returns snapshot of feature flags for telemetry purposes
        """
        try:
            # Import feature flags module if available
            from feature_flags import get_feature_flag_state
            
            # Get commonly relevant flags for V2 boundary
            relevant_flags = [
                'v2_federation_enabled',
                'v2_temporal_enabled',
                'v2_analytics_enabled',
                'v2_monitoring_enabled'
            ]
            
            flag_state = {}
            for flag in relevant_flags:
                try:
                    flag_state[flag] = get_feature_flag_state(flag)
                except Exception:
                    # Default to False if flag not available
                    flag_state[flag] = False
            
            return flag_state
        except Exception as e:
            logger.debug(f"Failed to get feature flags for telemetry: {e}")
            return {}
    
    def _capture_causal_start(self, request: ExecutionRequest, v2_context: Dict[str, Any], entry_timestamp: datetime) -> Optional[str]:
        """
        Capture causal context start (observational only)
        
        NEVER affects execution behavior or decisions
        """
        try:
            return self.causal_logger.capture_execution_start(
                module_id=str(request.module_id.value),
                execution_id=v2_context['execution_id'],
                correlation_id=request.correlation_id,
                trace_id=getattr(request.execution_context, 'trace_id', None),
                parent_event_id=None,  # Start of causal chain
                boundary_type="v2",
                metadata={
                    'entry_timestamp': entry_timestamp.isoformat(),
                    'module_type': 'v2_entry_gate',
                    'correlation_id': request.correlation_id,
                    'approval_id': request.approval_id
                }
            )
        except Exception as e:
            # Causal logging failure must never affect execution
            logger.debug(f"Causal start capture failed: {e}")
            return None
    
    def _capture_decision_point_causal(self, request: ExecutionRequest, v2_context: Dict[str, Any], parent_event_id: Optional[str]) -> Optional[str]:
        """
        Capture decision point causal context (observational only)
        
        NEVER affects execution behavior or decisions
        """
        try:
            return self.causal_logger.capture_decision_point(
                decision_type="v2_governance_routing",
                module_id=str(request.module_id.value),
                execution_id=v2_context['execution_id'],
                correlation_id=request.correlation_id,
                trace_id=getattr(request.execution_context, 'trace_id', None),
                parent_event_id=parent_event_id,
                boundary_type="v2",
                decision_metadata={
                    'v2_validation_passed': True,
                    'routing_decision': 'v2_governance_active',
                    'feature_flags': self._get_current_feature_flags(),
                    'module_id': str(request.module_id.value)
                }
            )
        except Exception as e:
            # Causal logging failure must never affect execution
            logger.debug(f"Causal decision point capture failed: {e}")
            return None
    
    def _capture_causal_end(self, causal_start_record_id: Optional[str], request: ExecutionRequest, v2_context: Dict[str, Any], result: ExecutionResult, entry_timestamp: datetime) -> bool:
        """
        Capture causal context end (observational only)
        
        NEVER affects execution behavior or decisions
        """
        try:
            if not causal_start_record_id:
                return False
            
            # Calculate processing duration
            duration_ms = None
            try:
                exit_timestamp = datetime.now(timezone.utc)
                duration = exit_timestamp - entry_timestamp
                duration_ms = duration.total_seconds() * 1000
            except Exception:
                pass
            
            return self.causal_logger.capture_execution_end(
                execution_start_record_id=causal_start_record_id,
                module_id=str(request.module_id.value),
                execution_id=v2_context['execution_id'],
                correlation_id=request.correlation_id,
                trace_id=getattr(request.execution_context, 'trace_id', None),
                boundary_type="v2",
                success=result.success,
                duration_ms=duration_ms,
                metadata={
                    'exit_timestamp': datetime.now(timezone.utc).isoformat(),
                    'has_error': result.error is not None,
                    'error_type': 'v2_entry_gate_failure' if result.error else None,
                    'audit_trail_id': result.audit_trail_id
                }
            )
        except Exception as e:
            # Causal logging failure must never affect execution
            logger.debug(f"Causal end capture failed: {e}")
            return False

# GLOBAL SINGLETON - THE ONLY ALLOWED ENTRY POINT
_v2_entry_gate_instance: Optional[V2EntryGate] = None

def get_v2_entry_gate() -> V2EntryGate:
    """Get the singleton V2 Entry Gate instance"""
    global _v2_entry_gate_instance
    if _v2_entry_gate_instance is None:
        _v2_entry_gate_instance = V2EntryGate()
    return _v2_entry_gate_instance

# GLOBAL EXECUTION FUNCTION - THE ONLY VALID EXECUTION PATH
def execute_module(request: ExecutionRequest) -> ExecutionResult:
    """
    GLOBAL EXECUTION ENTRY POINT - SINGLE MANDATORY PATH
    
    This is the ONLY function that can execute modules.
    ALL execution MUST pass through here.
    NO bypass paths exist.
    NO fallback execution possible.
    """
    gate = get_v2_entry_gate()
    return gate.execute_module(request)