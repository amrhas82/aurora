"""
Aurora Core Namespace Package

Provides transparent access to aurora_core package through the aurora.core namespace.
This enables imports like:
    from aurora.core.store import SQLiteStore
    from aurora.core.chunks.base import Chunk
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'store', 'chunks', 'activation', 'budget', 'config',
    'context', 'logging', 'optimization', 'resilience', 'types', 'exceptions'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_core.{_submodule_name}'
    _namespace = f'aurora.core.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


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
