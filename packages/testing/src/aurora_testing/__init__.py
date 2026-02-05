"""AURORA Testing Package

Provides testing utilities and fixtures:
- Reusable pytest fixtures
- Mock implementations (LLM, agents)
- Performance benchmarking utilities
"""

__version__ = "0.1.0"

# Re-export modules for easy access
# Note: Using old import path temporarily to avoid circular dependency during namespace setup
from aurora_testing import benchmarks, fixtures, mocks


__all__ = ["fixtures", "mocks", "benchmarks"]
