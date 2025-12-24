"""
AURORA Namespace Package

This namespace package provides unified access to all AURORA components
through a single import path: aurora.core, aurora.context_code, etc.

This is a PEP 420 implicit namespace package that aggregates the
individual aurora-* packages into a unified namespace.
"""

__path__ = __import__('pkgutil').extend_path(__path__, __name__)
