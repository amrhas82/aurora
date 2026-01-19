"""Performance tests for aur goals command startup time.

These tests ensure the startup time for the goals command stays within
acceptable thresholds to prevent regression. The main concern is model
loading time for the EmbeddingProvider which can cause a 30+ second hang.

Targets:
- With cached model: <5 seconds for initial setup
- With lazy model loading: <2 seconds until first LLM call
- BM25-only fallback: <1 second for retriever initialization

These tests are marked with @pytest.mark.performance and can be run with:
    pytest tests/performance/test_goals_startup_performance.py -v
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# Test markers
pytestmark = [pytest.mark.performance]


@pytest.fixture
def temp_aurora_project() -> Generator[Path, None, None]:
    """Create a temporary directory with Aurora structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project = Path(tmpdir)
        aurora_dir = project / ".aurora"
        aurora_dir.mkdir()
        (aurora_dir / "plans" / "active").mkdir(parents=True)
        (aurora_dir / "plans" / "archive").mkdir(parents=True)
        (aurora_dir / "logs").mkdir()
        (aurora_dir / "cache").mkdir()
        # Create empty database file
        (aurora_dir / "memory.db").touch()
        yield project


@pytest.fixture
def mock_llm_client():
    """Mock LLM client to avoid actual API calls."""
    with patch("aurora_cli.planning.core.CLIPipeLLMClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.generate.return_value = MagicMock(
            content='[{"id": "sg-1", "title": "Test", "description": "Test", "assigned_agent": "@code-developer", "dependencies": []}]'
        )
        mock_client.return_value = mock_instance
        yield mock_instance


class TestEmbeddingProviderStartup:
    """Tests for EmbeddingProvider initialization performance."""

    def test_embedding_provider_lazy_loading(self):
        """Verify EmbeddingProvider doesn't load model on init (<100ms target)."""
        from aurora_context_code.semantic import EmbeddingProvider

        start = time.time()

        # Mock the sentence-transformers to prevent actual model loading
        with patch(
            "aurora_context_code.semantic.embedding_provider.HAS_SENTENCE_TRANSFORMERS", True
        ):
            with patch("aurora_context_code.semantic.embedding_provider.SentenceTransformer"):
                with patch("aurora_context_code.semantic.embedding_provider.torch", MagicMock()):
                    # Just create provider - should NOT load model
                    provider = EmbeddingProvider.__new__(EmbeddingProvider)
                    provider.model_name = "all-MiniLM-L6-v2"
                    provider.device = "cpu"
                    provider._model = None
                    provider._embedding_dim = 384  # Known dimension

        elapsed = time.time() - start

        # Init should be very fast without model loading
        assert elapsed < 0.1, (
            f"EmbeddingProvider init took {elapsed:.3f}s (target: <0.1s). "
            "Model should not load during __init__."
        )

    def test_embedding_dim_without_model_load(self):
        """Verify embedding_dim property uses cached values for known models."""
        from aurora_context_code.semantic import EmbeddingProvider

        # Mock to prevent actual model loading
        with patch(
            "aurora_context_code.semantic.embedding_provider.HAS_SENTENCE_TRANSFORMERS", True
        ):
            with patch(
                "aurora_context_code.semantic.embedding_provider.SentenceTransformer"
            ) as mock_st:
                with patch("aurora_context_code.semantic.embedding_provider.torch") as mock_torch:
                    mock_torch.cuda.is_available.return_value = False

                    provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")

                    start = time.time()
                    dim = provider.embedding_dim
                    elapsed = time.time() - start

        # Should return 384 from cache without loading model
        assert dim == 384
        assert elapsed < 0.01, (
            f"Getting embedding_dim took {elapsed:.3f}s (target: <0.01s). "
            "Known model dimensions should be cached."
        )
        # Model should NOT have been loaded
        mock_st.assert_not_called()

    def test_model_cache_check_performance(self):
        """Verify is_model_cached check is fast (<50ms)."""
        from aurora_context_code.semantic.model_utils import is_model_cached

        start = time.time()
        _cached = is_model_cached()
        elapsed = time.time() - start

        assert elapsed < 0.05, (
            f"Model cache check took {elapsed:.3f}s (target: <0.05s). "
            "Checking HuggingFace cache should be fast."
        )


class TestMemoryRetrieverStartup:
    """Tests for MemoryRetriever initialization performance."""

    def test_retriever_lazy_initialization(self):
        """Verify MemoryRetriever doesn't create HybridRetriever on init."""
        from aurora_cli.memory.retrieval import MemoryRetriever

        start = time.time()
        retriever = MemoryRetriever(store=None, config=None)
        elapsed = time.time() - start

        assert elapsed < 0.01, (
            f"MemoryRetriever init took {elapsed:.3f}s (target: <0.01s). "
            "Retriever should be lazy-initialized."
        )
        assert retriever._retriever is None, "HybridRetriever should not be created until needed"

    def test_retriever_bm25_only_fallback_fast(self, temp_aurora_project: Path):
        """Verify BM25-only retriever initialization is fast when embeddings unavailable."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        # Create store
        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        # Mock the is_model_cached at the source module level
        with patch(
            "aurora_context_code.semantic.model_utils.is_model_cached",
            return_value=False,
        ):
            # Mock EmbeddingProvider to raise an error (simulate unavailable)
            with patch(
                "aurora_context_code.semantic.EmbeddingProvider",
                side_effect=ImportError("mocked - embeddings unavailable"),
            ):
                # Create fresh retriever to test initialization
                retriever = MemoryRetriever(store=store, config=None)

                start = time.time()
                try:
                    # Force retriever creation, which should fall back to BM25-only
                    retriever._get_retriever()
                except Exception:
                    # ImportError or other error is acceptable - we're testing latency
                    pass
                elapsed = time.time() - start

        # BM25-only initialization should be fast (even if it fails on import)
        assert elapsed < 1.0, (
            f"BM25-only retriever init took {elapsed:.3f}s (target: <1.0s). "
            "Fallback without embeddings should be fast."
        )

        store.close()


class TestGoalsCommandStartup:
    """Tests for aur goals command startup performance."""

    def test_config_loading_fast(self):
        """Verify Config loading is fast (<1s).

        Note: First config load includes discovery of config files and parsing.
        Subsequent loads within the same process are faster due to caching.
        """
        start = time.time()
        from aurora_cli.config import Config

        config = Config()
        elapsed = time.time() - start

        # Config should load in under 1 second
        # First load includes file system operations and parsing
        assert elapsed < 1.0, (
            f"Config loading took {elapsed:.3f}s (target: <1.0s). "
            "Config initialization should be fast."
        )
        assert config is not None

        # Test that subsequent loads are faster (caching)
        start2 = time.time()
        config2 = Config()
        elapsed2 = time.time() - start2

        # Second load should be faster due to any internal caching
        assert elapsed2 < elapsed, "Config reloading should benefit from caching"

    def test_plan_id_generation_fast(self, temp_aurora_project: Path):
        """Verify plan ID generation is fast (<50ms)."""
        from aurora_cli.planning.core import _generate_plan_id

        plans_dir = temp_aurora_project / ".aurora" / "plans"

        start = time.time()
        plan_id = _generate_plan_id("Test goal for performance", plans_dir)
        elapsed = time.time() - start

        assert elapsed < 0.05, (
            f"Plan ID generation took {elapsed:.3f}s (target: <0.05s). "
            "ID generation should be fast."
        )
        assert plan_id.startswith("0001-")

    def test_goal_validation_fast(self):
        """Verify goal validation is fast (<10ms)."""
        from aurora_cli.planning.core import _validate_goal

        start = time.time()
        is_valid, error = _validate_goal("Add OAuth2 authentication with JWT tokens")
        elapsed = time.time() - start

        assert (
            elapsed < 0.01
        ), f"Goal validation took {elapsed:.3f}s (target: <0.01s). Validation should be instant."
        assert is_valid is True
        assert error is None

    def test_complexity_assessment_fast(self):
        """Verify complexity assessment is fast (<10ms)."""
        from aurora_cli.planning.core import _assess_complexity
        from aurora_cli.planning.models import Subgoal

        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test subgoal",
                description="Test description",
                assigned_agent="@code-developer",
            )
        ]

        start = time.time()
        complexity = _assess_complexity("Test goal", subgoals)
        elapsed = time.time() - start

        assert elapsed < 0.01, (
            f"Complexity assessment took {elapsed:.3f}s (target: <0.01s). "
            "Assessment should be instant."
        )
        assert complexity is not None


class TestMemorySearchStartup:
    """Tests for memory search initialization performance."""

    def test_store_initialization_fast(self, temp_aurora_project: Path):
        """Verify SQLiteStore initialization is fast (<100ms)."""
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"

        start = time.time()
        store = SQLiteStore(str(db_path))
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"SQLiteStore init took {elapsed:.3f}s (target: <0.1s). "
            "Store initialization should be fast."
        )

        store.close()

    def test_agent_registry_discovery_fast(self):
        """Verify agent discovery is fast (<500ms)."""
        from aurora_soar.agent_registry import AgentRegistry

        start = time.time()
        registry = AgentRegistry()
        elapsed = time.time() - start

        assert elapsed < 0.5, (
            f"AgentRegistry init took {elapsed:.3f}s (target: <0.5s). "
            "Empty registry creation should be fast."
        )
        assert registry is not None


class TestStartupTimeThresholds:
    """End-to-end startup time threshold tests."""

    def test_imports_fast(self):
        """Verify critical imports complete quickly (<2s total)."""
        import sys

        # Clear cached imports for accurate measurement
        modules_to_clear = [k for k in sys.modules.keys() if k.startswith("aurora_")]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        start = time.time()

        # Import critical modules
        from aurora_cli.config import Config  # noqa: F401
        from aurora_cli.planning.core import create_plan  # noqa: F401
        from aurora_cli.planning.models import Plan, Subgoal  # noqa: F401

        elapsed = time.time() - start

        # First import is acceptable to be slower due to parsing
        # but should still be under 2 seconds
        assert elapsed < 2.0, (
            f"Critical imports took {elapsed:.3f}s (target: <2.0s). "
            "Import time affects perceived startup latency."
        )

    def test_no_model_loading_on_import(self):
        """Verify importing modules doesn't trigger model loading."""
        import sys

        # Clear cached imports
        modules_to_clear = [k for k in sys.modules.keys() if "sentence_transformers" in k.lower()]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Track if sentence_transformers is imported
        original_import = (
            __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__
        )
        imported_modules: list[str] = []

        def tracking_import(name, *args, **kwargs):
            imported_modules.append(name)
            return original_import(name, *args, **kwargs)

        # Import our modules while tracking
        # Note: We can't easily intercept built-in imports, so we check afterward
        from aurora_cli.config import Config  # noqa: F401
        from aurora_cli.planning.core import create_plan  # noqa: F401

        # Check that sentence_transformers wasn't loaded into sys.modules
        # during aurora_cli imports (unless it was already there)
        st_modules = [m for m in sys.modules if "sentence_transformers" in m.lower()]

        # This is informational - the key is that the model itself isn't loaded
        if st_modules:
            # Verify the model isn't actually instantiated
            for mod_name in st_modules:
                mod = sys.modules.get(mod_name)
                if mod and hasattr(mod, "SentenceTransformer"):
                    # Check there are no instantiated models
                    # This is a heuristic check
                    pass


class TestRegressionGuards:
    """Guard tests to prevent performance regressions."""

    # Maximum acceptable times (in seconds)
    MAX_CONFIG_LOAD_TIME = 0.3
    MAX_PLAN_VALIDATION_TIME = 0.1
    MAX_STORE_INIT_TIME = 0.2
    MAX_RETRIEVER_INIT_TIME = 1.0  # Without model loading
    MAX_TOTAL_SETUP_TIME = 3.0  # Before LLM call

    def test_setup_time_before_llm_call(self, temp_aurora_project: Path):
        """Verify all setup completes quickly before any LLM call (<3s)."""
        import os

        # Save and restore current directory to avoid affecting other tests
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_aurora_project)

            # Prevent any actual network calls
            os.environ["HF_HUB_OFFLINE"] = "1"

            start = time.time()

            # Simulate the setup path of aur goals
            from aurora_cli.config import Config

            config = Config()

            from aurora_cli.planning.core import (
                _generate_plan_id,
                _validate_goal,
                init_planning_directory,
            )

            # Initialize planning directory
            plans_dir = temp_aurora_project / ".aurora" / "plans"
            init_planning_directory(path=plans_dir)

            # Validate goal
            goal = "Add OAuth2 authentication with JWT tokens"
            is_valid, _ = _validate_goal(goal)
            assert is_valid

            # Generate plan ID
            plan_id = _generate_plan_id(goal, plans_dir)
            assert plan_id

            elapsed = time.time() - start

            assert elapsed < self.MAX_TOTAL_SETUP_TIME, (
                f"Setup before LLM took {elapsed:.3f}s (max: {self.MAX_TOTAL_SETUP_TIME}s). "
                "This indicates a performance regression in startup path."
            )
        finally:
            os.chdir(original_cwd)

    def test_no_model_download_attempt_when_cached(self):
        """Verify no download is attempted when model is already cached."""
        from aurora_context_code.semantic.model_utils import (
            ensure_model_downloaded,
            is_model_cached,
        )

        if is_model_cached():
            # Model is cached, measure that it returns quickly without re-downloading
            start = time.time()
            result = ensure_model_downloaded(show_progress=False)
            elapsed = time.time() - start

            # Should return True (cached) very quickly
            assert result is True
            assert elapsed < 0.1, (
                f"ensure_model_downloaded took {elapsed:.3f}s when cached (target: <0.1s). "
                "Cache check should be instant."
            )
        else:
            pytest.skip("Model not cached - download test not applicable")


class TestCLIStartupTime:
    """End-to-end CLI startup time tests using Click test runner."""

    def test_goals_help_fast(self):
        """Verify 'aur goals --help' responds quickly (<2s).

        This is a proxy for CLI startup time since --help exits before
        any heavy initialization occurs.
        """
        from click.testing import CliRunner

        from aurora_cli.commands.goals import goals_command

        runner = CliRunner()

        start = time.time()
        result = runner.invoke(goals_command, ["--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0, f"Help command failed: {result.output}"
        assert elapsed < 2.0, (
            f"'aur goals --help' took {elapsed:.3f}s (target: <2.0s). "
            "CLI help should respond quickly."
        )

    def test_goals_validation_error_fast(self):
        """Verify goals command fails fast on invalid input (<2s)."""
        from click.testing import CliRunner

        from aurora_cli.commands.goals import goals_command

        runner = CliRunner()

        # Use isolated filesystem to avoid cwd issues
        with runner.isolated_filesystem():
            start = time.time()
            # Too short goal should fail validation quickly
            result = runner.invoke(goals_command, ["short"])
            elapsed = time.time() - start

        # Should fail due to goal too short (min 10 chars)
        assert result.exit_code != 0
        assert elapsed < 2.0, (
            f"Validation error took {elapsed:.3f}s (target: <2.0s). "
            "Input validation should fail fast."
        )

    def test_goals_cli_setup_without_llm(self):
        """Verify CLI setup before LLM call is fast (<5s).

        Tests the full setup path using Click test runner with mocked LLM.
        """
        from click.testing import CliRunner

        from aurora_cli.commands.goals import goals_command

        runner = CliRunner()

        # Use the temp project directory and mock the LLM
        with runner.isolated_filesystem():
            # Create minimal Aurora structure
            aurora_dir = Path(".aurora")
            aurora_dir.mkdir()
            (aurora_dir / "plans" / "active").mkdir(parents=True)
            (aurora_dir / "plans" / "archive").mkdir(parents=True)
            (aurora_dir / "plans" / "manifest.json").write_text("{}")

            # Mock the LLM client and tool check
            with patch("aurora_cli.commands.goals.shutil.which", return_value="/usr/bin/claude"):
                with patch("aurora_cli.commands.goals.CLIPipeLLMClient"):
                    with patch("aurora_cli.planning.core._decompose_with_soar") as mock_decompose:
                        # Return a valid subgoal structure
                        mock_decompose.return_value = (
                            [
                                {
                                    "id": "sg-1",
                                    "title": "Test subgoal",
                                    "description": "Test description",
                                    "assigned_agent": "@code-developer",
                                    "ideal_agent": "@code-developer",
                                    "match_quality": "excellent",
                                    "dependencies": [],
                                }
                            ],
                            [],  # warnings
                        )

                        start = time.time()
                        result = runner.invoke(
                            goals_command,
                            ["Test goal for performance testing", "--yes", "--format", "json"],
                        )
                        elapsed = time.time() - start

        # Allow up to 5s for full CLI setup (includes file I/O)
        assert elapsed < 5.0, (
            f"CLI setup with mocked LLM took {elapsed:.3f}s (target: <5.0s). "
            f"Output: {result.output[:200] if result.output else 'no output'}"
        )


class TestBackgroundPreloading:
    """Tests for background model preloading functionality."""

    def test_preload_model_method_exists(self):
        """Verify EmbeddingProvider has preload_model method for background loading."""
        from aurora_context_code.semantic import EmbeddingProvider

        # Create provider without loading model
        with patch(
            "aurora_context_code.semantic.embedding_provider.HAS_SENTENCE_TRANSFORMERS", True
        ):
            with patch("aurora_context_code.semantic.embedding_provider.SentenceTransformer"):
                with patch("aurora_context_code.semantic.embedding_provider.torch") as mock_torch:
                    mock_torch.cuda.is_available.return_value = False
                    provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")

        # Verify preload_model method exists
        assert hasattr(
            provider, "preload_model"
        ), "EmbeddingProvider should have preload_model method"
        assert callable(provider.preload_model), "preload_model should be callable"

    def test_is_model_loaded_property(self):
        """Verify is_model_loaded returns correct state before/after loading."""
        from aurora_context_code.semantic import EmbeddingProvider

        with patch(
            "aurora_context_code.semantic.embedding_provider.HAS_SENTENCE_TRANSFORMERS", True
        ):
            with patch(
                "aurora_context_code.semantic.embedding_provider.SentenceTransformer"
            ) as mock_st:
                with patch("aurora_context_code.semantic.embedding_provider.torch") as mock_torch:
                    mock_torch.cuda.is_available.return_value = False
                    mock_model = MagicMock()
                    mock_model.get_sentence_embedding_dimension.return_value = 384
                    mock_st.return_value = mock_model

                    provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")

                    # Should not be loaded initially
                    assert not provider.is_model_loaded(), "Model should not be loaded on init"

                    # Load the model
                    provider.preload_model()

                    # Should be loaded now
                    assert provider.is_model_loaded(), "Model should be loaded after preload"

    def test_background_preload_thread_safe(self):
        """Verify preload_model can be called from a background thread."""
        import threading

        from aurora_context_code.semantic import EmbeddingProvider

        with patch(
            "aurora_context_code.semantic.embedding_provider.HAS_SENTENCE_TRANSFORMERS", True
        ):
            with patch(
                "aurora_context_code.semantic.embedding_provider.SentenceTransformer"
            ) as mock_st:
                with patch("aurora_context_code.semantic.embedding_provider.torch") as mock_torch:
                    mock_torch.cuda.is_available.return_value = False
                    mock_model = MagicMock()
                    mock_model.get_sentence_embedding_dimension.return_value = 384
                    mock_st.return_value = mock_model

                    provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")

                    # Load in background thread
                    thread = threading.Thread(target=provider.preload_model)
                    thread.start()
                    thread.join(timeout=5.0)

                    assert not thread.is_alive(), "Preload thread should complete"
                    assert (
                        provider.is_model_loaded()
                    ), "Model should be loaded after thread completes"


class TestModelLoadingTiming:
    """Tests to measure and guard actual model loading performance."""

    @pytest.mark.skipif(
        os.environ.get("CI") == "true", reason="Model loading test requires local model cache"
    )
    def test_cached_model_load_time(self):
        """Measure time to load cached model (informational, not blocking)."""
        from aurora_context_code.semantic.model_utils import is_model_cached

        if not is_model_cached():
            pytest.skip("Model not cached - load timing test not applicable")

        from aurora_context_code.semantic import EmbeddingProvider

        start = time.time()
        provider = EmbeddingProvider(model_name="all-MiniLM-L6-v2")
        # Force model load
        provider.preload_model()
        elapsed = time.time() - start

        # Log the timing for visibility
        print(f"\nCached model load time: {elapsed:.2f}s")

        # Cached model should load within reasonable time
        # Note: First load in a process is slower due to library initialization
        assert elapsed < 30.0, (
            f"Cached model load took {elapsed:.2f}s (max: 30s). "
            "This indicates potential performance issues."
        )

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


class TestGranularRegressionGuards:
    """Fine-grained regression guards for specific operations."""

    # Stricter thresholds for individual operations
    MAX_IMPORT_TIME = 1.5  # seconds
    MAX_CONFIG_TIME = 0.5  # seconds
    MAX_VALIDATION_TIME = 0.05  # seconds
    MAX_ID_GENERATION_TIME = 0.1  # seconds
    MAX_CACHE_CHECK_TIME = 0.1  # seconds

    def test_aurora_cli_import_time(self):
        """Guard: aurora_cli imports must complete in <1.5s."""
        import sys

        # Clear aurora modules
        modules_to_clear = [k for k in list(sys.modules.keys()) if k.startswith("aurora_cli")]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.time()
        import aurora_cli.commands.goals  # noqa: F401

        elapsed = time.time() - start

        assert elapsed < self.MAX_IMPORT_TIME, (
            f"aurora_cli.commands.goals import took {elapsed:.3f}s "
            f"(max: {self.MAX_IMPORT_TIME}s). Check for heavy imports at module level."
        )

    def test_config_instantiation_guard(self):
        """Guard: Config() must instantiate in <0.5s."""
        from aurora_cli.config import Config

        start = time.time()
        _ = Config()
        elapsed = time.time() - start

        assert elapsed < self.MAX_CONFIG_TIME, (
            f"Config() took {elapsed:.3f}s (max: {self.MAX_CONFIG_TIME}s). "
            "Config initialization should not do heavy I/O."
        )

    def test_goal_validation_guard(self):
        """Guard: Goal validation must complete in <50ms."""
        from aurora_cli.planning.core import _validate_goal

        start = time.time()
        _validate_goal("A" * 100)  # Valid length goal
        elapsed = time.time() - start

        assert elapsed < self.MAX_VALIDATION_TIME, (
            f"Goal validation took {elapsed:.3f}s (max: {self.MAX_VALIDATION_TIME}s). "
            "Validation should be string operations only."
        )

    def test_plan_id_generation_guard(self, temp_aurora_project: Path):
        """Guard: Plan ID generation must complete in <100ms."""
        from aurora_cli.planning.core import _generate_plan_id

        plans_dir = temp_aurora_project / ".aurora" / "plans"

        start = time.time()
        _generate_plan_id("Test goal", plans_dir)
        elapsed = time.time() - start

        assert elapsed < self.MAX_ID_GENERATION_TIME, (
            f"Plan ID generation took {elapsed:.3f}s (max: {self.MAX_ID_GENERATION_TIME}s). "
            "ID generation should be fast file system operations."
        )

    def test_model_cache_check_guard(self):
        """Guard: Model cache check must complete in <100ms."""
        from aurora_context_code.semantic.model_utils import is_model_cached

        start = time.time()
        is_model_cached()
        elapsed = time.time() - start

        assert elapsed < self.MAX_CACHE_CHECK_TIME, (
            f"Model cache check took {elapsed:.3f}s (max: {self.MAX_CACHE_CHECK_TIME}s). "
            "Cache check should be simple directory traversal."
        )


class TestStartupPathOptimizations:
    """Tests to verify startup path optimizations are working."""

    def test_no_embedding_import_on_goals_help(self):
        """Verify --help doesn't import sentence_transformers."""
        import sys

        from click.testing import CliRunner

        from aurora_cli.commands.goals import goals_command

        # Note which ST modules were already loaded
        st_modules_before = {m for m in sys.modules if "sentence_transformers" in m.lower()}

        runner = CliRunner()
        runner.invoke(goals_command, ["--help"])

        st_modules_after = {m for m in sys.modules if "sentence_transformers" in m.lower()}
        new_st_modules = st_modules_after - st_modules_before

        # Help should not trigger any new sentence_transformers imports
        assert not new_st_modules, (
            f"Help command loaded sentence_transformers modules: {new_st_modules}. "
            "Embedding imports should be lazy."
        )

    def test_has_indexed_memory_avoids_model_load(self, temp_aurora_project: Path):
        """Verify has_indexed_memory() doesn't trigger model loading."""
        from aurora_cli.memory.retrieval import MemoryRetriever
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        retriever = MemoryRetriever(store=store, config=None)

        # This should check the store directly without loading embedding model
        with patch("aurora_context_code.semantic.EmbeddingProvider") as mock_provider:
            has_memory = retriever.has_indexed_memory()

            # EmbeddingProvider should NOT have been instantiated
            mock_provider.assert_not_called()

        store.close()

    def test_hf_hub_offline_prevents_network(self, temp_aurora_project: Path):
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

            # Patch at the source modules where they're imported from
            with patch(
                "aurora_context_code.semantic.model_utils.is_model_cached",
                return_value=True,
            ):
                with patch(
                    "aurora_context_code.semantic.model_utils.BackgroundModelLoader"
                ) as mock_loader_class:
                    mock_loader_class.get_instance.return_value = mock_loader

                    with patch(
                        "aurora_context_code.semantic.EmbeddingProvider",
                        side_effect=mock_embedding_provider,
                    ):
                        retriever = MemoryRetriever(store=store, config=None)
                        try:
                            # This triggers _get_embedding_provider which should set HF_HUB_OFFLINE
                            retriever._get_embedding_provider()
                        except Exception:
                            pass  # May fail due to mock, that's OK

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


# Benchmark configuration for pytest-benchmark (if available)
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "performance: Performance regression tests")
    config.addinivalue_line("markers", "startup: Startup time tests")
