"""Unit tests for mem_search MCP tool.

These tests are written BEFORE implementation (TDD).
They should fail until the mem_search tool is implemented.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestMemSearch:
    """Tests for mem_search MCP tool."""

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_basic(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test mem_search returns search results."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "orchestrator.py",
                    "type": "code",
                    "name": "SOAROrchestrator",
                    "lines": "68-2447",
                },
                "hybrid_score": 0.564,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 74,
            "files_affected": 12,
        }
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = []

        # Mock git info
        mock_git_info.return_value = "41 commits, 11h ago"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="SOAR")

        # Assert
        assert isinstance(results, list)
        assert len(results) > 0
        assert results[0]["file"] == "orchestrator.py"

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_result_fields(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test results contain required fields."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "test.py",
                    "type": "code",
                    "name": "TestClass",
                    "lines": "10-50",
                },
                "hybrid_score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 5,
            "files_affected": 2,
        }
        mock_lsp.get_callers.return_value = [{"name": "caller1"}]
        mock_lsp.get_callees.return_value = [{"name": "callee1"}]

        mock_git_info.return_value = "10 commits, 2d ago"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

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

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    def test_mem_search_used_by_format_code(self, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test used_by format is 'N files(M)' for code results."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "code.py",
                    "type": "code",
                    "name": "MyFunc",
                    "lines": "1-10",
                },
                "hybrid_score": 0.9,
            }
        ]

        mock_lsp = Mock()
        mock_get_lsp.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 74,
            "files_affected": 12,
        }
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = []

        mock_git_info.return_value = "5 commits"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="func")

        # Assert
        assert results[0]["used_by"] == "12 files(74)"

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_used_by_format_kb(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test used_by is '-' for non-code (kb) results."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "KNOWLEDGE_BASE.md",
                    "type": "kb",
                    "name": "Entry Points",
                    "lines": "1-8",
                },
                "hybrid_score": 0.7,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp

        mock_git_info.return_value = "-"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="entry")

        # Assert
        assert results[0]["used_by"] == "-"

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_called_by_list(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test called_by returns list of caller functions."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "code.py",
                    "type": "code",
                    "name": "helper",
                    "lines": "10-20",
                },
                "hybrid_score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_get_lsp.return_value = mock_lsp
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "total_usages": 5,
            "files_affected": 2,
        }
        mock_lsp.get_callers.return_value = [
            {"name": "main_func", "file": "main.py", "line": 50},
            {"name": "process", "file": "worker.py", "line": 100},
        ]
        mock_lsp.get_callees.return_value = []

        mock_git_info.return_value = "3 commits"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="helper")

        # Assert
        called_by = results[0]["called_by"]
        assert isinstance(called_by, list)
        assert len(called_by) == 2
        assert "main_func" in called_by
        assert "process" in called_by

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_calling_list(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test calling returns list of called functions (where supported)."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "code.py",
                    "type": "code",
                    "name": "process_data",
                    "lines": "10-30",
                },
                "hybrid_score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_get_lsp.return_value = mock_lsp
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

        mock_git_info.return_value = "8 commits"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="process")

        # Assert
        calling = results[0]["calling"]
        assert isinstance(calling, list)
        assert len(calling) == 2
        assert "validate" in calling
        assert "save" in calling

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_limit_default(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test limit parameter defaults to 5."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {"file": f"file{i}.py", "type": "code", "name": f"sym{i}", "lines": "1-10"},
                "hybrid_score": 0.5,
            }
            for i in range(10)
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {"total_usages": 0, "files_affected": 0}
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = []

        mock_git_info.return_value = "-"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act - call without limit parameter
        results = mem_search(query="test")

        # Assert - should return max 5 results
        assert len(results) <= 5

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_git_info(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test git info included in results."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = [
            {
                "metadata": {
                    "file": "test.py",
                    "type": "code",
                    "name": "TestClass",
                    "lines": "1-10",
                },
                "hybrid_score": 0.8,
            }
        ]

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {"total_usages": 5, "files_affected": 2}
        mock_lsp.get_callers.return_value = []
        mock_lsp.get_callees.return_value = []

        mock_git_info.return_value = "23 commits, 2d ago"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        results = mem_search(query="test")

        # Assert
        git_info = results[0]["git"]
        assert isinstance(git_info, str)
        assert git_info == "23 commits, 2d ago"


class TestMemSearchInitialization:
    """Tests for mem_search initialization."""

    @patch("aurora_mcp.mem_search_tool._get_git_info")
    @patch("aurora_mcp.mem_search_tool._get_lsp")
    @patch("aurora_mcp.mem_search_tool.Path")
    @patch("aurora_cli.memory.retrieval.MemoryRetriever")
    @patch("aurora_lsp.facade.AuroraLSP")
    def test_mem_search_initialization(self, mock_lsp_class, mock_retriever_class, mock_path_class, mock_get_lsp, mock_git_info):
        """Test mem_search initializes correctly."""
        # Reset globals
        import aurora_mcp.mem_search_tool as mem_search_module
        mem_search_module._store = None
        mem_search_module._retriever = None
        mem_search_module._lsp_instance = None

        # Arrange
        mock_retriever = Mock()
        mock_retriever_class.return_value = mock_retriever
        mock_retriever.retrieve.return_value = []

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp

        mock_git_info.return_value = "-"

        # Mock Path
        mock_workspace = MagicMock()
        mock_db = MagicMock()
        mock_db.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_db
        mock_path_class.cwd.return_value = mock_workspace

        from aurora_mcp.mem_search_tool import mem_search

        # Act
        mem_search(query="test")

        # Assert - retriever should be initialized
        mock_retriever_class.assert_called_once()
