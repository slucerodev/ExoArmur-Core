"""
Compatibility shim for tests that import models_v1 as a top-level module.
Proxies to spec.contracts.models_v1.
"""

import sys
from spec.contracts import models_v1 as _real_models_v1

# Make this module a proxy to the real models_v1 module
sys.modules[__name__] = _real_models_v1
