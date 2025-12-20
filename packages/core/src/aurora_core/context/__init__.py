"""
Context management and retrieval for AURORA.

Provides abstract ContextProvider interface and implementations.
"""

from aurora_core.context.provider import ContextProvider
from aurora_core.context.code_provider import CodeContextProvider

__all__ = ['ContextProvider', 'CodeContextProvider']
