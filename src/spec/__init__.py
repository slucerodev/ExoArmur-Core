"""
ExoArmur V1 contract package.

This is the canonical, packaged location for V1 data contracts. It is
installed alongside the `exoarmur` package (see `pyproject.toml`'s
`[tool.setuptools.packages.find].include` allow-list).

Layout:
    spec.contracts.models_v1            - V1 Pydantic models (LOCKED)
    spec.contracts.shared_primitives_v1 - Shared primitive models
    spec.contracts.schemas/             - V2 coordination JSON schemas
    spec.contracts.*.yaml               - V2 contract specifications

V1 contracts are immutable by policy. New capabilities must be additive
and feature-flag gated. See `docs/CONTRACTS.md` for the policy.
"""
