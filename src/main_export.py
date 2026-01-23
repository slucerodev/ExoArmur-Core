"""
Temporary main module for schema export - identical to main.py but with absolute imports
"""

import sys
import os

# Add contracts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'spec', 'contracts'))

# Import everything from main.py
from main import *
