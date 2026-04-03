"""
Regression tests for Boundary Contract Enforcement Layer
Ensures strict domain separation and prevents architectural coupling
"""

import pytest
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from exoarmur.boundary.boundary_contract_registry import (
    BoundaryContractRegistry, ContractDomain, SchemaFingerprint, ContractViolation,
    get_boundary_contract_registry, configure_boundary_contract_registry,
    validate_contract_boundary
)
from exoarmur.boundary.boundary_module_registrar import (
    BoundaryContractModuleRegistrar, ModuleRegistrationConfig, get_boundary_module_registrar,
    register_to_domain, auto_register_exoarmur_modules
)
from exoarmur.boundary.dependency_edge_guard import (
    DependencyEdgeGuard, DependencyType, DependencyEdge, get_dependency_edge_guard,
    validate_function_call_dependency, validate_class_instantiation_dependency
)


class TestBoundaryContractRegistry:
    """Test boundary contract registry functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.registry = BoundaryContractRegistry(strict_mode=True)
    
    def teardown_method(self):
        """Cleanup after tests"""
        # Clear violations for clean test state
        self.registry.clear_violations()
    
    def test_module_registration(self):
        """Test module registration to domains"""
        # Register module to telemetry domain
        success = self.registry.register_module("telemetry_handler", ContractDomain.TELEMETRY_DOMAIN)
        assert success is True
        
        # Check module is registered
        modules = self.registry._domain_modules[ContractDomain.TELEMETRY_DOMAIN]
        assert "telemetry_handler" in modules
        
        # Try to register same module to different domain (should fail)
        success = self.registry.register_module("telemetry_handler", ContractDomain.CAUSAL_DOMAIN)
        assert success is False
        
        # Check violations
        violations = self.registry.get_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "MODULE_DOMAIN_CONFLICT"
    
    def test_schema_registration(self):
        """Test schema registration and fingerprinting"""
        # Define test schema
        @dataclass
        class TestSchema:
            field1: str
            field2: int
            field3: bool = True
        
        # Register schema to telemetry domain
        success = self.registry.register_schema("TestSchema", ContractDomain.TELEMETRY_DOMAIN, TestSchema)
        assert success is True
        
        # Check schema is registered
        schemas = self.registry._schema_fingerprints[ContractDomain.TELEMETRY_DOMAIN]
        assert "TestSchema" in schemas
        
        fingerprint = schemas["TestSchema"]
        assert fingerprint.schema_name == "TestSchema"
        assert fingerprint.domain == ContractDomain.TELEMETRY_DOMAIN
        assert fingerprint.field_count == 3
        assert "field1" in fingerprint.field_types
        assert "field2" in fingerprint.field_types
        assert "field3" in fingerprint.field_types
    
    def test_cross_domain_schema_reuse_detection(self):
        """Test detection of cross-domain schema reuse"""
        # Define test schema
        @dataclass
        class SharedSchema:
            field1: str
            field2: int
        
        # Register schema to telemetry domain
        success1 = self.registry.register_schema("SharedSchema", ContractDomain.TELEMETRY_DOMAIN, SharedSchema)
        assert success1 is True
        
        # Try to register same schema to causal domain (should fail)
        success2 = self.registry.register_schema("SharedSchema", ContractDomain.CAUSAL_DOMAIN, SharedSchema)
        assert success2 is False
        
        # Check violations
        violations = self.registry.get_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "CROSS_DOMAIN_SCHEMA_REUSE"
    
    def test_dependency_validation(self):
        """Test dependency validation between domains"""
        # Valid dependency: execution -> telemetry
        success = self.registry.validate_dependency(
            ContractDomain.EXECUTION_DOMAIN, 
            ContractDomain.TELEMETRY_DOMAIN,
            "test_context"
        )
        assert success is True
        
        # Invalid dependency: telemetry -> causal (forbidden)
        success = self.registry.validate_dependency(
            ContractDomain.TELEMETRY_DOMAIN,
            ContractDomain.CAUSAL_DOMAIN,
            "test_context"
        )
        assert success is False
        
        # Check violations
        violations = self.registry.get_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "FORBIDDEN_DEPENDENCY"
    
    def test_dependency_cycle_detection(self):
        """Test dependency cycle detection"""
        # Create a cycle: A -> B -> C -> A
        self.registry.validate_dependency(ContractDomain.EXECUTION_DOMAIN, ContractDomain.TELEMETRY_DOMAIN, "test")
        self.registry.validate_dependency(ContractDomain.TELEMETRY_DOMAIN, ContractDomain.AUDIT_REPLAY_DOMAIN, "test")
        
        # Try to create cycle back to execution
        success = self.registry.validate_dependency(
            ContractDomain.AUDIT_REPLAY_DOMAIN,
            ContractDomain.EXECUTION_DOMAIN,
            "test_context"
        )
        
        # This should be allowed (audit_replay can read from execution)
        assert success is True
        
        # But if we try to create a forbidden cycle, it should fail
        # Create a scenario that would create a cycle with forbidden dependencies
        self.registry.validate_dependency(ContractDomain.CAUSAL_DOMAIN, ContractDomain.TELEMETRY_DOMAIN, "test")
        
        # This should fail due to cycle detection
        success = self.registry.validate_dependency(
            ContractDomain.TELEMETRY_DOMAIN,
            ContractDomain.CAUSAL_DOMAIN,
            "test_context"
        )
        assert success is False
    
    def test_schema_drift_detection(self):
        """Test schema drift detection"""
        # Define initial schema
        @dataclass
        class TestSchema:
            field1: str
            field2: int
        
        # Register schema
        self.registry.register_schema("TestSchema", ContractDomain.TELEMETRY_DOMAIN, TestSchema)
        
        # Define drifted schema
        @dataclass
        class DriftedTestSchema:
            field1: str
            field2: int
            field3: str  # New field
        
        # Check for drift (should detect)
        success = self.registry.check_schema_drift("TestSchema", ContractDomain.TELEMETRY_DOMAIN, DriftedTestSchema)
        assert success is False
        
        # Check violations
        violations = self.registry.get_violations()
        assert len(violations) == 1
        assert violations[0].violation_type == "SCHEMA_DRIFT"
    
    def test_contract_boundary_decorator(self):
        """Test contract boundary validation decorator"""
        # Define test function with decorator
        @validate_contract_boundary(ContractDomain.EXECUTION_DOMAIN, ContractDomain.TELEMETRY_DOMAIN, "test")
        def test_function():
            return "success"
        
        # This should work (valid dependency)
        result = test_function()
        assert result == "success"
        
        # Define function with invalid dependency
        @validate_contract_boundary(ContractDomain.TELEMETRY_DOMAIN, ContractDomain.CAUSAL_DOMAIN, "test")
        def invalid_function():
            return "success"
        
        # This should raise exception (invalid dependency)
        with pytest.raises(RuntimeError):
            invalid_function()
    
    def test_domain_summary(self):
        """Test domain summary generation"""
        # Register some modules and schemas
        self.registry.register_module("test_module", ContractDomain.TELEMETRY_DOMAIN)
        
        @dataclass
        class TestSchema:
            field1: str
        
        self.registry.register_schema("TestSchema", ContractDomain.TELEMETRY_DOMAIN, TestSchema)
        
        # Get summary
        summary = self.registry.get_domain_summary()
        
        assert 'domains' in summary
        assert 'dependencies' in summary
        assert 'violation_count' in summary
        assert 'strict_mode' in summary
        
        telemetry_summary = summary['domains']['telemetry']
        assert telemetry_summary['module_count'] == 1
        assert telemetry_summary['schema_count'] == 1


class TestBoundaryModuleRegistrar:
    """Test boundary module registrar functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.registry = BoundaryContractRegistry(strict_mode=True)
        self.registrar = BoundaryContractModuleRegistrar(self.registry)
    
    def test_domain_determination_from_module_path(self):
        """Test domain determination from module paths"""
        # Test telemetry domain
        domain = self.registrar.determine_domain_from_module_path("exoarmur.telemetry.v2_telemetry_handler")
        assert domain == ContractDomain.TELEMETRY_DOMAIN
        
        # Test causal domain
        domain = self.registrar.determine_domain_from_module_path("exoarmur.causal.causal_context_logger")
        assert domain == ContractDomain.CAUSAL_DOMAIN
        
        # Test audit domain
        domain = self.registrar.determine_domain_from_module_path("exoarmur.audit.audit_normalizer")
        assert domain == ContractDomain.AUDIT_REPLAY_DOMAIN
        
        # Test default execution domain
        domain = self.registrar.determine_domain_from_module_path("exoarmur.core.some_module")
        assert domain == ContractDomain.EXECUTION_DOMAIN
    
    def test_module_config_registration(self):
        """Test module configuration registration"""
        config = ModuleRegistrationConfig(
            module_name="custom_module",
            domain=ContractDomain.TELEMETRY_DOMAIN,
            schemas=["CustomSchema"]
        )
        
        self.registrar.register_module_config(config)
        
        # Check config is registered
        assert "custom_module" in self.registrar._registration_configs
        registered_config = self.registrar._registration_configs["custom_module"]
        assert registered_config.domain == ContractDomain.TELEMETRY_DOMAIN
        assert "CustomSchema" in registered_config.schemas
    
    def test_module_registration_by_path(self):
        """Test module registration by path"""
        # This should work (mock module path)
        success = self.registrar.register_module_by_path("exoarmur.telemetry.v2_telemetry_handler")
        assert success is True
        
        # Check module is registered to correct domain
        modules = self.registry._domain_modules[ContractDomain.TELEMETRY_DOMAIN]
        assert "v2_telemetry_handler" in modules
    
    def test_registration_decorator(self):
        """Test registration decorator"""
        @register_to_domain(ContractDomain.TELEMETRY_DOMAIN, schemas=["TestSchema"])
        class TestModule:
            @dataclass
            class TestSchema:
                field1: str
        
        # Check module is registered
        registrar = get_boundary_module_registrar()
        config = registrar._registration_configs.get("TestModule")
        assert config is not None
        assert config.domain == ContractDomain.TELEMETRY_DOMAIN
        assert "TestSchema" in config.schemas


class TestDependencyEdgeGuard:
    """Test dependency edge guard functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.registry = BoundaryContractRegistry(strict_mode=True)
        self.guard = DependencyEdgeGuard(self.registry, strict_mode=True)
    
    def teardown_method(self):
        """Cleanup after tests"""
        self.guard.clear_blocked_dependencies()
    
    def test_function_call_validation(self):
        """Test function call dependency validation"""
        # Valid call: execution -> telemetry
        success = self.guard.validate_function_call(
            "execution_module",
            "telemetry_module",
            "some_function",
            "test_context"
        )
        assert success is True
        
        # Invalid call: telemetry -> causal (forbidden)
        success = self.guard.validate_function_call(
            "telemetry_module",
            "causal_module",
            "some_function",
            "test_context"
        )
        assert success is False
    
    def test_class_instantiation_validation(self):
        """Test class instantiation dependency validation"""
        # Valid instantiation: execution -> telemetry
        success = self.guard.validate_class_instantiation(
            "execution_module",
            "telemetry_module",
            "SomeClass",
            "test_context"
        )
        assert success is True
        
        # Invalid instantiation: telemetry -> causal (forbidden)
        success = self.guard.validate_class_instantiation(
            "telemetry_module",
            "causal_module",
            "SomeClass",
            "test_context"
        )
        assert success is False
    
    def test_attribute_access_validation(self):
        """Test attribute access dependency validation"""
        # Valid access: execution -> telemetry
        success = self.guard.validate_attribute_access(
            "execution_module",
            "telemetry_module",
            "some_attribute",
            "test_context"
        )
        assert success is True
        
        # Invalid access: telemetry -> causal (forbidden)
        success = self.guard.validate_attribute_access(
            "telemetry_module",
            "causal_module",
            "some_attribute",
            "test_context"
        )
        assert success is False
    
    def test_event_subscription_validation(self):
        """Test event subscription dependency validation"""
        # Valid subscription: execution -> telemetry
        success = self.guard.validate_event_subscription(
            "execution_module",
            "telemetry_module",
            "some_event",
            "test_context"
        )
        assert success is True
        
        # Invalid subscription: telemetry -> causal (forbidden)
        success = self.guard.validate_event_subscription(
            "telemetry_module",
            "causal_module",
            "some_event",
            "test_context"
        )
        assert success is False
    
    def test_dependency_injection_validation(self):
        """Test dependency injection validation"""
        # Valid injection: execution -> telemetry
        success = self.guard.validate_dependency_injection(
            "execution_module",
            "telemetry_module",
            "SomeService",
            "test_context"
        )
        assert success is True
        
        # Invalid injection: telemetry -> causal (forbidden)
        success = self.guard.validate_dependency_injection(
            "telemetry_module",
            "causal_module",
            "SomeService",
            "test_context"
        )
        assert success is False
    
    def test_dependency_caching(self):
        """Test dependency validation caching"""
        # First invalid call should fail and cache the result
        success1 = self.guard.validate_function_call(
            "telemetry_module",
            "causal_module",
            "some_function",
            "test_context"
        )
        assert success1 is False
        
        # Second identical call should also fail (from cache)
        success2 = self.guard.validate_function_call(
            "telemetry_module",
            "causal_module",
            "some_function",
            "test_context"
        )
        assert success2 is False
        
        # Check blocked dependencies
        assert len(self.guard._blocked_dependencies) > 0
    
    def test_active_dependencies_tracking(self):
        """Test active dependencies tracking"""
        # Add some valid dependencies
        self.guard.validate_function_call("execution_module", "telemetry_module", "func1", "test")
        self.guard.validate_class_instantiation("execution_module", "causal_module", "Class1", "test")
        
        # Get active dependencies
        active_deps = self.guard.get_active_dependencies()
        assert len(active_deps) >= 2
        
        # Get dependencies for specific domain
        execution_deps = self.guard.get_active_dependencies(ContractDomain.EXECUTION_DOMAIN)
        assert len(execution_deps) >= 2
    
    def test_dependency_graph(self):
        """Test dependency graph generation"""
        # Add some dependencies
        self.guard.validate_function_call("execution_module", "telemetry_module", "func1", "test")
        self.guard.validate_function_call("execution_module", "causal_module", "func2", "test")
        
        # Get dependency graph
        graph = self.guard.get_dependency_graph()
        assert 'execution' in graph
        assert 'telemetry' in graph['execution']
        assert 'causal' in graph['execution']
    
    def test_guard_summary(self):
        """Test guard state summary"""
        # Add some dependencies
        self.guard.validate_function_call("execution_module", "telemetry_module", "func1", "test")
        
        # Get summary
        summary = self.guard.get_guard_summary()
        
        assert 'strict_mode' in summary
        assert 'active_dependencies' in summary
        assert 'blocked_dependencies' in summary
        assert 'call_stack_depth' in summary
        assert 'dependency_graph' in summary
        
        assert summary['strict_mode'] is True
        assert summary['active_dependencies'] >= 1
    
    def test_function_call_decorator(self):
        """Test function call validation decorator"""
        # Define function with valid dependency
        @validate_function_call_dependency("test_context")
        def valid_function():
            return "success"
        
        # This should work
        result = valid_function()
        assert result == "success"
        
        # Define function with invalid dependency (mock scenario)
        # Note: This is hard to test without actual module structure
        # The decorator would need to be integrated with actual module imports
    
    def test_class_instantiation_decorator(self):
        """Test class instantiation validation decorator"""
        # Define class with valid dependency
        @validate_class_instantiation_dependency("test_context")
        class ValidClass:
            def __init__(self):
                self.value = "test"
        
        # This should work
        instance = ValidClass()
        assert instance.value == "test"


class TestBoundaryContractIntegration:
    """Test integration of boundary contract components"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.registry = BoundaryContractRegistry(strict_mode=True)
        self.registrar = BoundaryContractModuleRegistrar(self.registry)
        self.guard = DependencyEdgeGuard(self.registry, strict_mode=True)
    
    def test_end_to_end_contract_enforcement(self):
        """Test end-to-end contract enforcement"""
        # Register modules to domains
        self.registry.register_module("telemetry_handler", ContractDomain.TELEMETRY_DOMAIN)
        self.registry.register_module("causal_logger", ContractDomain.CAUSAL_DOMAIN)
        self.registry.register_module("execution_engine", ContractDomain.EXECUTION_DOMAIN)
        
        # Test valid dependencies
        assert self.guard.validate_function_call("execution_engine", "telemetry_handler", "log", "test")
        assert self.guard.validate_function_call("execution_engine", "causal_logger", "track", "test")
        
        # Test invalid dependencies
        assert not self.guard.validate_function_call("telemetry_handler", "causal_logger", "access", "test")
        assert not self.guard.validate_function_call("causal_logger", "telemetry_handler", "read", "test")
        
        # Check violations
        violations = self.registry.get_violations()
        assert len(violations) >= 2  # At least 2 forbidden dependencies
    
    def test_contract_violation_reporting(self):
        """Test contract violation reporting"""
        # Create a violation
        self.registry.validate_dependency(
            ContractDomain.TELEMETRY_DOMAIN,
            ContractDomain.CAUSAL_DOMAIN,
            "test_context"
        )
        
        # Get violations
        violations = self.registry.get_violations()
        assert len(violations) == 1
        
        violation = violations[0]
        assert violation.violation_type == "FORBIDDEN_DEPENDENCY"
        assert violation.source_domain == ContractDomain.TELEMETRY_DOMAIN
        assert violation.target_domain == ContractDomain.CAUSAL_DOMAIN
        assert violation.severity == "ERROR"
        
        # Test violation serialization
        violation_dict = violation.to_dict()
        assert 'violation_id' in violation_dict
        assert 'timestamp' in violation_dict
        assert 'violation_type' in violation_dict
        assert 'source_domain' in violation_dict
        assert 'target_domain' in violation_dict
        assert 'description' in violation_dict
    
    def test_fail_safe_behavior(self):
        """Test fail-safe behavior when registry is not available"""
        # Create guard without registry (should fail-safe)
        guard = DependencyEdgeGuard(registry=None, strict_mode=False)
        
        # All validations should pass (fail-safe)
        assert guard.validate_function_call("telemetry", "causal", "func", "test")
        assert guard.validate_class_instantiation("telemetry", "causal", "Class", "test")
        assert guard.validate_attribute_access("telemetry", "causal", "attr", "test")
        assert guard.validate_event_subscription("telemetry", "causal", "event", "test")
        assert guard.validate_dependency_injection("telemetry", "causal", "service", "test")


# Import dataclass for tests
from dataclasses import dataclass
