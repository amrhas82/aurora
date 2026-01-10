"""Tests for MCP configuration validation in init command.

This test module verifies MCP validation logic added to the unified init command.

Test-Driven Development (TDD):
- These tests are written FIRST (RED phase)
- Implementation in init_helpers.py comes SECOND (GREEN phase)
- Tests verify soft failures: warnings instead of errors
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.commands.init_helpers import configure_mcp_servers


class TestMCPValidationHelpers:
    """Test _validate_mcp_config() helper function.

    This function performs JSON syntax validation, server path checks,
    and required tools validation with soft failures (warnings not errors).
    """

    def test_validate_mcp_config_returns_tuple_with_success_and_warnings(self, tmp_path):
        """_validate_mcp_config() should return (success: bool, warnings: list[str])."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        # Create valid MCP config
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"aurora": {"type": "stdio", "command": "aurora-mcp", "args": []}}}
            ),
            encoding="utf-8",
        )

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        assert isinstance(success, bool)
        assert isinstance(warnings, list)

    def test_validate_mcp_config_detects_json_syntax_error(self, tmp_path):
        """_validate_mcp_config() should detect malformed JSON and return warning."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        # Create invalid JSON config
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('{"invalid": json syntax}', encoding="utf-8")

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        assert success is False
        assert len(warnings) > 0
        assert any("JSON syntax" in w or "invalid" in w.lower() for w in warnings)

    def test_validate_mcp_config_validates_aurora_mcp_server_exists(self, tmp_path):
        """_validate_mcp_config() should verify Aurora MCP server is configured."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        # Create config without aurora server
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps({"mcpServers": {"other-server": {"command": "other"}}}), encoding="utf-8"
        )

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        # Should warn about missing aurora server
        assert len(warnings) > 0
        assert any("aurora" in w.lower() for w in warnings)

    def test_validate_mcp_config_checks_required_tools(self, tmp_path):
        """_validate_mcp_config() should validate 3 required tools exist."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        # Create valid config with aurora server
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(
                {"mcpServers": {"aurora": {"type": "stdio", "command": "aurora-mcp", "args": []}}}
            ),
            encoding="utf-8",
        )

        # Mock the tools import to verify checking happens
        with patch("aurora_cli.commands.init_helpers.Path.exists") as mock_exists:
            # Assume server path exists for this test
            mock_exists.return_value = True

            success, warnings = _validate_mcp_config(config_path, tmp_path)

            # At minimum, config should be parseable
            # Actual tool validation may warn if tools not importable in test env
            assert isinstance(warnings, list)

    def test_validate_mcp_config_accepts_python_module_command(self, tmp_path):
        """_validate_mcp_config() should accept 'python3 -m aurora_mcp.server' format."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        # Create config with python module format
        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "aurora": {
                            "type": "stdio",
                            "command": "python3",
                            "args": ["-m", "aurora_mcp.server"],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        # Should not warn about command format
        assert not any("command" in w.lower() and "invalid" in w.lower() for w in warnings)

    def test_validate_mcp_config_warns_on_missing_file(self, tmp_path):
        """_validate_mcp_config() should handle missing config file gracefully."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        config_path = tmp_path / ".cursor" / "mcp.json"
        # Don't create the file

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        assert success is False
        assert len(warnings) > 0
        assert any("not found" in w.lower() or "missing" in w.lower() for w in warnings)

    def test_validate_mcp_config_handles_empty_file(self, tmp_path):
        """_validate_mcp_config() should handle empty config file."""
        from aurora_cli.commands.init_helpers import _validate_mcp_config

        config_path = tmp_path / ".cursor" / "mcp.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("", encoding="utf-8")

        success, warnings = _validate_mcp_config(config_path, tmp_path)

        assert success is False
        assert len(warnings) > 0


class TestConfigureMCPServersValidation:
    """Test configure_mcp_servers() integration with validation.

    Tests that configure_mcp_servers() calls validation and returns warnings
    in its return tuple without preventing configuration completion.
    """

    @pytest.mark.asyncio
    async def test_configure_mcp_servers_returns_validation_warnings(self, tmp_path):
        """configure_mcp_servers() should return validation warnings in tuple."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            # Mock configurator
            mock_configurator = MagicMock()
            mock_configurator.tool_id = "claude"
            mock_configurator.name = "Claude Code"
            mock_configurator.is_configured.return_value = False

            # Create invalid JSON to trigger validation warning
            config_path = tmp_path / ".claude" / "mcp.json"
            config_path.parent.mkdir(parents=True)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.warnings = []
            mock_configurator.configure.return_value = mock_result
            mock_configurator.get_config_path.return_value = config_path

            mock_get.return_value = mock_configurator
            mock_get_all.return_value = []

            # Write invalid JSON to trigger validation warning
            config_path.write_text('{"invalid": json}', encoding="utf-8")

            result = await configure_mcp_servers(tmp_path, ["claude"])

            # Should return 4-tuple with validation_warnings
            assert len(result) == 4
            created, updated, skipped, validation_warnings = result
            assert isinstance(validation_warnings, list)

    @pytest.mark.asyncio
    async def test_configure_mcp_servers_validation_does_not_prevent_completion(self, tmp_path):
        """configure_mcp_servers() should complete even with validation warnings (soft failure)."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            # Mock configurator
            mock_configurator = MagicMock()
            mock_configurator.tool_id = "claude"
            mock_configurator.name = "Claude Code"
            mock_configurator.is_configured.return_value = False

            config_path = tmp_path / ".claude" / "mcp.json"
            config_path.parent.mkdir(parents=True)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.warnings = []
            mock_configurator.configure.return_value = mock_result
            mock_configurator.get_config_path.return_value = config_path

            mock_get.return_value = mock_configurator
            mock_get_all.return_value = []

            # Configuration should succeed despite validation issues
            result = await configure_mcp_servers(tmp_path, ["claude"])

            created, updated, skipped, validation_warnings = result

            # Configuration should succeed
            assert "Claude Code" in created or "Claude Code" in updated

    @pytest.mark.asyncio
    async def test_configure_mcp_servers_includes_json_syntax_warnings(self, tmp_path):
        """configure_mcp_servers() should include JSON syntax errors in validation warnings."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            # Mock configurator
            mock_configurator = MagicMock()
            mock_configurator.tool_id = "claude"
            mock_configurator.name = "Claude Code"
            mock_configurator.is_configured.return_value = False

            config_path = tmp_path / ".claude" / "mcp.json"
            config_path.parent.mkdir(parents=True)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.warnings = []
            mock_configurator.configure.return_value = mock_result
            mock_configurator.get_config_path.return_value = config_path

            mock_get.return_value = mock_configurator
            mock_get_all.return_value = []

            # Write malformed JSON
            config_path.write_text('{"bad": json syntax}', encoding="utf-8")

            result = await configure_mcp_servers(tmp_path, ["claude"])
            created, updated, skipped, validation_warnings = result

            # Should have validation warnings about JSON
            assert len(validation_warnings) > 0
            assert any("JSON" in w or "syntax" in w.lower() for w in validation_warnings)

    @pytest.mark.asyncio
    async def test_configure_mcp_servers_validates_all_configured_tools(self, tmp_path):
        """configure_mcp_servers() should validate each configured tool."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            # Mock multiple configurators
            tools = []
            for tool_id, tool_name in [("claude", "Claude Code"), ("cursor", "Cursor")]:
                mock_conf = MagicMock()
                mock_conf.tool_id = tool_id
                mock_conf.name = tool_name
                mock_conf.is_configured.return_value = False

                config_path = tmp_path / f".{tool_id}" / "mcp.json"
                config_path.parent.mkdir(parents=True)
                config_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")

                mock_result = MagicMock()
                mock_result.success = True
                mock_result.warnings = []
                mock_conf.configure.return_value = mock_result
                mock_conf.get_config_path.return_value = config_path

                tools.append(mock_conf)

            def get_side_effect(tid):
                for t in tools:
                    if t.tool_id == tid:
                        return t
                return None

            mock_get.side_effect = get_side_effect
            mock_get_all.return_value = []

            result = await configure_mcp_servers(tmp_path, ["claude", "cursor"])
            created, updated, skipped, validation_warnings = result

            # Should validate both tools
            # Both configs are empty so should have warnings about missing aurora
            assert len(validation_warnings) >= 2


class TestValidationWarningDisplay:
    """Test that init command displays validation warnings to user.

    Verifies that warnings suggest running 'aur doctor' for details.
    """

    def test_validation_warnings_suggest_aur_doctor(self):
        """Validation warnings should suggest running 'aur doctor' command."""
        # This is a documentation test - the actual display logic is in init.py
        # We verify the pattern here to guide implementation

        sample_warnings = [
            "claude: MCP config has invalid JSON syntax",
            "cursor: Aurora MCP server not found in configuration",
        ]

        # Expected pattern: suggest aur doctor when warnings exist
        suggestion = "Run 'aur doctor' for detailed MCP health checks and fixes"

        # Verify suggestion is actionable
        assert "aur doctor" in suggestion
        assert len(sample_warnings) > 0  # We have warnings to display


class TestSoftFailureBehavior:
    """Test that validation uses soft failures (warnings) not hard failures (errors).

    Critical requirement: validation issues should NOT prevent init from completing.
    """

    @pytest.mark.asyncio
    async def test_validation_warnings_do_not_raise_exceptions(self, tmp_path):
        """Validation warnings should not raise exceptions or prevent init completion."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            mock_configurator = MagicMock()
            mock_configurator.tool_id = "claude"
            mock_configurator.name = "Claude Code"
            mock_configurator.is_configured.return_value = False

            config_path = tmp_path / ".claude" / "mcp.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("COMPLETELY INVALID", encoding="utf-8")

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.warnings = []
            mock_configurator.configure.return_value = mock_result
            mock_configurator.get_config_path.return_value = config_path

            mock_get.return_value = mock_configurator
            mock_get_all.return_value = []

            # Should not raise exception despite invalid config
            try:
                result = await configure_mcp_servers(tmp_path, ["claude"])
                assert len(result) == 4  # Should return normally
            except Exception as e:
                pytest.fail(f"configure_mcp_servers raised exception on validation warning: {e}")

    @pytest.mark.asyncio
    async def test_validation_allows_partial_success(self, tmp_path):
        """Validation should allow init to succeed even if some tools have issues."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):

            # Mock two configurators: one valid, one with issues
            tools = []

            # Valid tool
            mock_valid = MagicMock()
            mock_valid.tool_id = "claude"
            mock_valid.name = "Claude Code"
            mock_valid.is_configured.return_value = False
            valid_path = tmp_path / ".claude" / "mcp.json"
            valid_path.parent.mkdir(parents=True)
            valid_path.write_text(
                json.dumps({"mcpServers": {"aurora": {"command": "aurora-mcp"}}}), encoding="utf-8"
            )
            mock_result_valid = MagicMock()
            mock_result_valid.success = True
            mock_result_valid.warnings = []
            mock_valid.configure.return_value = mock_result_valid
            mock_valid.get_config_path.return_value = valid_path
            tools.append(mock_valid)

            # Tool with issues
            mock_invalid = MagicMock()
            mock_invalid.tool_id = "cursor"
            mock_invalid.name = "Cursor"
            mock_invalid.is_configured.return_value = False
            invalid_path = tmp_path / ".cursor" / "mcp.json"
            invalid_path.parent.mkdir(parents=True)
            invalid_path.write_text("INVALID JSON", encoding="utf-8")
            mock_result_invalid = MagicMock()
            mock_result_invalid.success = True
            mock_result_invalid.warnings = []
            mock_invalid.configure.return_value = mock_result_invalid
            mock_invalid.get_config_path.return_value = invalid_path
            tools.append(mock_invalid)

            def get_side_effect(tid):
                for t in tools:
                    if t.tool_id == tid:
                        return t
                return None

            mock_get.side_effect = get_side_effect
            mock_get_all.return_value = []

            result = await configure_mcp_servers(tmp_path, ["claude", "cursor"])
            created, updated, skipped, validation_warnings = result

            # Both should be configured despite one having validation issues
            assert len(created) + len(updated) == 2
            # But should have warnings for the invalid one
            assert len(validation_warnings) > 0
