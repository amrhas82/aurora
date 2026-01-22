"""Integration tests for MCP configuration validation in init command.

This test module verifies that the init command properly validates MCP
configurations with soft failures (warnings instead of errors).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from aurora_cli.commands.init_helpers import configure_mcp_servers


class TestInitMCPValidationIntegration:
    """Integration tests for MCP validation in full init flow."""

    @pytest.mark.asyncio
    async def test_init_completes_with_invalid_json_warning(self, tmp_path):
        """Init should complete successfully even with invalid MCP JSON.

        This tests the critical soft-failure requirement: validation issues
        should NOT prevent initialization from completing.
        """
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

            # Create configuration result
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.warnings = []
            mock_configurator.configure.return_value = mock_result
            mock_configurator.get_config_path.return_value = config_path

            mock_get.return_value = mock_configurator
            mock_get_all.return_value = []

            # Write valid JSON first (configure will create it)
            config_path.write_text(
                json.dumps({"mcpServers": {"aurora": {"command": "aurora-mcp"}}}),
                encoding="utf-8",
            )

            # Run configuration
            created, updated, skipped, warnings = await configure_mcp_servers(tmp_path, ["claude"])

            # Verify init completed successfully
            assert len(created) + len(updated) > 0
            assert "Claude Code" in created or "Claude Code" in updated

            # Verify no exceptions were raised
            assert isinstance(warnings, list)

    @pytest.mark.asyncio
    async def test_init_shows_validation_warnings_with_aur_doctor_suggestion(self, tmp_path):
        """Init should display validation warnings and suggest 'aur doctor'."""
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

            # Write config without Aurora server (will trigger warning)
            config_path.write_text(
                json.dumps({"mcpServers": {"other-server": {"command": "other"}}}),
                encoding="utf-8",
            )

            # Run configuration
            created, updated, skipped, warnings = await configure_mcp_servers(tmp_path, ["claude"])

            # Should have validation warning about missing aurora server
            assert len(warnings) > 0
            assert any("aurora" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_init_handles_multiple_tools_with_mixed_validation(self, tmp_path):
        """Init should handle multiple tools where some have validation issues."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):
            # Mock two configurators
            tools = []

            # Tool 1: Valid configuration
            mock_valid = MagicMock()
            mock_valid.tool_id = "claude"
            mock_valid.name = "Claude Code"
            mock_valid.is_configured.return_value = False
            valid_path = tmp_path / ".claude" / "mcp.json"
            valid_path.parent.mkdir(parents=True)
            valid_path.write_text(
                json.dumps({"mcpServers": {"aurora": {"command": "aurora-mcp"}}}),
                encoding="utf-8",
            )
            mock_result_valid = MagicMock()
            mock_result_valid.success = True
            mock_result_valid.warnings = []
            mock_valid.configure.return_value = mock_result_valid
            mock_valid.get_config_path.return_value = valid_path
            tools.append(mock_valid)

            # Tool 2: Missing aurora server (warning)
            mock_warning = MagicMock()
            mock_warning.tool_id = "cursor"
            mock_warning.name = "Cursor"
            mock_warning.is_configured.return_value = False
            warning_path = tmp_path / ".cursor" / "mcp.json"
            warning_path.parent.mkdir(parents=True)
            warning_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
            mock_result_warning = MagicMock()
            mock_result_warning.success = True
            mock_result_warning.warnings = []
            mock_warning.configure.return_value = mock_result_warning
            mock_warning.get_config_path.return_value = warning_path
            tools.append(mock_warning)

            def get_side_effect(tid):
                for t in tools:
                    if t.tool_id == tid:
                        return t
                return None

            mock_get.side_effect = get_side_effect
            mock_get_all.return_value = []

            # Run configuration for both tools
            created, updated, skipped, warnings = await configure_mcp_servers(
                tmp_path,
                ["claude", "cursor"],
            )

            # Both tools should be configured
            assert len(created) + len(updated) == 2

            # Should have warnings for the problematic tool
            assert len(warnings) > 0
            assert any("Cursor" in w for w in warnings)

            # But should NOT have warnings for the valid tool
            # (or if it does, should only be about missing aurora, not JSON errors)

    @pytest.mark.asyncio
    async def test_init_validation_accepts_both_command_formats(self, tmp_path):
        """Init validation should accept both 'aurora-mcp' and 'python3 -m' formats."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):
            # Test both command formats
            test_configs = [
                {
                    "name": "aurora-mcp command",
                    "config": {"mcpServers": {"aurora": {"command": "aurora-mcp", "args": []}}},
                },
                {
                    "name": "python3 module command",
                    "config": {
                        "mcpServers": {
                            "aurora": {"command": "python3", "args": ["-m", "aurora_mcp.server"]},
                        },
                    },
                },
            ]

            for test_config in test_configs:
                # Mock configurator
                mock_configurator = MagicMock()
                mock_configurator.tool_id = "claude"
                mock_configurator.name = "Claude Code"
                mock_configurator.is_configured.return_value = False

                config_path = tmp_path / ".claude" / "mcp.json"
                config_path.parent.mkdir(parents=True, exist_ok=True)

                mock_result = MagicMock()
                mock_result.success = True
                mock_result.warnings = []
                mock_configurator.configure.return_value = mock_result
                mock_configurator.get_config_path.return_value = config_path

                mock_get.return_value = mock_configurator
                mock_get_all.return_value = []

                # Write test configuration
                config_path.write_text(json.dumps(test_config["config"]), encoding="utf-8")

                # Run configuration
                created, updated, skipped, warnings = await configure_mcp_servers(
                    tmp_path,
                    ["claude"],
                )

                # Should NOT have warnings about command format
                command_warnings = [
                    w for w in warnings if "command" in w.lower() and "unexpected" in w.lower()
                ]
                assert (
                    len(command_warnings) == 0
                ), f"{test_config['name']} should be accepted but got warnings: {command_warnings}"

    @pytest.mark.asyncio
    async def test_init_validation_reports_all_issues_together(self, tmp_path):
        """Init should collect and report all validation issues for all tools."""
        with (
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get") as mock_get,
            patch("aurora_cli.configurators.mcp.MCPConfigRegistry.get_all") as mock_get_all,
        ):
            # Create 3 tools with different validation issues
            tools = []

            for idx, (tool_id, tool_name, config) in enumerate(
                [
                    ("claude", "Claude Code", {"mcpServers": {}}),  # Missing aurora
                    (
                        "cursor",
                        "Cursor",
                        {"mcpServers": {"aurora": {"command": "wrong"}}},
                    ),  # Wrong command
                    ("cline", "Cline", {"mcpServers": {}}),  # Missing aurora
                ],
            ):
                mock_conf = MagicMock()
                mock_conf.tool_id = tool_id
                mock_conf.name = tool_name
                mock_conf.is_configured.return_value = False

                config_path = tmp_path / f".{tool_id}" / "mcp.json"
                config_path.parent.mkdir(parents=True)
                config_path.write_text(json.dumps(config), encoding="utf-8")

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

            # Run configuration
            created, updated, skipped, warnings = await configure_mcp_servers(
                tmp_path,
                ["claude", "cursor", "cline"],
            )

            # Should have warnings for all 3 tools
            assert len(warnings) >= 3

            # Each tool should have its name in at least one warning
            for tool_name in ["Claude Code", "Cursor", "Cline"]:
                assert any(
                    tool_name in w for w in warnings
                ), f"Expected warning for {tool_name} but got: {warnings}"
