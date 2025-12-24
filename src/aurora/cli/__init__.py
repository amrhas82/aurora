"""
Aurora CLI Namespace Package

Provides transparent access to aurora_cli package through the aurora.cli namespace.
"""

import sys
import importlib


def __getattr__(name):
    """Dynamically import submodules from aurora_cli when accessed."""
    original_module_name = f'aurora_cli.{name}'
    try:
        module = importlib.import_module(original_module_name)
        sys.modules[f'aurora.cli.{name}'] = module
        return module
    except ImportError:
        raise AttributeError(f"module 'aurora.cli' has no attribute '{name}'")


# Re-export all public members
from aurora_cli import *  # noqa: F401, F403
