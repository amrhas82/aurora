"""
Aurora Testing Namespace Package

Provides transparent access to aurora_testing package through the aurora.testing namespace.
This enables imports like:
    from aurora.testing.fixtures import create_test_chunk
    from aurora.testing.mocks import MockMemoryStore
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'benchmarks', 'fixtures', 'mocks'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_testing.{_submodule_name}'
    _namespace = f'aurora.testing.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


def __getattr__(name):
    """Dynamically import submodules from aurora_testing when accessed."""
    original_module_name = f'aurora_testing.{name}'
    try:
        module = importlib.import_module(original_module_name)
        sys.modules[f'aurora.testing.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.testing' has no attribute '{name}'")


# Re-export all public members
from aurora_testing import *  # noqa: F401, F403
