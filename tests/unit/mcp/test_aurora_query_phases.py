"""
Unit tests for aurora_query phase parameter and multi-turn SOAR orchestration.

Tests TDD approach for refactoring aurora_query to support phase-based execution.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from aurora_mcp.tools import AuroraMCPTools


@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test_memory.db"
    return str(db_path)


@pytest.fixture
def tools_instance(mock_db_path):
    """Create AuroraMCPTools instance with mocked components."""
    with patch("aurora_mcp.tools.SQLiteStore"), \
         patch("aurora_mcp.tools.ActivationEngine"), \
         patch("aurora_mcp.tools.EmbeddingProvider"), \
         patch("aurora_mcp.tools.HybridRetriever"), \
         patch("aurora_mcp.tools.MemoryManager"), \
         patch("aurora_mcp.tools.get_global_registry"):
        tools = AuroraMCPTools(db_path=mock_db_path, config_path=None)
        yield tools


class TestPhaseParameterValidation:
    """Test phase parameter validation in aurora_query."""

    def test_invalid_phase_name_returns_error(self, tools_instance):
        """Test that invalid phase names return error JSON."""
        result = tools_instance.aurora_query(
            query="test query",
            phase="invalid_phase"  # Invalid phase name
        )

        data = json.loads(result)
        assert "error" in data
        assert data["error"]["type"] == "InvalidParameter"
        assert "invalid_phase" in data["error"]["message"].lower()

    def test_missing_phase_defaults_to_assess(self, tools_instance):
        """Test that missing phase parameter defaults to 'assess'."""
        with patch.object(tools_instance, "_handle_assess_phase") as mock_assess:
            mock_assess.return_value = {
                "phase": "assess",
                "progress": "1/9 assess",
                "status": "complete",
                "result": {"complexity": "SIMPLE"},
                "next_action": "Retrieve and respond",
                "metadata": {"duration_ms": 10}
            }

            result = tools_instance.aurora_query(query="test query")

            # Should call assess phase handler
            mock_assess.assert_called_once()

    def test_valid_phase_names_accepted(self, tools_instance):
        """Test that all valid phase names are accepted."""
        valid_phases = [
            "assess", "retrieve", "decompose", "verify",
            "route", "collect", "synthesize", "record", "respond"
        ]

        for phase in valid_phases:
            # Mock the specific phase handler
            handler_name = f"_handle_{phase}_phase"
            with patch.object(tools_instance, handler_name) as mock_handler:
                mock_handler.return_value = {
                    "phase": phase,
                    "progress": f"1/9 {phase}",
                    "status": "complete",
                    "result": {},
                    "next_action": "Continue",
                    "metadata": {"duration_ms": 10}
                }

                result = tools_instance.aurora_query(query="test", phase=phase)
                data = json.loads(result)

                # Should not have error
                assert "error" not in data
                assert data["phase"] == phase


class TestPhaseResponseSchema:
    """Test that phase responses conform to required schema."""

    @pytest.mark.parametrize("phase", [
        "assess", "retrieve", "decompose", "verify",
        "route", "collect", "synthesize", "record", "respond"
    ])
    def test_phase_response_has_required_fields(self, tools_instance, phase):
        """Test that each phase response has all required fields."""
        handler_name = f"_handle_{phase}_phase"

        with patch.object(tools_instance, handler_name) as mock_handler:
            mock_handler.return_value = {
                "phase": phase,
                "progress": f"1/9 {phase}",
                "status": "complete",
                "result": {"test": "data"},
                "next_action": "Do something",
                "metadata": {"duration_ms": 50}
            }

            result = tools_instance.aurora_query(query="test", phase=phase)
            data = json.loads(result)

            # Verify all required fields present
            assert "phase" in data
            assert "progress" in data
            assert "status" in data
            assert "result" in data
            assert "next_action" in data
            assert "metadata" in data

            # Verify field types
            assert isinstance(data["phase"], str)
            assert isinstance(data["progress"], str)
            assert isinstance(data["status"], str)
            assert isinstance(data["result"], dict)
            assert isinstance(data["next_action"], str)
            assert isinstance(data["metadata"], dict)

    def test_progress_field_format(self, tools_instance):
        """Test progress field follows 'N/9 phase_name' format."""
        with patch.object(tools_instance, "_handle_assess_phase") as mock_assess:
            mock_assess.return_value = {
                "phase": "assess",
                "progress": "1/9 assess",
                "status": "complete",
                "result": {},
                "next_action": "Continue",
                "metadata": {"duration_ms": 10}
            }

            result = tools_instance.aurora_query(query="test", phase="assess")
            data = json.loads(result)

            # Progress should be in format "N/9 phase_name"
            assert "/" in data["progress"]
            assert "9" in data["progress"]
            assert data["phase"] in data["progress"]

    def test_status_field_values(self, tools_instance):
        """Test status field is either 'complete' or 'error'."""
        valid_statuses = ["complete", "error"]

        with patch.object(tools_instance, "_handle_assess_phase") as mock_assess:
            for status in valid_statuses:
                mock_assess.return_value = {
                    "phase": "assess",
                    "progress": "1/9 assess",
                    "status": status,
                    "result": {},
                    "next_action": "Continue",
                    "metadata": {"duration_ms": 10}
                }

                result = tools_instance.aurora_query(query="test", phase="assess")
                data = json.loads(result)

                assert data["status"] in valid_statuses

    def test_metadata_contains_duration(self, tools_instance):
        """Test metadata field contains duration_ms."""
        with patch.object(tools_instance, "_handle_assess_phase") as mock_assess:
            mock_assess.return_value = {
                "phase": "assess",
                "progress": "1/9 assess",
                "status": "complete",
                "result": {},
                "next_action": "Continue",
                "metadata": {"duration_ms": 45}
            }

            result = tools_instance.aurora_query(query="test", phase="assess")
            data = json.loads(result)

            assert "duration_ms" in data["metadata"]
            assert isinstance(data["metadata"]["duration_ms"], (int, float))
