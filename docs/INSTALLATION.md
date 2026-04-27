# ExoArmur Core Installation Guide

## 🚀 Quick Installation (5 minutes)

### Prerequisites
- **Python 3.10+** (tested on 3.10–3.12)
- **pip** (Python package manager)
- **512MB RAM** minimum
- **Authorized evaluation access** — this repository is distributed under a proprietary evaluation license

### Authorized Evaluator Installation

ExoArmur Core is currently distributed as a private evaluation repository. Installation requires authorized access to this repository.

```bash
# Clone the repository (requires authorized access)
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
python examples/quickstart_replay.py
```

**Important**: Access to and use of ExoArmur Core is governed by the LICENSE file in this repository. Distribution, public posting, or commercial use requires explicit written agreement.

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

### Method 1: Authorized Repository Clone (Recommended)

This is the current distribution method for authorized evaluators.

```bash
# Clone the repository (requires authorized access)
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

### Method 3: Docker Installation (Not Currently Available)

Docker images are not currently publicly distributed. For authorized evaluators requiring containerized deployment, contact the maintainer for access instructions.

### Method 4: Conda Installation

Conda installation is not currently available. Use the authorized repository clone method with a conda-managed Python environment:

```bash
# Create conda environment
conda create -n exoarmur python=3.12
conda activate exoarmur

# Clone and install from repository
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core
pip install -e ".[dev]"
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
# ✅ ExoArmur v2.1.0 installed
# ✅ CLI available: ExoArmur v2.1.0
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

# Or add python to PATH
export PATH="/usr/local/bin:$PATH"
```

#### Issue: "ModuleNotFoundError: No module named 'exoarmur'"
**Solution:**
```bash
# Ensure you're in the repository directory and virtual environment is active
cd ExoArmur-Core
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Reinstall in development mode
pip install -e ".[dev]"

# Verify installation
python -c "import exoarmur; print(exoarmur.__version__)"
```

#### Issue: "exoarmur: command not found"
**Solution:**
```bash
# Use python -m instead
python -m exoarmur --version

# Or ensure virtual environment is active
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
exoarmur --version
```

#### Issue: Permission denied
**Solution:**
```bash
# Use virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

#### Issue: SSL certificate errors
**Solution:**
```bash
# Update pip
python3 -m pip install --upgrade pip

# If cloning from GitHub fails due to SSL, configure git:
git config --global http.sslVerify false
git clone https://github.com/slucerodev/ExoArmur-Core.git
git config --global http.sslVerify true
```

### Platform-Specific Issues

#### macOS
```bash
# If you get "xcrun: error: invalid active developer path"
xcode-select --install

# For M1/M2 Macs, use:
softwareupdate --install-rosetta --agree-to-license
arch -x86_64 python3 -m pip install -e ".[dev]"
```

#### Windows
```bash
# Use PowerShell instead of Command Prompt
# Install from PowerShell:
python -m pip install -e ".[dev]"

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
# Pull latest changes from repository
git pull origin main

# Update dependencies
pip install -e ".[dev]"

# Verify upgrade
python -m pytest -q
python examples/quickstart_replay.py
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
# Exit virtual environment
deactivate  # On Windows: deactivate

# Remove virtual environment
rm -rf .venv

# Remove configuration
rm -rf ~/.exoarmur

# Remove repository clone
cd ..
rm -rf ExoArmur-Core
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
- [README.md](../README.md) — Main project documentation
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) — Current status and phase information
- [docs/](./) — Additional documentation

### 4. Evaluation Support
- For authorized evaluators, contact the maintainer for support
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the troubleshooting section** above
2. **Run the verification script**: `python scripts/verify_installation.sh`
3. **Review the documentation**: [README.md](../README.md), [PROJECT_STATUS.md](../PROJECT_STATUS.md)
4. For authorized evaluators, contact the maintainer directly

---

## 🎉 You're Ready!

Once you've completed installation and verification, you're ready to:

- 🚀 **Run your first governance action**
- 📊 **Process telemetry events**
- 🔒 **Enforce deterministic policies**
- 📋 **Generate audit trails**
- 🔄 **Replay decisions**

Welcome to ExoArmur! 🎯