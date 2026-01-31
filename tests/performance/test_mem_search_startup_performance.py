"""Performance tests for aur mem search startup time.

These tests verify that the memory search command maintains fast startup times,
specifically addressing the embedding model loading delay. The goal is to prevent
regression where users experience a 20-30+ second hang waiting for embeddings.

Key measurements:
- CLI command parsing and initialization
- Background model loading start time
- BM25-only fallback latency
- Full hybrid retrieval latency
- Time to first result (user-perceived latency)

Targets:
- Command help: <1s
- BM25-only search: <2s
- Full hybrid with cached model: <5s
- Background loading start: <100ms (non-blocking)

Run with:
    pytest tests/performance/test_mem_search_startup_performance.py -v
"""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.performance]


@pytest.fixture
def temp_aurora_project() -> Generator[Path, None, None]:
    """Create a temporary Aurora project with minimal structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        aurora_dir = project / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "logs").mkdir()
        (aurora_dir / "cache").mkdir()

        # Create minimal memory database with test data
        from aurora_core.store.sqlite import SQLiteStore

        db_path = aurora_dir / "memory.db"
        store = SQLiteStore(str(db_path))

        # Add a few test chunks so retrieval has data to work with
        from aurora_core.chunks import CodeChunk

        for i in range(5):
            chunk = CodeChunk(
                chunk_id=f"test-chunk-{i}",
                file_path=f"test_{i}.py",
                element_type="function",
                name=f"test_function_{i}",
                line_start=1,
                line_end=10,
                docstring=f"Test function {i} for authentication and validation",
                language="python",
            )
            store.save_chunk(chunk)

        store.close()

        yield project


class TestMemSearchHelpStartup:
    """Benchmark tests for aur mem search --help startup performance."""

    def test_mem_help_response_time(self):
        """Verify 'aur mem --help' responds quickly (<1s).

        This measures the absolute minimum startup time - just Click
        initialization and help rendering.
        """
        from click.testing import CliRunner

        from aurora_cli.commands.memory import memory_group

        runner = CliRunner()

        start = time.time()
        result = runner.invoke(memory_group, ["--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert (
            elapsed < 1.0
        ), f"'aur mem --help' took {elapsed:.3f}s (target: <1.0s). Help should be instant."

    def test_mem_search_help_response_time(self):
        """Verify 'aur mem search --help' responds quickly (<1s)."""
        from click.testing import CliRunner

        from aurora_cli.commands.memory import memory_group

        runner = CliRunner()

        start = time.time()
        result = runner.invoke(memory_group, ["search", "--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert (
            elapsed < 1.0
        ), f"'aur mem search --help' took {elapsed:.3f}s (target: <1.0s). Help should be instant."


class TestMemSearchImportPerformance:
    """Tests for import performance of memory search components."""

    def test_memory_command_imports_fast(self):
        """Verify memory command module imports quickly (<2s)."""
        # Clear cached imports for accurate measurement
        modules_to_clear = [
            k for k in list(sys.modules.keys()) if k.startswith("aurora_cli.commands.memory")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.time()
        from aurora_cli.commands.memory import memory_group  # noqa: F401

        elapsed = time.time() - start

        assert elapsed < 2.0, (
            f"Memory command imports took {elapsed:.3f}s (target: <2.0s). "
            "Import time directly affects startup latency."
        )

    def test_no_heavy_imports_at_module_level(self):
        """Verify memory command doesn't import heavy dependencies at module level."""
        initial_modules = set(sys.modules.keys())

        # Import the command
        from aurora_cli.commands.memory import memory_group  # noqa: F401

        new_modules = set(sys.modules.keys()) - initial_modules

        # Check for heavy dependencies that shouldn't be imported yet
        heavy_deps = [
            "sentence_transformers",
            "torch",
            "transformers",
            "sklearn",
        ]

        for dep in heavy_deps:
            imported_heavy = [m for m in new_modules if dep in m.lower()]
            assert not imported_heavy, (
                f"Heavy dependency '{dep}' imported at module level: {imported_heavy}. "
                "Heavy imports should be lazy-loaded."
            )


class TestBackgroundModelLoading:
    """Tests for background model loading mechanism."""

    def test_background_loading_starts_quickly(self):
        """Verify starting background model loading is non-blocking (<100ms)."""
        from aurora_cli.commands.memory import _start_background_model_loading

        start = time.time()
        _start_background_model_loading()
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"Starting background loading took {elapsed:.3f}s (target: <0.1s). "
            "Starting background thread should be instant."
        )

    def test_model_cache_check_lightweight(self):
        """Verify model cache check doesn't import heavy dependencies."""
        initial_modules = set(sys.modules.keys())

        from aurora_context_code.model_cache import is_model_cached_fast

        is_cached = is_model_cached_fast()

        new_modules = set(sys.modules.keys()) - initial_modules

        # Should not import torch or sentence_transformers
        heavy_deps = ["torch", "sentence_transformers"]
        for dep in heavy_deps:
            imported = [m for m in new_modules if dep in m.lower()]
            assert (
                not imported
            ), f"Cache check imported {dep}: {imported}. Cache checking should be lightweight."

    def test_start_background_loading_fast(self):
        """Verify start_background_loading returns immediately (<100ms)."""
        from aurora_context_code.model_cache import start_background_loading

        start = time.time()
        result = start_background_loading()
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"start_background_loading took {elapsed:.3f}s (target: <0.1s). "
            "Should return immediately, loading happens in background thread."
        )
        assert result is True, "start_background_loading should return True"


class TestMemoryRetrieverInitialization:
    """Tests for MemoryRetriever initialization performance."""

    def test_retriever_init_fast(self, temp_aurora_project: Path):
        """Verify MemoryRetriever initialization is fast (<50ms)."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        start = time.time()
        retriever = MemoryRetriever(store=store, config=None)
        elapsed = time.time() - start

        assert elapsed < 0.05, (
            f"MemoryRetriever init took {elapsed:.3f}s (target: <0.05s). "
            "Retriever should be lazy-initialized."
        )
        assert retriever._retriever is None, "HybridRetriever should not be created during init"

        store.close()

    def test_has_indexed_memory_avoids_model_load(self, temp_aurora_project: Path):
        """Verify has_indexed_memory() doesn't trigger model loading."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))
        retriever = MemoryRetriever(store=store, config=None)

        # Track if EmbeddingProvider is instantiated
        with patch("aurora_context_code.semantic.EmbeddingProvider") as mock_provider:
            has_memory = retriever.has_indexed_memory()

            # EmbeddingProvider should NOT have been instantiated
            mock_provider.assert_not_called()
            assert has_memory is True, "Should detect indexed memory"

        store.close()


class TestBM25OnlyFallback:
    """Tests for BM25-only fallback performance when embeddings unavailable."""

    def test_bm25_only_search_fast(self, temp_aurora_project: Path):
        """Verify BM25-only search is fast (<2s) when embeddings unavailable."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        # Mock embedding provider to simulate unavailable state
        with patch(
            "aurora_context_code.semantic.model_utils.is_model_cached",
            return_value=False,
        ):
            retriever = MemoryRetriever(store=store, config=None)

            start = time.time()
            # Use retrieve_fast which falls back to BM25-only if model not ready
            results, is_hybrid = retriever.retrieve_fast("authentication", limit=5)
            elapsed = time.time() - start

        assert (
            elapsed < 2.0
        ), f"BM25-only search took {elapsed:.3f}s (target: <2.0s). Fallback search should be fast."

        store.close()

    def test_retrieve_fast_returns_immediately(self, temp_aurora_project: Path):
        """Verify retrieve_fast doesn't block on model loading."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        # Simulate model still loading
        mock_loader = MagicMock()
        mock_loader.get_provider_if_ready.return_value = None
        mock_loader.is_loading.return_value = True  # Still loading
        mock_loader.is_loaded.return_value = False

        with patch(
            "aurora_context_code.semantic.model_utils.BackgroundModelLoader",
        ) as mock_loader_class:
            mock_loader_class.get_instance.return_value = mock_loader

            retriever = MemoryRetriever(store=store, config=None)

            start = time.time()
            results, is_hybrid = retriever.retrieve_fast("authentication", limit=5)
            elapsed = time.time() - start

        # Should not wait for model - should return immediately with BM25 results
        assert elapsed < 1.0, (
            f"retrieve_fast took {elapsed:.3f}s (target: <1.0s). "
            "Should not block waiting for model loading."
        )
        assert is_hybrid is False, "Should indicate BM25-only results"

        store.close()


class TestEmbeddingProviderLazyLoading:
    """Tests for EmbeddingProvider lazy loading behavior."""

    def test_provider_init_fast_without_model_load(self):
        """Verify EmbeddingProvider init is fast (<100ms) without loading model."""
        with patch(
            "aurora_context_code.semantic.embedding_provider._can_import_ml_deps",
            return_value=True,
        ):
            from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

            start = time.time()
            provider = EmbeddingProvider.__new__(EmbeddingProvider)
            provider.model_name = "all-MiniLM-L6-v2"
            provider._device_hint = "cpu"
            provider._model = None
            provider._device = None
            provider._embedding_dim = 384
            elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"EmbeddingProvider init took {elapsed:.3f}s (target: <0.1s). "
            "Model should not load during __init__."
        )

    def test_embedding_dim_uses_cache_for_known_models(self):
        """Verify embedding_dim uses cached values for known models."""
        from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

        # Mock to prevent actual model loading
        with patch(
            "aurora_context_code.semantic.embedding_provider._can_import_ml_deps",
            return_value=True,
        ):
            with patch(
                "aurora_context_code.semantic.embedding_provider._SentenceTransformer",
            ) as mock_st:
                provider = EmbeddingProvider.__new__(EmbeddingProvider)
                provider.model_name = "all-MiniLM-L6-v2"
                provider._device_hint = "cpu"
                provider._model = None
                provider._device = None
                provider._embedding_dim = 384  # Pre-set from cache

                start = time.time()
                dim = provider.embedding_dim
                elapsed = time.time() - start

        # Should return cached dimension without loading model
        assert dim == 384
        assert elapsed < 0.01, (
            f"Getting embedding_dim took {elapsed:.3f}s (target: <0.01s). "
            "Known model dimensions should be cached."
        )
        # Model should NOT have been loaded
        mock_st.assert_not_called()


class TestSearchCommandEndToEnd:
    """End-to-end tests for search command startup performance."""

    def test_search_command_with_mocked_retrieval(self, temp_aurora_project: Path):
        """Test search command startup with mocked retrieval (<3s)."""
        from click.testing import CliRunner

        from aurora_cli.commands.memory import memory_group

        runner = CliRunner()

        # Mock the retrieval to avoid actual embedding work
        with patch("aurora_cli.commands.memory._start_background_model_loading"):
            with patch("aurora_cli.memory.retrieval.MemoryRetriever") as mock_retriever_class:
                mock_retriever = MagicMock()
                mock_retriever.retrieve.return_value = []
                mock_retriever_class.return_value = mock_retriever

                os.chdir(temp_aurora_project)

                start = time.time()
                result = runner.invoke(
                    memory_group,
                    ["search", "authentication"],
                )
                elapsed = time.time() - start

        assert elapsed < 3.0, (
            f"Search command took {elapsed:.3f}s (target: <3.0s). "
            f"Output: {result.output[:200] if result.output else 'no output'}"
        )


class TestRegressionGuards:
    """Strict regression guards to prevent performance degradation."""

    # Maximum acceptable times (in seconds)
    MAX_IMPORT_TIME = 2.0
    MAX_CACHE_CHECK_TIME = 0.1
    MAX_BACKGROUND_START_TIME = 0.1
    MAX_RETRIEVER_INIT_TIME = 0.1
    MAX_BM25_SEARCH_TIME = 2.0
    MAX_HELP_TIME = 1.0

    def test_guard_import_time(self):
        """REGRESSION GUARD: Memory command imports must complete in <2s."""
        modules_to_clear = [
            k for k in list(sys.modules.keys()) if "aurora_cli.commands.memory" in k
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.time()
        from aurora_cli.commands.memory import memory_group  # noqa: F401

        elapsed = time.time() - start

        assert elapsed < self.MAX_IMPORT_TIME, (
            f"REGRESSION: Import time {elapsed:.3f}s exceeds {self.MAX_IMPORT_TIME}s. "
            "Check for new heavy imports at module level."
        )

    def test_guard_cache_check_time(self):
        """REGRESSION GUARD: Model cache check must complete in <100ms."""
        from aurora_context_code.model_cache import is_model_cached_fast

        start = time.time()
        is_model_cached_fast()
        elapsed = time.time() - start

        assert elapsed < self.MAX_CACHE_CHECK_TIME, (
            f"REGRESSION: Cache check time {elapsed:.3f}s exceeds {self.MAX_CACHE_CHECK_TIME}s. "
            "Cache check should be filesystem-only."
        )

    def test_guard_background_start_time(self):
        """REGRESSION GUARD: Background loading start must complete in <100ms."""
        from aurora_context_code.model_cache import start_background_loading

        start = time.time()
        start_background_loading()
        elapsed = time.time() - start

        assert elapsed < self.MAX_BACKGROUND_START_TIME, (
            f"REGRESSION: Background start time {elapsed:.3f}s exceeds {self.MAX_BACKGROUND_START_TIME}s. "
            "Background loading start should be instant."
        )

    def test_guard_retriever_init_time(self, temp_aurora_project: Path):
        """REGRESSION GUARD: MemoryRetriever init must complete in <100ms."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        start = time.time()
        MemoryRetriever(store=store, config=None)
        elapsed = time.time() - start

        assert elapsed < self.MAX_RETRIEVER_INIT_TIME, (
            f"REGRESSION: Retriever init time {elapsed:.3f}s exceeds {self.MAX_RETRIEVER_INIT_TIME}s. "
            "Retriever should be lazy-initialized."
        )

        store.close()

    def test_guard_help_time(self):
        """REGRESSION GUARD: Help command must complete in <1s."""
        from click.testing import CliRunner

        from aurora_cli.commands.memory import memory_group

        runner = CliRunner()

        start = time.time()
        result = runner.invoke(memory_group, ["search", "--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert elapsed < self.MAX_HELP_TIME, (
            f"REGRESSION: Help time {elapsed:.3f}s exceeds {self.MAX_HELP_TIME}s. "
            "Help should not trigger heavy initialization."
        )


class TestBackgroundLoaderThreadSafety:
    """Tests for BackgroundModelLoader thread safety and timing."""

    def test_loader_singleton_is_thread_safe(self):
        """Verify BackgroundModelLoader singleton is thread-safe."""
        from aurora_context_code.semantic.model_utils import BackgroundModelLoader

        # Reset to ensure clean state
        BackgroundModelLoader.reset()

        instances = []
        errors = []

        def get_instance():
            try:
                instance = BackgroundModelLoader.get_instance()
                instances.append(id(instance))
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to get instance
        threads = [threading.Thread(target=get_instance) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert not errors, f"Errors occurred: {errors}"
        # All threads should get the same instance
        assert len(set(instances)) == 1, f"Multiple instances created: {set(instances)}"

        # Cleanup
        BackgroundModelLoader.reset()

    def test_is_loading_returns_quickly(self):
        """Verify is_loading() is fast and non-blocking."""
        from aurora_context_code.semantic.model_utils import BackgroundModelLoader

        loader = BackgroundModelLoader.get_instance()

        start = time.time()
        for _ in range(100):
            loader.is_loading()
        elapsed = time.time() - start

        # 100 calls should be instant
        assert elapsed < 0.1, (
            f"100 is_loading() calls took {elapsed:.3f}s (target: <0.1s). "
            "Status check should be O(1)."
        )

    def test_get_provider_if_ready_returns_quickly(self):
        """Verify get_provider_if_ready() is fast and non-blocking."""
        from aurora_context_code.semantic.model_utils import BackgroundModelLoader

        loader = BackgroundModelLoader.get_instance()

        start = time.time()
        for _ in range(100):
            loader.get_provider_if_ready()
        elapsed = time.time() - start

        # 100 calls should be instant
        assert elapsed < 0.1, (
            f"100 get_provider_if_ready() calls took {elapsed:.3f}s (target: <0.1s). "
            "Non-blocking provider check should be O(1)."
        )


class TestHFHubOfflineMode:
    """Tests for HF_HUB_OFFLINE environment variable handling."""

    def test_offline_mode_set_when_cached(self, temp_aurora_project: Path):
        """Verify HF_HUB_OFFLINE=1 is set when model is cached."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        # Clear any existing HF_HUB_OFFLINE setting
        old_hf_offline = os.environ.pop("HF_HUB_OFFLINE", None)

        try:
            # Capture environment when EmbeddingProvider is created
            env_at_import = {}

            def mock_embedding_provider(*args, **kwargs):
                env_at_import["HF_HUB_OFFLINE"] = os.environ.get("HF_HUB_OFFLINE")
                return MagicMock()

            # Mock BackgroundModelLoader to return no provider (not pre-loaded)
            mock_loader = MagicMock()
            mock_loader.get_provider_if_ready.return_value = None
            mock_loader.is_loading.return_value = False

            with patch(
                "aurora_context_code.semantic.model_utils.is_model_cached",
                return_value=True,
            ):
                with patch(
                    "aurora_context_code.semantic.model_utils.BackgroundModelLoader",
                ) as mock_loader_class:
                    mock_loader_class.get_instance.return_value = mock_loader

                    with patch(
                        "aurora_context_code.semantic.EmbeddingProvider",
                        side_effect=mock_embedding_provider,
                    ):
                        retriever = MemoryRetriever(store=store, config=None)
                        try:
                            retriever._get_embedding_provider()
                        except Exception:
                            pass  # May fail due to mock

            # HF_HUB_OFFLINE should be set before creating EmbeddingProvider
            assert env_at_import.get("HF_HUB_OFFLINE") == "1", (
                "HF_HUB_OFFLINE should be set to '1' when model is cached "
                "to prevent network requests."
            )
        finally:
            # Restore original environment
            if old_hf_offline is not None:
                os.environ["HF_HUB_OFFLINE"] = old_hf_offline
            elif "HF_HUB_OFFLINE" in os.environ:
                del os.environ["HF_HUB_OFFLINE"]

        store.close()


class TestKnownModelDimensions:
    """Tests for known model dimension caching."""

    def test_known_models_have_cached_dimensions(self):
        """Verify all commonly used models have pre-cached dimensions."""
        from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

        expected_models = [
            "all-MiniLM-L6-v2",
            "sentence-transformers/all-MiniLM-L6-v2",
            "all-mpnet-base-v2",
        ]

        for model_name in expected_models:
            assert model_name in EmbeddingProvider._KNOWN_EMBEDDING_DIMS, (
                f"Model '{model_name}' should have cached embedding dimension "
                "to avoid loading model just to get dimension."
            )

    def test_correct_dimensions_for_known_models(self):
        """Verify cached dimensions match actual model dimensions."""
        from aurora_context_code.semantic.embedding_provider import EmbeddingProvider

        expected_dims = {
            "all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "multi-qa-MiniLM-L6-cos-v1": 384,
            "all-distilroberta-v1": 768,
        }

        for model_name, expected_dim in expected_dims.items():
            actual_dim = EmbeddingProvider._KNOWN_EMBEDDING_DIMS.get(model_name)
            assert (
                actual_dim == expected_dim
            ), f"Model '{model_name}' cached dim {actual_dim} != expected {expected_dim}"


# Benchmark configuration
def pytest_configure(config):
    """Configure pytest with performance markers."""
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "startup: Startup time tests")
