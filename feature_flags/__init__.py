"""
Compatibility shim for tests that import feature_flags as a top-level package.
This module acts as a proxy to exoarmur.feature_flags, ensuring tests can access it.
"""

import sys
from exoarmur import feature_flags as _real_feature_flags

# Make this module a proxy to the real feature_flags module
sys.modules[__name__] = _real_feature_flags
