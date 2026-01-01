"""E2E tests for interactive setup wizard.

Tests the complete wizard flow in a real environment.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from aurora_cli.main import cli
from click.testing import CliRunner


@pytest.fixture
def temp_aurora_home(monkeypatch, tmp_path):
    """Create temporary Aurora home for testing."""
    aurora_home = tmp_path / ".aurora"
    monkeypatch.setenv("AURORA_HOME", str(aurora_home))
    return aurora_home


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


def test_wizard_complete_flow_skip_indexing(runner: CliRunner, temp_aurora_home: Path):
    """Test complete wizard flow without indexing."""
    # Simulate user inputs:
    # - No indexing
    # - Provider: Anthropic (1)
    # - API key: skip (empty)
    # - MCP: No
    inputs = "n\n1\n\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    # Verify successful completion
    assert result.exit_code == 0
    assert "Welcome" in result.output
    assert "Setup Complete" in result.output
    assert "Configuration Summary" in result.output

    # Verify config file was created
    config_file = temp_aurora_home / "config.json"
    assert config_file.exists()

    # Verify config has correct permissions
    if os.name != 'nt':  # Skip on Windows
        stat_info = config_file.stat()
        permissions = oct(stat_info.st_mode)[-3:]
        assert permissions == "600"


def test_wizard_anthropic_with_api_key(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard with Anthropic provider and valid API key."""
    # Simulate user inputs:
    # - No indexing
    # - Provider: Anthropic (1)
    # - API key: sk-ant-test123
    # - MCP: No
    inputs = "n\n1\nsk-ant-test123\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "✓ Valid Anthropic API key format" in result.output or "Setup Complete" in result.output
    assert "Configuration Summary" in result.output


def test_wizard_openai_provider(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard with OpenAI provider selection."""
    # Simulate user inputs:
    # - No indexing
    # - Provider: OpenAI (2)
    # - API key: sk-test123
    # - MCP: No
    inputs = "n\n2\nsk-test123\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "Setup Complete" in result.output


def test_wizard_ollama_provider(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard with Ollama (local) provider."""
    # Simulate user inputs:
    # - No indexing
    # - Provider: Ollama (3)
    # - MCP: No
    inputs = "n\n3\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "Setup Complete" in result.output
    assert "Not needed for Ollama" in result.output


def test_wizard_with_mcp_enabled(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard with MCP server enabled."""
    # Simulate user inputs:
    # - No indexing
    # - Provider: Anthropic (1)
    # - API key: skip
    # - MCP: Yes
    inputs = "n\n1\n\ny\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "MCP server enabled" in result.output or "Setup Complete" in result.output


def test_wizard_environment_detection(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard detects environment correctly."""
    inputs = "n\n1\n\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "Environment Detection" in result.output
    assert "Python version" in result.output
    assert "Working directory" in result.output


def test_wizard_displays_all_steps(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard displays all expected steps."""
    inputs = "n\n1\n\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    # Check for step headers
    assert "Step 1/7: Memory Indexing" in result.output
    assert "Step 2/7: LLM Provider" in result.output
    assert "Step 3/7: API Key" in result.output
    assert "Step 4/7: MCP Server" in result.output
    assert "Step 5/7: Creating Configuration" in result.output
    # Step 6 (indexing) skipped
    # Step 7 is completion


def test_wizard_next_steps_displayed(runner: CliRunner, temp_aurora_home: Path):
    """Test wizard displays next steps in completion."""
    inputs = "n\n1\n\nn\n"

    result = runner.invoke(cli, ["init", "--interactive"], input=inputs)

    assert result.exit_code == 0
    assert "Next Steps" in result.output
    assert "aur doctor" in result.output
    assert "aur version" in result.output
    assert "aur query" in result.output
