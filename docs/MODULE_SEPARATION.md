# Module Separation and Export

This document describes the split-ready layout and the exact export process for
ExoArmur Core and proprietary modules.

## Goals
- Keep **Core** Apache-2.0 and standalone.
- Allow **modules** to be exported into their own repos with full history.
- Enforce hard boundaries so cross-module imports fail fast.

## Repository Layout
- **Core**: `src/exoarmur/`, `tests/`, `spec/`, `docs/`, `scripts/`, `tools/`
- **Modules**: `modules/<module_name>/` (self-contained)

> `spec/` remains at the repo root and is reserved for locked contract definitions.

## Boundary Rules (Hard)
- Core MUST NOT import from `modules/` or any module prefixes.
- Modules MAY import from Core (`exoarmur.*`) only.
- Modules MUST NOT import other modules.

Boundary enforcement is implemented in `tools/boundary_check.py` with
configuration in `tools/boundary_manifest.json`.

## Export: Core
Preferred method: **git-filter-repo**

```bash
# From repo root
bash tools/export_core.sh /tmp/exoarmur-core-export
```

If `git-filter-repo` is unavailable, install it:
```bash
python3 -m pip install git-filter-repo
```

## Export: Module
Each module includes `export_manifest.json` describing its export path.

```bash
# From repo root
bash tools/export_module.sh EXAMPLE_MODULE_TEMPLATE /tmp/exoarmur-example-module
```

```bash
# From repo root
bash tools/export_module.sh exoarmur_exolock /tmp/exoarmur-exolock
```

```bash
# From repo root
bash tools/export_module.sh exoarmur_control_plane /tmp/exoarmur-control-plane
```

If `git-filter-repo` is unavailable, the script falls back to `git subtree split`.

## Verification Checklist
- `python3 tools/boundary_check.py` passes locally and in CI.
- `python3 -m pytest -q` remains green.
- `git status --porcelain` is empty after gates.
- Exported repos contain **only** their declared paths with full history.
