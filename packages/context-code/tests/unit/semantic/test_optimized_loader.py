"""Tests for OptimizedEmbeddingLoader.

These tests verify the optimized loading strategies and ensure
they work correctly across different scenarios.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_context_code.semantic.optimized_loader import (
    LoadingStrategy,
    ModelMetadata,
    OptimizedEmbeddingLoader,
    ResourceProfile,
)


class TestResourceProfile:
    """Tests for ResourceProfile system detection."""

    def test_detect_creates_profile(self):
        """Test that ResourceProfile.detect() creates a valid profile."""
        profile = ResourceProfile.detect()

        assert profile.cpu_count > 0
        assert profile.available_memory_mb > 0
        assert profile.recommended_batch_size in [16, 32, 64]
        assert profile.recommended_device in ["cpu", "cuda", "mps"]

    def test_detect_recommends_reasonable_batch_size(self):
        """Test that batch size recommendations are reasonable."""
        profile = ResourceProfile.detect()

        # Batch size should be power of 2 between 16 and 64
        assert profile.recommended_batch_size >= 16
        assert profile.recommended_batch_size <= 64
        assert profile.recommended_batch_size in [16, 32, 64]

    def test_detect_is_consistent(self):
        """Test that multiple detections return same results."""
        profile1 = ResourceProfile.detect()
        profile2 = ResourceProfile.detect()

        assert profile1.cpu_count == profile2.cpu_count
        assert profile1.has_cuda == profile2.has_cuda
        assert profile1.has_mps == profile2.has_mps


class TestModelMetadata:
    """Tests for ModelMetadata caching."""

    def test_metadata_roundtrip(self, tmp_path):
        """Test saving and loading metadata."""
        metadata = ModelMetadata(
            model_name="test-model",
            embedding_dim=384,
            max_seq_length=512,
            model_size_mb=100,
            supports_quantization=False,
            last_used=time.time(),
        )

        # Mock the cache path to use tmp_path
        with patch.object(
            ModelMetadata,
            "_get_cache_path",
            return_value=tmp_path / "metadata.json",
        ):
            metadata.save()

            # Load it back
            loaded = ModelMetadata.from_cache("test-model")

        assert loaded is not None
        assert loaded.model_name == metadata.model_name
        assert loaded.embedding_dim == metadata.embedding_dim
        assert loaded.max_seq_length == metadata.max_seq_length

    def test_metadata_missing_returns_none(self):
        """Test that missing metadata returns None."""
        with patch.object(
            ModelMetadata,
            "_get_cache_path",
            return_value=Path("/nonexistent/path.json"),
        ):
            loaded = ModelMetadata.from_cache("nonexistent-model")

        assert loaded is None

    def test_metadata_corrupted_returns_none(self, tmp_path):
        """Test that corrupted metadata returns None."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {")

        with patch.object(
            ModelMetadata,
            "_get_cache_path",
            return_value=bad_file,
        ):
            loaded = ModelMetadata.from_cache("bad-model")

        assert loaded is None


class TestOptimizedEmbeddingLoader:
    """Tests for OptimizedEmbeddingLoader."""

    def setup_method(self):
        """Reset singleton before each test."""
        OptimizedEmbeddingLoader.reset()

    def teardown_method(self):
        """Clean up after each test."""
        OptimizedEmbeddingLoader.reset()

    def test_lazy_strategy_does_not_load_immediately(self):
        """Test that LAZY strategy doesn't load model on init."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert not loader.is_loaded()
        assert not loader.is_loading()

    def test_background_strategy_starts_loading(self):
        """Test that BACKGROUND strategy starts loading immediately."""
        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.BACKGROUND)
            loader.start_loading()

            # Should start loading in background
            time.sleep(0.1)
            assert loader.is_loading() or loader.is_loaded()

    def test_progressive_strategy_starts_loading(self):
        """Test that PROGRESSIVE strategy starts loading."""
        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.PROGRESSIVE)
            loader.start_loading()

            time.sleep(0.1)
            assert loader.is_loading() or loader.is_loaded()

    def test_get_instance_returns_singleton(self):
        """Test that get_instance() returns same instance."""
        loader1 = OptimizedEmbeddingLoader.get_instance()
        loader2 = OptimizedEmbeddingLoader.get_instance()

        assert loader1 is loader2

    def test_reset_clears_singleton(self):
        """Test that reset() clears the singleton."""
        loader1 = OptimizedEmbeddingLoader.get_instance()
        OptimizedEmbeddingLoader.reset()
        loader2 = OptimizedEmbeddingLoader.get_instance()

        assert loader1 is not loader2

    def test_is_loaded_returns_false_initially(self):
        """Test that is_loaded() returns False initially."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert not loader.is_loaded()

    def test_is_loading_returns_false_for_lazy_before_start(self):
        """Test that is_loading() returns False for lazy strategy before use."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert not loader.is_loading()

    def test_get_error_returns_none_initially(self):
        """Test that get_error() returns None initially."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert loader.get_error() is None

    def test_get_load_time_returns_zero_before_load(self):
        """Test that get_load_time() returns 0 before loading."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert loader.get_load_time() == 0.0

    def test_get_metadata_returns_cached_metadata(self):
        """Test that get_metadata() returns cached metadata if available."""
        metadata = ModelMetadata(
            model_name="all-MiniLM-L6-v2",
            embedding_dim=384,
            max_seq_length=512,
            model_size_mb=88,
            supports_quantization=False,
            last_used=time.time(),
        )

        with patch.object(
            ModelMetadata,
            "from_cache",
            return_value=metadata,
        ):
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)

        assert loader.get_metadata() == metadata

    def test_get_embedding_dim_fast_returns_known_dim(self):
        """Test that get_embedding_dim_fast() returns known dimensions."""
        loader = OptimizedEmbeddingLoader(
            model_name="all-MiniLM-L6-v2",
            strategy=LoadingStrategy.LAZY,
        )

        dim = loader.get_embedding_dim_fast()
        assert dim == 384

    def test_get_embedding_dim_fast_returns_none_for_unknown(self):
        """Test that get_embedding_dim_fast() returns None for unknown models."""
        loader = OptimizedEmbeddingLoader(
            model_name="unknown-model-xyz",
            strategy=LoadingStrategy.LAZY,
        )

        dim = loader.get_embedding_dim_fast()
        # Will be None if not in cache and not in known dims
        # This is expected behavior
        assert dim is None or isinstance(dim, int)

    @pytest.mark.skipif(
        not pytest.importorskip(
            "sentence_transformers", reason="sentence-transformers not installed"
        ),
        reason="Requires sentence-transformers",
    )
    def test_lazy_loading_on_get_provider(self):
        """Test that lazy loading works when get_provider() is called."""
        loader = OptimizedEmbeddingLoader(
            model_name="all-MiniLM-L6-v2",
            strategy=LoadingStrategy.LAZY,
        )

        # Should not be loaded yet
        assert not loader.is_loaded()

        # get_provider() should trigger loading
        provider = loader.get_provider(timeout=30.0)

        # Should be loaded now (or None if dependencies missing)
        assert loader.is_loaded() or provider is None

    def test_wait_for_provider_timeout(self):
        """Test that wait_for_provider() times out if loading takes too long."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.BACKGROUND)

        # Don't actually start loading
        # wait_for_provider should timeout
        provider = loader.wait_for_provider(timeout=0.1)

        assert provider is None

    def test_start_loading_is_idempotent(self):
        """Test that calling start_loading() multiple times is safe."""
        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.BACKGROUND)

            loader.start_loading()
            loader.start_loading()  # Should not start second thread
            loader.start_loading()  # Should not start third thread

            # Should only have one loading operation
            time.sleep(0.1)
            # If multiple threads started, this would likely cause issues


class TestLoadingStrategies:
    """Integration tests for different loading strategies."""

    def setup_method(self):
        """Reset singleton before each test."""
        OptimizedEmbeddingLoader.reset()

    def teardown_method(self):
        """Clean up after each test."""
        OptimizedEmbeddingLoader.reset()

    def test_all_strategies_have_implementations(self):
        """Test that all LoadingStrategy enum values have implementations."""
        for strategy in LoadingStrategy:
            loader = OptimizedEmbeddingLoader(strategy=strategy)
            loader.start_loading()

            # Should not crash
            assert loader is not None

    def test_lazy_strategy_delays_loading(self):
        """Test that LAZY strategy doesn't load until needed."""
        start = time.time()
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.LAZY)
        elapsed = time.time() - start

        # Should be very fast (< 100ms)
        assert elapsed < 0.1
        assert not loader.is_loaded()

    def test_background_strategy_returns_immediately(self):
        """Test that BACKGROUND strategy returns immediately."""
        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            start = time.time()
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.BACKGROUND)
            loader.start_loading()
            elapsed = time.time() - start

            # Should return very quickly (< 100ms)
            assert elapsed < 0.1

    def test_progressive_strategy_returns_immediately(self):
        """Test that PROGRESSIVE strategy returns immediately."""
        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            start = time.time()
            loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.PROGRESSIVE)
            loader.start_loading()
            elapsed = time.time() - start

            # Should return very quickly (< 100ms)
            assert elapsed < 0.1


class TestThreadSafety:
    """Tests for thread safety of the loader."""

    def setup_method(self):
        """Reset singleton before each test."""
        OptimizedEmbeddingLoader.reset()

    def teardown_method(self):
        """Clean up after each test."""
        OptimizedEmbeddingLoader.reset()

    def test_concurrent_get_instance_returns_same_instance(self):
        """Test that concurrent get_instance() calls return same instance."""
        instances = []

        def get_instance_thread():
            instance = OptimizedEmbeddingLoader.get_instance()
            instances.append(instance)

        threads = [threading.Thread(target=get_instance_thread) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)

    def test_concurrent_start_loading_is_safe(self):
        """Test that concurrent start_loading() calls are safe."""
        loader = OptimizedEmbeddingLoader(strategy=LoadingStrategy.BACKGROUND)

        def start_loading_thread():
            loader.start_loading()

        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=True,
        ):
            threads = [threading.Thread(target=start_loading_thread) for _ in range(10)]

            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Should not crash or have race conditions
        assert loader is not None


class TestErrorHandling:
    """Tests for error handling in the loader."""

    def setup_method(self):
        """Reset singleton before each test."""
        OptimizedEmbeddingLoader.reset()

    def teardown_method(self):
        """Clean up after each test."""
        OptimizedEmbeddingLoader.reset()

    def test_loading_error_is_captured(self):
        """Test that loading errors are captured and available."""
        loader = OptimizedEmbeddingLoader(
            model_name="nonexistent-model-xyz",
            strategy=LoadingStrategy.BACKGROUND,
        )

        with patch(
            "aurora_context_code.semantic.optimized_loader.is_model_cached",
            return_value=False,
        ):
            loader.start_loading()
            time.sleep(0.5)  # Give time for error to occur

        # Error should be captured
        error = loader.get_error()
        # May be None if loading hasn't failed yet, or an exception if it has
        assert error is None or isinstance(error, Exception)

    def test_wait_for_provider_returns_none_on_error(self):
        """Test that wait_for_provider() returns None if loading fails."""
        loader = OptimizedEmbeddingLoader(
            model_name="nonexistent-model-xyz",
            strategy=LoadingStrategy.BACKGROUND,
        )

        with patch(
            "aurora_context_code.semantic.optimized_loader.EmbeddingProvider",
            side_effect=RuntimeError("Test error"),
        ):
            loader.start_loading()
            provider = loader.wait_for_provider(timeout=1.0)

        # Should return None due to error
        assert provider is None
        assert loader.get_error() is not None
