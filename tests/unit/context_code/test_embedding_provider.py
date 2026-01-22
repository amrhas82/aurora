"""Tests for EmbeddingProvider None handling."""

from unittest.mock import patch

import pytest


def test_handles_none_provider():
    """Test that EmbeddingProvider handles None _SentenceTransformer gracefully.

    When _lazy_import() fails to load sentence_transformers, _SentenceTransformer
    remains None. The code should check for None before calling it.

    This test ensures mypy's 'None not callable' error on line 258 is fixed.
    """
    # Mock _can_import_ml_deps to return True (so __init__ doesn't raise)
    with patch(
        "aurora_context_code.semantic.embedding_provider._can_import_ml_deps",
        return_value=True,
    ):
        from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

        # Create provider instance
        provider = EmbeddingProvider()

        # Simulate the case where _lazy_import() was called but failed
        # This sets _HAS_SENTENCE_TRANSFORMERS to False and leaves _SentenceTransformer as None
        import aurora_context_code.semantic.embedding_provider as ep_module

        # Store original values
        original_st = ep_module._SentenceTransformer
        original_has_st = ep_module._HAS_SENTENCE_TRANSFORMERS

        try:
            # Simulate failed import scenario
            ep_module._SentenceTransformer = None
            ep_module._HAS_SENTENCE_TRANSFORMERS = True  # Pretend import succeeded

            # This should raise a clear error, not AttributeError: 'NoneType' not callable
            with pytest.raises(RuntimeError, match="SentenceTransformer.*not loaded"):
                provider._ensure_model_loaded()

        finally:
            # Restore original values
            ep_module._SentenceTransformer = original_st
            ep_module._HAS_SENTENCE_TRANSFORMERS = original_has_st
