"""
Boundary Contract Enforcement Layer
Structural guardrail system preventing architectural coupling and enforcing isolation rules
"""

import hashlib
import importlib
import inspect
import threading
from enum import Enum
from typing import Dict, Set, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ContractDomain(Enum):
    """Strict domain separation for system components"""
    EXECUTION_DOMAIN = "execution"
    TELEMETRY_DOMAIN = "telemetry"
    CAUSAL_DOMAIN = "causal"
    AUDIT_REPLAY_DOMAIN = "audit_replay"
    SAFETY_DECISION_DOMAIN = "safety_decision"
    ENVIRONMENT_DOMAIN = "environment"


class DependencyDirection(Enum):
    """Allowed dependency directions between domains"""
    EXECUTION_TO_TELEMETRY = (ContractDomain.EXECUTION_DOMAIN, ContractDomain.TELEMETRY_DOMAIN)
    EXECUTION_TO_CAUSAL = (ContractDomain.EXECUTION_DOMAIN, ContractDomain.CAUSAL_DOMAIN)
    EXECUTION_TO_AUDIT_REPLAY = (ContractDomain.EXECUTION_DOMAIN, ContractDomain.AUDIT_REPLAY_DOMAIN)
    EXECUTION_TO_SAFETY_DECISION = (ContractDomain.EXECUTION_DOMAIN, ContractDomain.SAFETY_DECISION_DOMAIN)
    EXECUTION_TO_ENVIRONMENT = (ContractDomain.EXECUTION_DOMAIN, ContractDomain.ENVIRONMENT_DOMAIN)
    
    # NO reverse dependencies allowed
    # TELEMETRY_DOMAIN MUST NOT READ OR DEPEND ON CAUSAL_DOMAIN
    # CAUSAL_DOMAIN MUST NOT READ OR DEPEND ON TELEMETRY_DOMAIN
    # BOTH MUST BE READ-ONLY relative to EXECUTION_DOMAIN
    # SAFETY_DECISION_DOMAIN MUST NOT CONSUME OBSERVABILITY LAYERS
    # AUDIT_REPLAY_DOMAIN MUST ONLY CONSUME EXECUTION SNAPSHOTS


@dataclass(frozen=True)
class SchemaFingerprint:
    """Immutable schema fingerprint for drift detection"""
    schema_name: str
    domain: ContractDomain
    fingerprint_hash: str
    field_types: Dict[str, str]
    field_count: int
    is_mutable: bool
    created_at: datetime
    version: str = "1.0.0"
    
    @classmethod
    def from_schema(cls, schema_name: str, domain: ContractDomain, schema_obj: Any) -> 'SchemaFingerprint':
        """Generate fingerprint from schema object"""
        field_types = {}
        field_count = 0
        is_mutable = False
        
        if hasattr(schema_obj, '__dataclass_fields__'):
            # Dataclass schema
            from dataclasses import fields, is_dataclass
            if is_dataclass(schema_obj):
                for field_info in fields(schema_obj):
                    field_types[field_info.name] = str(field_info.type)
                    field_count += 1
                    is_mutable = is_mutable or not field_info.init
        
        elif hasattr(schema_obj, '__annotations__'):
            # Class with annotations
            field_types = {k: str(v) for k, v in schema_obj.__annotations__.items()}
            field_count = len(field_types)
            is_mutable = not getattr(schema_obj, '__frozen__', False)
        
        # Generate fingerprint hash
        fingerprint_data = f"{schema_name}:{domain.value}:{field_count}:{sorted(field_types.items())}:{is_mutable}"
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        
        return cls(
            schema_name=schema_name,
            domain=domain,
            fingerprint_hash=fingerprint_hash,
            field_types=field_types,
            field_count=field_count,
            is_mutable=is_mutable,
            created_at=datetime.now(timezone.utc)
        )


@dataclass(frozen=True)
class ContractViolation:
    """Immutable contract violation record"""
    violation_id: str
    timestamp: datetime
    violation_type: str
    source_domain: ContractDomain
    target_domain: ContractDomain
    description: str
    detected_at: str
    severity: str = "ERROR"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'violation_id': self.violation_id,
            'timestamp': self.timestamp.isoformat(),
            'violation_type': self.violation_type,
            'source_domain': self.source_domain.value,
            'target_domain': self.target_domain.value,
            'description': self.description,
            'detected_at': self.detected_at,
            'severity': self.severity
        }


class BoundaryContractRegistry:
    """
    Boundary Contract Registry - Enforces strict domain separation
    
    Structural guardrail system that prevents architectural coupling
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize boundary contract registry
        
        Args:
            strict_mode: Whether to enforce strict contract validation
        """
        self.strict_mode = strict_mode
        self._lock = threading.RLock()
        
        # Domain registrations
        self._domain_modules: Dict[ContractDomain, Set[str]] = {
            domain: set() for domain in ContractDomain
        }
        
        # Schema fingerprints by domain
        self._schema_fingerprints: Dict[ContractDomain, Dict[str, SchemaFingerprint]] = {
            domain: {} for domain in ContractDomain
        }
        
        # Allowed dependencies (directional)
        self._allowed_dependencies: Set[Tuple[ContractDomain, ContractDomain]] = set()
        self._initialize_allowed_dependencies()
        
        # Dependency graph for cycle detection
        self._dependency_graph: Dict[ContractDomain, Set[ContractDomain]] = {
            domain: set() for domain in ContractDomain
        }
        
        # Contract violations
        self._violations: List[ContractViolation] = []
        
        logger.info("BoundaryContractRegistry initialized - STRUCTURAL GUARDRAIL SYSTEM")
    
    def _initialize_allowed_dependencies(self):
        """Initialize allowed dependency directions"""
        # Execution domain can depend on other domains (write operations)
        self._allowed_dependencies.add((ContractDomain.EXECUTION_DOMAIN, ContractDomain.TELEMETRY_DOMAIN))
        self._allowed_dependencies.add((ContractDomain.EXECUTION_DOMAIN, ContractDomain.CAUSAL_DOMAIN))
        self._allowed_dependencies.add((ContractDomain.EXECUTION_DOMAIN, ContractDomain.AUDIT_REPLAY_DOMAIN))
        self._allowed_dependencies.add((ContractDomain.EXECUTION_DOMAIN, ContractDomain.SAFETY_DECISION_DOMAIN))
        self._allowed_dependencies.add((ContractDomain.EXECUTION_DOMAIN, ContractDomain.ENVIRONMENT_DOMAIN))
        
        # Audit/Replay domain can read from execution domain (read-only)
        self._allowed_dependencies.add((ContractDomain.AUDIT_REPLAY_DOMAIN, ContractDomain.EXECUTION_DOMAIN))
        
        # Safety decision domain can read from execution domain (read-only)
        self._allowed_dependencies.add((ContractDomain.SAFETY_DECISION_DOMAIN, ContractDomain.EXECUTION_DOMAIN))
        
        # Environment domain can read from execution domain (read-only)
        self._allowed_dependencies.add((ContractDomain.ENVIRONMENT_DOMAIN, ContractDomain.EXECUTION_DOMAIN))
        
        # NO other dependencies allowed
        # TELEMETRY_DOMAIN MUST NOT READ OR DEPEND ON CAUSAL_DOMAIN
        # CAUSAL_DOMAIN MUST NOT READ OR DEPEND ON TELEMETRY_DOMAIN
        # BOTH MUST BE READ-ONLY relative to EXECUTION_DOMAIN
        # SAFETY_DECISION_DOMAIN MUST NOT CONSUME OBSERVABILITY LAYERS
    
    def register_module(self, module_name: str, domain: ContractDomain) -> bool:
        """
        Register a module to a specific domain
        
        Args:
            module_name: Name of the module
            domain: Domain the module belongs to
            
        Returns:
            True if registration successful, False if violates contracts
        """
        with self._lock:
            # Check if module is already registered to a different domain
            for existing_domain, modules in self._domain_modules.items():
                if existing_domain != domain and module_name in modules:
                    violation = ContractViolation(
                        violation_id=f"module_domain_conflict_{module_name}",
                        timestamp=datetime.now(timezone.utc),
                        violation_type="MODULE_DOMAIN_CONFLICT",
                        source_domain=existing_domain,
                        target_domain=domain,
                        description=f"Module {module_name} already registered to {existing_domain.value}, cannot register to {domain.value}",
                        detected_at="module_registration"
                    )
                    self._violations.append(violation)
                    logger.error(f"Contract violation: {violation.description}")
                    return False
            
            # Register module to domain
            self._domain_modules[domain].add(module_name)
            logger.debug(f"Registered module {module_name} to {domain.value} domain")
            return True
    
    def register_schema(self, schema_name: str, domain: ContractDomain, schema_obj: Any) -> bool:
        """
        Register a schema fingerprint for drift detection
        
        Args:
            schema_name: Name of the schema
            domain: Domain the schema belongs to
            schema_obj: Schema object to fingerprint
            
        Returns:
            True if registration successful, False if violates contracts
        """
        with self._lock:
            # Generate fingerprint
            fingerprint = SchemaFingerprint.from_schema(schema_name, domain, schema_obj)
            
            # Check for cross-domain schema conflicts
            for other_domain, fingerprints in self._schema_fingerprints.items():
                if other_domain != domain and schema_name in fingerprints:
                    existing_fingerprint = fingerprints[schema_name]
                    
                    # Check if schemas are identical (cross-domain reuse)
                    if (fingerprint.fingerprint_hash == existing_fingerprint.fingerprint_hash and
                        fingerprint.field_count == existing_fingerprint.field_count):
                        violation = ContractViolation(
                            violation_id=f"cross_domain_schema_{schema_name}",
                            timestamp=datetime.now(timezone.utc),
                            violation_type="CROSS_DOMAIN_SCHEMA_REUSE",
                            source_domain=domain,
                            target_domain=other_domain,
                            description=f"Schema {schema_name} reused across {domain.value} and {other_domain.value} domains",
                            detected_at="schema_registration"
                        )
                        self._violations.append(violation)
                        logger.error(f"Contract violation: {violation.description}")
                        return False
            
            # Register schema fingerprint
            self._schema_fingerprints[domain][schema_name] = fingerprint
            logger.debug(f"Registered schema {schema_name} to {domain.value} domain")
            return True
    
    def validate_dependency(self, source_domain: ContractDomain, target_domain: ContractDomain, 
                          context: str = "unknown") -> bool:
        """
        Validate dependency between domains
        
        Args:
            source_domain: Domain making the dependency
            target_domain: Domain being depended on
            context: Context of the dependency for error reporting
            
        Returns:
            True if dependency is allowed, False if violates contracts
        """
        with self._lock:
            # Check if dependency is allowed
            if (source_domain, target_domain) not in self._allowed_dependencies:
                violation = ContractViolation(
                    violation_id=f"forbidden_dependency_{source_domain.value}_to_{target_domain.value}",
                    timestamp=datetime.now(timezone.utc),
                    violation_type="FORBIDDEN_DEPENDENCY",
                    source_domain=source_domain,
                    target_domain=target_domain,
                    description=f"Forbidden dependency from {source_domain.value} to {target_domain.value} in {context}",
                    detected_at="dependency_validation"
                )
                self._violations.append(violation)
                logger.error(f"Contract violation: {violation.description}")
                return False
            
            # Check for cycles
            if self._would_create_cycle(source_domain, target_domain):
                violation = ContractViolation(
                    violation_id=f"dependency_cycle_{source_domain.value}_to_{target_domain.value}",
                    timestamp=datetime.now(timezone.utc),
                    violation_type="DEPENDENCY_CYCLE",
                    source_domain=source_domain,
                    target_domain=target_domain,
                    description=f"Dependency would create cycle from {source_domain.value} to {target_domain.value} in {context}",
                    detected_at="dependency_validation"
                )
                self._violations.append(violation)
                logger.error(f"Contract violation: {violation.description}")
                return False
            
            # Add to dependency graph
            self._dependency_graph[source_domain].add(target_domain)
            logger.debug(f"Validated dependency: {source_domain.value} -> {target_domain.value} in {context}")
            return True
    
    def _would_create_cycle(self, source_domain: ContractDomain, target_domain: ContractDomain) -> bool:
        """Check if adding dependency would create a cycle"""
        # Simple cycle detection using DFS
        visited = set()
        recursion_stack = set()
        
        def has_cycle(domain: ContractDomain) -> bool:
            visited.add(domain)
            recursion_stack.add(domain)
            
            # Check neighbors
            for neighbor in self._dependency_graph[domain]:
                if neighbor == source_domain and domain == target_domain:
                    # Would create cycle back to source
                    return True
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True
            
            recursion_stack.remove(domain)
            return False
        
        return has_cycle(target_domain)
    
    def validate_import_boundary(self, importing_module: str, imported_module: str) -> bool:
        """
        Validate import boundary between modules
        
        Args:
            importing_module: Module doing the import
            imported_module: Module being imported
            
        Returns:
            True if import is allowed, False if violates contracts
        """
        with self._lock:
            # Find domains for both modules
            importing_domain = None
            imported_domain = None
            
            for domain, modules in self._domain_modules.items():
                if importing_module in modules:
                    importing_domain = domain
                if imported_module in modules:
                    imported_domain = domain
            
            # If either module is not registered, allow import (fail-safe)
            if importing_domain is None or imported_domain is None:
                logger.debug(f"Import validation: module not registered, allowing {importing_module} -> {imported_module}")
                return True
            
            # Validate dependency
            return self.validate_dependency(importing_domain, imported_domain, f"import {importing_module} -> {imported_module}")
    
    def check_schema_drift(self, schema_name: str, domain: ContractDomain, schema_obj: Any) -> bool:
        """
        Check for schema drift against registered fingerprint
        
        Args:
            schema_name: Name of the schema
            domain: Domain the schema belongs to
            schema_obj: Current schema object
            
        Returns:
            True if no drift detected, False if drift detected
        """
        with self._lock:
            if domain not in self._schema_fingerprints or schema_name not in self._schema_fingerprints[domain]:
                # Schema not registered, register it now
                return self.register_schema(schema_name, domain, schema_obj)
            
            # Generate current fingerprint
            current_fingerprint = SchemaFingerprint.from_schema(schema_name, domain, schema_obj)
            registered_fingerprint = self._schema_fingerprints[domain][schema_name]
            
            # Check for drift
            if current_fingerprint.fingerprint_hash != registered_fingerprint.fingerprint_hash:
                violation = ContractViolation(
                    violation_id=f"schema_drift_{schema_name}",
                    timestamp=datetime.now(timezone.utc),
                    violation_type="SCHEMA_DRIFT",
                    source_domain=domain,
                    target_domain=domain,
                    description=f"Schema drift detected for {schema_name} in {domain.value} domain",
                    detected_at="schema_drift_check"
                )
                self._violations.append(violation)
                logger.error(f"Contract violation: {violation.description}")
                return False
            
            return True
    
    def get_violations(self, domain: Optional[ContractDomain] = None) -> List[ContractViolation]:
        """
        Get contract violations
        
        Args:
            domain: Optional domain to filter violations
            
        Returns:
            List of contract violations
        """
        with self._lock:
            if domain is None:
                return self._violations.copy()
            
            return [
                violation for violation in self._violations
                if violation.source_domain == domain or violation.target_domain == domain
            ]
    
    def clear_violations(self):
        """Clear all violations (for testing)"""
        with self._lock:
            self._violations.clear()
    
    def get_domain_summary(self) -> Dict[str, Any]:
        """Get summary of domain registrations and dependencies"""
        with self._lock:
            return {
                'domains': {
                    domain.value: {
                        'modules': list(modules),
                        'schemas': list(fingerprints.keys()),
                        'module_count': len(modules),
                        'schema_count': len(fingerprints)
                    }
                    for domain, modules, fingerprints in 
                    [(d, self._domain_modules[d], self._schema_fingerprints[d]) for d in ContractDomain]
                },
                'dependencies': [
                    {
                        'source': source.value,
                        'target': target.value,
                        'allowed': (source, target) in self._allowed_dependencies
                    }
                    for source, targets in self._dependency_graph.items()
                    for target in targets
                ],
                'violation_count': len(self._violations),
                'strict_mode': self.strict_mode
            }


# Global boundary contract registry instance (singleton pattern)
_boundary_contract_registry: Optional[BoundaryContractRegistry] = None


def get_boundary_contract_registry() -> BoundaryContractRegistry:
    """Get global boundary contract registry instance"""
    global _boundary_contract_registry
    if _boundary_contract_registry is None:
        _boundary_contract_registry = BoundaryContractRegistry()
    return _boundary_contract_registry


def configure_boundary_contract_registry(strict_mode: bool = True) -> BoundaryContractRegistry:
    """Configure global boundary contract registry"""
    global _boundary_contract_registry
    if _boundary_contract_registry:
        # Don't reconfigure existing instance
        return _boundary_contract_registry
    
    _boundary_contract_registry = BoundaryContractRegistry(strict_mode)
    return _boundary_contract_registry


# Decorator for contract validation
def validate_contract_boundary(source_domain: ContractDomain, target_domain: ContractDomain, context: str = "unknown"):
    """
    Decorator to validate contract boundary for function calls
    
    Args:
        source_domain: Domain making the call
        target_domain: Domain being called
        context: Context of the call for error reporting
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            registry = get_boundary_contract_registry()
            if registry.strict_mode and not registry.validate_dependency(source_domain, target_domain, context):
                raise RuntimeError(f"Contract boundary violation in {context}: {source_domain.value} -> {target_domain.value}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
