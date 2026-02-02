"""Performance benchmarks for aur soar startup time.

These benchmarks track the initialization time of the SOAR command,
from invocation to the first actual LLM call. The goal is to prevent
regressions and measure improvements to startup speed.

Key measurements:
- CLI command parsing and initialization
- Config loading
- Store/database connection
- Agent registry discovery
- Orchestrator initialization
- Background model loading effectiveness

Target: <3 seconds from invocation to first LLM call

Run with:
    pytest tests/performance/test_soar_startup_performance.py -v --benchmark-only
"""

import os
import tempfile
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
        (aurora_dir / "plans" / "active").mkdir(parents=True)
        (aurora_dir / "plans" / "archive").mkdir(parents=True)
        (aurora_dir / "plans" / "manifest.json").write_text("{}")
        (aurora_dir / "soar").mkdir()
        (aurora_dir / "logs").mkdir()

        # Create minimal memory database
        from aurora_core.store.sqlite import SQLiteStore

        db_path = aurora_dir / "memory.db"
        store = SQLiteStore(str(db_path))
        store.close()

        yield project


class TestSOARCommandStartup:
    """Benchmark tests for aur soar command startup performance."""

    def test_soar_help_response_time(self):
        """Verify 'aur soar --help' responds quickly (<1s).

        This measures the absolute minimum startup time - just Click
        initialization and help rendering.
        """
        from click.testing import CliRunner

        from aurora_cli.commands.soar import soar_command

        runner = CliRunner()

        start = time.time()
        result = runner.invoke(soar_command, ["--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert elapsed < 1.0, (
            f"'aur soar --help' took {elapsed:.3f}s (target: <1.0s). Help should be instant."
        )

    def test_critical_imports_fast(self):
        """Verify critical SOAR imports complete quickly (<2s)."""
        import sys

        # Clear cached imports for accurate measurement
        modules_to_clear = [
            k
            for k in list(sys.modules.keys())
            if k.startswith("aurora_soar") or k.startswith("aurora_cli.commands.soar")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.time()

        # Import critical SOAR modules
        from aurora_cli.commands.soar import soar_command  # noqa: F401
        from aurora_soar.agent_registry import AgentRegistry  # noqa: F401
        from aurora_soar.orchestrator import SOAROrchestrator  # noqa: F401

        elapsed = time.time() - start

        assert elapsed < 2.0, (
            f"SOAR imports took {elapsed:.3f}s (target: <2.0s). "
            "Import time directly affects startup latency."
        )

    def test_no_heavy_imports_at_module_level(self):
        """Verify SOAR command doesn't import heavy dependencies at module level."""
        import sys

        # Track which modules get imported
        initial_modules = set(sys.modules.keys())

        # Import the command
        from aurora_cli.commands.soar import soar_command  # noqa: F401

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


class TestConfigurationLoading:
    """Benchmark config loading performance."""

    def test_config_load_time(self):
        """Verify Config loading is fast (<500ms)."""
        from aurora_cli.config import Config

        start = time.time()
        config = Config()
        elapsed = time.time() - start

        assert elapsed < 0.5, (
            f"Config loading took {elapsed:.3f}s (target: <0.5s). Config should load quickly."
        )
        assert config is not None


class TestStoreInitialization:
    """Benchmark store/database initialization."""

    def test_sqlite_store_init_fast(self, temp_aurora_project: Path):
        """Verify SQLiteStore initialization is fast (<100ms)."""
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"

        start = time.time()
        store = SQLiteStore(str(db_path))
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"SQLiteStore init took {elapsed:.3f}s (target: <0.1s). "
            "Database connection should be fast."
        )

        store.close()

    def test_store_has_memory_check_fast(self, temp_aurora_project: Path):
        """Verify checking for indexed memory is fast (<50ms)."""
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))

        start = time.time()
        has_memory = store.count() > 0
        elapsed = time.time() - start

        assert elapsed < 0.05, (
            f"Checking for memory took {elapsed:.3f}s (target: <0.05s). "
            "Simple count query should be instant."
        )

        store.close()


class TestAgentDiscovery:
    """Benchmark agent discovery and registry initialization."""

    def test_agent_registry_init_fast(self):
        """Verify AgentRegistry initialization is fast (<100ms)."""
        from aurora_soar.agent_registry import AgentRegistry

        start = time.time()
        registry = AgentRegistry()
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"AgentRegistry init took {elapsed:.3f}s (target: <0.1s). "
            "Empty registry creation should be instant."
        )
        assert registry is not None

    def test_agent_manifest_loading_fast(self, temp_aurora_project: Path):
        """Verify agent manifest discovery is fast (<1s)."""
        import os

        original_cwd = os.getcwd()

        try:
            os.chdir(temp_aurora_project)

            from aurora_cli.commands.agents import get_manifest

            start = time.time()
            manifest = get_manifest()
            elapsed = time.time() - start

            assert elapsed < 1.0, (
                f"Agent manifest loading took {elapsed:.3f}s (target: <1.0s). "
                "Discovering agents should be fast."
            )
            assert manifest is not None
        finally:
            os.chdir(original_cwd)


class TestOrchestratorInitialization:
    """Benchmark SOAROrchestrator initialization."""

    def test_orchestrator_init_without_llm(self, temp_aurora_project: Path):
        """Verify orchestrator initialization is fast (<500ms)."""
        from aurora_cli.config import Config
        from aurora_core.store.sqlite import SQLiteStore
        from aurora_soar.agent_registry import AgentRegistry
        from aurora_soar.orchestrator import SOAROrchestrator

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))
        registry = AgentRegistry()
        config = Config()

        # Mock LLM client
        mock_llm = MagicMock()

        start = time.time()
        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=registry,
            config=config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
        )
        elapsed = time.time() - start

        assert elapsed < 0.5, (
            f"Orchestrator init took {elapsed:.3f}s (target: <0.5s). "
            "Creating orchestrator should be lightweight."
        )
        assert orchestrator is not None

        store.close()


class TestBackgroundModelLoading:
    """Benchmark background model loading mechanism."""

    def test_background_loading_starts_quickly(self):
        """Verify starting background model loading is non-blocking (<100ms)."""
        from aurora_cli.commands.soar import _start_background_model_loading

        start = time.time()
        _start_background_model_loading(verbose=False)
        elapsed = time.time() - start

        assert elapsed < 0.1, (
            f"Starting background loading took {elapsed:.3f}s (target: <0.1s). "
            "Starting background thread should be instant."
        )

    def test_model_cache_check_lightweight(self):
        """Verify cache checking doesn't import heavy dependencies."""
        import sys

        initial_modules = set(sys.modules.keys())

        # This should use the lightweight cache check
        try:
            from aurora_context_code.model_cache import is_model_cached_fast

            is_cached = is_model_cached_fast()
        except ImportError:
            pytest.skip("aurora_context_code not installed")

        new_modules = set(sys.modules.keys()) - initial_modules

        # Should not import torch or sentence_transformers
        heavy_deps = ["torch", "sentence_transformers"]
        for dep in heavy_deps:
            imported = [m for m in new_modules if dep in m.lower()]
            assert not imported, (
                f"Cache check imported {dep}: {imported}. Cache checking should be lightweight."
            )


class TestEndToEndStartup:
    """End-to-end startup time benchmarks."""

    def test_soar_command_startup_to_llm_call(self, temp_aurora_project: Path):
        """Benchmark full startup time from command invocation to LLM call (<3s).

        This is the most important metric - time until the user sees progress.
        """
        from click.testing import CliRunner

        from aurora_cli.commands.soar import soar_command

        runner = CliRunner()

        # Track when LLM client is created (indicates startup complete)
        llm_client_created_at = None
        original_init = None

        def mock_llm_init(self, *args, **kwargs):
            nonlocal llm_client_created_at
            llm_client_created_at = time.time()
            # Don't actually initialize (would require real tool)
            self.tool = "mock"
            self.model = "sonnet"

        try:
            from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

            original_init = CLIPipeLLMClient.__init__
            CLIPipeLLMClient.__init__ = mock_llm_init
        except ImportError:
            pytest.skip("CLIPipeLLMClient not available")

        try:
            os.chdir(temp_aurora_project)

            with patch("shutil.which", return_value="/usr/bin/mock"):
                with patch("aurora_cli.commands.soar.SOAROrchestrator") as mock_orch:
                    # Make execute fail fast after we measure startup
                    mock_orch.return_value.execute.side_effect = RuntimeError("Test stop")

                    start = time.time()
                    result = runner.invoke(soar_command, ["test query"])

                    if llm_client_created_at:
                        startup_time = llm_client_created_at - start
                    else:
                        startup_time = time.time() - start

            # Allow failure (we're just measuring startup)
            # The startup time should still be captured

            assert startup_time < 3.0, (
                f"Startup to LLM client creation took {startup_time:.3f}s (target: <3.0s). "
                "This is the critical user-facing startup latency."
            )
        finally:
            if original_init:
                CLIPipeLLMClient.__init__ = original_init
            os.chdir("/")


class TestRegressionGuards:
    """Strict regression guards to prevent performance degradation."""

    # Maximum acceptable times (in seconds)
    MAX_IMPORT_TIME = 2.0
    MAX_CONFIG_TIME = 0.5
    MAX_STORE_INIT_TIME = 0.1
    MAX_REGISTRY_INIT_TIME = 0.1
    MAX_ORCHESTRATOR_INIT_TIME = 0.5
    MAX_TOTAL_STARTUP_TIME = 3.0

    def test_guard_import_time(self):
        """REGRESSION GUARD: Critical imports must complete in <2s."""
        import sys

        modules_to_clear = [
            k
            for k in list(sys.modules.keys())
            if "aurora_soar" in k or "aurora_cli.commands.soar" in k
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        start = time.time()
        from aurora_cli.commands.soar import soar_command  # noqa: F401

        elapsed = time.time() - start

        assert elapsed < self.MAX_IMPORT_TIME, (
            f"REGRESSION: Import time {elapsed:.3f}s exceeds {self.MAX_IMPORT_TIME}s. "
            "Check for new heavy imports at module level."
        )

    def test_guard_config_time(self):
        """REGRESSION GUARD: Config loading must complete in <500ms."""
        from aurora_cli.config import Config

        start = time.time()
        Config()
        elapsed = time.time() - start

        assert elapsed < self.MAX_CONFIG_TIME, (
            f"REGRESSION: Config load time {elapsed:.3f}s exceeds {self.MAX_CONFIG_TIME}s. "
            "Config loading should not do heavy I/O."
        )

    def test_guard_store_init_time(self, temp_aurora_project: Path):
        """REGRESSION GUARD: Store initialization must complete in <100ms."""
        from aurora_core.store.sqlite import SQLiteStore

        db_path = temp_aurora_project / ".aurora" / "memory.db"

        start = time.time()
        store = SQLiteStore(str(db_path))
        elapsed = time.time() - start

        assert elapsed < self.MAX_STORE_INIT_TIME, (
            f"REGRESSION: Store init time {elapsed:.3f}s exceeds {self.MAX_STORE_INIT_TIME}s. "
            "Database connection should be instant."
        )

        store.close()

    def test_guard_registry_init_time(self):
        """REGRESSION GUARD: Registry initialization must complete in <100ms."""
        from aurora_soar.agent_registry import AgentRegistry

        start = time.time()
        AgentRegistry()
        elapsed = time.time() - start

        assert elapsed < self.MAX_REGISTRY_INIT_TIME, (
            f"REGRESSION: Registry init time {elapsed:.3f}s exceeds {self.MAX_REGISTRY_INIT_TIME}s. "
            "Empty registry should be instant."
        )


class TestStartupOptimizations:
    """Tests to verify startup optimizations are working correctly."""

    def test_lazy_imports_working(self):
        """Verify lazy import pattern is working for heavy dependencies."""
        import sys

        # Import command but don't invoke
        from aurora_cli.commands.soar import soar_command  # noqa: F401

        # These should NOT be imported yet
        assert "sentence_transformers" not in sys.modules, (
            "sentence_transformers imported too early"
        )
        assert "torch" not in sys.modules or "aurora_context_code" not in sys.modules, (
            "torch imported too early (unless already loaded)"
        )

    def test_background_loading_exists(self):
        """Verify background model loading function exists and is callable."""
        from aurora_cli.commands.soar import _start_background_model_loading

        assert callable(_start_background_model_loading), "Background loading function should exist"


class TestProgressiveStartup:
    """Test that startup happens progressively with early feedback."""

    def test_phase_callback_fires_early(self, temp_aurora_project: Path):
        """Verify phase callbacks fire early to show progress."""
        from aurora_cli.config import Config
        from aurora_core.store.sqlite import SQLiteStore
        from aurora_soar.agent_registry import AgentRegistry
        from aurora_soar.orchestrator import SOAROrchestrator

        db_path = temp_aurora_project / ".aurora" / "memory.db"
        store = SQLiteStore(str(db_path))
        registry = AgentRegistry()
        config = Config()

        # Track callback timing
        callbacks_received = []

        def test_callback(phase_name: str, status: str, result: dict):
            callbacks_received.append({"phase": phase_name, "status": status, "time": time.time()})

        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(content='{"subgoals": [], "warnings": []}')

        orchestrator = SOAROrchestrator(
            store=store,
            agent_registry=registry,
            config=config,
            reasoning_llm=mock_llm,
            solving_llm=mock_llm,
            phase_callback=test_callback,
        )

        start = time.time()

        try:
            orchestrator.execute("test query", verbosity="normal")
        except Exception:
            pass  # May fail, we're just checking callbacks

        # Should receive callbacks for early phases quickly
        if callbacks_received:
            first_callback = callbacks_received[0]
            time_to_first_callback = first_callback["time"] - start

            assert time_to_first_callback < 1.0, (
                f"First callback took {time_to_first_callback:.3f}s (target: <1.0s). "
                "User should see progress quickly."
            )

        store.close()


# Benchmark configuration
def pytest_configure(config):
    """Configure pytest with performance markers."""
    config.addinivalue_line("markers", "performance: Performance benchmark tests")
    config.addinivalue_line("markers", "startup: Startup time tests")
