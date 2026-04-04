# ExoArmur Quickstart

Get ExoArmur-Core running in under 60 seconds with these copy-paste commands.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/slucerodev/ExoArmur-Core.git
cd ExoArmur-Core

# 2. Run the quickstart script
./scripts/quickstart.sh
```

That's it! The script will:
- Set up a Python virtual environment
- Install required dependencies  
- Run a minimal demo execution
- Show you the system is working

## Expected Output

You should see output similar to this:

```
🚀 ExoArmur Quickstart Setup
==========================
✅ Python version check passed (3.12.x)
✅ Repository root check passed
✅ Virtual environment already exists
🔧 Activating virtual environment...
⬆️ Upgrading pip...
📦 Installing quickstart requirements...
✅ Quickstart requirements installed

🎯 Running ExoArmur Quickstart...
==============================
🚀 ExoArmur Quickstart Starting...
==================================================
📋 Generated IDs:
   tenant_id: quickstart_tenant
   cell_id: quickstart_cell
   correlation_id: 12345678-1234-1234-1234-123456789abc
   trace_id: 87654321-4321-4321-4321-cba987654321

✅ Core imports successful
✅ Audit record created
✅ System components initialized
✅ Audit record normalized
✅ Safety evaluation: APPROVED
✅ Audit record stored for replay
✅ Replay test: SUCCESS

🎯 EXECUTION SUCCESS
==================================================
✅ Safety Verdict: APPROVED
✅ Execution Result: Quickstart test completed successfully
✅ Correlation ID: 12345678-1234-1234-1234-123456789abc
✅ Trace ID: 87654321-4321-4321-4321-cba987654321
✅ Replay Status: SUCCESS

🎉 ExoArmur-Core Quickstart completed successfully!
   The system is properly installed and functional.

🎉 Quickstart completed successfully!
ExoArmur-Core is properly installed and functional.
```

## Next Steps

After quickstart completes, run proof mode for deterministic validation:

```bash
exoarmur proof
```

## Troubleshooting

If you see "QUICKSTART FAILED":

1. **Python version**: Ensure you have Python 3.12+ installed
2. **Dependencies**: Run `pip install -r requirements-quickstart.txt` manually
3. **Permissions**: Make sure the script is executable: `chmod +x scripts/quickstart.sh`

## Manual Installation

If the script doesn't work, you can run manually:

```bash
# Setup environment
python3 -m venv venv_quickstart
source venv_quickstart/bin/activate
pip install -r requirements-quickstart.txt

# Run quickstart
python -m exoarmur.quickstart.run_quickstart
```

## What This Tests

The quickstart validates:
- ✅ Core system imports work
- ✅ Safety evaluation system functions
- ✅ Audit normalization works
- ✅ Replay engine can store and retrieve
- ✅ All components integrate properly

This is a minimal smoke test - it doesn't modify any existing behavior or require external dependencies.

## System Status

**Deterministic Execution Ready (Local Validation)**

This quickstart demonstrates that ExoArmur-Core is properly installed and functional for local development and validation. For production deployment, see the full documentation.
