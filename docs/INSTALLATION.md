# ExoArmur Core Installation Guide

## 🚀 Quick Installation (5 minutes)

### Prerequisites
- **Python 3.10+** (tested on 3.10–3.12)
- **pip** (Python package manager)
- **512MB RAM** minimum

### One-Command Installation
```bash
pip install exoarmur-core
```

### Verify Installation
```bash
# Check if everything is working
python scripts/verify_installation.sh

# Or run the quick start demo
python scripts/quick_start.py
```

---

## 📋 System Requirements

### Operating Systems
- ✅ **Linux** (Ubuntu 18.04+, CentOS 7+, Debian 9+)
- ✅ **macOS** (10.14+)
- ✅ **Windows** (10+)

### Python Versions
- ✅ **Python 3.10** (minimum)
- ✅ **Python 3.11**
- ✅ **Python 3.12** (recommended for CI)

### Hardware Requirements
- **RAM**: 512MB minimum, 1GB recommended
- **Disk**: 100MB for installation
- **CPU**: Any modern processor

---

## 🛠️ Installation Methods

### Method 1: pip install (Recommended)
```bash
# Standard installation
pip install exoarmur-core

# With development tools
pip install exoarmur-core[dev]

# With V2 capabilities
# V2 capabilities require no additional pip extras.
# They are activated via environment variables at runtime:
# EXOARMUR_FLAG_V2_FEDERATION_ENABLED=true
# EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=true
# EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=true
pip install exoarmur-core

# Everything
pip install exoarmur-core[dev]
```

### Method 2: Development Installation
```bash
# Clone repository
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest -q
```

### Method 3: Docker Installation
```bash
# Pull the image
docker pull exoarmur/exoarmur-core:latest

# Run the container
docker run -it --rm exoarmur/exoarmur-core:latest

# Or with volume mount
docker run -it --rm -v $(pwd):/workspace exoarmur/exoarmur-core:latest
```

### Method 4: Conda Installation
```bash
# Create conda environment
conda create -n exoarmur python=3.12
conda activate exoarmur

# Install from PyPI
pip install exoarmur-core

# Or install with conda-forge (if available)
conda install -c conda-forge exoarmur-core
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Core configuration
export EXOARMUR_LOG_LEVEL=INFO
export EXOARMUR_AUDIT_RETENTION_DAYS=30

# Feature flags
export EXOARMUR_FLAG_V2_FEDERATION_ENABLED=false
export EXOARMUR_FLAG_V2_CONTROL_PLANE_ENABLED=false
export EXOARMUR_FLAG_V2_OPERATOR_APPROVAL_REQUIRED=false

# Infrastructure
export EXOARMUR_NATS_URL=nats://localhost:4222
export EXOARMUR_METRICS_ENABLED=true
```

### Configuration File
Create `~/.exoarmur/config.yaml`:
```yaml
core:
  log_level: INFO
  audit_retention_days: 30

feature_flags:
  v2_federation_enabled: false
  v2_control_plane_enabled: false
  v2_operator_approval_required: false

infrastructure:
  nats_url: nats://localhost:4222
  metrics_enabled: true
  health_check_interval: 30
```

---

## ✅ Verification

### Automated Verification
```bash
# Run comprehensive verification
python scripts/verify_installation.sh

# Expected output:
# ✅ Python 3.12.3 (>= 3.8)
# ✅ ExoArmur v2.0.0 installed
# ✅ CLI available: ExoArmur v2.0.0
# ✅ All dependencies available
# ✅ Core functionality working
# ✅ Feature flags working
# ✅ Deterministic timestamp working
# ✅ CLI health check passed
# ✅ Test suite available
#
# 📊 Verification Summary:
# ======================
# ✅ All checks passed - ExoArmur is properly installed!
```

### Manual Verification
```bash
# Check CLI
exoarmur --version
exoarmur --help

# Check health
exoarmur health

# Run quick start demo
python scripts/quick_start.py

# Run test suite
pytest -q tests/test_v2_restrained_autonomy.py
```

---

## 🚦 Troubleshooting

### Common Issues

#### Issue: "python: command not found"
**Solution:**
```bash
# Use python3 instead
python3 --version
python3 -m pip install exoarmur-core

# Or add python to PATH
export PATH="/usr/local/bin:$PATH"
```

#### Issue: "ModuleNotFoundError: No module named 'exoarmur'"
**Solution:**
```bash
# Check if package is installed
python3 -m pip list | grep exoarmur

# Reinstall if needed
python3 -m pip uninstall exoarmur-core
python3 -m pip install exoarmur-core

# Or try user installation
python3 -m pip install --user exoarmur-core
```

#### Issue: "exoarmur: command not found"
**Solution:**
```bash
# Check pip install location
python3 -c "import site; print(site.USER_SCRIPTS)"

# Add to PATH
export PATH="$(python3 -c "import site; print(site.USER_SCRIPTS)"):$PATH"

# Or use python -m
python3 -m exoarmur --version
```

#### Issue: Permission denied
**Solution:**
```bash
# Use user installation
python3 -m pip install --user exoarmur-core

# Or use virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install exoarmur-core
```

#### Issue: SSL certificate errors
**Solution:**
```bash
# Update pip
python3 -m pip install --upgrade pip

# Use trusted hosts
python3 -m pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org exoarmur-core

# Or use conda
conda install -c conda-forge exoarmur-core
```

### Platform-Specific Issues

#### macOS
```bash
# If you get "xcrun: error: invalid active developer path"
xcode-select --install

# For M1/M2 Macs, use:
softwareupdate --install-rosetta --agree-to-license
arch -x86_64 python3 -m pip install exoarmur-core
```

#### Windows
```bash
# Use PowerShell instead of Command Prompt
# Install from PowerShell:
python -m pip install exoarmur-core

# If you get DLL errors, install Microsoft C++ Build Tools:
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

#### Linux
```bash
# Install build dependencies
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install python3-dev python3-pip build-essential

# CentOS/RHEL:
sudo yum install python3-devel python3-pip gcc
```

---

## 🔄 Upgrading

### Upgrade from Previous Version
```bash
# Check current version
exoarmur --version

# Upgrade to latest
pip install --upgrade exoarmur-core

# Verify upgrade
exoarmur health
```

### Upgrade from Development Installation
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -e ".[dev]"

# Run tests
pytest -q
```

---

## 🗑️ Uninstallation

### Remove Package
```bash
# Uninstall package
pip uninstall exoarmur-core

# Remove configuration
rm -rf ~/.exoarmur

# Remove virtual environment (if used)
deactivate  # Exit virtual environment
rm -rf .venv
```

### Clean Up Docker
```bash
# Remove Docker image
docker rmi exoarmur/exoarmur-core:latest

# Remove all ExoArmur containers
docker rm $(docker ps -a -q --filter ancestor=exoarmur/exoarmur-core)
```

---

## 📚 Next Steps

After successful installation:

### 1. Quick Start
```bash
# Run the quick start demo
python scripts/quick_start.py
```

### 2. Try the CLI
```bash
# Check system health
exoarmur health

# Run a demo
exoarmur demo

# See all commands
exoarmur --help
```

### 3. Read Documentation
- [Main Documentation](https://slucerodev.github.io/ExoArmur-Core/)
- [API Reference](https://slucerodev.github.io/ExoArmur-Core/docs/api/)
- [Examples](https://github.com/slucerodev/ExoArmur-Core/tree/main/examples)

### 4. Join the Community
- [GitHub Discussions](https://github.com/slucerodev/ExoArmur-Core/discussions)
- [Issues](https://github.com/slucerodev/ExoArmur-Core/issues)
- [Contributing Guide](https://github.com/slucerodev/ExoArmur-Core/blob/main/CONTRIBUTING.md)

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Run the verification script**: `python scripts/verify_installation.sh`
3. **Search existing issues**: https://github.com/slucerodev/ExoArmur-Core/issues
4. **Create a new issue**: https://github.com/slucerodev/ExoArmur-Core/issues/new
5. **Join the discussion**: https://github.com/slucerodev/ExoArmur-Core/discussions

### Support Information
- **Documentation**: https://slucerodev.github.io/ExoArmur-Core/docs/
- **Issues**: https://github.com/slucerodev/ExoArmur-Core/issues
- **Discussions**: https://github.com/slucerodev/ExoArmur-Core/discussions
- **Email**: team@exoarmur.dev

---

## 🎉 You're Ready!

Once you've completed installation and verification, you're ready to:

- 🚀 **Run your first governance action**
- 📊 **Process telemetry events**
- 🔒 **Enforce deterministic policies**
- 📋 **Generate audit trails**
- 🔄 **Replay decisions**

Welcome to ExoArmur! 🎯