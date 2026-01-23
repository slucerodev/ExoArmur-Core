"""
Boundary Enforcement Test

Ensures federation modules do not import execution modules.
"""

import ast
import os
import pytest
from pathlib import Path


def get_imports_from_file(file_path):
    """Extract all imports from a Python file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        
        return imports
        
    except (FileNotFoundError, SyntaxError):
        return []


def test_federation_execution_boundary():
    """
    Test that federation modules do not import execution modules
    
    This enforces the architectural boundary between federation and execution layers.
    """
    # Federation module paths
    federation_dir = Path("src/federation")
    
    # Execution module patterns that should not be imported by federation
    forbidden_patterns = [
        "safety_gate",
        "execution_intent", 
        "execution_engine",
        "policy_engine",
        "collective_confidence",
        "local_decision"
    ]
    
    # Allowed execution patterns (shared utilities)
    allowed_patterns = [
        "clock",
        "audit_interface",
        "crypto"
    ]
    
    boundary_violations = []
    
    # Walk through all federation Python files
    if federation_dir.exists():
        for py_file in federation_dir.glob("*.py"):
            imports = get_imports_from_file(py_file)
            
            for imp in imports:
                # Check if import contains forbidden pattern
                for forbidden in forbidden_patterns:
                    if forbidden in imp and not any(allowed in imp for allowed in allowed_patterns):
                        boundary_violations.append(f"{py_file}: imports {imp}")
    
    if boundary_violations:
        pytest.fail(f"Boundary violations found:\n" + "\n".join(boundary_violations))


def test_execution_federation_boundary():
    """
    Test that execution modules do not import federation modules
    
    This ensures the execution layer remains independent of federation specifics.
    """
    # Execution module paths (if they exist)
    execution_dirs = [
        Path("src/execution"),
        Path("src/safety"),
        Path("src/policy")
    ]
    
    # Federation module patterns that should not be imported by execution
    forbidden_patterns = [
        "handshake_controller",
        "observation_ingest",
        "belief_aggregation",
        "arbitration_service",
        "visibility_api",
        "federate_identity_store"
    ]
    
    boundary_violations = []
    
    for exec_dir in execution_dirs:
        if exec_dir.exists():
            for py_file in exec_dir.glob("*.py"):
                imports = get_imports_from_file(py_file)
                
                for imp in imports:
                    for forbidden in forbidden_patterns:
                        if forbidden in imp:
                            boundary_violations.append(f"{py_file}: imports {imp}")
    
    if boundary_violations:
        pytest.fail(f"Boundary violations found:\n" + "\n".join(boundary_violations))


def test_module_layer_isolation():
    """
    Test that modules maintain proper layer isolation
    """
    # Define expected layer structure
    layers = {
        "contracts": ["spec/contracts"],
        "federation": ["src/federation"],
        "execution": ["src/execution", "src/safety", "src/policy"],
        "shared": ["src/federation/clock.py", "src/federation/crypto.py", "src/federation/audit_interface.py"]
    }
    
    # Federation should only import from contracts and shared
    federation_files = []
    federation_dir = Path("src/federation")
    if federation_dir.exists():
        federation_files.extend(federation_dir.glob("*.py"))
    
    for py_file in federation_files:
        imports = get_imports_from_file(py_file)
        
        for imp in imports:
            # Allow imports from contracts
            if imp.startswith("spec.contracts"):
                continue
            
            # Allow imports from shared utilities
            if any(shared in imp for shared in ["clock", "crypto", "audit_interface"]):
                continue
            
            # Allow standard library
            if imp in ["datetime", "typing", "logging", "hashlib", "uuid", "enum", "pydantic", "fastapi"]:
                continue
            
            # Allow local federation imports
            if imp.startswith("src.federation") or not imp.startswith("src"):
                continue
            
            # Anything else is a violation
            pytest.fail(f"Layer violation in {py_file}: imports {imp}")


def test_no_circular_imports():
    """
    Test for circular imports between modules
    """
    # This is a basic check - more sophisticated analysis could be added
    modules = {}
    
    # Build module dependency map
    federation_dir = Path("src/federation")
    if federation_dir.exists():
        for py_file in federation_dir.glob("*.py"):
            module_name = py_file.stem
            imports = get_imports_from_file(py_file)
            
            # Filter to local imports
            local_imports = []
            for imp in imports:
                if imp.startswith("src.federation"):
                    local_imports.append(imp.replace("src.federation.", ""))
            
            modules[module_name] = local_imports
    
    # Check for circular dependencies
    for module, deps in modules.items():
        for dep in deps:
            dep_module = dep.split('.')[0]
            if dep_module in modules:
                # Check if dependency depends back on us
                if module in modules[dep_module]:
                    pytest.fail(f"Circular import detected: {module} <-> {dep_module}")


def test_feature_flag_boundary():
    """
    Test that feature flags properly control module boundaries
    """
    # This test ensures that feature flags create proper boundaries
    # between V1 and V2 functionality
    
    # Check that V2 features are properly gated
    v2_features = [
        "observation_ingest",
        "belief_aggregation", 
        "arbitration_service",
        "visibility_api"
    ]
    
    for feature in v2_features:
        try:
            # Import the module
            module_path = f"src.federation.{feature}"
            module = __import__(module_path, fromlist=[feature])
            
            # Check if the main class has feature flag parameter
            class_name = feature.replace('_', '').title()
            if hasattr(module, class_name):
                cls = getattr(module, class_name)
                
                # Check constructor for feature_flag_enabled parameter
                import inspect
                sig = inspect.signature(cls.__init__)
                
                # Should have feature_flag_enabled parameter with default False
                if 'feature_flag_enabled' in sig.parameters:
                    param = sig.parameters['feature_flag_enabled']
                    assert param.default is False, f"{feature} should default to disabled"
                else:
                    pytest.fail(f"{feature} missing feature_flag_enabled parameter")
                    
        except ImportError:
            # Module doesn't exist - skip
            continue
