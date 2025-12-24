"""
Aurora SOAR Namespace Package

Provides transparent access to aurora_soar package through the aurora.soar namespace.
This enables imports like:
    from aurora.soar.orchestrator import SOAROrchestrator
    from aurora.soar.phases.implementation import ImplementationPhase
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'agent_registry', 'headless', 'orchestrator', 'phases'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_soar.{_submodule_name}'
    _namespace = f'aurora.soar.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


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
