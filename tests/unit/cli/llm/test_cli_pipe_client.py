"""Unit tests for CLIPipeLLMClient.

TDD: These tests are written FIRST before implementation.
All tests should FAIL initially (RED phase).
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest


class TestCLIPipeLLMClientConstruction:
    """Tests for CLIPipeLLMClient constructor."""

    def test_constructor_validates_tool_exists(self):
        """Tool must exist in PATH or raise ValueError."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value=None):
            with pytest.raises(ValueError, match="not found in PATH"):
                CLIPipeLLMClient(tool="nonexistent_tool")

    def test_constructor_accepts_valid_tool(self):
        """Valid tool in PATH is accepted."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude")
            assert client._tool == "claude"

    def test_constructor_default_tool_is_claude(self):
        """Default tool is 'claude'."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient()
            assert client._tool == "claude"


class TestCLIPipeLLMClientGenerate:
    """Tests for CLIPipeLLMClient.generate() method."""

    def test_generate_pipes_to_tool(self, tmp_path):
        """generate() calls subprocess.run with correct arguments."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="Test response", stderr="")

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            client.generate(prompt="Hello, world!")

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["claude", "-p"]
            assert "Hello, world!" in call_args[1]["input"]

    def test_generate_returns_llm_response(self, tmp_path):
        """generate() returns proper LLMResponse object."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
        from aurora_reasoning.llm_client import LLMResponse

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="Test response content", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            response = client.generate(prompt="Test prompt")

            assert isinstance(response, LLMResponse)
            assert response.content == "Test response content"
            assert response.model == "claude"

    def test_generate_handles_timeout(self, tmp_path):
        """generate() enforces 180-second timeout."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="Response", stderr="")

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            client.generate(prompt="Test")

            call_args = mock_run.call_args
            assert call_args[1]["timeout"] == 180

    def test_generate_raises_on_failure(self, tmp_path):
        """generate() raises RuntimeError on non-zero exit code."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=1, stdout="", stderr="Tool failed")

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="Tool failed"):
                client.generate(prompt="Test")


class TestCLIPipeLLMClientGenerateJSON:
    """Tests for CLIPipeLLMClient.generate_json() method."""

    def test_generate_json_extracts_json(self, tmp_path):
        """generate_json() parses plain JSON response."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        json_response = '{"result": "success", "value": 42}'
        mock_result = Mock(returncode=0, stdout=json_response, stderr="")

        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json(prompt="Give me JSON")

            assert result == {"result": "success", "value": 42}

    def test_generate_json_handles_markdown(self, tmp_path):
        """generate_json() extracts JSON from ```json blocks."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        markdown_response = """Here's the JSON:

```json
{"key": "value", "nested": {"a": 1}}
```

Hope that helps!"""
        mock_result = Mock(returncode=0, stdout=markdown_response, stderr="")

        with patch("subprocess.run", return_value=mock_result):
            result = client.generate_json(prompt="Give me JSON")

            assert result == {"key": "value", "nested": {"a": 1}}


class TestCLIPipeLLMClientTokens:
    """Tests for CLIPipeLLMClient token counting."""

    def test_count_tokens_heuristic(self):
        """count_tokens() returns len(text) // 4."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude")

        # 100 characters should be ~25 tokens
        text = "a" * 100
        assert client.count_tokens(text) == 25

        # 47 characters should be 11 tokens (integer division)
        text = "b" * 47
        assert client.count_tokens(text) == 11

    def test_default_model_returns_tool_name(self):
        """default_model property returns the tool name."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/cursor"):
            client = CLIPipeLLMClient(tool="cursor")

        assert client.default_model == "cursor"


class TestCLIPipeLLMClientJSONFiles:
    """Tests for JSON file placeholder functionality."""

    def test_generate_writes_input_json(self, tmp_path):
        """input.json is written before LLM call."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="Response", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            client.generate(prompt="Test prompt", system="System message")

        input_file = tmp_path / "input.json"
        assert input_file.exists()

        input_data = json.loads(input_file.read_text())
        assert "prompt" in input_data
        assert input_data["prompt"] == "Test prompt"

    def test_generate_writes_output_json(self, tmp_path):
        """output.json is written after LLM call."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="LLM Response Text", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            client.generate(prompt="Test")

        output_file = tmp_path / "output.json"
        assert output_file.exists()

        output_data = json.loads(output_file.read_text())
        assert "content" in output_data
        assert output_data["content"] == "LLM Response Text"

    def test_generate_writes_state_json(self, tmp_path):
        """state.json tracks current operation."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=tmp_path)

        mock_result = Mock(returncode=0, stdout="Response", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            client.generate(prompt="Test", phase_name="decompose")

        state_file = tmp_path / "state.json"
        assert state_file.exists()

        state_data = json.loads(state_file.read_text())
        assert "phase" in state_data
        assert state_data["phase"] == "decompose"

    def test_soar_dir_created(self, tmp_path):
        """.aurora/soar/ directory is created automatically."""
        from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

        soar_dir = tmp_path / ".aurora" / "soar"
        assert not soar_dir.exists()

        with patch("shutil.which", return_value="/usr/bin/claude"):
            client = CLIPipeLLMClient(tool="claude", soar_dir=soar_dir)

        mock_result = Mock(returncode=0, stdout="Response", stderr="")

        with patch("subprocess.run", return_value=mock_result):
            client.generate(prompt="Test")

        assert soar_dir.exists()
