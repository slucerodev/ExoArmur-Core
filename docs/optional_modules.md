# Optional Module Integration
This document defines the standard, reusable pattern for integrating optional proprietary modules with ExoArmur-Core.

## Definition
An **optional module integration** is an integration where ExoArmur-Core remains fully functional without the module installed, and integration behavior is only enabled when the module is explicitly installed and importable.

## Requirements
- **No hard dependency**: Core MUST NOT require optional modules at runtime.
- **Explicit test skips**: Integration tests MUST use explicit `pytest.skip`/`pytest.importorskip` when the module is absent, with a clear message explaining how to enable the module.
- **Clear enablement**: Documentation MUST state how to install the module and make it importable (e.g., `exoarmur_dpo`).
- **Boundary rationale**: The core remains sealed and open; proprietary modules are opt‑in and boundary‑enforced.

## Forbidden practices
- Creating stubs or fake packages in Core to satisfy imports.
- Vendoring proprietary module code into Core.
- Silent skips or skips without messaging.
- Weakening assertions to “make tests pass.”

## Test Matrix
- **Core‑only (module absent)**: Integration tests MUST be skipped with explicit messaging.
- **Core + Module (module present)**: Integration tests MUST execute and pass fully.

### CI note (descriptive only)
CI SHOULD represent both modes explicitly (Core‑only and Core+Module) with clear reporting; no CI changes are required by this document.
