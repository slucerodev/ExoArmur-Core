# Phase 2B PoD Integration Receipt (Core)

Date: 2026-02-11T13:34:36-06:00
Branch: fix/pytest-green-no-path-hacks
HEAD: feb191315ebb36e2e6819585c502bce331bf1133
Allowlist commit: 4d8e0e9 (chore(core): allowlist exoarmur.pod plugin group)

PoD entry point target: exoarmur_pod.plugin:pod_provider

Tests added (verbatim names):
- test_pod_provider_discovered_after_discover_providers
- test_pod_provider_runtime_load_via_registry_api
- test_pod_absent_safe_behavior
- test_pod_provider_failure_isolated

Invariants enforced (by the tests above):
- PoD provider is discoverable after discover_providers() and resolves to exoarmur_pod.plugin.
- PoD provider loads via registry API and returns a non-None instance.
- Absence of PoD entry points yields safe behavior with zero pod count and safe lookup.
- Provider load failure is isolated and does not corrupt registry state or counts.

Core test suite: python3 -m pytest -q (green)

Environment note: System Python is PEP 668 externally-managed; Core and PoD were installed in a local venv at /home/oem/CascadeProjects/ExoArmur/.venv without --break-system-packages.
