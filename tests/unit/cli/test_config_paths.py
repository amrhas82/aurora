"""Tests for config.py path changes (project-specific vs global).

This test module verifies that Aurora configuration uses project-specific paths
for all files except budget_tracker.json.

Test-Driven Development (TDD):
- These tests are written FIRST (RED phase)
- Implementation in config.py comes SECOND (GREEN phase)
"""

import os
import tempfile
from pathlib import Path

import pytest

from aurora_cli.config import CONFIG_SCHEMA, Config, load_config


class TestConfigDefaultPaths:
    """Test that default Config dataclass paths are project-specific."""

    def test_logging_file_is_project_specific(self):
        """Logging file should be in ./.aurora/logs/aurora.log (project-specific)."""
        config = Config()
        assert config.logging_file == "./.aurora/logs/aurora.log"
        assert not config.logging_file.startswith("~/")

    def test_mcp_log_file_is_project_specific(self):
        """MCP log file should be in ./.aurora/logs/mcp.log (project-specific)."""
        config = Config()
        assert config.mcp_log_file == "./.aurora/logs/mcp.log"
        assert not config.mcp_log_file.startswith("~/")

    def test_db_path_is_project_specific(self):
        """Database path should be ./.aurora/memory.db (project-specific)."""
        config = Config()
        assert config.db_path == "./.aurora/memory.db"
        assert not config.db_path.startswith("~/")

    def test_agents_manifest_path_is_project_specific(self):
        """Agent manifest should be in ./.aurora/cache/agent_manifest.json (project-specific)."""
        config = Config()
        assert config.agents_manifest_path == "./.aurora/cache/agent_manifest.json"
        assert not config.agents_manifest_path.startswith("~/")

    def test_planning_base_dir_is_project_specific(self):
        """Planning base directory should be ./.aurora/plans (project-specific)."""
        config = Config()
        assert config.planning_base_dir == "./.aurora/plans"
        assert not config.planning_base_dir.startswith("~/")

    def test_budget_tracker_path_is_global(self):
        """Budget tracker should remain global at ~/.aurora/budget_tracker.json."""
        config = Config()
        assert config.budget_tracker_path == "~/.aurora/budget_tracker.json"
        assert config.budget_tracker_path.startswith("~/")


class TestConfigSchemaDefaultPaths:
    """Test that CONFIG_SCHEMA nested structure uses project-specific paths."""

    def test_schema_logging_file_is_project_specific(self):
        """CONFIG_SCHEMA logging.file should be project-specific."""
        assert CONFIG_SCHEMA["logging"]["file"] == "./.aurora/logs/aurora.log"
        assert not CONFIG_SCHEMA["logging"]["file"].startswith("~/")

    def test_schema_mcp_log_file_is_project_specific(self):
        """CONFIG_SCHEMA mcp.log_file should be project-specific."""
        assert CONFIG_SCHEMA["mcp"]["log_file"] == "./.aurora/logs/mcp.log"
        assert not CONFIG_SCHEMA["mcp"]["log_file"].startswith("~/")

    def test_schema_database_path_is_project_specific(self):
        """CONFIG_SCHEMA database.path should be project-specific."""
        assert CONFIG_SCHEMA["database"]["path"] == "./.aurora/memory.db"
        assert not CONFIG_SCHEMA["database"]["path"].startswith("~/")

    def test_schema_agents_manifest_path_is_project_specific(self):
        """CONFIG_SCHEMA agents.manifest_path should be project-specific."""
        assert CONFIG_SCHEMA["agents"]["manifest_path"] == "./.aurora/cache/agent_manifest.json"
        assert not CONFIG_SCHEMA["agents"]["manifest_path"].startswith("~/")

    def test_schema_planning_base_dir_is_project_specific(self):
        """CONFIG_SCHEMA planning.base_dir should be project-specific."""
        assert CONFIG_SCHEMA["planning"]["base_dir"] == "./.aurora/plans"
        assert not CONFIG_SCHEMA["planning"]["base_dir"].startswith("~/")

    def test_schema_budget_tracker_path_is_global(self):
        """CONFIG_SCHEMA budget.tracker_path should remain global."""
        assert CONFIG_SCHEMA["budget"]["tracker_path"] == "~/.aurora/budget_tracker.json"
        assert CONFIG_SCHEMA["budget"]["tracker_path"].startswith("~/")


class TestConfigPathExpansion:
    """Test that path expansion works correctly for project-specific paths."""

    def test_get_db_path_expands_relative_to_absolute(self):
        """get_db_path() should expand ./.aurora/memory.db to absolute path."""
        config = Config(db_path="./.aurora/memory.db")
        db_path = config.get_db_path()

        # Should be absolute
        assert Path(db_path).is_absolute()
        # Should end with .aurora/memory.db
        assert db_path.endswith(".aurora/memory.db")
        # Should NOT contain "./" at start
        assert not db_path.startswith("./")

    def test_get_manifest_path_expands_relative_to_absolute(self):
        """get_manifest_path() should expand project-specific path to absolute."""
        config = Config(agents_manifest_path="./.aurora/cache/agent_manifest.json")
        manifest_path = config.get_manifest_path()

        # Should be absolute
        assert Path(manifest_path).is_absolute()
        # Should end with .aurora/cache/agent_manifest.json
        assert manifest_path.endswith(".aurora/cache/agent_manifest.json")

    def test_get_plans_path_expands_relative_to_absolute(self):
        """get_plans_path() should expand project-specific path to absolute."""
        config = Config(planning_base_dir="./.aurora/plans")
        plans_path = config.get_plans_path()

        # Should be absolute
        assert Path(plans_path).is_absolute()
        # Should end with .aurora/plans
        assert plans_path.endswith(".aurora/plans")

    def test_path_expansion_uses_current_directory(self):
        """Project-specific paths should resolve relative to current directory."""
        config = Config(db_path="./.aurora/memory.db")
        db_path = config.get_db_path()

        # Should contain the current working directory
        current_dir = Path.cwd()
        assert str(current_dir) in db_path


class TestLoadConfigWithProjectPaths:
    """Test that load_config() handles project-specific paths correctly."""

    def test_load_config_defaults_to_project_paths(self):
        """load_config() with no file should use project-specific defaults."""
        # Use a temp directory where no config file exists
        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily override AURORA_HOME to prevent loading global config
            original_aurora_home = os.environ.get("AURORA_HOME")
            os.environ["AURORA_HOME"] = tmpdir
            original_cwd = os.getcwd()

            try:
                os.chdir(tmpdir)

                config = load_config(path=None)

                # Verify project-specific paths
                assert config.logging_file == "./.aurora/logs/aurora.log"
                assert config.mcp_log_file == "./.aurora/logs/mcp.log"
                assert config.db_path == "./.aurora/memory.db"
                assert config.agents_manifest_path == "./.aurora/cache/agent_manifest.json"
                assert config.planning_base_dir == "./.aurora/plans"

                # Verify global budget tracker
                assert config.budget_tracker_path == "~/.aurora/budget_tracker.json"
            finally:
                os.chdir(original_cwd)
                if original_aurora_home is not None:
                    os.environ["AURORA_HOME"] = original_aurora_home
                else:
                    os.environ.pop("AURORA_HOME", None)

    def test_load_config_with_env_override_aurora_plans_dir(self):
        """AURORA_PLANS_DIR environment variable should override planning_base_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Set environment variable
            test_plans_dir = "/tmp/custom-plans"
            original_env = os.environ.get("AURORA_PLANS_DIR")
            os.environ["AURORA_PLANS_DIR"] = test_plans_dir

            try:
                config = load_config(path=None)
                assert config.planning_base_dir == test_plans_dir
            finally:
                # Restore original environment
                if original_env is not None:
                    os.environ["AURORA_PLANS_DIR"] = original_env
                else:
                    os.environ.pop("AURORA_PLANS_DIR", None)

    def test_load_config_from_file_respects_project_paths(self):
        """Config file with project-specific paths should be loaded correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create config file with project-specific paths
            config_path = Path(tmpdir) / "test_config.json"
            config_data = {
                "version": "1.1.0",
                "logging": {"file": "./.aurora/logs/custom.log"},
                "database": {"path": "./.aurora/custom_memory.db"},
                "planning": {"base_dir": "./.aurora/custom_plans"},
            }

            import json

            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(path=str(config_path))

            # Verify custom project-specific paths loaded
            assert config.logging_file == "./.aurora/logs/custom.log"
            assert config.db_path == "./.aurora/custom_memory.db"
            assert config.planning_base_dir == "./.aurora/custom_plans"


class TestConfigValidationWithProjectPaths:
    """Test that validation works with project-specific paths."""

    def test_validate_allows_project_specific_db_path(self):
        """Validation should accept project-specific database path."""
        config = Config(db_path="./.aurora/memory.db")
        # Should not raise
        config.validate()

    def test_validate_allows_project_specific_planning_base_dir(self):
        """Validation should accept project-specific planning directory."""
        config = Config(planning_base_dir="./.aurora/plans")
        # Should not raise
        config.validate()

    def test_validate_rejects_empty_db_path(self):
        """Validation should reject empty database path."""
        config = Config(db_path="")
        with pytest.raises(Exception) as exc_info:
            config.validate()
        assert "db_path cannot be empty" in str(exc_info.value)

    def test_validate_rejects_empty_planning_base_dir(self):
        """Validation should reject empty planning base directory."""
        config = Config(planning_base_dir="")
        with pytest.raises(Exception) as exc_info:
            config.validate()
        assert "planning_base_dir cannot be empty" in str(exc_info.value)


class TestBackwardsCompatibility:
    """Test backwards compatibility with old global paths."""

    def test_config_accepts_old_global_paths(self):
        """Config should still accept old global paths (for migration)."""
        config = Config(
            logging_file="~/.aurora/aurora.log",
            mcp_log_file="~/.aurora/mcp.log",
            db_path="~/.aurora/memory.db",
            agents_manifest_path="~/.aurora/cache/agent_manifest.json",
            planning_base_dir="~/.aurora/plans",
        )

        # Should not raise during validation
        config.validate()

        # Should expand paths correctly
        db_path = config.get_db_path()
        assert Path(db_path).is_absolute()
        assert "/.aurora/memory.db" in db_path

    def test_load_config_handles_global_paths_in_file(self):
        """load_config() should handle config files with old global paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create config file with old global paths
            config_path = Path(tmpdir) / "old_config.json"
            config_data = {
                "version": "1.1.0",
                "logging": {"file": "~/.aurora/aurora.log"},
                "database": {"path": "~/.aurora/memory.db"},
            }

            import json

            with open(config_path, "w") as f:
                json.dump(config_data, f)

            config = load_config(path=str(config_path))

            # Should load old paths correctly
            assert config.logging_file == "~/.aurora/aurora.log"
            assert config.db_path == "~/.aurora/memory.db"
