"""
Aurora SOAR Namespace Package

Provides transparent access to aurora_soar package through the aurora.soar namespace.
"""

import sys
import importlib


def __getattr__(name):
    """Dynamically import submodules from aurora_soar when accessed."""
    original_module_name = f'aurora_soar.{name}'
    try:
        module = importlib.import_module(original_module_name)
        sys.modules[f'aurora.soar.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.soar' has no attribute '{name}'")


# Re-export all public members
from aurora_soar import *  # noqa: F401, F403
