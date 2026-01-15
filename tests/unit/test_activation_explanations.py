"""Unit tests for activation score explanations.

Tests the logic for generating human-readable explanations of activation scores
including access count, commit count, and recency information.
"""

from datetime import datetime, timedelta


def test_explain_activation_full_metadata():
    """Full metadata: access count, commit count, and recency all present."""
    from aurora_cli.commands.memory import _explain_activation_score

    # Create timestamp for "2 days ago"
    two_days_ago = (datetime.now() - timedelta(days=2)).timestamp()

    metadata = {"access_count": 5, "commit_count": 23, "last_modified": two_days_ago}
    activation_score = 0.85

    explanation = _explain_activation_score(metadata, activation_score)

    assert "accessed 5x" in explanation.lower()
    assert "23 commit" in explanation.lower()
    assert "last used" in explanation.lower() or "ago" in explanation.lower()


def test_explain_activation_no_git():
    """No git metadata: only access count and recency."""
    from aurora_cli.commands.memory import _explain_activation_score

    one_week_ago = (datetime.now() - timedelta(weeks=1)).timestamp()

    metadata = {"access_count": 3, "commit_count": None, "last_modified": one_week_ago}
    activation_score = 0.65

    explanation = _explain_activation_score(metadata, activation_score)

    assert "accessed 3x" in explanation.lower()
    assert "commit" not in explanation.lower()  # Should not mention commits
    assert "last used" in explanation.lower() or "ago" in explanation.lower()


def test_explain_activation_no_recency():
    """No recency: only access count and commit count."""
    from aurora_cli.commands.memory import _explain_activation_score

    metadata = {"access_count": 2, "commit_count": 10, "last_modified": None}
    activation_score = 0.55

    explanation = _explain_activation_score(metadata, activation_score)

    assert "accessed 2x" in explanation.lower()
    assert "10 commit" in explanation.lower()
    assert "last used" not in explanation.lower()  # No recency info


def test_explain_activation_minimal():
    """Minimal metadata: only access count."""
    from aurora_cli.commands.memory import _explain_activation_score

    metadata = {"access_count": 1, "commit_count": None, "last_modified": None}
    activation_score = 0.45

    explanation = _explain_activation_score(metadata, activation_score)

    assert "accessed 1x" in explanation.lower()
    assert "commit" not in explanation.lower()
    assert "last used" not in explanation.lower()


def test_explain_activation_plural_handling():
    """Test proper pluralization for commit count."""
    from aurora_cli.commands.memory import _explain_activation_score

    # Single commit - should be "1 commit"
    metadata_single = {"access_count": 1, "commit_count": 1, "last_modified": None}

    explanation_single = _explain_activation_score(metadata_single, 0.5)
    assert "1 commit" in explanation_single.lower()
    assert "1 commits" not in explanation_single.lower()  # Not plural

    # Multiple commits - should be "2 commits"
    metadata_multiple = {"access_count": 2, "commit_count": 2, "last_modified": None}

    explanation_multiple = _explain_activation_score(metadata_multiple, 0.5)
    assert "2 commits" in explanation_multiple.lower()
