"""
Configuration system for AURORA.

Provides configuration loading, validation, and access.
"""

from aurora_core.config.loader import Config
from aurora_core.config.schema import get_schema

__all__ = ["Config", "get_schema"]
