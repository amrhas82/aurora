"""Tests for filesystem utilities."""

from pathlib import Path

import pytest

from aurora_planning.utils.filesystem import find_project_root, read_markdown_file


class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_finds_project_root_in_current_directory(self, tmp_path: Path):
        """Test finding project root in current directory."""
        aurora_dir = tmp_path / "aurora"
        aurora_dir.mkdir()

        root = find_project_root(tmp_path)
        assert root == tmp_path

    def test_finds_project_root_in_parent_directory(self, tmp_path: Path):
        """Test finding project root in parent directory."""
        aurora_dir = tmp_path / "aurora"
        aurora_dir.mkdir()
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        root = find_project_root(sub_dir)
        assert root == tmp_path

    def test_returns_none_when_no_aurora_directory(self, tmp_path: Path):
        """Test returns None when no aurora directory found."""
        root = find_project_root(tmp_path)
        assert root is None


class TestReadMarkdownFile:
    """Tests for read_markdown_file function."""

    def test_reads_existing_file(self, tmp_path: Path):
        """Test reading an existing markdown file."""
        test_file = tmp_path / "test.md"
        content = "# Test\n\nThis is test content."
        test_file.write_text(content)

        result = read_markdown_file(str(test_file))
        assert result == content

    def test_raises_error_for_nonexistent_file(self, tmp_path: Path):
        """Test raises FileNotFoundError for non-existent file."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError) as exc_info:
            read_markdown_file(str(nonexistent))
        assert "not found" in str(exc_info.value).lower()

    def test_reads_unicode_content(self, tmp_path: Path):
        """Test reading file with unicode content."""
        test_file = tmp_path / "unicode.md"
        content = "# Test\n\nUnicode: 日本語 🎉"
        test_file.write_text(content, encoding="utf-8")

        result = read_markdown_file(str(test_file))
        assert result == content
