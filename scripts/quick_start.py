#!/usr/bin/env python3
"""
ExoArmur Quick Start Script
Demonstrates basic ExoArmur functionality in 5 minutes
"""

import sys
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_banner():
    """Print ExoArmur banner"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    ExoArmur Core v0.3.0                        ║
║              Deterministic Governance Runtime                   ║
╚══════════════════════════════════════════════════════════════╝
    """)

def check_dependencies():
    """Check if ExoArmur is properly installed"""
    print("🔍 Checking dependencies...")
    
    try:
        from exoarmur import PhaseGate, ReplayEngine, __version__
        print(f"✅ ExoArmur v{__version__} found")
    except ImportError as e:
        print(f"❌ ExoArmur not found: {e}")
        print("💡 Install with: pip install exoarmur-core")
        return False
    
    try:
        print("✅ Core components importable")
    except ImportError as e:
        print(f"❌ Core components not importable: {e}")
        return False
    
    return True

def demo_phase_gate():
    """Demonstrate PhaseGate functionality"""
    print("\n🎛️  Demo: Phase Gate")
    print("=" * 40)
    
    try:
        from exoarmur.core.phase_gate import PhaseGate
        
        # Create phase gate
        phase_gate = PhaseGate()
        print("✅ PhaseGate initialized")
        
        # Check current phase
        current_phase = phase_gate.get_current_phase()
        print(f"📋 Current phase: {current_phase}")
        
        # Check Phase 2 eligibility
        try:
            phase_gate.check_phase_2_eligibility("demo_check")
            print("✅ Phase 2 eligibility check passed")
        except Exception as e:
            print(f"⚠️  Phase 2 eligibility check: {e}")
            print("   (Expected if Phase 2 is not enabled)")
            
    except Exception as e:
        print(f"⚠️  Phase gate demo error: {e}")

def demo_deterministic_timestamps():
    """Demonstrate deterministic timestamp functionality"""
    print("\n🔒 Demo: Deterministic Timestamps")
    print("=" * 40)
    
    try:
        from exoarmur.clock import deterministic_timestamp
        
        # Generate timestamps with same seed
        ts1 = deterministic_timestamp("demo", "test-seed")
        time.sleep(0.1)  # Small delay
        ts2 = deterministic_timestamp("demo", "test-seed")
        
        print(f"📅 Timestamp 1: {ts1.isoformat()}")
        print(f"📅 Timestamp 2: {ts2.isoformat()}")
        
        if ts1 == ts2:
            print("✅ Deterministic timestamps working correctly")
        else:
            print("❌ Deterministic timestamps failed")
            
    except Exception as e:
        print(f"⚠️  Deterministic timestamp demo error: {e}")

def demo_feature_flags():
    """Demonstrate feature flag functionality"""
    print("\n🎛️  Demo: Feature Flags")
    print("=" * 40)
    
    try:
        from exoarmur.feature_flags import get_feature_flags
        
        flags = get_feature_flags()
        all_flags = flags.get_all_flags()
        
        print(f"📋 Total feature flags: {len(all_flags)}")
        print("   Available flags:")
        
        for flag_name, flag_config in all_flags.items():
            status = "ENABLED" if flag_config['current_value'] else "DISABLED"
            print(f"   • {flag_name}: {status}")
            
    except Exception as e:
        print(f"⚠️  Feature flags demo error: {e}")

def demo_replay_engine():
    """Demonstrate replay engine functionality"""
    print("\n🔄 Demo: Replay Engine")
    print("=" * 40)
    
    try:
        from exoarmur.replay.replay_engine import ReplayEngine
        
        # Create replay engine with empty audit store
        replay = ReplayEngine(audit_store={})
        print("🔄 Replay engine initialized")
        
        print("📝 To test replay functionality:")
        print("   1. Run: exoarmur demo --operator-decision deny")
        print("   2. Copy the AUDIT_STREAM_ID from output")
        print("   3. Run: exoarmur replay <AUDIT_STREAM_ID>")
        print("✅ Replay verification available")
        
    except Exception as e:
        print(f"⚠️  Replay demo error: {e}")

def demo_audit_components():
    """Demonstrate audit components"""
    print("\n📋 Demo: Audit Components")
    print("=" * 40)
    
    try:
        from exoarmur.audit.audit_logger import AuditLogger
        
        # Create audit logger
        audit_logger = AuditLogger()
        print("📝 Audit logger initialized")
        
        # Show available methods
        methods = [method for method in dir(audit_logger) if not method.startswith('_')]
        print(f"🔧 Available methods: {len(methods)}")
        for method in methods[:5]:  # Show first 5
            print(f"   • {method}")
        if len(methods) > 5:
            print(f"   ... and {len(methods) - 5} more")
            
    except Exception as e:
        print(f"⚠️  Audit demo error: {e}")

def run_cli_demos():
    """Run CLI demonstrations"""
    print("\n💻 Demo: CLI Commands")
    print("=" * 40)
    
    import subprocess
    
    # Try to run CLI commands
    commands = [
        ["exoarmur", "--version"],
        ["exoarmur", "--help"],
    ]
    
    for cmd in commands:
        try:
            print(f"💻 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Command successful")
                if result.stdout:
                    # Show first few lines of output
                    lines = result.stdout.strip().split('\n')[:3]
                    for line in lines:
                        print(f"   {line}")
                    if len(result.stdout.strip().split('\n')) > 3:
                        print("   ...")
            else:
                print(f"⚠️  Command failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("⚠️  Command timed out")
        except FileNotFoundError:
            print("⚠️  CLI not found - install with: pip install exoarmur-core")
        except Exception as e:
            print(f"⚠️  CLI error: {e}")
        
        print()

def demo_performance():
    """Demonstrate performance characteristics"""
    print("\n⚡ Demo: Performance")
    print("=" * 40)
    
    try:
        from exoarmur.clock import deterministic_timestamp
        import time
        
        # Test deterministic timestamp performance
        print("📊 Testing deterministic timestamp performance...")
        
        iterations = 1000
        start_time = time.time()
        
        for i in range(iterations):
            deterministic_timestamp("perf-test", f"iteration-{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  Generated {iterations} timestamps in {duration:.3f}s")
        print(f"⚡ Average: {(duration/iterations)*1000:.2f}ms per timestamp")
        print("✅ Performance test completed")
        
    except Exception as e:
        print(f"⚠️  Performance demo error: {e}")

def print_next_steps():
    """Print next steps for the user"""
    print("\n🎉 Quick Start Complete!")
    print("=" * 40)
    print("📚 Next Steps:")
    print("• Read the full documentation: https://github.com/slucerodev/ExoArmur-Core")
    print("• Try the V2 demo: exoarmur demo --operator-decision deny")
    print("• Run health check: exoarmur health")
    print("• Explore examples in the examples/ directory")
    print("• Check out the API docs: http://localhost:8000/docs (when running)")
    print()
    print("🔧 Development:")
    print("• Install dev dependencies: pip install -e .[dev]")
    print("• Run tests: pytest -q")
    print("• Contribute: https://github.com/slucerodev/ExoArmur-Core/blob/main/CONTRIBUTING.md")
    print()
    print("🆘 Need Help?")
    print("• Documentation: https://slucerodev.github.io/ExoArmur-Core/docs/")
    print("• Issues: https://github.com/slucerodev/ExoArmur-Core/issues")
    print("• Discussions: https://github.com/slucerodev/ExoArmur-Core/discussions")

def main():
    """Main quick start function"""
    print_banner()
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install ExoArmur first.")
        sys.exit(1)
    
    # Run demos
    demo_phase_gate()
    demo_deterministic_timestamps()
    demo_feature_flags()
    demo_replay_engine()
    demo_audit_components()
    run_cli_demos()
    demo_performance()
    
    # Print next steps
    print_next_steps()

if __name__ == "__main__":
    main()