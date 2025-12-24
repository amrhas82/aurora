"""
Aurora Core Namespace Package

Provides transparent access to aurora_core package through the aurora.core namespace.
This enables imports like:
    from aurora.core.store import SQLiteStore
    from aurora.core.chunks.base import Chunk
"""

import sys
import importlib


def __getattr__(name):
    """Dynamically import submodules from aurora_core when accessed."""
    # Map aurora.core.store -> aurora_core.store
    original_module_name = f'aurora_core.{name}'
    try:
        module = importlib.import_module(original_module_name)
        # Cache in sys.modules under both names
        sys.modules[f'aurora.core.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.core' has no attribute '{name}'")


# Re-export all public aurora_core members at the package level
from aurora_core import *  # noqa: F401, F403
