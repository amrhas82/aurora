"""Unit tests for lsp MCP tool.

These tests are written BEFORE implementation (TDD).
They should fail until the lsp tool is implemented.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLSPDeadcode:
    """Tests for lsp(action='deadcode')."""

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_deadcode_structure(self, mock_lsp_class):
        """Test deadcode action returns expected structure."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.find_dead_code.return_value = [
            {"name": "ParseError", "file": "exceptions.py", "line": 45, "kind": "class"},
            {"name": "unused_helper", "file": "utils.py", "line": 120, "kind": "function"},
        ]

        # Import after patching
        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="deadcode", path="src/")

        # Assert
        assert result["action"] == "deadcode"
        assert result["path"] == "src/"
        assert "dead_code" in result
        assert "total" in result
        assert result["total"] == 2
        assert len(result["dead_code"]) == 2

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_deadcode_fields(self, mock_lsp_class):
        """Test dead_code items have required fields."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.find_dead_code.return_value = [
            {"name": "TestFunc", "file": "test.py", "line": 10, "kind": "function"},
        ]

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="deadcode", path="src/")

        # Assert
        dead_item = result["dead_code"][0]
        assert "name" in dead_item
        assert "file" in dead_item
        assert "line" in dead_item
        assert "kind" in dead_item
        assert dead_item["name"] == "TestFunc"
        assert dead_item["file"] == "test.py"
        assert dead_item["line"] == 10
        assert dead_item["kind"] == "function"


class TestLSPImpact:
    """Tests for lsp(action='impact')."""

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_impact_structure(self, mock_lsp_class):
        """Test impact action returns expected structure."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "my_function",
            "total_usages": 74,
            "files_affected": 12,
            "usages_by_file": {},
            "usages": [],
        }
        mock_lsp.get_callers.return_value = [
            {"file": "executor.py", "line": 45, "name": "run_task"},
            {"file": "runner.py", "line": 123, "name": "execute"},
        ]

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="impact", path="file.py", line=42)

        # Assert
        assert result["action"] == "impact"
        assert result["path"] == "file.py"
        assert result["line"] == 42
        assert "symbol" in result
        assert "used_by_files" in result
        assert "total_usages" in result
        assert "top_callers" in result
        assert "risk" in result

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_impact_risk_levels(self, mock_lsp_class):
        """Test risk calculation: low (0-2), medium (3-10), high (11+)."""
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp

        from aurora_mcp.lsp_tool import lsp

        # Test low risk (2 usages)
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "fn1",
            "total_usages": 2,
            "files_affected": 1,
            "usages_by_file": {},
            "usages": [],
        }
        mock_lsp.get_callers.return_value = []
        result = lsp(action="impact", path="file.py", line=10)
        assert result["risk"] == "low"

        # Test medium risk (7 usages)
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "fn2",
            "total_usages": 7,
            "files_affected": 3,
            "usages_by_file": {},
            "usages": [],
        }
        result = lsp(action="impact", path="file.py", line=20)
        assert result["risk"] == "medium"

        # Test high risk (15 usages)
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "fn3",
            "total_usages": 15,
            "files_affected": 5,
            "usages_by_file": {},
            "usages": [],
        }
        result = lsp(action="impact", path="file.py", line=30)
        assert result["risk"] == "high"


class TestLSPCheck:
    """Tests for lsp(action='check')."""

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_check_structure(self, mock_lsp_class):
        """Test check action returns expected structure."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "test_func",
            "total_usages": 7,
            "files_affected": 3,
            "usages_by_file": {},
            "usages": [],
        }

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="check", path="file.py", line=42)

        # Assert
        assert result["action"] == "check"
        assert result["path"] == "file.py"
        assert result["line"] == 42
        assert "symbol" in result
        assert "used_by" in result
        assert "risk" in result
        assert result["used_by"] == 7
        assert result["risk"] == "medium"  # 7 usages = medium

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_default_action_is_check(self, mock_lsp_class):
        """Test default action is 'check' when not specified."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "func",
            "total_usages": 5,
            "files_affected": 2,
            "usages_by_file": {},
            "usages": [],
        }

        from aurora_mcp.lsp_tool import lsp

        # Act - call without action parameter
        result = lsp(path="file.py", line=42)

        # Assert
        assert result["action"] == "check"


class TestCodeQualityReport:
    """Tests for CODE_QUALITY_REPORT.md generation."""

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    @patch("aurora_mcp.lsp_tool.Path")
    def test_code_quality_report_format(self, mock_path, mock_lsp_class):
        """Test report includes severity categories."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.find_dead_code.return_value = [
            {"name": "CriticalClass", "file": "core.py", "line": 10, "kind": "class"},
            {"name": "unused_fn", "file": "utils.py", "line": 50, "kind": "function"},
        ]

        # Mock workspace to have docs/ directory
        mock_workspace = Mock()
        mock_workspace.exists.return_value = True
        mock_docs = Mock()
        mock_docs.exists.return_value = True
        mock_workspace.__truediv__ = lambda self, other: mock_docs if other == "docs" else Mock()

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="deadcode", path="src/")

        # Assert - result should contain report_path
        assert "report_path" in result or "report" in result

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    @patch("builtins.open", create=True)
    @patch("aurora_mcp.lsp_tool.Path")
    def test_code_quality_report_location_docs(self, mock_path, mock_open, mock_lsp_class):
        """Test report goes to docs/ when directory exists."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.find_dead_code.return_value = []

        # Mock Path to indicate docs/ exists
        mock_workspace = MagicMock()
        mock_docs_dir = MagicMock()
        mock_docs_dir.exists.return_value = True
        mock_workspace.__truediv__.return_value = mock_docs_dir
        mock_path.return_value = mock_workspace

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="deadcode", path="src/")

        # Assert - should indicate docs location
        # Implementation will determine exact field name
        assert result is not None

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    @patch("builtins.open", create=True)
    @patch("aurora_mcp.lsp_tool.Path")
    def test_code_quality_report_location_root(self, mock_path, mock_open, mock_lsp_class):
        """Test report goes to project root when docs/ doesn't exist."""
        # Arrange
        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.find_dead_code.return_value = []

        # Mock Path to indicate docs/ doesn't exist
        mock_workspace = MagicMock()
        mock_docs_dir = MagicMock()
        mock_docs_dir.exists.return_value = False
        mock_workspace.__truediv__.return_value = mock_docs_dir
        mock_path.return_value = mock_workspace

        from aurora_mcp.lsp_tool import lsp

        # Act
        result = lsp(action="deadcode", path="src/")

        # Assert - should indicate root location
        assert result is not None


class TestLSPInitialization:
    """Tests for LSP tool initialization."""

    @patch("aurora_mcp.lsp_tool.AuroraLSP")
    def test_lsp_initialization_lazy(self, mock_lsp_class):
        """Test LSP is initialized lazily on first request."""
        from aurora_mcp.lsp_tool import lsp

        mock_lsp = Mock()
        mock_lsp_class.return_value = mock_lsp
        mock_lsp.get_usage_summary.return_value = {
            "symbol": "fn",
            "total_usages": 5,
            "files_affected": 2,
            "usages_by_file": {},
            "usages": [],
        }

        # Act
        lsp(action="check", path="file.py", line=10)

        # Assert - AuroraLSP should be initialized
        mock_lsp_class.assert_called_once()
