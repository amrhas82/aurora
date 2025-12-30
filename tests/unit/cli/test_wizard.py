"""Unit tests for interactive setup wizard.

Tests the wizard flow, input validation, and configuration creation.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from aurora_cli.wizard import InteractiveWizard
from click.testing import CliRunner


@pytest.fixture
def wizard():
    """Wizard instance fixture."""
    return InteractiveWizard()


@pytest.fixture
def runner():
    """Click test runner fixture."""
    return CliRunner()


class TestWizardFlow:
    """Test wizard flow and step execution."""

    def test_wizard_initialization(self, wizard: InteractiveWizard):
        """Test wizard initializes with correct defaults."""
        assert wizard.config_data == {}
        assert wizard.should_index is False
        assert wizard.api_key is None
        assert wizard.enable_mcp is False

    @patch("aurora_cli.wizard.console")
    @patch("aurora_cli.wizard.subprocess.run")
    def test_step_1_welcome_with_git(
        self,
        mock_subprocess,
        mock_console,
        wizard: InteractiveWizard,
    ):
        """Test welcome step detects git repository."""
        # Mock successful git detection
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        wizard.step_1_welcome()

        # Verify console prints were called
        assert mock_console.print.called
        # Verify subprocess was called to detect git
        mock_subprocess.assert_called_once()

    @patch("aurora_cli.wizard.console")
    @patch("aurora_cli.wizard.subprocess.run")
    def test_step_1_welcome_without_git(
        self,
        mock_subprocess,
        mock_console,
        wizard: InteractiveWizard,
    ):
        """Test welcome step handles missing git."""
        # Mock git not found
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_subprocess.return_value = mock_result

        wizard.step_1_welcome()

        assert mock_console.print.called

    @patch("aurora_cli.wizard.click.confirm")
    def test_step_2_indexing_yes(
        self,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test indexing prompt when user says yes."""
        mock_confirm.return_value = True

        wizard.step_2_indexing_prompt()

        assert wizard.should_index is True
        mock_confirm.assert_called_once()

    @patch("aurora_cli.wizard.click.confirm")
    def test_step_2_indexing_no(
        self,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test indexing prompt when user says no."""
        mock_confirm.return_value = False

        wizard.step_2_indexing_prompt()

        assert wizard.should_index is False

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_3_anthropic_provider(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test provider selection for Anthropic."""
        mock_prompt.return_value = "1"

        wizard.step_3_embeddings_provider()

        assert wizard.config_data["provider"] == "anthropic"

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_3_openai_provider(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test provider selection for OpenAI."""
        mock_prompt.return_value = "2"

        wizard.step_3_embeddings_provider()

        assert wizard.config_data["provider"] == "openai"

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_3_ollama_provider(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test provider selection for Ollama."""
        mock_prompt.return_value = "3"

        wizard.step_3_embeddings_provider()

        assert wizard.config_data["provider"] == "ollama"


class TestAPIKeyValidation:
    """Test API key input and validation."""

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_4_valid_anthropic_key(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test valid Anthropic API key is accepted."""
        wizard.config_data["provider"] = "anthropic"
        mock_prompt.return_value = "sk-ant-test123"

        wizard.step_4_api_key_input()

        assert wizard.api_key == "sk-ant-test123"

    @patch("aurora_cli.wizard.click.confirm")
    @patch("aurora_cli.wizard.click.prompt")
    def test_step_4_invalid_anthropic_key(
        self,
        mock_prompt,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test invalid Anthropic API key is rejected."""
        wizard.config_data["provider"] = "anthropic"
        mock_prompt.return_value = "invalid-key"
        mock_confirm.return_value = False  # Don't retry

        wizard.step_4_api_key_input()

        assert wizard.api_key is None

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_4_valid_openai_key(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test valid OpenAI API key is accepted."""
        wizard.config_data["provider"] = "openai"
        mock_prompt.return_value = "sk-test123"

        wizard.step_4_api_key_input()

        assert wizard.api_key == "sk-test123"

    @patch("aurora_cli.wizard.click.prompt")
    def test_step_4_skip_api_key(
        self,
        mock_prompt,
        wizard: InteractiveWizard,
    ):
        """Test API key can be skipped."""
        wizard.config_data["provider"] = "anthropic"
        mock_prompt.return_value = ""

        wizard.step_4_api_key_input()

        assert wizard.api_key is None

    def test_step_4_ollama_no_key_needed(self, wizard: InteractiveWizard):
        """Test Ollama doesn't require API key."""
        wizard.config_data["provider"] = "ollama"

        wizard.step_4_api_key_input()

        assert wizard.api_key is None


class TestMCPPrompt:
    """Test MCP server prompt."""

    @patch("aurora_cli.wizard.click.confirm")
    def test_step_5_enable_mcp(
        self,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test enabling MCP server."""
        mock_confirm.return_value = True

        wizard.step_5_mcp_prompt()

        assert wizard.enable_mcp is True

    @patch("aurora_cli.wizard.click.confirm")
    def test_step_5_disable_mcp(
        self,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test disabling MCP server."""
        mock_confirm.return_value = False

        wizard.step_5_mcp_prompt()

        assert wizard.enable_mcp is False


class TestConfigCreation:
    """Test configuration file creation."""

    @patch("aurora_cli.wizard.os.chmod")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("aurora_cli.wizard._get_aurora_home")
    def test_step_6_creates_config(
        self,
        mock_get_home,
        mock_open,
        mock_chmod,
        wizard: InteractiveWizard,
    ):
        """Test config file is created with correct structure."""
        # Setup
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = False
        mock_config = MagicMock(spec=Path)
        mock_config.exists.return_value = False
        mock_home.__truediv__ = (
            lambda self, other: mock_config if other == "config.json" else mock_home
        )
        mock_get_home.return_value = mock_home

        wizard.api_key = "sk-ant-test123"
        wizard.config_data["provider"] = "anthropic"

        # Execute
        wizard.step_6_create_config()

        # Verify directory creation
        mock_home.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        # Verify file write
        mock_open.assert_called_once()
        # Verify permissions set
        mock_chmod.assert_called_once()

    @patch("aurora_cli.wizard.click.confirm")
    @patch("aurora_cli.wizard._get_aurora_home")
    def test_step_6_existing_config_overwrite_no(
        self,
        mock_get_home,
        mock_confirm,
        wizard: InteractiveWizard,
    ):
        """Test existing config is not overwritten if user declines."""
        # Setup
        mock_home = MagicMock(spec=Path)
        mock_home.exists.return_value = True
        mock_config = MagicMock(spec=Path)
        mock_config.exists.return_value = True
        mock_home.__truediv__ = lambda self, other: mock_config
        mock_get_home.return_value = mock_home
        mock_confirm.return_value = False

        # Execute
        wizard.step_6_create_config()

        # Verify confirm was called
        mock_confirm.assert_called_once()


class TestIndexing:
    """Test indexing step."""

    @patch("aurora_cli.memory_manager.MemoryManager")
    @patch("aurora_cli.config.load_config")
    @patch("pathlib.Path.cwd")
    def test_step_7_successful_indexing(
        self,
        mock_cwd,
        mock_load_config,
        mock_manager_class,
        wizard: InteractiveWizard,
    ):
        """Test successful indexing."""
        # Setup
        mock_cwd.return_value = Path("/test")
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_stats = MagicMock()
        mock_stats.files_indexed = 10
        mock_stats.chunks_created = 100
        mock_stats.duration_seconds = 1.5

        mock_manager = MagicMock()
        mock_manager.index_path.return_value = mock_stats
        mock_manager_class.return_value = mock_manager

        # Execute
        wizard.step_7_run_index()

        # Verify
        mock_manager.index_path.assert_called_once()
        assert mock_manager.index_path.call_args[0][0] == Path("/test")

    @patch("aurora_cli.memory_manager.MemoryManager")
    @patch("aurora_cli.config.load_config")
    def test_step_7_no_files_indexed(
        self,
        mock_load_config,
        mock_manager_class,
        wizard: InteractiveWizard,
    ):
        """Test indexing when no files found."""
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_stats = MagicMock()
        mock_stats.files_indexed = 0

        mock_manager = MagicMock()
        mock_manager.index_path.return_value = mock_stats
        mock_manager_class.return_value = mock_manager

        # Should not raise exception
        wizard.step_7_run_index()


class TestCompletion:
    """Test completion step."""

    @patch("aurora_cli.wizard.console")
    def test_step_8_displays_summary(
        self,
        mock_console,
        wizard: InteractiveWizard,
    ):
        """Test completion displays summary."""
        wizard.config_data["provider"] = "anthropic"
        wizard.api_key = "sk-ant-test123"
        wizard.should_index = True
        wizard.enable_mcp = True

        wizard.step_8_completion()

        # Verify console prints were called
        assert mock_console.print.called
        assert mock_console.print.call_count >= 5  # Multiple prints for summary

    @patch("aurora_cli.wizard.console")
    def test_step_8_missing_api_key_warning(
        self,
        mock_console,
        wizard: InteractiveWizard,
    ):
        """Test completion warns about missing API key."""
        wizard.config_data["provider"] = "anthropic"
        wizard.api_key = None  # No API key set

        wizard.step_8_completion()

        # Should display but not crash
        assert mock_console.print.called


class TestFullWizardFlow:
    """Test complete wizard execution."""

    @patch("aurora_cli.wizard.InteractiveWizard.step_8_completion")
    @patch("aurora_cli.wizard.InteractiveWizard.step_7_run_index")
    @patch("aurora_cli.wizard.InteractiveWizard.step_6_create_config")
    @patch("aurora_cli.wizard.InteractiveWizard.step_5_mcp_prompt")
    @patch("aurora_cli.wizard.InteractiveWizard.step_4_api_key_input")
    @patch("aurora_cli.wizard.InteractiveWizard.step_3_embeddings_provider")
    @patch("aurora_cli.wizard.InteractiveWizard.step_2_indexing_prompt")
    @patch("aurora_cli.wizard.InteractiveWizard.step_1_welcome")
    def test_run_executes_all_steps_with_indexing(
        self,
        mock_step_1,
        mock_step_2,
        mock_step_3,
        mock_step_4,
        mock_step_5,
        mock_step_6,
        mock_step_7,
        mock_step_8,
        wizard: InteractiveWizard,
    ):
        """Test run() executes all steps in order when indexing."""
        wizard.should_index = True

        wizard.run()

        # Verify all steps called in order
        mock_step_1.assert_called_once()
        mock_step_2.assert_called_once()
        mock_step_3.assert_called_once()
        mock_step_4.assert_called_once()
        mock_step_5.assert_called_once()
        mock_step_6.assert_called_once()
        mock_step_7.assert_called_once()
        mock_step_8.assert_called_once()

    @patch("aurora_cli.wizard.InteractiveWizard.step_8_completion")
    @patch("aurora_cli.wizard.InteractiveWizard.step_7_run_index")
    @patch("aurora_cli.wizard.InteractiveWizard.step_6_create_config")
    @patch("aurora_cli.wizard.InteractiveWizard.step_5_mcp_prompt")
    @patch("aurora_cli.wizard.InteractiveWizard.step_4_api_key_input")
    @patch("aurora_cli.wizard.InteractiveWizard.step_3_embeddings_provider")
    @patch("aurora_cli.wizard.InteractiveWizard.step_2_indexing_prompt")
    @patch("aurora_cli.wizard.InteractiveWizard.step_1_welcome")
    def test_run_skips_indexing_when_declined(
        self,
        mock_step_1,
        mock_step_2,
        mock_step_3,
        mock_step_4,
        mock_step_5,
        mock_step_6,
        mock_step_7,
        mock_step_8,
        wizard: InteractiveWizard,
    ):
        """Test run() skips indexing step when user declines."""
        wizard.should_index = False

        wizard.run()

        # Verify indexing step NOT called
        mock_step_7.assert_not_called()
        # But completion IS called
        mock_step_8.assert_called_once()
