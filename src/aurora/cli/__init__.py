"""
Aurora CLI Namespace Package

Provides transparent access to aurora_cli package through the aurora.cli namespace.
This enables imports like:
    from aurora.cli.config import Config
    from aurora.cli.commands.init import init_command
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'commands', 'config', 'errors', 'escalation', 'execution',
    'main', 'memory_manager'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_cli.{_submodule_name}'
    _namespace = f'aurora.cli.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


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
