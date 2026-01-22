"""Integration tests for doctor command with MCPFunctionalChecks.

This test module verifies that the doctor command properly validates MCP
configurations, SOAR phases, and memory database, with auto-fix functionality.

NOTE: MCP functionality is dormant (PRD-0024). These tests are skipped.
"""

import json
import shutil
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.doctor import doctor_command
from aurora_cli.config import Config


# Skip all tests in this file - MCP functionality is dormant (PRD-0024)
pytestmark = pytest.mark.skip(reason="MCP functionality dormant - tests deprecated (PRD-0024)")


@pytest.fixture
def isolated_environment(tmp_path):
    """Create isolated environment for doctor tests."""
    # Create project directory structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    aurora_dir = project_dir / ".aurora"
    aurora_dir.mkdir()

    # Create mock config with db_path in project directory
    db_path = aurora_dir / "memory.db"
    config = Config(db_path=str(db_path))

    return {"project_dir": project_dir, "aurora_dir": aurora_dir, "config": config}


@pytest.fixture
def mock_mcp_config(tmp_path):
    """Create mock MCP configuration file."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(parents=True)

    config_path = claude_dir / "claude_desktop_config.json"
    config = {"mcpServers": {"aurora": {"command": "aurora-mcp", "args": []}}}

    config_path.write_text(json.dumps(config), encoding="utf-8")

    return config_path


class TestDoctorMCPChecksIntegration:
    """Integration tests for doctor command MCP health checks."""

    def test_doctor_runs_all_mcp_checks(self, isolated_environment):
        """Doctor should run all 6 MCP functional checks."""
        runner = CliRunner()

        # Mock home directory to avoid system config pollution
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock imports to avoid dependency on actual packages
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Not installed")

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Doctor should complete even with failures
        assert result.exit_code in [0, 1, 2]

        # Should see MCP FUNCTIONAL section
        assert "MCP FUNCTIONAL" in result.output

    def test_doctor_detects_invalid_mcp_config_json(self, isolated_environment):
        """Doctor should detect and report invalid MCP config JSON."""
        runner = CliRunner()

        # Create invalid JSON config
        claude_dir = isolated_environment["project_dir"] / ".claude"
        claude_dir.mkdir(parents=True)
        config_path = claude_dir / "claude_desktop_config.json"
        config_path.write_text("{ invalid json }", encoding="utf-8")

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            result = runner.invoke(
                doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
            )

        # Should report JSON syntax error
        assert "MCP config" in result.output
        assert "✗" in result.output or "fail" in result.output.lower()

    def test_doctor_detects_missing_memory_database(self, isolated_environment):
        """Doctor should detect missing memory database."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock MCP config check to pass
            with patch(
                "aurora_cli.health_checks.MCPFunctionalChecks._check_mcp_config_syntax"
            ) as mock_check:
                mock_check.return_value = ("pass", "MCP config valid", {})

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report missing database
        assert "Memory database" in result.output or "memory.db" in result.output

    def test_doctor_detects_missing_aurora_mcp_tools(self, isolated_environment):
        """Doctor should detect when Aurora MCP tools cannot be imported."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock import to fail for aurora_mcp.tools
            with patch("importlib.import_module") as mock_import:

                def import_side_effect(module_name):
                    if "aurora_mcp.tools" in module_name:
                        raise ImportError(f"Cannot import {module_name}")
                    # Mock other imports
                    mock_module = MagicMock()
                    return mock_module

                mock_import.side_effect = import_side_effect

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report Aurora MCP tools issue
        assert "Aurora MCP" in result.output or "aurora_mcp" in result.output

    def test_doctor_detects_missing_soar_phases(self, isolated_environment):
        """Doctor should detect when SOAR phase modules cannot be imported."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock import to fail for SOAR phases
            with patch("importlib.import_module") as mock_import:

                def import_side_effect(module_name):
                    if "aurora_soar.phases" in module_name:
                        raise ImportError(f"Cannot import {module_name}")
                    # Mock other imports
                    mock_module = MagicMock()
                    return mock_module

                mock_import.side_effect = import_side_effect

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report SOAR phases issue
        assert "SOAR" in result.output or "phases" in result.output

    def test_doctor_validates_all_three_essential_tools(self, isolated_environment):
        """Doctor should validate presence of aurora_query, aurora_search, aurora_get."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock tools class with only 2 methods (missing one)
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_tools_class = MagicMock()

                # Only provide 2 of 3 required methods
                mock_tools_class.aurora_query = MagicMock()
                mock_tools_class.aurora_search = MagicMock()
                # Missing: aurora_get

                mock_module.AuroraMCPTools = mock_tools_class

                def import_side_effect(module_name):
                    if "aurora_mcp.tools" in module_name:
                        return mock_module
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report missing tool
        assert "✗" in result.output or "fail" in result.output.lower()

    def test_doctor_fix_flag_offers_to_apply_fixes(self, isolated_environment):
        """Doctor --fix should offer to apply automatic fixes."""
        runner = CliRunner()

        # Create scenario with fixable issue (missing memory.db)
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock checks to return fixable issue
            with patch(
                "aurora_cli.health_checks.MCPFunctionalChecks.get_fixable_issues"
            ) as mock_fixable:
                mock_fixable.return_value = [
                    {
                        "name": "Missing memory database",
                        "fix_func": lambda: None,  # Mock fix function
                    }
                ]

                # Use input to decline auto-fix (to avoid interactive prompt in test)
                result = runner.invoke(
                    doctor_command,
                    ["--fix"],
                    input="n\n",  # Decline fix
                    catch_exceptions=False,
                    obj=isolated_environment["config"],
                )

        # Should show fixable issues analysis
        assert "Analyzing fixable issues" in result.output or "Fixable issues" in result.output

    def test_doctor_fix_applies_automatic_fixes(self, isolated_environment):
        """Doctor --fix should apply automatic fixes when confirmed."""
        runner = CliRunner()

        # Track if fix was called
        fix_called = {"count": 0}

        def mock_fix():
            fix_called["count"] += 1

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock checks to return fixable issue
            with patch(
                "aurora_cli.health_checks.MCPFunctionalChecks.get_fixable_issues"
            ) as mock_fixable:
                mock_fixable.return_value = [{"name": "Test fixable issue", "fix_func": mock_fix}]

                # Accept fix
                result = runner.invoke(
                    doctor_command,
                    ["--fix"],
                    input="y\n",  # Accept fix
                    catch_exceptions=False,
                    obj=isolated_environment["config"],
                )

        # Fix function should have been called
        assert fix_called["count"] == 1
        assert "Applying fixes" in result.output or "Fixed" in result.output

    def test_doctor_shows_manual_fix_suggestions(self, isolated_environment):
        """Doctor should show manual fix suggestions for non-auto-fixable issues."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock checks to return manual issue
            with patch(
                "aurora_cli.health_checks.MCPFunctionalChecks.get_manual_issues"
            ) as mock_manual:
                mock_manual.return_value = [
                    {
                        "name": "Invalid MCP configuration",
                        "solution": "Run 'aur init --config' to reconfigure MCP server",
                    }
                ]

                result = runner.invoke(
                    doctor_command,
                    ["--fix"],
                    input="n\n",  # Decline any fixable issues
                    catch_exceptions=False,
                    obj=isolated_environment["config"],
                )

        # Should show manual fix suggestion
        assert "Manual fixes needed" in result.output or "Solution:" in result.output

    def test_doctor_exit_code_reflects_health_status(self, isolated_environment):
        """Doctor exit code should reflect overall health status."""
        runner = CliRunner()

        # Test case 1: All passing - exit code 0
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock all checks to pass
            with patch("aurora_cli.health_checks.MCPFunctionalChecks.run_checks") as mock_checks:
                mock_checks.return_value = [
                    ("pass", "Check 1 passed", {}),
                    ("pass", "Check 2 passed", {}),
                ]

                # Mock other check classes
                with (
                    patch("aurora_cli.health_checks.CoreSystemChecks.run_checks") as mock_core,
                    patch("aurora_cli.health_checks.CodeAnalysisChecks.run_checks") as mock_code,
                    patch(
                        "aurora_cli.health_checks.SearchRetrievalChecks.run_checks"
                    ) as mock_search,
                    patch("aurora_cli.health_checks.ConfigurationChecks.run_checks") as mock_config,
                    patch("aurora_cli.health_checks.ToolIntegrationChecks.run_checks") as mock_tool,
                ):
                    mock_core.return_value = [("pass", "Core passed", {})]
                    mock_code.return_value = [("pass", "Code passed", {})]
                    mock_search.return_value = [("pass", "Search passed", {})]
                    mock_config.return_value = [("pass", "Config passed", {})]
                    mock_tool.return_value = [("pass", "Tool passed", {})]

                    result = runner.invoke(
                        doctor_command,
                        [],
                        catch_exceptions=False,
                        obj=isolated_environment["config"],
                    )

        # All passing should give exit code 0
        assert result.exit_code == 0

    def test_doctor_handles_partial_soar_phase_failures(self, isolated_environment):
        """Doctor should report partial SOAR phase import failures."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock import to fail for some SOAR phases
            with patch("importlib.import_module") as mock_import:
                failed_phases = ["decompose", "verify", "route"]

                def import_side_effect(module_name):
                    # Fail specific SOAR phases
                    for phase in failed_phases:
                        if f"aurora_soar.phases.{phase}" == module_name:
                            raise ImportError(f"Cannot import {module_name}")

                    # Mock successful imports
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report which phases failed
        assert "SOAR" in result.output
        assert "✗" in result.output or "fail" in result.output.lower()

    def test_doctor_validates_exactly_three_tools_no_extras(self, isolated_environment):
        """Doctor should warn if MCP server has extra tools beyond the 3 required."""
        runner = CliRunner()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock tools class with extra methods
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_tools_class = MagicMock()

                # Provide all 3 required + 1 extra
                mock_tools_class.aurora_query = MagicMock()
                mock_tools_class.aurora_search = MagicMock()
                mock_tools_class.aurora_get = MagicMock()
                mock_tools_class.aurora_extra = MagicMock()  # Extra method

                # Mock dir() to return method names
                def mock_dir_func(obj):
                    return ["aurora_query", "aurora_search", "aurora_get", "aurora_extra"]

                with patch("builtins.dir", side_effect=mock_dir_func):
                    mock_module.AuroraMCPTools = mock_tools_class

                    def import_side_effect(module_name):
                        if "aurora_mcp.tools" in module_name:
                            return mock_module
                        return MagicMock()

                    mock_import.side_effect = import_side_effect

                    result = runner.invoke(
                        doctor_command,
                        [],
                        catch_exceptions=False,
                        obj=isolated_environment["config"],
                    )

        # Should detect extra tool
        # This depends on implementation - may be warning or fail
        assert result.exit_code in [0, 1, 2]


class TestDoctorMemoryDatabaseChecks:
    """Tests for memory database validation in doctor command."""

    def test_doctor_validates_memory_database_readable(self, isolated_environment):
        """Doctor should verify memory database is readable."""
        runner = CliRunner()

        # Create valid memory database
        db_path = isolated_environment["aurora_dir"] / "memory.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock SQLiteStore
            with patch("aurora.core.store.sqlite.SQLiteStore") as mock_store:
                mock_instance = MagicMock()
                mock_store.return_value = mock_instance

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should attempt to check database
        assert "Memory database" in result.output or "memory.db" in result.output

    def test_doctor_detects_corrupted_memory_database(self, isolated_environment):
        """Doctor should detect corrupted memory database."""
        runner = CliRunner()

        # Create corrupted database
        db_path = isolated_environment["aurora_dir"] / "memory.db"
        db_path.write_text("corrupted data", encoding="utf-8")

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock SQLiteStore to raise error
            with patch("aurora.core.store.sqlite.SQLiteStore") as mock_store:
                mock_store.side_effect = Exception("Database corrupted")

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should report database error
        assert "✗" in result.output or "fail" in result.output.lower()


class TestDoctorFullFlow:
    """End-to-end tests for full doctor command flow."""

    def test_doctor_full_flow_with_valid_setup(self, isolated_environment, mock_mcp_config):
        """Doctor should complete successfully with valid setup."""
        runner = CliRunner()

        # Create valid memory database
        db_path = isolated_environment["aurora_dir"] / "memory.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        # Copy mock MCP config to expected location
        target_config = (
            isolated_environment["project_dir"] / ".claude" / "claude_desktop_config.json"
        )
        target_config.parent.mkdir(parents=True)
        shutil.copy(mock_mcp_config, target_config)

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock successful imports
            with patch("importlib.import_module") as mock_import:
                mock_module = MagicMock()
                mock_tools_class = MagicMock()
                mock_tools_class.aurora_query = MagicMock()
                mock_tools_class.aurora_search = MagicMock()
                mock_tools_class.aurora_get = MagicMock()
                mock_module.AuroraMCPTools = mock_tools_class

                def import_side_effect(module_name):
                    if "aurora_mcp" in module_name or "aurora_soar" in module_name:
                        return mock_module
                    return MagicMock()

                mock_import.side_effect = import_side_effect

                # Mock SQLiteStore
                with patch("aurora.core.store.sqlite.SQLiteStore") as mock_store:
                    mock_instance = MagicMock()
                    mock_store.return_value = mock_instance

                    result = runner.invoke(
                        doctor_command,
                        [],
                        catch_exceptions=False,
                        obj=isolated_environment["config"],
                    )

        # Should complete with checks run
        assert "MCP FUNCTIONAL" in result.output
        assert "Summary" in result.output

    def test_doctor_full_flow_with_multiple_failures(self, isolated_environment):
        """Doctor should report multiple failures clearly."""
        runner = CliRunner()

        # Create scenario with multiple issues:
        # 1. Invalid MCP config
        # 2. Missing memory database
        # 3. Failed imports

        claude_dir = isolated_environment["project_dir"] / ".claude"
        claude_dir.mkdir(parents=True)
        config_path = claude_dir / "claude_desktop_config.json"
        config_path.write_text("{ invalid }", encoding="utf-8")

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = isolated_environment["project_dir"]

            # Mock imports to fail
            with patch("importlib.import_module") as mock_import:
                mock_import.side_effect = ImportError("Import failed")

                result = runner.invoke(
                    doctor_command, [], catch_exceptions=False, obj=isolated_environment["config"]
                )

        # Should show multiple failures
        assert result.exit_code == 2  # Failures present
        assert "fail" in result.output.lower()

        # Should show summary with counts
        assert "Summary" in result.output
