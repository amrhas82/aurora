"""
Aurora Testing Namespace Package

Provides transparent access to aurora_testing package through the aurora.testing namespace.
"""

import sys
import importlib


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
