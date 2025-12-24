"""
Aurora Context Code Namespace Package

Provides transparent access to aurora_context_code package through the aurora.context_code namespace.
This enables imports like:
    from aurora.context_code.semantic.hybrid_retriever import HybridRetriever
    from aurora.context_code.parser import PythonParser
"""

import sys
import importlib


# Pre-populate sys.modules with all known submodules to enable direct imports
_SUBMODULES = [
    'languages', 'parser', 'registry', 'semantic'
]

for _submodule_name in _SUBMODULES:
    _original = f'aurora_context_code.{_submodule_name}'
    _namespace = f'aurora.context_code.{_submodule_name}'
    try:
        if _original not in sys.modules:
            _module = importlib.import_module(_original)
        else:
            _module = sys.modules[_original]
        sys.modules[_namespace] = _module
    except ImportError:
        pass  # Submodule may not exist yet


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
