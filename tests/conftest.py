"""
Pytest configuration for AURORA tests.

Adds src directory to Python path for aurora.* imports.
"""

import sys
from pathlib import Path


# Add src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
