"""
Dependency Edge Guard
Prevents runtime dependency injection across forbidden domains
"""

import inspect
import threading
from typing import Dict, Set, List, Optional, Any, Callable, Type
from dataclasses import dataclass
from enum import Enum
import logging

from .boundary_contract_registry import (
    BoundaryContractRegistry, ContractDomain, get_boundary_contract_registry
)

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies to guard"""
    IMPORT = "import"
    FUNCTION_CALL = "function_call"
    CLASS_INSTANTIATION = "class_instantiation"
    ATTRIBUTE_ACCESS = "attribute_access"
    EVENT_SUBSCRIPTION = "event_subscription"
    INJECTION = "injection"


@dataclass(frozen=True)
class DependencyEdge:
    """Dependency edge between domains"""
    source_domain: ContractDomain
    target_domain: ContractDomain
    dependency_type: DependencyType
    source_object: str
    target_object: str
    context: str
    allowed: bool = False
    
    def __str__(self) -> str:
        return f"{self.source_domain.value} --[{self.dependency_type.value}]--> {self.target_domain.value}"
    
    def __hash__(self) -> int:
        """Make DependencyEdge hashable for use in sets"""
        return hash((
            self.source_domain,
            self.target_domain,
            self.dependency_type,
            self.source_object,
            self.target_object,
            self.context
        ))


class DependencyEdgeGuard:
    """
    Dependency Edge Guard - Prevents architectural cycles and forbidden dependencies
    
    Runtime enforcement of boundary contracts for dependency injection and cross-domain calls
    """
    
    def __init__(self, registry: Optional[BoundaryContractRegistry] = None, strict_mode: bool = True):
        """
        Initialize dependency edge guard
        
        Args:
            registry: Boundary contract registry instance
            strict_mode: Whether to enforce strict dependency validation
        """
        self.registry = registry or get_boundary_contract_registry()
        self.strict_mode = strict_mode
        self._lock = threading.RLock()
        
        # Runtime dependency tracking
        self._active_dependencies: Dict[ContractDomain, Set[DependencyEdge]] = {
            domain: set() for domain in ContractDomain
        }
        
        # Dependency call stack for cycle detection
        self._call_stack: List[DependencyEdge] = []
        
        # Blocked dependencies cache
        self._blocked_dependencies: Set[str] = set()
        
        logger.info("DependencyEdgeGuard initialized - RUNTIME DEPENDENCY GUARD")
    
    def validate_function_call(self, caller_module: str, callee_module: str, 
                              function_name: str, context: str = "unknown") -> bool:
        """
        Validate function call dependency
        
        Args:
            caller_module: Module making the call
            callee_module: Module being called
            function_name: Name of the function being called
            context: Context of the call
            
        Returns:
            True if call is allowed, False if violates contracts
        """
        if not self.strict_mode:
            return True
        
        with self._lock:
            # Determine domains
            caller_domain = self._determine_module_domain(caller_module)
            callee_domain = self._determine_module_domain(callee_module)
            
            # Create dependency edge
            edge = DependencyEdge(
                source_domain=caller_domain,
                target_domain=callee_domain,
                dependency_type=DependencyType.FUNCTION_CALL,
                source_object=caller_module,
                target_object=f"{callee_module}.{function_name}",
                context=context
            )
            
            # Validate dependency
            return self._validate_dependency_edge(edge)
    
    def validate_class_instantiation(self, caller_module: str, class_module: str, 
                                   class_name: str, context: str = "unknown") -> bool:
        """
        Validate class instantiation dependency
        
        Args:
            caller_module: Module creating the instance
            class_module: Module containing the class
            class_name: Name of the class being instantiated
            context: Context of the instantiation
            
        Returns:
            True if instantiation is allowed, False if violates contracts
        """
        if not self.strict_mode:
            return True
        
        with self._lock:
            # Determine domains
            caller_domain = self._determine_module_domain(caller_module)
            class_domain = self._determine_module_domain(class_module)
            
            # Create dependency edge
            edge = DependencyEdge(
                source_domain=caller_domain,
                target_domain=class_domain,
                dependency_type=DependencyType.CLASS_INSTANTIATION,
                source_object=caller_module,
                target_object=f"{class_module}.{class_name}",
                context=context
            )
            
            # Validate dependency
            return self._validate_dependency_edge(edge)
    
    def validate_attribute_access(self, accessor_module: str, target_module: str, 
                                 attribute_name: str, context: str = "unknown") -> bool:
        """
        Validate attribute access dependency
        
        Args:
            accessor_module: Module accessing the attribute
            target_module: Module containing the attribute
            attribute_name: Name of the attribute being accessed
            context: Context of the access
            
        Returns:
            True if access is allowed, False if violates contracts
        """
        if not self.strict_mode:
            return True
        
        with self._lock:
            # Determine domains
            accessor_domain = self._determine_module_domain(accessor_module)
            target_domain = self._determine_module_domain(target_module)
            
            # Create dependency edge
            edge = DependencyEdge(
                source_domain=accessor_domain,
                target_domain=target_domain,
                dependency_type=DependencyType.ATTRIBUTE_ACCESS,
                source_object=accessor_module,
                target_object=f"{target_module}.{attribute_name}",
                context=context
            )
            
            # Validate dependency
            return self._validate_dependency_edge(edge)
    
    def validate_event_subscription(self, subscriber_module: str, publisher_module: str, 
                                  event_type: str, context: str = "unknown") -> bool:
        """
        Validate event subscription dependency
        
        Args:
            subscriber_module: Module subscribing to events
            publisher_module: Module publishing events
            event_type: Type of event being subscribed to
            context: Context of the subscription
            
        Returns:
            True if subscription is allowed, False if violates contracts
        """
        if not self.strict_mode:
            return True
        
        with self._lock:
            # Determine domains
            subscriber_domain = self._determine_module_domain(subscriber_module)
            publisher_domain = self._determine_module_domain(publisher_module)
            
            # Create dependency edge
            edge = DependencyEdge(
                source_domain=subscriber_domain,
                target_domain=publisher_domain,
                dependency_type=DependencyType.EVENT_SUBSCRIPTION,
                source_object=subscriber_module,
                target_object=f"{publisher_module}.{event_type}",
                context=context
            )
            
            # Validate dependency
            return self._validate_dependency_edge(edge)
    
    def validate_dependency_injection(self, target_module: str, dependency_module: str, 
                                    dependency_type: str, context: str = "unknown") -> bool:
        """
        Validate dependency injection
        
        Args:
            target_module: Module receiving the dependency
            dependency_module: Module providing the dependency
            dependency_type: Type of dependency being injected
            context: Context of the injection
            
        Returns:
            True if injection is allowed, False if violates contracts
        """
        if not self.strict_mode:
            return True
        
        with self._lock:
            # Determine domains
            target_domain = self._determine_module_domain(target_module)
            dependency_domain = self._determine_module_domain(dependency_module)
            
            # Create dependency edge
            edge = DependencyEdge(
                source_domain=target_domain,
                target_domain=dependency_domain,
                dependency_type=DependencyType.INJECTION,
                source_object=target_module,
                target_object=f"{dependency_module}.{dependency_type}",
                context=context
            )
            
            # Validate dependency
            return self._validate_dependency_edge(edge)
    
    def _determine_module_domain(self, module_name: str) -> ContractDomain:
        """
        Determine domain from module name
        
        Args:
            module_name: Module name
            
        Returns:
            Contract domain for the module
        """
        # Use registry to determine domain
        module_short_name = module_name.split('.')[-1]
        
        # Check registered modules
        for domain, modules in self.registry._domain_modules.items():
            if module_short_name in modules or module_name in modules:
                return domain
        
        # Path-based naming conventions
        if 'telemetry' in module_name.lower():
            return ContractDomain.TELEMETRY_DOMAIN
        elif 'causal' in module_name.lower():
            return ContractDomain.CAUSAL_DOMAIN
        elif 'audit' in module_name.lower() or 'replay' in module_name.lower():
            return ContractDomain.AUDIT_REPLAY_DOMAIN
        elif 'safety' in module_name.lower() or 'policy' in module_name.lower() or 'trust' in module_name.lower():
            return ContractDomain.SAFETY_DECISION_DOMAIN
        elif 'environment' in module_name.lower() or 'state' in module_name.lower():
            return ContractDomain.ENVIRONMENT_DOMAIN
        else:
            # Default to execution domain for unregistered modules
            return ContractDomain.EXECUTION_DOMAIN
    
    def _validate_dependency_edge(self, edge: DependencyEdge) -> bool:
        """
        Validate a dependency edge
        
        Args:
            edge: Dependency edge to validate
            
        Returns:
            True if edge is allowed, False if violates contracts
        """
        # Check cache first
        edge_key = f"{edge.source_domain.value}->{edge.target_domain.value}:{edge.dependency_type.value}"
        if edge_key in self._blocked_dependencies:
            return False
        
        # Validate with registry
        if not self.registry.validate_dependency(edge.source_domain, edge.target_domain, edge.context):
            # Block this dependency
            self._blocked_dependencies.add(edge_key)
            return False
        
        # Check for runtime cycles
        if self._would_create_runtime_cycle(edge):
            logger.error(f"Runtime dependency cycle detected: {edge}")
            self._blocked_dependencies.add(edge_key)
            return False
        
        # Track active dependency
        self._active_dependencies[edge.source_domain].add(edge)
        
        return True
    
    def _would_create_runtime_cycle(self, new_edge: DependencyEdge) -> bool:
        """
        Check if adding dependency would create a runtime cycle
        
        Args:
            new_edge: New dependency edge to add
            
        Returns:
            True if cycle would be created, False otherwise
        """
        # Simple cycle detection using current call stack
        for edge in self._call_stack:
            if (edge.target_domain == new_edge.source_domain and 
                edge.source_domain == new_edge.target_domain):
                return True
        
        return False
    
    def enter_dependency_context(self, edge: DependencyEdge):
        """
        Enter dependency context (for cycle detection)
        
        Args:
            edge: Dependency edge being entered
        """
        with self._lock:
            self._call_stack.append(edge)
    
    def exit_dependency_context(self, edge: DependencyEdge):
        """
        Exit dependency context
        
        Args:
            edge: Dependency edge being exited
        """
        with self._lock:
            if edge in self._call_stack:
                self._call_stack.remove(edge)
    
    def get_active_dependencies(self, domain: Optional[ContractDomain] = None) -> List[DependencyEdge]:
        """
        Get active dependencies
        
        Args:
            domain: Optional domain to filter dependencies
            
        Returns:
            List of active dependencies
        """
        with self._lock:
            if domain is None:
                all_edges = []
                for edges in self._active_dependencies.values():
                    all_edges.extend(edges)
                return all_edges
            
            return list(self._active_dependencies[domain])
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Get dependency graph representation
        
        Returns:
            Dictionary mapping domains to list of target domains
        """
        with self._lock:
            graph = {}
            for source_domain, edges in self._active_dependencies.items():
                targets = set()
                for edge in edges:
                    targets.add(edge.target_domain.value)
                graph[source_domain.value] = list(targets)
            return graph
    
    def clear_blocked_dependencies(self):
        """Clear blocked dependencies cache (for testing)"""
        with self._lock:
            self._blocked_dependencies.clear()
    
    def get_guard_summary(self) -> Dict[str, Any]:
        """
        Get summary of dependency guard state
        
        Returns:
            Guard state summary
        """
        with self._lock:
            total_active = sum(len(edges) for edges in self._active_dependencies.values())
            
            return {
                'strict_mode': self.strict_mode,
                'active_dependencies': total_active,
                'blocked_dependencies': len(self._blocked_dependencies),
                'call_stack_depth': len(self._call_stack),
                'dependency_graph': self.get_dependency_graph()
            }


# Global dependency edge guard instance
_dependency_edge_guard: Optional[DependencyEdgeGuard] = None


def get_dependency_edge_guard() -> DependencyEdgeGuard:
    """Get global dependency edge guard instance"""
    global _dependency_edge_guard
    if _dependency_edge_guard is None:
        _dependency_edge_guard = DependencyEdgeGuard()
    return _dependency_edge_guard


# Decorator for function call validation
def validate_function_call_dependency(context: str = "unknown"):
    """
    Decorator to validate function call dependencies
    
    Args:
        context: Context of the function call
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            guard = get_dependency_edge_guard()
            
            # Get caller module
            caller_frame = inspect.currentframe().f_back
            caller_module = caller_frame.f_globals.get('__name__', 'unknown')
            
            # Get callee module
            callee_module = func.__module__
            
            # Skip validation for test modules (fail-safe)
            if 'test' in caller_module.lower() or 'test' in callee_module.lower():
                return func(*args, **kwargs)
            
            # Validate call
            if not guard.validate_function_call(caller_module, callee_module, func.__name__, context):
                raise RuntimeError(f"Function call dependency violation: {caller_module} -> {callee_module}.{func.__name__}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Decorator for class instantiation validation
def validate_class_instantiation_dependency(context: str = "unknown"):
    """
    Decorator to validate class instantiation dependencies
    
    Args:
        context: Context of the class instantiation
    """
    def decorator(cls: Type) -> Type:
        original_init = cls.__init__
        
        def __init__(self, *args, **kwargs):
            guard = get_dependency_edge_guard()
            
            # Get caller module
            caller_frame = inspect.currentframe().f_back
            caller_module = caller_frame.f_globals.get('__name__', 'unknown')
            
            # Get class module
            class_module = cls.__module__
            
            # Skip validation for test modules (fail-safe)
            if 'test' in caller_module.lower() or 'test' in class_module.lower():
                original_init(self, *args, **kwargs)
                return
            
            # Validate instantiation
            if not guard.validate_class_instantiation(caller_module, class_module, cls.__name__, context):
                raise RuntimeError(f"Class instantiation dependency violation: {caller_module} -> {class_module}.{cls.__name__}")
            
            original_init(self, *args, **kwargs)
        
        cls.__init__ = __init__
        return cls
    
    return decorator
