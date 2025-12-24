"""
Aurora Context Code Namespace Package

Provides transparent access to aurora_context_code package through the aurora.context_code namespace.
"""

import sys
import importlib


def __getattr__(name):
    """Dynamically import submodules from aurora_context_code when accessed."""
    original_module_name = f'aurora_context_code.{name}'
    try:
        module = importlib.import_module(original_module_name)
        sys.modules[f'aurora.context_code.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.context_code' has no attribute '{name}'")


# Re-export all public members
from aurora_context_code import *  # noqa: F401, F403
