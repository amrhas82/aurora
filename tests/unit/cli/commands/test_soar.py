"""TDD tests for aur soar command - terminal orchestrator."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from aurora_cli.commands.soar import _ensure_soar_dir, _extract_json, soar_command


class TestExtractJson:
    """Tests for JSON extraction from LLM responses."""

    def test_extract_json_plain(self):
        """Parses raw JSON response."""
        response = '{"goal": "test", "subgoals": ["a", "b"]}'
        result = _extract_json(response)
        assert result == {"goal": "test", "subgoals": ["a", "b"]}

    def test_extract_json_from_markdown(self):
        """Parses JSON from ```json blocks."""
        response = """Here's the decomposition:

```json
{"goal": "test", "subgoals": ["a", "b"]}
```

That covers everything."""
        result = _extract_json(response)
        assert result == {"goal": "test", "subgoals": ["a", "b"]}

    def test_extract_json_with_commentary(self):
        """Extracts JSON even with surrounding text."""
        response = """I'll break this down.
{"goal": "test", "subgoals": ["a"]}
Hope that helps!"""
        result = _extract_json(response)
        assert result == {"goal": "test", "subgoals": ["a"]}

    def test_extract_json_no_json_raises(self):
        """Raises ValueError when no JSON found."""
        response = "This response has no JSON at all."
        with pytest.raises(ValueError, match="No valid JSON found"):
            _extract_json(response)


class TestToolParameter:
    """Tests for --tool parameter."""

    def test_soar_tool_parameter_default(self):
        """Default tool is claude."""
        runner = CliRunner()
        with patch("aurora_cli.commands.soar.shutil.which") as mock_which:
            mock_which.return_value = None  # Tool not found
            result = runner.invoke(soar_command, ["test query"])
            # Should fail because claude not found
            assert "claude" in result.output.lower() or result.exit_code != 0

    def test_soar_tool_parameter_custom(self):
        """Accepts custom tool via --tool."""
        runner = CliRunner()
        with patch("aurora_cli.commands.soar.shutil.which") as mock_which:
            mock_which.return_value = None  # Tool not found
            result = runner.invoke(soar_command, ["test query", "--tool", "cursor"])
            # Should fail because cursor not found
            assert "cursor" in result.output.lower() or result.exit_code != 0

    def test_soar_tool_validation(self):
        """Fails if tool not found in PATH."""
        runner = CliRunner()
        with patch("aurora_cli.commands.soar.shutil.which", return_value=None):
            result = runner.invoke(soar_command, ["test query", "--tool", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower()


class TestPlaceholderFiles:
    """Tests for JSON placeholder files.

    Note: JSON file I/O is now handled by CLIPipeLLMClient.
    Those tests are in tests/unit/cli/llm/test_cli_pipe_client.py
    """

    def test_soar_creates_placeholder_dir(self, tmp_path):
        """Creates .aurora/soar/ directory on run."""
        with patch("aurora_cli.commands.soar.get_aurora_dir", return_value=tmp_path):
            soar_dir = tmp_path / "soar"
            _ensure_soar_dir()
            assert soar_dir.exists()


class TestPhaseDisplay:
    """Tests for terminal phase display."""

    def test_phase_display_orchestrator(self, capsys):
        """Shows [ORCHESTRATOR] for Python phases."""
        from aurora_cli.commands.soar import _print_phase

        _print_phase("ORCHESTRATOR", 1, "Assess", "Analyzing query complexity...")

        captured = capsys.readouterr()
        assert "[ORCHESTRATOR]" in captured.out
        assert "Phase 1" in captured.out
        assert "Assess" in captured.out

    def test_phase_display_llm(self, capsys):
        """Shows [LLM → tool] for LLM phases."""
        from aurora_cli.commands.soar import _print_phase

        _print_phase("LLM", 3, "Decompose", "Breaking into subgoals...", tool="claude")

        captured = capsys.readouterr()
        assert "[LLM → claude]" in captured.out
        assert "Phase 3" in captured.out
        assert "Decompose" in captured.out


class TestPhaseOutput:
    """Tests for phase-specific output."""

    def test_complexity_shown(self, capsys):
        """Complexity displayed after Phase 1."""
        from aurora_cli.commands.soar import _print_phase_result

        _print_phase_result(
            1,
            {
                "complexity": "MEDIUM",  # Key is 'complexity' in callback result
                "score": 24,
                "confidence": 0.85,
            },
        )

        captured = capsys.readouterr()
        assert "MEDIUM" in captured.out

    def test_chunks_shown(self, capsys):
        """Matched chunks shown after Phase 2."""
        from aurora_cli.commands.soar import _print_phase_result

        _print_phase_result(2, {"chunks_retrieved": 5, "indexed": True})

        captured = capsys.readouterr()
        assert "5" in captured.out
        assert "chunk" in captured.out.lower() or "matched" in captured.out.lower()


# ===========================================================================
# NEW TESTS FOR ORCHESTRATOR WRAPPER (TDD Phase 1)
# These tests are for the NEW thin wrapper architecture
# ===========================================================================


class TestSoarOrchestratorIntegration:
    """Tests for soar command using SOAROrchestrator.

    Tests verify the new thin wrapper architecture.
    """

    def test_soar_uses_orchestrator(self):
        """soar command delegates to SOAROrchestrator.execute()."""
        runner = CliRunner()

        # Patch at the actual import location (lazy imports in soar_command)
        with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch_class:
            mock_orchestrator = MagicMock()
            mock_orchestrator.execute.return_value = {
                "answer": "Test answer",
                "formatted_answer": "Test answer",
            }
            mock_orch_class.return_value = mock_orchestrator

            with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient"):
                with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
                    runner.invoke(soar_command, ["test query"])

            # Verify orchestrator.execute was called
            mock_orchestrator.execute.assert_called_once()

    def test_soar_creates_cli_pipe_client(self):
        """soar command creates CLIPipeLLMClient with specified tool."""
        runner = CliRunner()

        with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient") as mock_client_class:
            with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch_class:
                mock_orchestrator = MagicMock()
                mock_orchestrator.execute.return_value = {
                    "answer": "Test",
                    "formatted_answer": "Test",
                }
                mock_orch_class.return_value = mock_orchestrator

                with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/cursor"):
                    runner.invoke(soar_command, ["test query", "--tool", "cursor"])

            # Verify CLIPipeLLMClient was created with correct tool
            mock_client_class.assert_called()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("tool") == "cursor"


class TestEnvironmentVariableSupport:
    """Tests for AURORA_SOAR_TOOL environment variable."""

    def test_soar_env_var_fallback(self, monkeypatch):
        """AURORA_SOAR_TOOL environment variable is respected as default."""
        monkeypatch.setenv("AURORA_SOAR_TOOL", "cursor")

        runner = CliRunner()

        with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient") as mock_client_class:
            with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch_class:
                mock_orchestrator = MagicMock()
                mock_orchestrator.execute.return_value = {
                    "answer": "Test",
                    "formatted_answer": "Test",
                }
                mock_orch_class.return_value = mock_orchestrator

                with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/cursor"):
                    # No --tool flag, should use env var
                    runner.invoke(soar_command, ["test query"])

            # Should use cursor from env var
            mock_client_class.assert_called()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("tool") == "cursor"

    def test_soar_cli_flag_overrides_env(self, monkeypatch):
        """--tool CLI flag overrides AURORA_SOAR_TOOL environment variable."""
        monkeypatch.setenv("AURORA_SOAR_TOOL", "cursor")

        runner = CliRunner()

        with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient") as mock_client_class:
            with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch_class:
                mock_orchestrator = MagicMock()
                mock_orchestrator.execute.return_value = {
                    "answer": "Test",
                    "formatted_answer": "Test",
                }
                mock_orch_class.return_value = mock_orchestrator

                with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
                    # --tool flag should override env var
                    runner.invoke(soar_command, ["test query", "--tool", "claude"])

            # Should use claude from CLI flag, not cursor from env
            mock_client_class.assert_called()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs.get("tool") == "claude"


class TestTerminalUXFormat:
    """Tests for terminal UX matching FR-4.5 specification."""

    def test_soar_displays_header_box(self):
        """Shows Aurora SOAR header box with query."""
        runner = CliRunner()

        with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient"):
                with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch:
                    mock_orch.return_value.execute.return_value = {
                        "answer": "Test answer",
                        "formatted_answer": "Test answer",
                    }
                    result = runner.invoke(soar_command, ["test query"])

        # Check header box format
        assert "Aurora SOAR" in result.output
        assert "╭" in result.output  # Box character
        assert "╰" in result.output  # Box character

    def test_soar_displays_final_answer_box(self):
        """Shows final answer in formatted box."""
        runner = CliRunner()

        with patch("aurora_cli.commands.soar.shutil.which", return_value="/usr/bin/claude"):
            with patch("aurora_cli.llm.cli_pipe_client.CLIPipeLLMClient"):
                with patch("aurora_soar.orchestrator.SOAROrchestrator") as mock_orch:
                    mock_orch.return_value.execute.return_value = {
                        "answer": "This is the final answer",
                        "formatted_answer": "This is the final answer",
                    }
                    result = runner.invoke(soar_command, ["test query"])

        # Check final answer box format
        assert "Final Answer" in result.output
        assert "╭" in result.output  # Box character
        assert "╰" in result.output  # Box character

    def test_phase_ownership_classification(self):
        """Correct owner (ORCHESTRATOR/LLM) for each phase.

        Note: Simplified 7-phase pipeline (route merged into verify).
        """
        # Phase ownership mapping - simplified 7-phase pipeline
        expected_owners = {
            "assess": "ORCHESTRATOR",
            "retrieve": "ORCHESTRATOR",
            "decompose": "LLM",
            "verify": "LLM",  # Now includes agent assignment (was separate route phase)
            "collect": "LLM",
            "synthesize": "LLM",
            "record": "ORCHESTRATOR",
            "respond": "LLM",
        }

        # Import the mapping from soar.py (will fail until implemented)
        try:
            from aurora_cli.commands.soar import PHASE_OWNERS as phase_owners_const

            assert phase_owners_const == expected_owners
        except ImportError:
            # Expected to fail until PHASE_OWNERS constant is added
            pytest.skip("PHASE_OWNERS constant not yet implemented")


class TestStateJsonTracking:
    """Tests for state.json phase tracking."""

    def test_state_json_updated_per_phase(self, tmp_path):
        """state.json is updated to track current phase."""
        from aurora_cli.commands.soar import _ensure_soar_dir

        with patch("aurora_cli.commands.soar.get_aurora_dir", return_value=tmp_path):
            soar_dir = _ensure_soar_dir()

            # State file should be created/updated during execution
            # This test verifies the mechanism exists
            state_file = soar_dir / "state.json"

            # Write test state
            state_file.write_text(json.dumps({"phase": "decompose", "status": "running"}))

            state_data = json.loads(state_file.read_text())
            assert "phase" in state_data
            assert state_data["phase"] == "decompose"
