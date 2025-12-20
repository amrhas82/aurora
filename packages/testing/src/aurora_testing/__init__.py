"""
AURORA Testing Package

Provides testing utilities and fixtures:
- Reusable pytest fixtures
- Mock implementations (LLM, agents)
- Performance benchmarking utilities
"""

__version__ = "0.1.0"

# Re-export modules for easy access
from aurora_testing import benchmarks, fixtures, mocks


__all__ = ["fixtures", "mocks", "benchmarks"]
