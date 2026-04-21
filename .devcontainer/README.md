# ExoArmur Live Demo (GitHub Codespaces)

One-click access to a fully configured ExoArmur environment. No installation needed.

## 🚀 Launch the Demo

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/slucerodev/ExoArmur-Core)

Click the badge above → select machine type (2-core is fine) → wait ~2 minutes for setup.

## ✅ What's Pre-Configured

- Python 3.12 with all dependencies installed
- ExoArmur installed in editable mode (`pip install -e '.[v2]'`)
- `PYTHONHASHSEED=0` set for deterministic operation
- All 1000+ tests ready to run
- Demo scripts and examples ready to execute

## 🎯 Try These Commands

When the terminal opens, you'll see the welcome banner. Key commands:

```bash
# 1. Verify deterministic replay (run 3 times, same hash = ✅)
exoarmur proof

# 2. Verify reversible actions (Claim 3)
python examples/reversible_action_demo.py

# 3. Verify ML isolation (Claim 4)
python -m pytest tests/test_ml_isolation.py -v

# 4. Run full test suite
python -m pytest tests/ -q --tb=short

# 5. Check doctrine verification status
cat docs/DOCTRINE_VERIFICATION.md | grep "Overall Assessment"
```

## 📚 Documentation Available

| File | Purpose |
|------|---------|
| `docs/DOCTRINE.md` | The 5 verified claims of ExoArmur |
| `docs/DOCTRINE_VERIFICATION.md` | Detailed verification evidence |
| `docs/ARCHITECTURE.md` | System architecture & ML isolation |
| `docs/ML_ISOLATION.md` | ML isolation policy (Claim 4) |
| `docs/GOVERNANCE.md` | Reversibility guarantees (Claim 3) |

## 🔒 Security Notes

- This is a **demo environment** — no production secrets
- Determinism verified with `PYTHONHASHSEED=0`
- All cryptographic attestations use SHA-256
- No external dependencies required

## 🛠️ Customization

The `.devcontainer/devcontainer.json` defines the environment. Modify and rebuild if needed:

```bash
# In VS Code: Command Palette → "Codespaces: Rebuild Container"
```

## 📊 Expected Test Results

```
~1000+ passed, ~8 skipped, ~3 xfailed (expected)
0 failed, 0 errors
```

Any other result is a bug — report it.
