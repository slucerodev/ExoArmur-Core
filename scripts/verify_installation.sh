#!/bin/bash

set -euo pipefail

# ExoArmur Installation Verification Script
# Validates that ExoArmur Core is properly installed and functional

echo "🔍 ExoArmur Installation Verification"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "PASS" ]; then
        echo -e "✅ ${GREEN}$message${NC}"
    elif [ "$status" = "FAIL" ]; then
        echo -e "❌ ${RED}$message${NC}"
    elif [ "$status" = "WARN" ]; then
        echo -e "⚠️  ${YELLOW}$message${NC}"
    else
        echo -e "ℹ️  $message"
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    echo "Checking Python version..."
    
    if ! command_exists python3; then
        print_status "FAIL" "Python 3 not found"
        return 1
    fi
    
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local required_version="3.8"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_status "PASS" "Python $python_version (>= $required_version)"
        return 0
    else
        print_status "FAIL" "Python $python_version (< $required_version)"
        return 1
    fi
}

# Function to check package installation
check_package_installation() {
    echo "Checking ExoArmur package installation..."
    
    if ! python3 -c "import exoarmur" 2>/dev/null; then
        print_status "FAIL" "ExoArmur package not importable"
        return 1
    fi
    
    local version=$(python3 -c "import exoarmur; print(getattr(exoarmur, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
    print_status "PASS" "ExoArmur v$version installed"
    return 0
}

# Function to check CLI availability
check_cli_availability() {
    echo "Checking CLI availability..."
    
    if ! command_exists exoarmur; then
        print_status "WARN" "ExoArmur CLI not in PATH (package may be installed but CLI not available)"
        return 1
    fi
    
    local cli_version=$(exoarmur --version 2>/dev/null || echo "unknown")
    print_status "PASS" "CLI available: $cli_version"
    return 0
}

# Function to check core functionality
check_core_functionality() {
    echo "Checking core functionality..."
    
    # Test basic import and initialization using a separate script
    cat > /tmp/test_core.py << 'EOF'
import sys
try:
    from exoarmur import PhaseGate, ReplayEngine, __version__
    print(f'Core imports: SUCCESS (v{__version__})')
except Exception as e:
    print(f'Core imports: FAILED - {e}')
    sys.exit(1)
EOF
    
    if python3 /tmp/test_core.py 2>/dev/null; then
        print_status "PASS" "Core functionality working"
        rm -f /tmp/test_core.py
        return 0
    else
        print_status "FAIL" "Core functionality failed"
        rm -f /tmp/test_core.py
        return 1
    fi
}

# Function to check feature flags
check_feature_flags() {
    echo "Checking feature flags..."
    
    cat > /tmp/test_flags.py << 'EOF'
import sys
try:
    from exoarmur.feature_flags import get_feature_flags
    flags = get_feature_flags()
    print(f'Feature flags loaded: {len(flags.get_all_flags())} configured')
except Exception as e:
    print(f'Feature flags: FAILED - {e}')
    sys.exit(1)
EOF
    
    if python3 /tmp/test_flags.py 2>/dev/null; then
        print_status "PASS" "Feature flags working"
        rm -f /tmp/test_flags.py
        return 0
    else
        print_status "FAIL" "Feature flags failed"
        rm -f /tmp/test_flags.py
        return 1
    fi
}

# Function to check deterministic timestamp
check_deterministic_timestamp() {
    echo "Checking deterministic timestamp functionality..."
    
    cat > /tmp/test_timestamp.py << 'EOF'
import sys
try:
    from exoarmur.clock import deterministic_timestamp
    import time
    
    # Test deterministic behavior
    ts1 = deterministic_timestamp('test', 'seed')
    time.sleep(0.1)
    ts2 = deterministic_timestamp('test', 'seed')
    
    if ts1 == ts2:
        print('Deterministic timestamp: SUCCESS')
    else:
        print('Deterministic timestamp: FAILED - timestamps differ')
        sys.exit(1)
except Exception as e:
    print(f'Deterministic timestamp: FAILED - {e}')
    sys.exit(1)
EOF
    
    if python3 /tmp/test_timestamp.py 2>/dev/null; then
        print_status "PASS" "Deterministic timestamp working"
        rm -f /tmp/test_timestamp.py
        return 0
    else
        print_status "FAIL" "Deterministic timestamp failed"
        rm -f /tmp/test_timestamp.py
        return 1
    fi
}

# Function to run CLI health check
run_cli_health_check() {
    echo "Running CLI health check..."
    
    if command_exists exoarmur; then
        if exoarmur health >/dev/null 2>&1; then
            print_status "PASS" "CLI health check passed"
            return 0
        else
            print_status "FAIL" "CLI health check failed"
            return 1
        fi
    else
        print_status "WARN" "CLI not available, skipping health check"
        return 0
    fi
}

# Function to check dependencies
check_dependencies() {
    echo "Checking critical dependencies..."
    
    local deps=("fastapi" "pydantic" "ulid" "nats" "click" "httpx")
    local missing_deps=()
    
    for dep in "${deps[@]}"; do
        if ! python3 -c "import $dep" 2>/dev/null; then
            missing_deps+=("$dep")
        fi
    done
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        print_status "PASS" "All dependencies available"
        return 0
    else
        print_status "FAIL" "Missing dependencies: ${missing_deps[*]}"
        return 1
    fi
}

# Function to check test suite availability
check_test_suite() {
    echo "Checking test suite..."
    
    if [ -d "tests" ] && [ -f "tests/test_v2_restrained_autonomy.py" ]; then
        print_status "PASS" "Test suite available"
        return 0
    else
        print_status "WARN" "Test suite not found (may not be installed with package)"
        return 0
    fi
}

# Function to provide installation recommendations
provide_recommendations() {
    echo ""
    echo "📋 Installation Recommendations:"
    echo "==============================="
    
    if ! command_exists python3; then
        echo "• Install Python 3.8+: https://www.python.org/downloads/"
    fi
    
    if ! python3 -c "import exoarmur" 2>/dev/null; then
        echo "• Install ExoArmur: pip install exoarmur-core"
        echo "• For development: pip install -e .[dev]"
    fi
    
    if ! command_exists exoarmur; then
        echo "• Ensure pip install directory is in your PATH"
        echo "• Try: python -m pip install --user exoarmur-core"
    fi
    
    echo ""
    echo "📚 Documentation: https://github.com/slucerodev/ExoArmur-Core"
    echo "🐛 Issues: https://github.com/slucerodev/ExoArmur-Core/issues"
}

# Main verification function
main() {
    local failed_checks=0
    
    echo "Starting verification at $(date)"
    echo ""
    
    # Run all checks
    check_python_version || ((failed_checks++))
    check_package_installation || ((failed_checks++))
    check_cli_availability || ((failed_checks++))
    check_dependencies || ((failed_checks++))
    check_core_functionality || ((failed_checks++))
    check_feature_flags || ((failed_checks++))
    check_deterministic_timestamp || ((failed_checks++))
    run_cli_health_check || ((failed_checks++))
    check_test_suite || ((failed_checks++))
    
    echo ""
    echo "📊 Verification Summary:"
    echo "======================="
    
    if [ $failed_checks -eq 0 ]; then
        print_status "PASS" "All checks passed - ExoArmur is properly installed!"
        echo ""
        echo "🚀 Next steps:"
        echo "• Run: exoarmur --help"
        echo "• Try: exoarmur demo --operator-decision deny"
        echo "• Read: https://github.com/slucerodev/ExoArmur-Core#readme"
        exit 0
    else
        print_status "FAIL" "$failed_checks check(s) failed"
        echo ""
        provide_recommendations
        exit 1
    fi
}

# Run main function
main "$@"