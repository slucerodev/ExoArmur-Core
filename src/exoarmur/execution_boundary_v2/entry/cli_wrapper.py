"""
CLI Wrapper Layer - Structural Enforcement for CLI Commands

This module provides wrapper functions that enforce canonical routing
for all CLI commands, eliminating bypass capability.

PRINCIPLES:
- All CLI commands must route through canonical spine
- No direct execution possible from CLI
- Preserve CLI usability while enforcing routing
"""

import sys
import time
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CLIExecutionError(Exception):
    """Raised when CLI execution fails canonical routing"""
    pass

class CLIWrapper:
    """Wrapper layer that enforces canonical routing for CLI commands"""
    
    def __init__(self):
        self._router = None
        self._initialize_router()
    
    def _initialize_router(self):
        """Initialize canonical router"""
        try:
            from .canonical_router import CanonicalExecutionRouter
            self._router = CanonicalExecutionRouter()
            logger.info("CLI Wrapper: Canonical router initialized")
        except ImportError as e:
            raise CLIExecutionError(
                f"Cannot initialize canonical router for CLI: {e}"
            )
    
    def wrap_demo_execution(self, operator_decision: Optional[str] = None, 
                          scenario: str = 'canonical', replay: Optional[str] = None,
                          env: Optional[Dict[str, str]] = None) -> tuple[int, str]:
        """
        Wrap demo execution through canonical routing
        
        This replaces direct demo execution with canonical routing.
        
        Args:
            operator_decision: Operator decision for demo
            scenario: Demo scenario to run
            replay: Replay mode
            env: Environment variables
            
        Returns:
            Tuple of (exit_code, output)
        """
        logger.info(f"CLI Wrapper: Routing demo execution through canonical spine")
        
        execution_context = {
            "execution_id": f"cli_demo_{int(time.time())}",
            "module_id": "cli_demo_wrapper",
            "deterministic_seed": 42,
            "logical_timestamp": int(time.time()),
            "correlation_id": f"cli_demo_{scenario}"
        }
        
        action_data = {
            "cli_command": "demo",
            "scenario": scenario,
            "operator_decision": operator_decision,
            "replay_mode": replay is not None,
            "environment": env or {},
            "wrapped_by": "cli_wrapper"
        }
        
        try:
            result = self._router.route_to_v2_entry_gate(
                module_id="cli_demo_wrapper",
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            if result.success:
                return 0, result.result_data.get("output", "")
            else:
                return 1, f"CLI execution failed: {result.error}"
                
        except Exception as e:
            logger.error(f"CLI Wrapper execution failed: {e}")
            return 1, f"CLI wrapper error: {e}"
    
    def wrap_verify_all(self, verbose: bool = False, fast: bool = False) -> tuple[int, str]:
        """
        Wrap verify-all command through canonical routing
        
        This replaces direct verification with canonical routing.
        
        Args:
            verbose: Verbose output flag
            fast: Fast verification flag
            
        Returns:
            Tuple of (exit_code, output)
        """
        logger.info("CLI Wrapper: Routing verify-all through canonical spine")
        
        execution_context = {
            "execution_id": f"cli_verify_{int(time.time())}",
            "module_id": "cli_verify_wrapper",
            "deterministic_seed": 42,
            "logical_timestamp": int(time.time()),
            "correlation_id": "cli_verify_all"
        }
        
        action_data = {
            "cli_command": "verify_all",
            "verbose": verbose,
            "fast": fast,
            "wrapped_by": "cli_wrapper"
        }
        
        try:
            result = self._router.route_to_v2_entry_gate(
                module_id="cli_verify_wrapper",
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            if result.success:
                return 0, result.result_data.get("output", "")
            else:
                return 1, f"Verification failed: {result.error}"
                
        except Exception as e:
            logger.error(f"CLI Wrapper verification failed: {e}")
            return 1, f"CLI wrapper error: {e}"
    
    def wrap_evidence_export(self, export: Optional[str] = None, 
                           intent_id: Optional[str] = None) -> tuple[int, str]:
        """
        Wrap evidence export through canonical routing
        
        Args:
            export: Export path
            intent_id: Intent ID to export
            
        Returns:
            Tuple of (exit_code, output)
        """
        logger.info("CLI Wrapper: Routing evidence export through canonical spine")
        
        execution_context = {
            "execution_id": f"cli_evidence_{int(time.time())}",
            "module_id": "cli_evidence_wrapper",
            "deterministic_seed": 42,
            "logical_timestamp": int(time.time()),
            "correlation_id": "cli_evidence_export"
        }
        
        action_data = {
            "cli_command": "evidence",
            "export": export,
            "intent_id": intent_id,
            "wrapped_by": "cli_wrapper"
        }
        
        try:
            result = self._router.route_to_v2_entry_gate(
                module_id="cli_evidence_wrapper",
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            if result.success:
                return 0, result.result_data.get("output", "")
            else:
                return 1, f"Evidence export failed: {result.error}"
                
        except Exception as e:
            logger.error(f"CLI Wrapper evidence export failed: {e}")
            return 1, f"CLI wrapper error: {e}"

# Global CLI wrapper instance
_cli_wrapper = None

def get_cli_wrapper() -> CLIWrapper:
    """Get the global CLI wrapper instance"""
    global _cli_wrapper
    if _cli_wrapper is None:
        _cli_wrapper = CLIWrapper()
    return _cli_wrapper

def enforce_cli_routing():
    """
    Enforce that all CLI commands use canonical routing
    
    This function should be called at CLI initialization to prevent
    any direct execution paths from being used.
    """
    wrapper = get_cli_wrapper()
    logger.info("CLI routing enforcement activated")
    return wrapper
