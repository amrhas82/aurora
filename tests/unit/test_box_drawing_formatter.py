"""Unit tests for box-drawing score formatter.

Tests the box-drawing formatter function that displays search results with
scores in a rich box-drawing format.
"""

import sys
from pathlib import Path

import pytest
from rich.text import Text

# Add CLI package to path for import
cli_path = Path(__file__).parent.parent.parent / "packages" / "cli" / "src"
sys.path.insert(0, str(cli_path))

from aurora_cli.commands.memory import _format_score_box


def test_format_box_header():
    """Test box header formatting with file, type, name, and lines.

    Expected format:
    ┌─ auth.py | func | authenticate (Lines 45-67) ─────────┐

    Width should be 78 characters (terminal standard).
    """
    # Mock SearchResult
    class MockResult:
        def __init__(self):
            self.metadata = {
                "file_path": "auth.py",
                "type": "function",
                "name": "authenticate",
                "line_start": 45,
                "line_end": 67,
            }
            self.content = "def authenticate(user, password): pass"
            self.hybrid_score = 0.856
            self.bm25_score = 0.950
            self.semantic_score = 0.820
            self.activation_score = 0.650

    result = MockResult()

    box_text = _format_score_box(result, rank=1, terminal_width=78)

    # Verify box structure
    assert isinstance(box_text, Text)
    box_str = str(box_text)

    # Check for header elements
    assert "┌─" in box_str
    assert "auth.py" in box_str
    assert "func" in box_str
    assert "authenticate" in box_str
    assert "Lines 45-67" in box_str
    assert "─┐" in box_str


def test_format_box_scores():
    """Test score lines formatting with proper prefixes and precision.

    Expected format:
    │   ├─ BM25:       0.950 ...
    │   ├─ Semantic:   0.820 ...
    │   └─ Activation: 0.650 ...

    Scores should have 3 decimal places precision.
    """
    class MockResult:
        def __init__(self):
            self.metadata = {"name": "test_func", "file_path": "test.py", "type": "function"}
            self.content = "def test_func(): pass"
            self.hybrid_score = 0.856
            self.bm25_score = 0.950
            self.semantic_score = 0.820
            self.activation_score = 0.650

    result = MockResult()

    box_text = _format_score_box(result, rank=1)
    box_str = str(box_text)

    # Verify score lines
    assert "├─ BM25:" in box_str
    assert "├─ Semantic:" in box_str
    assert "└─ Activation:" in box_str

    # Verify precision (3 decimal places)
    assert "0.950" in box_str
    assert "0.820" in box_str
    assert "0.650" in box_str


def test_format_box_footer():
    """Test box footer formatting.

    Expected format:
    └──────────────────────────────────────────────────────┘

    Width should match header width.
    """
    class MockResult:
        def __init__(self):
            self.metadata = {"name": "test", "file_path": "test.py", "type": "function"}
            self.content = "def test(): pass"
            self.hybrid_score = 0.5
            self.bm25_score = 0.5
            self.semantic_score = 0.5
            self.activation_score = 0.5

    result = MockResult()

    box_text = _format_score_box(result, rank=1, terminal_width=78)
    box_str = str(box_text)

    # Verify footer
    assert "└" in box_str
    assert "─" in box_str
    assert "┘" in box_str

    # Check that footer is at the end
    lines = box_str.strip().split("\n")
    last_line = lines[-1]
    assert last_line.startswith("└")
    assert last_line.endswith("┘")


def test_format_box_git_metadata():
    """Test git metadata line formatting.

    Expected format:
    │ Git: 23 commits, last modified 2 days ago │
    """
    class MockResult:
        def __init__(self):
            self.metadata = {
                "name": "test_func",
                "file_path": "test.py",
                "type": "function",
                "commit_count": 23,
                "last_modified": "2 days ago",
            }
            self.content = "def test_func(): pass"
            self.hybrid_score = 0.5
            self.bm25_score = 0.5
            self.semantic_score = 0.5
            self.activation_score = 0.5

    result = MockResult()

    box_text = _format_score_box(result, rank=1)
    box_str = str(box_text)

    # Verify git metadata
    assert "Git:" in box_str
    assert "23 commits" in box_str
    assert "2 days ago" in box_str


def test_format_box_width_adjustment():
    """Test that long names truncate to fit width.

    Long names should truncate without breaking box structure.
    """
    class MockResult:
        def __init__(self):
            self.metadata = {
                "name": "VeryLongFunctionNameThatExceedsDisplayWidth",
                "file_path": "extremely_long_file_path_that_should_be_truncated.py",
                "type": "function",
            }
            self.content = "def VeryLongFunctionNameThatExceedsDisplayWidth(): pass"
            self.hybrid_score = 0.5
            self.bm25_score = 0.5
            self.semantic_score = 0.5
            self.activation_score = 0.5

    result = MockResult()

    box_text = _format_score_box(result, rank=1, terminal_width=78)
    box_str = str(box_text)

    # Verify truncation indicators
    assert "..." in box_str or "VeryLong" in box_str

    # Verify all lines are roughly the same width (within 2 chars due to box drawing)
    lines = box_str.strip().split("\n")
    widths = [len(line.rstrip()) for line in lines]

    # All lines should be close to terminal width (78)
    for width in widths:
        assert 70 <= width <= 80, f"Line width {width} not near terminal width 78"


def test_format_box_empty_git_metadata():
    """Test handling of missing git metadata.

    When git metadata is unavailable, line should be omitted or show dashes.
    """
    class MockResult:
        def __init__(self):
            self.metadata = {
                "name": "test_func",
                "file_path": "test.py",
                "type": "function",
                # No commit_count or last_modified
            }
            self.content = "def test_func(): pass"
            self.hybrid_score = 0.5
            self.bm25_score = 0.5
            self.semantic_score = 0.5
            self.activation_score = 0.5

    result = MockResult()

    box_text = _format_score_box(result, rank=1)
    box_str = str(box_text)

    # Git line should be omitted when no metadata available
    # (implementation omits it rather than showing placeholder)
    # Just verify the box is still valid
    assert "┌" in box_str
    assert "└" in box_str
    assert "Final Score:" in box_str


def test_format_box_returns_rich_text():
    """Test that function returns Rich Text object.

    Function should return Rich Text object for proper styling.
    """
    class MockResult:
        def __init__(self):
            self.metadata = {"name": "test", "file_path": "test.py", "type": "function"}
            self.content = "def test(): pass"
            self.hybrid_score = 0.5
            self.bm25_score = 0.5
            self.semantic_score = 0.5
            self.activation_score = 0.5

    result = MockResult()

    box_text = _format_score_box(result, rank=1)

    # Verify it's a Rich Text object
    assert isinstance(box_text, Text)

    # Verify it has content
    assert len(str(box_text)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
