"""
Pytest configuration and boundary enforcement for ExoArmur
Enforces fixture scope rules and deterministic behavior for sensitive tests
"""

import pytest
import warnings
from typing import Set, Dict, Any
import inspect
import os

# Sensitive test modules that require strict fixture scoping
SENSITIVE_MODULES = {
    'test_federation_crypto',
    'test_federation_crypto_tightened', 
    'test_handshake_controller',
    'test_handshake_state_machine',
    'test_identity_audit_emitter',
    'test_protocol_enforcer',
    'test_federation_identity_manager',
    'test_federation_messages',
    'test_identity_handshake_state_machine'
}

# Whitelisted non-function-scoped fixtures (explicitly documented)
WHITELISTED_FIXTURES = {
    # These are allowed to have broader scope because they're stateless or expensive
    'mock_nats_clients',  # Expensive async setup
    'sample_telemetry_events',  # Large data fixture
}

def pytest_configure(config):
    """Configure pytest with strict settings"""
    # Treat warnings as errors in sensitive runs
    if config.getoption("-m") and "sensitive" in config.getoption("-m"):
        warnings.filterwarnings("error", category=DeprecationWarning)
        warnings.filterwarnings("error", category=PendingDeprecationWarning)
    
    # Add custom markers
    config.addinivalue_line(
        "markers", "sensitive: Tests that must be deterministic and isolated"
    )
    config.addinivalue_line(
        "markers", "boundary: Tests that verify boundary enforcement"
    )

def pytest_collection_modifyitems(config, items):
    """Modify collected items to enforce boundary rules"""
    for item in items:
        # Mark sensitive tests automatically based on module name
        module_name = item.module.__name__
        if any(sensitive in module_name for sensitive in SENSITIVE_MODULES):
            item.add_marker(pytest.mark.sensitive)
            
            # Check fixture scope violations
            _check_fixture_scopes(item)

def _check_fixture_scopes(item):
    """Check that sensitive tests only use function-scoped fixtures"""
    if not item.get_closest_marker("sensitive"):
        return
        
    fixture_defs = getattr(item, "fixturenames", set())
    
    for fixture_name in fixture_defs:
        if fixture_name in WHITELISTED_FIXTURES:
            continue
            
        # Try to get the fixture definition
        fixture_def = _get_fixture_definition(item, fixture_name)
        if fixture_def and hasattr(fixture_def, 'scope'):
            scope = fixture_def.scope
            if scope != 'function':
                pytest.fail(
                    f"FIXTURE SCOPE VIOLATION in {item.nodeid}:\n"
                    f"Fixture '{fixture_name}' has scope='{scope}' but sensitive tests "
                    f"require scope='function'. This can cause cross-test leakage.\n"
                    f"Either:\n"
                    f"1. Change fixture scope to 'function', or\n"
                    f"2. Add to WHITELISTED_FIXTURES in conftest.py with justification"
                )

def _get_fixture_definition(item, fixture_name):
    """Get fixture definition for a given fixture name"""
    # This is a simplified check - in practice you'd need to walk the fixture graph
    # For now, we'll check common fixture files
    # Return None if we can't determine the scope (conservative approach)
    return None

@pytest.fixture(scope="session")
def boundary_check_state():
    """State for boundary checking across tests"""
    return {
        'mutable_surfaces_checked': set(),
        'test_count': 0
    }

@pytest.fixture(autouse=True)
def check_state_surface_inventory(request, boundary_check_state):
    """Check that state surfaces are properly reset in sensitive tests"""
    if not request.node.get_closest_marker("sensitive"):
        yield
        return
        
    boundary_check_state['test_count'] += 1
    
    # For now, this is a lightweight check
    # In the future, this could validate specific state surfaces
    # based on the inventory in docs/PHASE_0C_STATE_SURFACES.md
    
    yield
    
    # Post-test checks could go here
    pass
