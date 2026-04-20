# ExoArmur Determinism Scope

This document defines which modules require deterministic time handling and which may use wall-clock time.

## Overview

ExoArmur has a two-tier determinism model:

- **Core Determinism**: Required for replay-critical components
- **Non-Core Flexibility**: Non-replay components may use wall-clock time

## Core Determinism (Required)

These modules MUST use deterministic time via `exoarmur.clock.utc_now()`:

| Module | Reason |
|--------|--------|
| `execution_boundary_v2/` | Replay verification requires deterministic timestamps |
| `replay/` | Replay engine must reconstruct identical timelines |
| `proof/` | Proof bundles require deterministic replay hashes |
| `sdk/` | Public API must produce deterministic proof bundles |

### Core Clock Usage

```python
from exoarmur.clock import utc_now

# Deterministic timestamp for replay
timestamp = utc_now()
```

## Non-Core Flexibility (Wall-Clock Allowed)

These modules MAY use `datetime.now(timezone.utc)` for actual operations:

| Module | Reason |
|--------|--------|
| `federation/` | Cross-cell coordination needs real-time awareness |
| `observability/` | Metrics and monitoring require wall-clock time |
| `identity_containment/` | Real-time identity operations |
| `control_plane/` | Operator interfaces use wall-clock |
| `telemetry/` | Ingestion timestamps are wall-clock by nature |

### Non-Core Clock Usage

```python
from datetime import datetime, timezone

# Wall-clock time for non-replay operations
timestamp = datetime.now(timezone.utc)
```

## Why This Separation?

1. **Core Replay**: Deterministic timestamps enable cryptographic replay verification
2. **Non-Core Operations**: Federation, observability, and coordination need actual time awareness
3. **Boundary Safety**: Clear separation prevents accidental non-determinism in replay-critical paths

## Validation

The determinism check (`scripts/check_determinism.py`) validates core modules only:

```bash
# Check core determinism
./scripts/check_determinism.py

# Full report
./scripts/infra/verify_env_parity.py
```

## Future Work

Modules in the "Non-Core Flexibility" category may be moved to deterministic time if:
- They become part of replay-critical paths
- They generate proof bundles
- They participate in execution boundary decisions
