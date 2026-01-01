"""Unit tests for semantic score explanations.

Tests the logic for generating human-readable explanations of semantic similarity
scores based on threshold-based relevance levels.
"""

import pytest


def test_explain_semantic_very_high():
    """Very high relevance: semantic score ≥0.9."""
    from aurora_cli.commands.memory import _explain_semantic_score

    semantic_score = 0.95

    explanation = _explain_semantic_score(semantic_score)

    assert "very high conceptual relevance" in explanation.lower()


def test_explain_semantic_high():
    """High relevance: semantic score 0.8-0.89."""
    from aurora_cli.commands.memory import _explain_semantic_score

    semantic_score = 0.85

    explanation = _explain_semantic_score(semantic_score)

    assert "high conceptual relevance" in explanation.lower()
    assert "very high" not in explanation.lower()  # Should not be "very high"


def test_explain_semantic_moderate():
    """Moderate relevance: semantic score 0.7-0.79."""
    from aurora_cli.commands.memory import _explain_semantic_score

    semantic_score = 0.75

    explanation = _explain_semantic_score(semantic_score)

    assert "moderate conceptual relevance" in explanation.lower()


def test_explain_semantic_low():
    """Low relevance: semantic score <0.7."""
    from aurora_cli.commands.memory import _explain_semantic_score

    semantic_score = 0.65

    explanation = _explain_semantic_score(semantic_score)

    assert "low conceptual relevance" in explanation.lower()


def test_explain_semantic_boundary_conditions():
    """Test exact boundary values."""
    from aurora_cli.commands.memory import _explain_semantic_score

    # Boundary at 0.9 - should be "very high"
    assert "very high" in _explain_semantic_score(0.9).lower()

    # Just below 0.9 - should be "high"
    assert "high" in _explain_semantic_score(0.89).lower()
    assert "very high" not in _explain_semantic_score(0.89).lower()

    # Boundary at 0.8 - should be "high"
    assert "high" in _explain_semantic_score(0.8).lower()

    # Just below 0.8 - should be "moderate"
    assert "moderate" in _explain_semantic_score(0.79).lower()

    # Boundary at 0.7 - should be "moderate"
    assert "moderate" in _explain_semantic_score(0.7).lower()

    # Just below 0.7 - should be "low"
    assert "low" in _explain_semantic_score(0.69).lower()
