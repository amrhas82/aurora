"""Unit tests for doctor CLI command.

Tests the `aur doctor` command that performs health checks and auto-repair.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.main import cli


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


class TestDoctorCommandBasics:
    """Test basic doctor command functionality."""

    def test_help_text(self, runner: CliRunner):
        """Test help text displays correctly."""
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "doctor" in result.output.lower()
        assert "health" in result.output.lower() or "check" in result.output.lower()

    def test_doctor_command_exists(self, runner: CliRunner):
        """Test doctor command is registered."""
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0


class TestHealthCheckCategories:
    """Test health check category execution."""

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_all_categories_run(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test all four health check categories are executed."""
        # Mock health check results - all pass
        mock_core_checks.return_value.run_checks.return_value = [
            ("pass", "CLI version check", {"version": "0.2.0"}),
            ("pass", "Database exists", {"path": "~/.aurora/memory.db"}),
        ]
        mock_code_checks.return_value.run_checks.return_value = [
            ("pass", "Tree-sitter available", {}),
        ]
        mock_search_checks.return_value.run_checks.return_value = [
            ("pass", "Vector store functional", {}),
        ]
        mock_config_checks.return_value.run_checks.return_value = [
            ("pass", "Config file valid", {}),
        ]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        # Should succeed with exit code 0
        assert result.exit_code == 0
        # Output should mention all categories
        assert "CORE SYSTEM" in result.output or "Core System" in result.output
        assert "CODE ANALYSIS" in result.output or "Code Analysis" in result.output
        assert (
            "SEARCH" in result.output
            and "RETRIEVAL" in result.output
            or "Search & Retrieval" in result.output
        )
        assert "CONFIGURATION" in result.output or "Configuration" in result.output


class TestHealthCheckOutput:
    """Test health check output formatting."""

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_output_shows_status_indicators(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test output displays status indicators (checkmark, warning, X)."""
        # Mix of pass/warning/fail
        mock_core_checks.return_value.run_checks.return_value = [
            ("pass", "CLI version check", {"version": "0.2.0"}),
            ("warning", "Database size large", {"size_mb": 150}),
        ]
        mock_code_checks.return_value.run_checks.return_value = [
            ("fail", "Tree-sitter not available", {}),
        ]
        mock_search_checks.return_value.run_checks.return_value = [
            ("pass", "Vector store functional", {}),
        ]
        mock_config_checks.return_value.run_checks.return_value = [
            ("pass", "Config file valid", {}),
        ]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        # Should have status indicators (checkmark, warning, X)
        # Rich will use unicode symbols or text indicators
        output = result.output
        # Check for status indicators (flexible for different formatting)
        assert "✓" in output or "pass" in output.lower() or "ok" in output.lower()
        assert "⚠" in output or "warning" in output.lower() or "warn" in output.lower()
        assert "✗" in output or "fail" in output.lower() or "error" in output.lower()

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_output_shows_summary_line(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test output displays summary line with counts."""
        # Mix of results
        mock_core_checks.return_value.run_checks.return_value = [
            ("pass", "Check 1", {}),
            ("pass", "Check 2", {}),
        ]
        mock_code_checks.return_value.run_checks.return_value = [
            ("warning", "Check 3", {}),
        ]
        mock_search_checks.return_value.run_checks.return_value = [
            ("fail", "Check 4", {}),
        ]
        mock_config_checks.return_value.run_checks.return_value = [
            ("pass", "Check 5", {}),
        ]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        # Should show summary: "3 passed, 1 warning, 1 failed" or similar
        output = result.output.lower()
        # Check for count indicators
        assert ("passed" in output or "pass" in output) and "3" in output
        assert "warning" in output and "1" in output
        assert ("failed" in output or "fail" in output) and "1" in output


class TestHealthCheckExitCodes:
    """Test health check exit codes."""

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_exit_code_0_all_pass(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test exit code 0 when all checks pass."""
        # All pass
        mock_core_checks.return_value.run_checks.return_value = [("pass", "Check 1", {})]
        mock_code_checks.return_value.run_checks.return_value = [("pass", "Check 2", {})]
        mock_search_checks.return_value.run_checks.return_value = [("pass", "Check 3", {})]
        mock_config_checks.return_value.run_checks.return_value = [("pass", "Check 4", {})]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        assert result.exit_code == 0

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_exit_code_1_with_warnings(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test exit code 1 when there are warnings but no failures."""
        # Some warnings, no failures
        mock_core_checks.return_value.run_checks.return_value = [("pass", "Check 1", {})]
        mock_code_checks.return_value.run_checks.return_value = [("warning", "Check 2", {})]
        mock_search_checks.return_value.run_checks.return_value = [("pass", "Check 3", {})]
        mock_config_checks.return_value.run_checks.return_value = [("warning", "Check 4", {})]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        assert result.exit_code == 1

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_exit_code_2_with_failures(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test exit code 2 when there are failures."""
        # Some failures
        mock_core_checks.return_value.run_checks.return_value = [("pass", "Check 1", {})]
        mock_code_checks.return_value.run_checks.return_value = [("fail", "Check 2", {})]
        mock_search_checks.return_value.run_checks.return_value = [("pass", "Check 3", {})]
        mock_config_checks.return_value.run_checks.return_value = [("pass", "Check 4", {})]
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor"])

        assert result.exit_code == 2


class TestCoreSystemChecks:
    """Test CoreSystemChecks class."""

    def test_core_system_checks_class_exists(self):
        """Test CoreSystemChecks class can be imported."""
        from aurora_cli.health_checks import CoreSystemChecks

        checks = CoreSystemChecks()
        assert hasattr(checks, "run_checks")

    def test_cli_version_check(self):
        """Test CLI version check."""
        from aurora_cli.health_checks import CoreSystemChecks

        checks = CoreSystemChecks()
        results = checks.run_checks()

        # Should have at least one result
        assert len(results) > 0
        # Should check CLI version
        version_checks = [r for r in results if "version" in r[1].lower()]
        assert len(version_checks) > 0

    def test_database_existence_check(self):
        """Test database existence check."""
        from aurora_cli.health_checks import CoreSystemChecks

        checks = CoreSystemChecks()
        results = checks.run_checks()

        # Should check database
        db_checks = [r for r in results if "database" in r[1].lower()]
        assert len(db_checks) > 0


class TestCodeAnalysisChecks:
    """Test CodeAnalysisChecks class."""

    def test_code_analysis_checks_class_exists(self):
        """Test CodeAnalysisChecks class can be imported."""
        from aurora_cli.health_checks import CodeAnalysisChecks

        checks = CodeAnalysisChecks()
        assert hasattr(checks, "run_checks")

    def test_tree_sitter_check(self):
        """Test tree-sitter availability check."""
        from aurora_cli.health_checks import CodeAnalysisChecks

        checks = CodeAnalysisChecks()
        results = checks.run_checks()

        # Should check tree-sitter
        ts_checks = [r for r in results if "tree" in r[1].lower() or "parser" in r[1].lower()]
        assert len(ts_checks) > 0


class TestSearchRetrievalChecks:
    """Test SearchRetrievalChecks class."""

    def test_search_retrieval_checks_class_exists(self):
        """Test SearchRetrievalChecks class can be imported."""
        from aurora_cli.health_checks import SearchRetrievalChecks

        checks = SearchRetrievalChecks()
        assert hasattr(checks, "run_checks")

    def test_vector_store_check(self):
        """Test vector store check."""
        from aurora_cli.health_checks import SearchRetrievalChecks

        checks = SearchRetrievalChecks()
        results = checks.run_checks()

        # Should check vector store or embeddings
        vector_checks = [
            r
            for r in results
            if "vector" in r[1].lower() or "embedding" in r[1].lower() or "search" in r[1].lower()
        ]
        assert len(vector_checks) > 0


class TestConfigurationChecks:
    """Test ConfigurationChecks class."""

    def test_configuration_checks_class_exists(self):
        """Test ConfigurationChecks class can be imported."""
        from aurora_cli.health_checks import ConfigurationChecks

        checks = ConfigurationChecks()
        assert hasattr(checks, "run_checks")

    def test_config_file_check(self):
        """Test config file check."""
        from aurora_cli.health_checks import ConfigurationChecks

        checks = ConfigurationChecks()
        results = checks.run_checks()

        # Should check config file
        config_checks = [r for r in results if "config" in r[1].lower()]
        assert len(config_checks) > 0


class TestDoctorFixFlag:
    """Test doctor --fix auto-repair functionality."""

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_fix_flag_exists(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test --fix flag is recognized."""
        # Mock with some fixable issues
        mock_core_checks.return_value.run_checks.return_value = [
            ("fail", "Database missing", {"fixable": True}),
        ]
        mock_code_checks.return_value.run_checks.return_value = []
        mock_search_checks.return_value.run_checks.return_value = []
        mock_config_checks.return_value.run_checks.return_value = []
        mock_tool_checks.return_value.run_checks.return_value = []
        mock_mcp_checks.return_value.run_checks.return_value = []

        result = runner.invoke(cli, ["doctor", "--fix"], input="n\n")

        # Should recognize the flag (not show "no such option" error)
        assert "no such option" not in result.output.lower()

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_fix_prompts_before_changes(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test --fix prompts user before making changes."""
        # Mock with fixable issues
        mock_core_checks.return_value.run_checks.return_value = [
            ("fail", "Config missing", {"fixable": True}),
        ]
        mock_core_checks.return_value.get_fixable_issues.return_value = [
            {"name": "Config missing", "fix_func": lambda: None},
        ]
        mock_code_checks.return_value.run_checks.return_value = []
        mock_code_checks.return_value.get_fixable_issues.return_value = []
        mock_search_checks.return_value.run_checks.return_value = []
        mock_search_checks.return_value.get_fixable_issues.return_value = []
        mock_config_checks.return_value.run_checks.return_value = []
        mock_config_checks.return_value.get_fixable_issues.return_value = []

        result = runner.invoke(cli, ["doctor", "--fix"], input="n\n")

        # Should show prompt
        assert "fix" in result.output.lower()

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_fix_accepts_user_input(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test --fix accepts user confirmation."""
        # Mock fixable issue
        mock_fix_func = MagicMock()
        mock_core_checks.return_value.run_checks.return_value = [
            ("fail", "Config missing", {"fixable": True}),
        ]
        mock_core_checks.return_value.get_fixable_issues.return_value = [
            {"name": "Config missing", "fix_func": mock_fix_func},
        ]
        mock_code_checks.return_value.run_checks.return_value = []
        mock_code_checks.return_value.get_fixable_issues.return_value = []
        mock_search_checks.return_value.run_checks.return_value = []
        mock_search_checks.return_value.get_fixable_issues.return_value = []
        mock_config_checks.return_value.run_checks.return_value = []
        mock_config_checks.return_value.get_fixable_issues.return_value = []

        result = runner.invoke(cli, ["doctor", "--fix"], input="y\n")

        # Should call fix function when user accepts
        mock_fix_func.assert_called_once()

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_fix_skips_when_declined(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test --fix skips fixes when user declines."""
        # Mock fixable issue
        mock_fix_func = MagicMock()
        mock_core_checks.return_value.run_checks.return_value = [
            ("fail", "Config missing", {"fixable": True}),
        ]
        mock_core_checks.return_value.get_fixable_issues.return_value = [
            {"name": "Config missing", "fix_func": mock_fix_func},
        ]
        mock_code_checks.return_value.run_checks.return_value = []
        mock_code_checks.return_value.get_fixable_issues.return_value = []
        mock_search_checks.return_value.run_checks.return_value = []
        mock_search_checks.return_value.get_fixable_issues.return_value = []
        mock_config_checks.return_value.run_checks.return_value = []
        mock_config_checks.return_value.get_fixable_issues.return_value = []

        result = runner.invoke(cli, ["doctor", "--fix"], input="n\n")

        # Should NOT call fix function when user declines
        mock_fix_func.assert_not_called()

    @patch("aurora_cli.commands.doctor.MCPFunctionalChecks")
    @patch("aurora_cli.commands.doctor.ToolIntegrationChecks")
    @patch("aurora_cli.commands.doctor.CoreSystemChecks")
    @patch("aurora_cli.commands.doctor.CodeAnalysisChecks")
    @patch("aurora_cli.commands.doctor.SearchRetrievalChecks")
    @patch("aurora_cli.commands.doctor.ConfigurationChecks")
    def test_fix_shows_manual_instructions(
        self,
        mock_config_checks,
        mock_search_checks,
        mock_code_checks,
        mock_core_checks,
        mock_tool_checks,
        mock_mcp_checks,
        runner: CliRunner,
    ):
        """Test --fix shows manual instructions for non-fixable issues."""
        # Mock manual issue
        mock_core_checks.return_value.run_checks.return_value = [
            ("fail", "API key missing", {"fixable": False, "solution": "Set ANTHROPIC_API_KEY"}),
        ]
        mock_core_checks.return_value.get_fixable_issues.return_value = []
        mock_core_checks.return_value.get_manual_issues.return_value = [
            {"name": "API key missing", "solution": "Set ANTHROPIC_API_KEY"},
        ]
        mock_code_checks.return_value.run_checks.return_value = []
        mock_code_checks.return_value.get_fixable_issues.return_value = []
        mock_code_checks.return_value.get_manual_issues.return_value = []
        mock_search_checks.return_value.run_checks.return_value = []
        mock_search_checks.return_value.get_fixable_issues.return_value = []
        mock_search_checks.return_value.get_manual_issues.return_value = []
        mock_config_checks.return_value.run_checks.return_value = []
        mock_config_checks.return_value.get_fixable_issues.return_value = []
        mock_config_checks.return_value.get_manual_issues.return_value = []

        result = runner.invoke(cli, ["doctor", "--fix"], input="n\n")

        # Should show manual fix instructions
        assert "manual" in result.output.lower() or "Set ANTHROPIC_API_KEY" in result.output
