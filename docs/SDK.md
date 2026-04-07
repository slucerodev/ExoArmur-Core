# ExoArmur SDK

The ExoArmur SDK provides a public API for integrating with ExoArmur's governance capabilities.

## Public API

```{eval-rst}
.. autoclass:: exoarmur.sdk.public_api.SDKConfig
    :members:

.. automodule:: exoarmur.sdk.public_api
    :members:
    :undoc-members:
```

## Core Functions

- `run_governed_execution()` - Execute actions under governance
- `replay_governed_execution()` - Replay and verify execution
- `verify_governance_integrity()` - Verify governance integrity

## Usage

```python
from exoarmur.sdk.public_api import run_governed_execution, SDKConfig

# Configure SDK
config = SDKConfig(
    enable_logging=True,
    timeout_seconds=30
)

# Run governed execution
result = run_governed_execution(
    intent=your_action_intent,
    config=config
)
```
