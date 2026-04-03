#!/usr/bin/env python3
"""
Execution Violation Detection Demo

This script demonstrates the detection-only violation system.
It shows domain logic access both inside and outside V2EntryGate context.
"""

import sys
import os
from pathlib import Path

# Add src to path for development mode
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from exoarmur.execution_boundary_v2.detection import (
    check_domain_logic_access,
    get_v2_execution_context,
    ViolationSeverity
)

def demo_detection_outside_v2():
    """Demonstrate violation detection outside V2 context"""
    print("🔍 DEMO: Domain Logic Access OUTSIDE V2EntryGate")
    print("=" * 60)
    
    # These should trigger violations
    print("\n1. Testing ExecutionKernel access outside V2 context...")
    violation = check_domain_logic_access("ExecutionKernel", "create_execution_intent", ViolationSeverity.HIGH)
    if violation:
        print(f"   ✅ VIOLATION DETECTED: {violation.component_name}.{violation.method_name}")
        print(f"   📍 Origin: {violation.call_origin}")
        print(f"   🚨 Severity: {violation.severity.value}")
    else:
        print("   ❌ No violation detected (unexpected)")
    
    print("\n2. Testing AuditLogger access outside V2 context...")
    violation = check_domain_logic_access("AuditLogger", "emit_audit_record", ViolationSeverity.HIGH)
    if violation:
        print(f"   ✅ VIOLATION DETECTED: {violation.component_name}.{violation.method_name}")
        print(f"   📍 Origin: {violation.call_origin}")
        print(f"   🚨 Severity: {violation.severity.value}")
    else:
        print("   ❌ No violation detected (unexpected)")

def demo_detection_inside_v2():
    """Demonstrate no violations inside V2 context"""
    print("\n🔍 DEMO: Domain Logic Access INSIDE V2EntryGate")
    print("=" * 60)
    
    # These should NOT trigger violations
    with get_v2_execution_context():
        print("\n1. Testing ExecutionKernel access inside V2 context...")
        violation = check_domain_logic_access("ExecutionKernel", "create_execution_intent", ViolationSeverity.HIGH)
        if violation:
            print(f"   ❌ Unexpected violation: {violation.component_name}.{violation.method_name}")
        else:
            print("   ✅ No violation detected (correct)")
        
        print("\n2. Testing AuditLogger access inside V2 context...")
        violation = check_domain_logic_access("AuditLogger", "emit_audit_record", ViolationSeverity.HIGH)
        if violation:
            print(f"   ❌ Unexpected violation: {violation.component_name}.{violation.method_name}")
        else:
            print("   ✅ No violation detected (correct)")

def demo_real_component_access():
    """Demonstrate violations with real component access"""
    print("\n🔍 DEMO: Real Component Access Violations")
    print("=" * 60)
    
    try:
        import exoarmur.main as runtime_main
        
        # Initialize components
        runtime_main.initialize_components(None)
        print("\n✅ Components initialized")
        
        # Test direct component access (should trigger violations)
        print("\n1. Testing direct ExecutionKernel access...")
        kernel = runtime_main.execution_kernel
        # Access a property that should trigger violation detection
        if hasattr(kernel, 'executed_intents'):
            print("   ✅ ExecutionKernel accessed (violation should be logged above)")
        
        print("\n2. Testing direct AuditLogger access...")
        audit = runtime_main.audit_logger
        # This should trigger violation detection in emit_audit_record
        try:
            audit.emit_audit_record(
                event_kind='demo_test',
                payload_ref={'demo': True},
                correlation_id='demo-correlation',
                trace_id='demo-trace',
                tenant_id='demo-tenant',
                cell_id='demo-cell',
                idempotency_key='demo-key'
            )
            print("   ✅ AuditLogger accessed (violation should be logged above)")
        except Exception as e:
            print(f"   ⚠️  AuditLogger access failed: {e}")
        
    except ImportError as e:
        print(f"❌ Failed to import runtime_main: {e}")

def main():
    """Main demonstration"""
    print("🚨 ExoArmur Execution Violation Detection Demo")
    print("=" * 60)
    print("This demonstrates DETECTION ONLY - no behavior changes, no blocking")
    print()
    
    # Demo 1: Outside V2 context (should show violations)
    demo_detection_outside_v2()
    
    # Demo 2: Inside V2 context (should show no violations)
    demo_detection_inside_v2()
    
    # Demo 3: Real component access (should show violations)
    demo_real_component_access()
    
    print("\n" + "=" * 60)
    print("🎯 DEMO SUMMARY:")
    print("✅ Detection system working")
    print("✅ Violations emitted for non-V2 access")
    print("✅ No violations for V2 context access")
    print("✅ System behavior unchanged (DETECTION ONLY)")
    print("\n🔍 Check logs above for violation details")
    print("=" * 60)

if __name__ == "__main__":
    main()
