"""Unit tests for mem_search MCP tool.

These tests are written BEFORE implementation (TDD).
They should fail until the mem_search tool is implemented.
"""

import pytest
from unittest.mock import Mock, patch


class TestMemSearch:
    """Tests for mem_search MCP tool."""

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_basic(self, mock_lsp_class, mock_store_class):
        """Test mem_search returns search results."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "orchestrator.py",
                "type": "code",
                "symbol": "SOAROrchestrator",
                "lines": "68-2447",
                "score": 0.564,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 74,
            "files_affected": 12,
        }

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="SOAR")

        # Assert
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["file"] == "orchestrator.py"

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_result_fields(self, mock_lsp_class, mock_store_class):
        """Test results contain required fields."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "test.py",
                "type": "code",
                "symbol": "TestClass",
                "lines": "10-50",
                "score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 5,
            "files_affected": 2,
        }

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="test")

        # Assert
        result = results[0]
        assert "file" in result
        assert "type" in result
        assert "symbol" in result
        assert "lines" in result
        assert "score" in result
        assert "used_by" in result
        assert "called_by" in result
        assert "calling" in result
        assert "git" in result

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_used_by_format_code(self, mock_lsp_class, mock_store_class):
        """Test used_by format is 'N files(M)' for code results."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "code.py",
                "type": "code",
                "symbol": "MyFunc",
                "lines": "1-10",
                "score": 0.9,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 74,
            "files_affected": 12,
        }

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="func")

        # Assert
        assert results[0]["used_by"] == "12 files(74)"

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_used_by_format_kb(self, mock_lsp_class, mock_store_class):
        """Test used_by is '-' for non-code (kb) results."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "KNOWLEDGE_BASE.md",
                "type": "kb",
                "symbol": "Entry Points",
                "lines": "1-8",
                "score": 0.7,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="entry")

        # Assert
        assert results[0]["used_by"] == "-"

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_called_by_list(self, mock_lsp_class, mock_store_class):
        """Test called_by returns list of caller functions."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "code.py",
                "type": "code",
                "symbol": "helper",
                "lines": "10-20",
                "score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 5,
            "files_affected": 2,
        }
        mock_lsp.get_callers.return_value = [
            {"name": "main_func", "file": "main.py", "line": 50},
            {"name": "process", "file": "worker.py", "line": 100},
        ]

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="helper")

        # Assert
        called_by = results[0]["called_by"]
        assert isinstance(called_by, list)
        assert len(called_by) == 2
        assert "main_func" in called_by
        assert "process" in called_by

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_calling_list(self, mock_lsp_class, mock_store_class):
        """Test calling returns list of called functions (where supported)."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "code.py",
                "type": "code",
                "symbol": "process_data",
                "lines": "10-30",
                "score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 3,
            "files_affected": 1,
        }
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = [
            {"name": "validate", "file": "validators.py", "line": 10},
            {"name": "save", "file": "storage.py", "line": 50},
        ]

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="process")

        # Assert
        calling = results[0]["calling"]
        assert isinstance(calling, list)
        assert len(calling) == 2
        assert "validate" in calling
        assert "save" in calling

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_limit_default(self, mock_lsp_class, mock_store_class):
        """Test limit parameter defaults to 5."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [{"file": f"file{i}.py", "type": "code", "symbol": f"sym{i}", "lines": "1-10", "score": 0.5} for i in range(10)]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {"total_usages": 0, "files_affected": 0}
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = []

        from aurora_mcp.mem_search_tool import mem_search

        # Act - call without limit parameter
        results = mem_search(query="test")

        # Assert - should return max 5 results
        assert len(results) <= 5

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_git_info(self, mock_lsp_class, mock_store_class):
        """Test git info included in results."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = [
            {
                "file": "test.py",
                "type": "code",
                "symbol": "TestClass",
                "lines": "1-10",
                "score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {"total_usages": 5, "files_affected": 2}

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="test")

        # Assert
        git_info = results[0]["git"]
        assert isinstance(git_info, str)
        # Format should be like "N commits, Xh/Xd ago" or "-"


class TestMemSearchInitialization:
    """Tests for mem_search initialization."""

    @patch("aurora_mcp.mem_search_tool.MemoryStore")
    @patch("aurora_mcp.mem_search_tool.AuroraLSP")
    def test_mem_search_initialization(self, mock_lsp_class, mock_store_class):
        """Test mem_search initializes correctly."""
        # Arrange
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.search.return_value = []

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        mem_search(query="test")

        # Assert - both store and LSP should be initialized
        mock_store_class.assert_called_once()
        # LSP might not be called if no code results
