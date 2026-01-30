"""
Compatibility shim for tests that import main as a top-level module.
This module acts as a proxy to exoarmur.main, ensuring that when tests
do 'import main', they get access to the same module and its mutable state.
"""

import sys
from exoarmur import main as _real_main

# Make this module a proxy to the real main module
# This ensures that attribute access goes to the actual exoarmur.main module
sys.modules[__name__] = _real_main
