"""
Compatibility shim for tests that import approval as a top-level module.
Proxies to exoarmur.approval.approval_gate.
"""

import sys
from exoarmur.approval import approval_gate as _real_approval

# Make this module a proxy to the real approval module
sys.modules[__name__] = _real_approval
