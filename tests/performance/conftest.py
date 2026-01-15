"""Pytest configuration for performance benchmarks.

Configures pytest-benchmark and custom fixtures for performance testing.
"""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "ml: Tests requiring ML dependencies")


@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration for pytest-benchmark."""
    return {
        "min_rounds": 3,
        "max_time": 60.0,  # Max 60 seconds per benchmark
        "min_time": 0.000005,
        "warmup": True,
        "warmup_iterations": 1,
    }
