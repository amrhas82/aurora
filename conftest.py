"""Pytest configuration for AURORA project.

This file sets up the Python path to enable imports from both:
1. Namespace packages in src/aurora/ (aurora.core, aurora.cli, etc.)
2. Implementation packages in packages/*/src/ (aurora_core, aurora_cli, etc.)

This configuration supports:
- Local development without installation
- Editable installations (pip install -e .)
- Regular package installations
"""

import sys
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent

# Add namespace package directory (src/) to path
# This enables imports like: from aurora.core import ...
src_path = PROJECT_ROOT / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Add implementation package directories to path
# This enables the namespace packages to find their underlying implementations
PACKAGE_DIRS = [
    "packages/core/src",
    "packages/cli/src",
    "packages/context-code/src",
    "packages/soar/src",
    "packages/reasoning/src",
    "packages/testing/src",
]

for package_dir in PACKAGE_DIRS:
    package_path = PROJECT_ROOT / package_dir
    if package_path.exists() and str(package_path) not in sys.path:
        sys.path.insert(0, str(package_path))
