"""Context management and retrieval for AURORA.

Provides abstract ContextProvider interface and implementations.
"""

from aurora_core.context.code_provider import CodeContextProvider
from aurora_core.context.provider import ContextProvider


__all__ = ["ContextProvider", "CodeContextProvider"]
