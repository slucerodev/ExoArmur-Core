"""
Boundary Contract Module Registration System
Automatic registration of modules and schemas to appropriate domains
"""

import inspect
import importlib
import pkgutil
from typing import Dict, Set, List, Optional, Any, Type
from dataclasses import dataclass
import logging

from .boundary_contract_registry import (
    BoundaryContractRegistry, ContractDomain, get_boundary_contract_registry
)

logger = logging.getLogger(__name__)


@dataclass
class ModuleRegistrationConfig:
    """Configuration for module registration"""
    module_name: str
    domain: ContractDomain
    schemas: List[str] = None
    dependencies: List[ContractDomain] = None
    
    def __post_init__(self):
        if self.schemas is None:
            self.schemas = []
        if self.dependencies is None:
            self.dependencies = []


class BoundaryContractModuleRegistrar:
    """
    Automatic module and schema registration system
    
    Scans and registers modules to appropriate domains based on naming conventions
    and explicit configuration
    """
    
    def __init__(self, registry: Optional[BoundaryContractRegistry] = None):
        """
        Initialize module registrar
        
        Args:
            registry: Boundary contract registry instance
        """
        self.registry = registry or get_boundary_contract_registry()
        self._registration_configs: Dict[str, ModuleRegistrationConfig] = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Initialize default registration configurations based on naming conventions"""
        # Telemetry domain modules
        telemetry_modules = [
            'v2_telemetry_handler',
            'telemetry',
            'metrics',
            'monitoring'
        ]
        
        # Causal domain modules
        causal_modules = [
            'causal_context_logger',
            'causal',
            'lineage',
            'traceability'
        ]
        
        # Audit/Replay domain modules
        audit_replay_modules = [
            'audit_normalizer',
            'audit_logger',
            'replay_engine',
            'replay_envelope_builder',
            'audit',
            'replay'
        ]
        
        # Safety/Decision domain modules
        safety_decision_modules = [
            'safety_gate',
            'policy_evaluator',
            'trust_evaluator',
            'safety',
            'policy',
            'trust',
            'decision'
        ]
        
        # Execution domain modules (default)
        execution_modules = [
            'core',
            'execution',
            'engine',
            'processor',
            'handler'
        ]
        
        # Environment domain modules
        environment_modules = [
            'environment',
            'state',
            'context',
            'config'
        ]
        
        # Register telemetry modules
        for module_name in telemetry_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.TELEMETRY_DOMAIN
            )
        
        # Register causal modules
        for module_name in causal_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.CAUSAL_DOMAIN
            )
        
        # Register audit/replay modules
        for module_name in audit_replay_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.AUDIT_REPLAY_DOMAIN
            )
        
        # Register safety/decision modules
        for module_name in safety_decision_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.SAFETY_DECISION_DOMAIN
            )
        
        # Register environment modules
        for module_name in environment_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.ENVIRONMENT_DOMAIN
            )
        
        # Register execution modules (default)
        for module_name in execution_modules:
            self._registration_configs[module_name] = ModuleRegistrationConfig(
                module_name=module_name,
                domain=ContractDomain.EXECUTION_DOMAIN
            )
    
    def register_module_config(self, config: ModuleRegistrationConfig):
        """
        Register a module configuration
        
        Args:
            config: Module registration configuration
        """
        self._registration_configs[config.module_name] = config
        logger.debug(f"Registered module config: {config.module_name} -> {config.domain.value}")
    
    def determine_domain_from_module_path(self, module_path: str) -> ContractDomain:
        """
        Determine domain from module path
        
        Args:
            module_path: Full module path (e.g., 'exoarmur.telemetry.v2_telemetry_handler')
            
        Returns:
            Contract domain for the module
        """
        # Extract module name from path
        parts = module_path.split('.')
        module_name = parts[-1] if parts else module_path
        
        # Check explicit configurations first
        if module_name in self._registration_configs:
            return self._registration_configs[module_name].domain
        
        # Check path-based naming conventions
        if 'telemetry' in module_path.lower():
            return ContractDomain.TELEMETRY_DOMAIN
        elif 'causal' in module_path.lower():
            return ContractDomain.CAUSAL_DOMAIN
        elif 'audit' in module_path.lower() or 'replay' in module_path.lower():
            return ContractDomain.AUDIT_REPLAY_DOMAIN
        elif 'safety' in module_path.lower() or 'policy' in module_path.lower() or 'trust' in module_path.lower():
            return ContractDomain.SAFETY_DECISION_DOMAIN
        elif 'environment' in module_path.lower() or 'state' in module_path.lower():
            return ContractDomain.ENVIRONMENT_DOMAIN
        else:
            # Default to execution domain
            return ContractDomain.EXECUTION_DOMAIN
    
    def register_module_by_path(self, module_path: str) -> bool:
        """
        Register a module by its path
        
        Args:
            module_path: Full module path
            
        Returns:
            True if registration successful, False if violates contracts
        """
        try:
            # Determine domain
            domain = self.determine_domain_from_module_path(module_path)
            
            # Extract module name
            module_name = module_path.split('.')[-1]
            
            # Register module
            success = self.registry.register_module(module_name, domain)
            
            if success:
                logger.debug(f"Registered module {module_path} to {domain.value} domain")
                
                # Try to register schemas from the module
                self._register_module_schemas(module_path, domain)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to register module {module_path}: {e}")
            return False
    
    def _register_module_schemas(self, module_path: str, domain: ContractDomain):
        """
        Register schemas from a module
        
        Args:
            module_path: Module path
            domain: Domain the module belongs to
        """
        try:
            module = importlib.import_module(module_path)
            
            # Find dataclass schemas
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, '__dataclass_fields__'):
                    # This is a dataclass schema
                    schema_name = f"{module_path}.{name}"
                    self.registry.register_schema(schema_name, domain, obj)
                    logger.debug(f"Registered schema {schema_name} to {domain.value} domain")
            
        except Exception as e:
            logger.debug(f"Failed to register schemas for module {module_path}: {e}")
    
    def register_package(self, package_path: str) -> Dict[str, bool]:
        """
        Register all modules in a package
        
        Args:
            package_path: Package path
            
        Returns:
            Dictionary mapping module names to registration success status
        """
        results = {}
        
        try:
            package = importlib.import_module(package_path)
            
            # Import all submodules
            for importer, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                if not ispkg:
                    success = self.register_module_by_path(modname)
                    results[modname] = success
                    if not success:
                        logger.warning(f"Failed to register module {modname}")
        
        except Exception as e:
            logger.error(f"Failed to register package {package_path}: {e}")
        
        return results
    
    def validate_all_dependencies(self) -> bool:
        """
        Validate all registered dependencies
        
        Returns:
            True if all dependencies are valid, False if violations found
        """
        violations = self.registry.get_violations()
        
        if violations:
            logger.error(f"Found {len(violations)} contract violations:")
            for violation in violations:
                logger.error(f"  - {violation.description}")
            return False
        
        logger.info("All contract dependencies validated successfully")
        return True
    
    def get_registration_summary(self) -> Dict[str, Any]:
        """
        Get summary of module registrations
        
        Returns:
            Registration summary
        """
        return {
            'registered_configs': len(self._registration_configs),
            'configs': {
                name: {
                    'domain': config.domain.value,
                    'schemas': config.schemas,
                    'dependencies': [d.value for d in config.dependencies]
                }
                for name, config in self._registration_configs.items()
            },
            'domain_summary': self.registry.get_domain_summary()
        }


# Global module registrar instance
_boundary_module_registrar: Optional[BoundaryContractModuleRegistrar] = None


def get_boundary_module_registrar() -> BoundaryContractModuleRegistrar:
    """Get global boundary module registrar instance"""
    global _boundary_module_registrar
    if _boundary_module_registrar is None:
        _boundary_module_registrar = BoundaryContractModuleRegistrar()
    return _boundary_module_registrar


def auto_register_exoarmur_modules() -> Dict[str, bool]:
    """
    Automatically register all ExoArmur modules to appropriate domains
    
    Returns:
        Dictionary mapping module names to registration success status
    """
    registrar = get_boundary_module_registrar()
    results = {}
    
    # Register core packages
    packages_to_register = [
        'exoarmur.telemetry',
        'exoarmur.causal',
        'exoarmur.audit',
        'exoarmur.replay',
        'exoarmur.boundary',
        'exoarmur.execution_boundary_v2',
        'exoarmur.core'
    ]
    
    for package_path in packages_to_register:
        package_results = registrar.register_package(package_path)
        results.update(package_results)
    
    # Validate all dependencies
    registrar.validate_all_dependencies()
    
    logger.info(f"Auto-registration completed: {len(results)} modules processed")
    return results


# Decorator for automatic module registration
def register_to_domain(domain: ContractDomain, schemas: Optional[List[str]] = None):
    """
    Decorator to automatically register a module to a domain
    
    Args:
        domain: Domain to register the module to
        schemas: List of schema names to register
    """
    def decorator(module):
        registrar = get_boundary_module_registrar()
        
        # Register module
        module_name = module.__name__.split('.')[-1]
        config = ModuleRegistrationConfig(
            module_name=module_name,
            domain=domain,
            schemas=schemas or []
        )
        registrar.register_module_config(config)
        
        # Register schemas if specified
        if schemas:
            registry = registrar.registry
            for schema_name in schemas:
                if hasattr(module, schema_name):
                    schema_obj = getattr(module, schema_name)
                    full_schema_name = f"{module.__name__}.{schema_name}"
                    registry.register_schema(full_schema_name, domain, schema_obj)
        
        return module
    
    return decorator
