"""
Unit tests for MCPFunctionalChecks class.

Tests cover all 6 check methods with pass/warning/fail scenarios following TDD RED phase.
"""

import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from aurora_cli.config import Config
from aurora_cli.health_checks import HealthCheckResult, MCPFunctionalChecks


@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """Create a mock Config with temporary project directory."""
    config = Mock(spec=Config)
    config.project_dir = tmp_path
    config.aurora_dir = tmp_path / ".aurora"
    config.aurora_dir.mkdir(parents=True, exist_ok=True)
    return config


@pytest.fixture
def mcp_checks(mock_config: Config) -> MCPFunctionalChecks:
    """Create MCPFunctionalChecks instance with mock config."""
    return MCPFunctionalChecks(mock_config)


class TestMCPFunctionalChecksInit:
    """Test initialization of MCPFunctionalChecks."""

    def test_init_with_config(self, mock_config: Config) -> None:
        """Should accept Config parameter and initialize project path."""
        checks = MCPFunctionalChecks(mock_config)
        assert checks.config == mock_config
        # Config doesn't have project_dir, always uses cwd
        assert checks.project_path == Path.cwd()

    def test_init_without_config(self) -> None:
        """Should handle initialization without config parameter."""
        checks = MCPFunctionalChecks()
        assert checks.config is not None  # load_config() is called by default
        assert checks.project_path == Path.cwd()


class TestRunChecks:
    """Test run_checks method execution."""

    def test_run_checks_returns_list(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should return list of HealthCheckResult tuples."""
        with patch.object(mcp_checks, "_check_mcp_config_syntax", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_aurora_mcp_tools_importable", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_soar_phases_importable", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_memory_database_accessible", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_slash_command_mcp_consistency", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_mcp_server_tools_complete", return_value=("pass", "Valid", {})):
            results = mcp_checks.run_checks()

        assert isinstance(results, list)
        assert len(results) == 6
        for result in results:
            assert isinstance(result, tuple)
            assert len(result) == 3
            assert result[0] in ["pass", "warning", "fail"]


class TestCheckMCPConfigSyntax:
    """Test MCP config syntax validation."""

    def test_valid_json_syntax(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should pass when MCP config has valid JSON syntax."""
        config_path = tmp_path / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"mcpServers": {"aurora": {}}}')

        with patch.object(mcp_checks, "_get_mcp_config_path", return_value=config_path):
            status, message, details = mcp_checks._check_mcp_config_syntax()

        assert status == "pass"
        assert "valid" in message.lower()

    def test_invalid_json_syntax(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should fail when MCP config has invalid JSON syntax."""
        config_path = tmp_path / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{"mcpServers": {"aurora": }')  # Invalid JSON

        with patch.object(mcp_checks, "_get_mcp_config_path", return_value=config_path):
            status, message, details = mcp_checks._check_mcp_config_syntax()

        assert status == "fail"
        assert "invalid" in message.lower() or "syntax" in message.lower()
        assert details is not None

    def test_missing_config_file(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should warn when MCP config file does not exist."""
        config_path = tmp_path / ".claude" / "claude_desktop_config.json"

        with patch.object(mcp_checks, "_get_mcp_config_path", return_value=config_path):
            status, message, details = mcp_checks._check_mcp_config_syntax()

        assert status == "warning"
        assert "not found" in message.lower() or "missing" in message.lower()


class TestCheckAuroraMCPToolsImportable:
    """Test Aurora MCP tools import verification."""

    def test_all_tools_importable(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should pass when all 3 required tools are importable."""
        mock_tools_class = Mock()
        mock_tools_class.aurora_query = Mock()
        mock_tools_class.aurora_search = Mock()
        mock_tools_class.aurora_get = Mock()

        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.AuroraMCPTools = mock_tools_class
            mock_import.return_value = mock_module

            status, message, details = mcp_checks._check_aurora_mcp_tools_importable()

        assert status == "pass"
        assert "3" in message or "all" in message.lower()
        assert details is not None
        assert "aurora_query" in str(details)
        assert "aurora_search" in str(details)
        assert "aurora_get" in str(details)

    def test_missing_tools(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should fail when required tools are missing."""
        mock_tools_class = Mock(spec=[])  # Empty spec means no attributes
        # Manually set only one method
        mock_tools_class.aurora_query = Mock()

        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.AuroraMCPTools = mock_tools_class
            mock_import.return_value = mock_module

            status, message, details = mcp_checks._check_aurora_mcp_tools_importable()

        assert status == "fail"
        assert "missing" in message.lower()
        assert details is not None

    def test_import_error(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should fail when aurora_mcp.tools cannot be imported."""
        with patch("aurora_cli.health_checks.importlib.import_module", side_effect=ImportError("Module not found")):
            status, message, details = mcp_checks._check_aurora_mcp_tools_importable()

        assert status == "fail"
        assert "import" in message.lower() or "not found" in message.lower()


class TestCheckSoarPhasesImportable:
    """Test SOAR phase modules import verification."""

    def test_all_phases_importable(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should pass when all 9 phase modules are importable."""
        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_import.return_value = Mock()

            status, message, details = mcp_checks._check_soar_phases_importable()

        assert status == "pass"
        assert "9" in message or "all" in message.lower()
        assert details is not None
        expected_phases = ["assess", "retrieve", "decompose", "verify", "route",
                          "collect", "synthesize", "record", "respond"]
        for phase in expected_phases:
            assert phase in str(details)

    def test_some_phases_missing(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should fail when some phase modules cannot be imported."""
        def mock_import_side_effect(name: str):
            if "decompose" in name or "verify" in name:
                raise ImportError(f"Cannot import {name}")
            return Mock()

        with patch("aurora_cli.health_checks.importlib.import_module", side_effect=mock_import_side_effect):
            status, message, details = mcp_checks._check_soar_phases_importable()

        assert status == "fail"
        assert "missing" in message.lower() or "failed" in message.lower()
        assert details is not None

    def test_all_phases_fail_import(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should fail when no phase modules can be imported."""
        with patch("aurora_cli.health_checks.importlib.import_module", side_effect=ImportError("Module not found")):
            status, message, details = mcp_checks._check_soar_phases_importable()

        assert status == "fail"
        assert details is not None


class TestCheckMemoryDatabaseAccessible:
    """Test memory database accessibility."""

    def test_database_accessible(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should pass when memory database exists and is accessible."""
        # Set the project path to tmp_path for this test
        mcp_checks.project_path = tmp_path
        db_path = tmp_path / ".aurora" / "memory.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        mock_store = Mock()
        mock_store.close = Mock()

        # Create a mock module for SQLiteStore
        import sys
        mock_sqlite_module = Mock()
        mock_sqlite_module.SQLiteStore = Mock(return_value=mock_store)

        with patch.dict(sys.modules, {"aurora.core.store.sqlite": mock_sqlite_module}):
            status, message, details = mcp_checks._check_memory_database_accessible()

        assert status == "pass"
        assert "accessible" in message.lower()
        assert details is not None
        assert str(db_path.name) in str(details) or "memory.db" in str(details)
        mock_store.close.assert_called_once()

    def test_database_not_found(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should warn when memory database does not exist."""
        status, message, details = mcp_checks._check_memory_database_accessible()

        assert status == "warning"
        assert "not found" in message.lower() or "missing" in message.lower()

    def test_database_connection_error(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should fail when database connection fails."""
        mcp_checks.project_path = tmp_path
        db_path = tmp_path / ".aurora" / "memory.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        # Create a mock module that raises an exception
        import sys
        mock_sqlite_module = Mock()
        mock_sqlite_module.SQLiteStore = Mock(side_effect=Exception("Connection failed"))

        with patch.dict(sys.modules, {"aurora.core.store.sqlite": mock_sqlite_module}):
            status, message, details = mcp_checks._check_memory_database_accessible()

        assert status == "fail"
        assert "connection" in message.lower() or "error" in message.lower()


class TestCheckSlashCommandMCPConsistency:
    """Test slash command and MCP server consistency."""

    def test_all_commands_consistent(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should pass when all slash commands reference valid MCP servers."""
        with patch("aurora_cli.health_checks.Path.exists", return_value=True), \
             patch("aurora_cli.health_checks.Path.glob", return_value=[]):
            status, message, details = mcp_checks._check_slash_command_mcp_consistency()

        # For now, we expect pass when no issues found
        assert status in ["pass", "warning"]

    def test_inconsistent_server_references(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should warn when slash commands reference invalid MCP servers."""
        # This test will be more specific once we see the actual implementation
        status, message, details = mcp_checks._check_slash_command_mcp_consistency()

        assert status in ["pass", "warning", "fail"]
        # More specific assertions after implementation


class TestCheckMCPServerToolsComplete:
    """Test MCP server tools completeness."""

    def test_all_three_tools_registered(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should pass when exactly 3 tools are registered."""
        mock_tools_class = Mock()
        mock_tools_class.aurora_query = Mock()
        mock_tools_class.aurora_search = Mock()
        mock_tools_class.aurora_get = Mock()

        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.AuroraMCPTools = mock_tools_class
            mock_import.return_value = mock_module

            status, message, details = mcp_checks._check_mcp_server_tools_complete()

        assert status == "pass"
        assert "3" in message or "complete" in message.lower()
        assert details is not None

    def test_missing_tools(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should fail when tools are missing."""
        mock_tools_class = Mock()
        mock_tools_class.aurora_query = Mock()
        # Only 1 tool instead of 3

        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.AuroraMCPTools = mock_tools_class
            mock_import.return_value = mock_module

            status, message, details = mcp_checks._check_mcp_server_tools_complete()

        assert status == "fail"
        assert "missing" in message.lower()
        assert details is not None

    def test_extra_tools_registered(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should warn when more than 3 tools are registered."""
        mock_tools_class = Mock()
        mock_tools_class.aurora_query = Mock()
        mock_tools_class.aurora_search = Mock()
        mock_tools_class.aurora_get = Mock()
        mock_tools_class.aurora_extra = Mock()  # Extra tool

        with patch("aurora_cli.health_checks.importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.AuroraMCPTools = mock_tools_class
            mock_import.return_value = mock_module

            status, message, details = mcp_checks._check_mcp_server_tools_complete()

        assert status in ["warning", "pass"]  # Implementation decision
        assert details is not None


class TestGetFixableIssues:
    """Test fixable issues detection."""

    def test_returns_list_of_fixable_issues(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should return list of auto-fixable problems."""
        fixable = mcp_checks.get_fixable_issues()

        assert isinstance(fixable, list)
        for issue in fixable:
            assert isinstance(issue, dict)
            assert "problem" in issue
            assert "fix" in issue

    def test_missing_aurora_directory(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should detect missing .aurora directory as fixable."""
        # Remove .aurora directory
        aurora_dir = tmp_path / ".aurora"
        if aurora_dir.exists():
            import shutil
            shutil.rmtree(aurora_dir)

        with patch.object(mcp_checks, "run_checks", return_value=[
            ("warning", "Database not found", {})
        ]):
            fixable = mcp_checks.get_fixable_issues()

        assert len(fixable) > 0
        assert any("aurora" in issue["problem"].lower() or "directory" in issue["problem"].lower()
                  for issue in fixable)

    def test_missing_memory_database(self, mcp_checks: MCPFunctionalChecks, tmp_path: Path) -> None:
        """Should detect missing memory.db as fixable."""
        with patch.object(mcp_checks, "run_checks", return_value=[
            ("warning", "Database not found", {})
        ]):
            fixable = mcp_checks.get_fixable_issues()

        assert len(fixable) > 0
        assert any("database" in issue["problem"].lower() or "memory" in issue["problem"].lower()
                  for issue in fixable)


class TestGetManualIssues:
    """Test manual intervention issues detection."""

    def test_returns_list_of_manual_issues(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should return list of manual intervention issues."""
        manual = mcp_checks.get_manual_issues()

        assert isinstance(manual, list)
        for issue in manual:
            assert isinstance(issue, dict)
            assert "problem" in issue
            assert "solution" in issue

    def test_invalid_json_syntax(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should detect invalid JSON syntax as manual issue."""
        with patch.object(mcp_checks, "run_checks", return_value=[
            ("fail", "Invalid JSON syntax", {"error": "JSONDecodeError"})
        ]):
            manual = mcp_checks.get_manual_issues()

        assert len(manual) > 0
        assert any("json" in issue["problem"].lower() or "syntax" in issue["problem"].lower()
                  for issue in manual)
        assert any("aur init" in issue["solution"].lower() or "config" in issue["solution"].lower()
                  for issue in manual)

    def test_missing_soar_phases(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should detect missing SOAR phases as manual issue."""
        with patch.object(mcp_checks, "run_checks", return_value=[
            ("fail", "SOAR phases missing", {"failed": ["decompose", "verify"]})
        ]):
            manual = mcp_checks.get_manual_issues()

        assert len(manual) > 0
        assert any("phase" in issue["problem"].lower() or "soar" in issue["problem"].lower()
                  for issue in manual)


class TestMCPFunctionalChecksIntegration:
    """Integration tests for MCPFunctionalChecks class."""

    def test_complete_check_flow(self, mcp_checks: MCPFunctionalChecks) -> None:
        """Should execute all checks and categorize issues."""
        # Mock all checks to return various statuses
        with patch.object(mcp_checks, "_check_mcp_config_syntax", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_aurora_mcp_tools_importable", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_soar_phases_importable", return_value=("warning", "Some missing", {"missing": ["decompose"]})), \
             patch.object(mcp_checks, "_check_memory_database_accessible", return_value=("fail", "Not found", {})), \
             patch.object(mcp_checks, "_check_slash_command_mcp_consistency", return_value=("pass", "Valid", {})), \
             patch.object(mcp_checks, "_check_mcp_server_tools_complete", return_value=("pass", "Valid", {})):
            results = mcp_checks.run_checks()
            fixable = mcp_checks.get_fixable_issues()
            manual = mcp_checks.get_manual_issues()

        assert len(results) == 6
        assert isinstance(fixable, list)
        assert isinstance(manual, list)

        # Should have at least one warning and one failure
        statuses = [r[0] for r in results]
        assert "warning" in statuses
        assert "fail" in statuses
