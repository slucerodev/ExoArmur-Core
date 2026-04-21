"""
Determinism Protected Modules Configuration

Defines the list of modules that require strict determinism enforcement.
Any code in these modules is subject to:
- Static analysis for nondeterministic patterns
- Runtime guards for wall-clock usage
- DeterministicClock assertions
- CI/CD blocking on violations
"""

from typing import Set, List
from dataclasses import dataclass
from enum import Enum


class ProtectionLevel(str, Enum):
    """Determinism protection levels"""
    STRICT = "strict"  # All nondeterminism prohibited
    CONTROLLED = "controlled"  # Only explicitly seeded randomness allowed


@dataclass(frozen=True)
class ProtectedModule:
    """A module that requires determinism protection"""
    module_path: str
    protection_level: ProtectionLevel
    description: str


# Core critical paths - strict protection
# Note: These paths match the Python module paths (e.g., exoarmur.federation)
# The scanner will match file paths to these module paths
STRICT_MODULES: List[ProtectedModule] = [
    ProtectedModule(
        module_path="exoarmur.replay",
        protection_level=ProtectionLevel.STRICT,
        description="ReplayEngine must produce identical results across runs"
    ),
    ProtectedModule(
        module_path="exoarmur.safety",
        protection_level=ProtectionLevel.STRICT,
        description="Safety gate decisions must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.policy",
        protection_level=ProtectionLevel.STRICT,
        description="Policy decisions must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.execution_boundary_v2",
        protection_level=ProtectionLevel.STRICT,
        description="Execution boundary must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.federation",
        protection_level=ProtectionLevel.STRICT,
        description="Federation coordination must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.identity_containment",
        protection_level=ProtectionLevel.STRICT,
        description="Identity containment must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.collective_confidence",
        protection_level=ProtectionLevel.STRICT,
        description="Confidence aggregation must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.v2_restrained_autonomy",
        protection_level=ProtectionLevel.STRICT,
        description="Autonomy decisions must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.audit",
        protection_level=ProtectionLevel.STRICT,
        description="Audit logging must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.causal",
        protection_level=ProtectionLevel.STRICT,
        description="Causal tracking must be deterministic"
    ),
    ProtectedModule(
        module_path="exoarmur.reliability",
        protection_level=ProtectionLevel.STRICT,
        description="Retry logic must be deterministic"
    ),
]


# Files that are exempt from determinism enforcement
# These are explicitly for non-critical paths or infrastructure
EXEMPT_FILES: Set[str] = {
    "exoarmur.federation.clock",  # SystemClock for non-critical paths
    "exoarmur.v2_restrained_autonomy.mock_executor",  # Mock executor for testing
}


def get_protected_module_paths() -> Set[str]:
    """Get all protected module paths"""
    return {module.module_path for module in STRICT_MODULES}


def get_protected_module(module_path: str) -> ProtectedModule:
    """Get protected module configuration by path"""
    for module in STRICT_MODULES:
        if module_path.startswith(module.module_path):
            return module
    return None


def is_module_protected(module_path: str) -> bool:
    """Check if a module is protected"""
    return get_protected_module(module_path) is not None


def get_protection_level(module_path: str) -> ProtectionLevel:
    """Get protection level for a module"""
    module = get_protected_module(module_path)
    return module.protection_level if module else None


def is_module_exempt(module_path: str) -> bool:
    """Check if a module is exempt from determinism enforcement"""
    for exempt_path in EXEMPT_FILES:
        if module_path.startswith(exempt_path):
            return True
    return False
