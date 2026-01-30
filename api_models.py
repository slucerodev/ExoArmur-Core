"""
Compatibility shim for tests that import api_models as a top-level module.
Proxies to exoarmur.api_models.
"""

import sys
from exoarmur import api_models as _real_api_models

# Make this module a proxy to the real api_models module
sys.modules[__name__] = _real_api_models
