"""Lazy V2 dependency resolver.

Only this module is allowed to import execution_boundary_v2 symbols.
"""

from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace


@lru_cache(maxsize=None)
def load_v2_entry_gate() -> SimpleNamespace:
    from exoarmur.execution_boundary_v2.entry.v2_entry_gate import ExecutionRequest, execute_module

    return SimpleNamespace(ExecutionRequest=ExecutionRequest, execute_module=execute_module)


@lru_cache(maxsize=None)
def load_v2_core_types() -> SimpleNamespace:
    from exoarmur.execution_boundary_v2.core.core_types import (
        DeterministicSeed,
        ExecutionID,
        ModuleExecutionContext,
        ModuleID,
        ModuleVersion,
    )

    return SimpleNamespace(
        DeterministicSeed=DeterministicSeed,
        ExecutionID=ExecutionID,
        ModuleExecutionContext=ModuleExecutionContext,
        ModuleID=ModuleID,
        ModuleVersion=ModuleVersion,
    )


@lru_cache(maxsize=None)
def load_v2_safety_models() -> SimpleNamespace:
    from exoarmur.execution_boundary_v2.interfaces.executor_plugin import ExecutorResult
    from exoarmur.execution_boundary_v2.models.action_intent import ActionIntent
    from exoarmur.execution_boundary_v2.models.policy_decision import PolicyDecision, PolicyVerdict

    return SimpleNamespace(
        ActionIntent=ActionIntent,
        ExecutorResult=ExecutorResult,
        PolicyDecision=PolicyDecision,
        PolicyVerdict=PolicyVerdict,
    )


@lru_cache(maxsize=None)
def load_v2_diagnostics() -> SimpleNamespace:
    from exoarmur.execution_boundary_v2.detection import ViolationSeverity, check_domain_logic_access

    return SimpleNamespace(
        ViolationSeverity=ViolationSeverity,
        check_domain_logic_access=check_domain_logic_access,
    )
