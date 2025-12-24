"""
Aurora Reasoning Namespace Package

Provides transparent access to aurora_reasoning package through the aurora.reasoning namespace.
"""

import sys
import importlib


def __getattr__(name):
    """Dynamically import submodules from aurora_reasoning when accessed."""
    original_module_name = f'aurora_reasoning.{name}'
    try:
        module = importlib.import_module(original_module_name)
        sys.modules[f'aurora.reasoning.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.reasoning' has no attribute '{name}'")


# Re-export all public members
from aurora_reasoning import *  # noqa: F401, F403
