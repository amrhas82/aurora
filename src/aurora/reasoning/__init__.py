"""
Aurora Reasoning Namespace Package

Provides transparent access to aurora_reasoning package through the aurora.reasoning namespace.
This enables imports like:
    from aurora.reasoning.decompose import decompose_problem
    from aurora.reasoning.synthesize import synthesize_solution
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'decompose', 'llm_client', 'prompts', 'synthesize', 'verify'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_reasoning.{_submodule_name}'
    _namespace = f'aurora.reasoning.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


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
