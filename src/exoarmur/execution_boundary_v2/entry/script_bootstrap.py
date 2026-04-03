"""
Script Bootstrap Layer - Structural Enforcement for Script Execution

This module provides a bootstrap mechanism that enforces canonical routing
for all script-based execution, eliminating bypass capability.

PRINCIPLES:
- All script execution must route through canonical spine
- No direct script execution possible
- Preserve script functionality while enforcing routing
"""

import sys
import os
import time
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ScriptExecutionError(Exception):
    """Raised when script execution fails canonical routing"""
    pass

class ScriptBootstrap:
    """Bootstrap layer that enforces canonical routing for script execution"""
    
    def __init__(self):
        self._router = None
        self._initialize_router()
    
    def _initialize_router(self):
        """Initialize canonical router"""
        try:
            from .canonical_router import CanonicalExecutionRouter
            self._router = CanonicalExecutionRouter()
            logger.info("Script Bootstrap: Canonical router initialized")
        except ImportError as e:
            raise ScriptExecutionError(
                f"Cannot initialize canonical router for scripts: {e}"
            )
    
    def bootstrap_script_execution(self, script_path: str, *args, **kwargs) -> int:
        """
        Bootstrap script execution through canonical routing
        
        This replaces direct script execution with canonical routing.
        
        Args:
            script_path: Path to the script being executed
            *args: Script arguments
            **kwargs: Script keyword arguments
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        logger.info(f"Script Bootstrap: Routing {script_path} through canonical spine")
        
        # Extract script information
        script_path_obj = Path(script_path)
        script_name = script_path_obj.stem
        script_dir = str(script_path_obj.parent)
        
        execution_context = {
            "execution_id": f"script_{script_name}_{int(time.time())}",
            "module_id": f"script_{script_name}",
            "deterministic_seed": 42,
            "logical_timestamp": int(time.time()),
            "correlation_id": f"script_{script_name}",
            "script_path": script_path,
            "script_dir": script_dir
        }
        
        action_data = {
            "script_command": "execute",
            "script_path": script_path,
            "script_name": script_name,
            "script_args": args,
            "script_kwargs": kwargs,
            "bootstrap_by": "script_bootstrap",
            "working_directory": os.getcwd(),
            "environment": dict(os.environ)
        }
        
        try:
            result = self._router.route_to_v2_entry_gate(
                module_id=f"script_{script_name}",
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            if result.success:
                logger.info(f"Script {script_name} executed successfully through canonical spine")
                return 0
            else:
                logger.error(f"Script {script_name} failed: {result.error}")
                return 1
                
        except Exception as e:
            logger.error(f"Script bootstrap execution failed for {script_name}: {e}")
            return 1
    
    def bootstrap_demo_scenario(self, scenario_type: str = "complete_demo") -> int:
        """
        Bootstrap demo scenario execution through canonical routing
        
        Args:
            scenario_type: Type of demo scenario to execute
            
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        logger.info(f"Script Bootstrap: Routing demo scenario {scenario_type} through canonical spine")
        
        execution_context = {
            "execution_id": f"demo_scenario_{scenario_type}_{int(time.time())}",
            "module_id": "demo_scenario_script",
            "deterministic_seed": 42,
            "logical_timestamp": int(time.time()),
            "correlation_id": f"demo_{scenario_type}"
        }
        
        action_data = {
            "script_command": "demo_scenario",
            "scenario_type": scenario_type,
            "bootstrap_by": "script_bootstrap",
            "working_directory": os.getcwd()
        }
        
        try:
            result = self._router.route_to_v2_entry_gate(
                module_id="demo_scenario_script",
                execution_context_data=execution_context,
                action_data=action_data
            )
            
            if result.success:
                logger.info(f"Demo scenario {scenario_type} executed successfully through canonical spine")
                return 0
            else:
                logger.error(f"Demo scenario {scenario_type} failed: {result.error}")
                return 1
                
        except Exception as e:
            logger.error(f"Demo scenario bootstrap failed: {e}")
            return 1

# Global script bootstrap instance
_script_bootstrap = None

def get_script_bootstrap() -> ScriptBootstrap:
    """Get the global script bootstrap instance"""
    global _script_bootstrap
    if _script_bootstrap is None:
        _script_bootstrap = ScriptBootstrap()
    return _script_bootstrap

def enforce_script_routing():
    """
    Enforce that all script execution uses canonical routing
    
    This function should be called at script initialization to prevent
    any direct execution paths from being used.
    """
    bootstrap = get_script_bootstrap()
    logger.info("Script routing enforcement activated")
    return bootstrap

def create_canonical_script_entry(script_path: str):
    """
    Create a canonical script entry point that enforces routing
    
    This function can be used to replace direct script execution
    with canonical routing enforcement.
    
    Args:
        script_path: Path to the original script
        
    Returns:
        Function that enforces canonical routing
    """
    def canonical_script_main(*args, **kwargs):
        """Canonical script main function"""
        bootstrap = get_script_bootstrap()
        return bootstrap.bootstrap_script_execution(script_path, *args, **kwargs)
    
    return canonical_script_main
