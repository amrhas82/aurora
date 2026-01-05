"""Tests for checkpoint flow in Aurora Planning System.

This module tests the checkpoint flow that displays a decomposition
summary and prompts the user for confirmation before generating plan files.

Test Coverage:
- DecompositionSummary model validation
- Summary display formatting with Rich
- Confirmation prompt handling (Y/n/invalid/Ctrl+C)
- Non-interactive mode (--yes flag)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aurora_cli.planning.models import (
    AgentGap,
    Complexity,
    DecompositionSummary,
    FileResolution,
    Subgoal,
)


class TestDecompositionSummaryModel:
    """Test DecompositionSummary model validation."""

    def test_valid_summary(self) -> None:
        """Test valid decomposition summary creation."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Implement authentication",
                description="Add OAuth2 authentication flow",
                recommended_agent="@full-stack-dev",
            ),
            Subgoal(
                id="sg-2",
                title="Add security tests",
                description="Write security tests for auth flow",
                recommended_agent="@qa-test-architect",
            ),
        ]

        gaps = [
            AgentGap(
                subgoal_id="sg-2",
                recommended_agent="@security-expert",
                agent_exists=False,
                fallback="@full-stack-dev",
                suggested_capabilities=["security", "testing"],
            )
        ]

        summary = DecompositionSummary(
            goal="Implement OAuth2 authentication",
            subgoals=subgoals,
            agents_assigned=2,
            agent_gaps=gaps,
            files_resolved=5,
            avg_confidence=0.82,
            complexity=Complexity.MODERATE,
            decomposition_source="soar",
            warnings=["Memory not indexed"],
        )

        assert summary.goal == "Implement OAuth2 authentication"
        assert len(summary.subgoals) == 2
        assert summary.agents_assigned == 2
        assert len(summary.agent_gaps) == 1
        assert summary.files_resolved == 5
        assert summary.avg_confidence == 0.82
        assert summary.complexity == Complexity.MODERATE
        assert summary.decomposition_source == "soar"
        assert len(summary.warnings) == 1

    def test_empty_subgoals_invalid(self) -> None:
        """Test that empty subgoals list is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            DecompositionSummary(
                goal="Test goal",
                subgoals=[],  # Invalid: must have at least 1
                agents_assigned=0,
                agent_gaps=[],
                files_resolved=0,
                avg_confidence=0.0,
                complexity=Complexity.SIMPLE,
                decomposition_source="heuristic",
                warnings=[],
            )

        assert "subgoals" in str(exc_info.value)

    def test_invalid_confidence_score(self) -> None:
        """Test that confidence score must be between 0.0 and 1.0."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test task",
                description="Test description",
                recommended_agent="@full-stack-dev",
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            DecompositionSummary(
                goal="Test goal",
                subgoals=subgoals,
                agents_assigned=1,
                agent_gaps=[],
                files_resolved=1,
                avg_confidence=1.5,  # Invalid: > 1.0
                complexity=Complexity.SIMPLE,
                decomposition_source="heuristic",
                warnings=[],
            )

        assert "avg_confidence" in str(exc_info.value)

    def test_invalid_decomposition_source(self) -> None:
        """Test that decomposition_source must be 'soar' or 'heuristic'."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test task",
                description="Test description",
                recommended_agent="@full-stack-dev",
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            DecompositionSummary(
                goal="Test goal",
                subgoals=subgoals,
                agents_assigned=1,
                agent_gaps=[],
                files_resolved=1,
                avg_confidence=0.8,
                complexity=Complexity.SIMPLE,
                decomposition_source="invalid",  # Invalid: not 'soar' or 'heuristic'
                warnings=[],
            )

        assert "decomposition_source" in str(exc_info.value)

    def test_warnings_defaults_to_empty_list(self) -> None:
        """Test that warnings defaults to empty list."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test task",
                description="Test description for the task",
                recommended_agent="@full-stack-dev",
            )
        ]

        summary = DecompositionSummary(
            goal="Test goal with enough characters",
            subgoals=subgoals,
            agents_assigned=1,
            agent_gaps=[],
            files_resolved=1,
            avg_confidence=0.8,
            complexity=Complexity.SIMPLE,
            decomposition_source="heuristic",
        )

        assert summary.warnings == []


class TestSummaryDisplay:
    """Test summary display formatting."""

    def test_display_method_exists(self) -> None:
        """Test that display method exists on DecompositionSummary."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="Test task",
                description="Test description for the task",
                recommended_agent="@full-stack-dev",
            )
        ]

        summary = DecompositionSummary(
            goal="Test goal with enough characters",
            subgoals=subgoals,
            agents_assigned=1,
            agent_gaps=[],
            files_resolved=1,
            avg_confidence=0.8,
            complexity=Complexity.SIMPLE,
            decomposition_source="heuristic",
            warnings=[],
        )

        # Should have display method
        assert hasattr(summary, "display")
        assert callable(summary.display)


class TestConfirmationPrompt:
    """Test confirmation prompt functionality."""

    def test_prompt_yes_returns_true(self, monkeypatch) -> None:
        """Test that 'Y' input returns True."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return 'Y'
        monkeypatch.setattr("builtins.input", lambda _: "Y")

        result = prompt_for_confirmation()
        assert result is True

    def test_prompt_y_lowercase_returns_true(self, monkeypatch) -> None:
        """Test that 'y' input returns True."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return 'y'
        monkeypatch.setattr("builtins.input", lambda _: "y")

        result = prompt_for_confirmation()
        assert result is True

    def test_prompt_enter_returns_true(self, monkeypatch) -> None:
        """Test that pressing Enter (empty input) returns True."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return empty string
        monkeypatch.setattr("builtins.input", lambda _: "")

        result = prompt_for_confirmation()
        assert result is True

    def test_prompt_no_returns_false(self, monkeypatch) -> None:
        """Test that 'n' input returns False."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return 'n'
        monkeypatch.setattr("builtins.input", lambda _: "n")

        result = prompt_for_confirmation()
        assert result is False

    def test_prompt_N_uppercase_returns_false(self, monkeypatch) -> None:
        """Test that 'N' input returns False."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return 'N'
        monkeypatch.setattr("builtins.input", lambda _: "N")

        result = prompt_for_confirmation()
        assert result is False

    def test_prompt_invalid_then_valid(self, monkeypatch) -> None:
        """Test that invalid input prompts retry."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to return invalid then valid
        inputs = iter(["invalid", "maybe", "Y"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        result = prompt_for_confirmation()
        assert result is True

    def test_prompt_keyboard_interrupt_returns_false(self, monkeypatch) -> None:
        """Test that Ctrl+C (KeyboardInterrupt) returns False gracefully."""
        from aurora_cli.planning.checkpoint import prompt_for_confirmation

        # Mock user input to raise KeyboardInterrupt
        def raise_interrupt(_):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", raise_interrupt)

        result = prompt_for_confirmation()
        assert result is False
