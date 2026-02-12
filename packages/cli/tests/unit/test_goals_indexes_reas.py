"""Tests for goals command indexing output as 'reas' type.

Verifies that successful goal creation triggers indexing of the goals.json
file with type='reas' (reasoning traces).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from aurora_core.chunk_types import get_chunk_type


class TestGoalsIndexesAsReas:
    """Tests for goals output indexing with 'reas' type."""

    def test_goals_context_returns_reas_type(self):
        """goals_output context should return 'reas' type."""
        chunk_type = get_chunk_type(context="goals_output")
        assert chunk_type == "reas"

    def test_goals_context_overrides_json_extension(self):
        """goals_output context should override .json extension type."""
        # .json would normally default to 'code'
        without_context = get_chunk_type(file_path="goals.json")
        with_context = get_chunk_type(file_path="goals.json", context="goals_output")

        assert without_context == "code"  # Default for unknown extension
        assert with_context == "reas"  # Context overrides

    def test_index_goals_result_called_on_success(self):
        """_index_goals_result should be called when goals succeeds."""
        from aurora_cli.commands.goals import _index_goals_result

        # Mock store
        mock_store = MagicMock()
        mock_store.save_chunk = MagicMock()

        # Mock config with store
        mock_config = MagicMock()

        # Create temp goals file
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            goals_file = Path(tmpdir) / "goals.json"
            goals_data = {
                "plan_id": "test-plan",
                "goal": "Test goal",
                "subgoals": [{"title": "Subgoal 1", "assigned_agent": "test"}],
            }
            goals_file.write_text(json.dumps(goals_data))

            # Mock embedding provider
            with patch("aurora_context_code.semantic.EmbeddingProvider") as mock_embed:
                mock_provider = MagicMock()
                mock_provider.embed_chunk.return_value = b"\x00" * 384
                mock_embed.return_value = mock_provider

                # Call the indexing function
                _index_goals_result(goals_file, mock_store)

            # Verify chunks were saved
            assert mock_store.save_chunk.called, "Should have saved chunks"

            # Check saved chunks have 'reas' type
            for call in mock_store.save_chunk.call_args_list:
                chunk = call[0][0]
                assert chunk.type == "reas", f"Chunk should have type 'reas', got '{chunk.type}'"

    def test_index_goals_handles_missing_file(self):
        """_index_goals_result should handle missing file gracefully."""
        from aurora_cli.commands.goals import _index_goals_result

        mock_store = MagicMock()

        # Should not raise, just log warning
        _index_goals_result(Path("/nonexistent/goals.json"), mock_store)

        # Store should not be called
        assert not mock_store.save_chunk.called
