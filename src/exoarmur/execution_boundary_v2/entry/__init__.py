"""
V2 Entry Gate Module - Single Execution Boundary

This module provides the canonical entry point for all execution in ExoArmur.
All execution must pass through V2EntryGate to ensure proper governance,
audit, and determinism guarantees.

Key Components:
- V2EntryGate: The authoritative execution boundary
- execute_module: Global execution function (single entry point)
- CanonicalExecutionRouter: Thin routing layer for convergence
"""

from .v2_entry_gate import (
    V2EntryGate,
    ExecutionRequest,
    ExecutionResult,
    ModuleExecutionContext,
    execute_module,
    get_v2_entry_gate
)

from .canonical_router import (
    CanonicalExecutionRouter,
    get_canonical_router
)

__all__ = [
    "V2EntryGate",
    "ExecutionRequest", 
    "ExecutionResult",
    "ModuleExecutionContext",
    "execute_module",
    "get_v2_entry_gate",
    "CanonicalExecutionRouter",
    "get_canonical_router"
]