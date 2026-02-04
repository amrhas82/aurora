"""Pytest fixtures for semantic retrieval tests.

Provides test isolation by clearing shared caches between tests.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def clear_hybrid_retriever_cache():
    """Clear HybridRetriever cache before and after each test.

    This ensures test isolation by preventing cached retrievers
    from affecting subsequent tests.
    """
    # Clear before test
    try:
        from aurora_context_code.semantic.hybrid_retriever import clear_retriever_cache
        clear_retriever_cache()
    except ImportError:
        pass

    yield

    # Clear after test
    try:
        from aurora_context_code.semantic.hybrid_retriever import clear_retriever_cache
        clear_retriever_cache()
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def reset_hybrid_logger():
    """Reset the HybridRetriever logger state between tests.

    This ensures caplog can capture logs correctly across tests.
    """
    logger = logging.getLogger("aurora_context_code.semantic.hybrid_retriever")
    original_propagate = logger.propagate
    original_level = logger.level
    original_handlers = logger.handlers.copy()

    # Reset logger state for test isolation
    logger.propagate = True
    logger.setLevel(logging.DEBUG)  # Allow all levels through
    logger.handlers = []  # Remove any handlers added by previous tests

    yield

    # Restore original state
    logger.propagate = original_propagate
    logger.setLevel(original_level)
    logger.handlers = original_handlers
