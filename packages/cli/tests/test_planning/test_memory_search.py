"""Tests for memory search integration in goal decomposition.

Tests memory search functionality for finding relevant context files
based on goal keywords, with relevance scoring and filtering.
"""

from unittest.mock import Mock, patch

from aurora_cli.planning.memory import search_memory_for_goal


class TestMemorySearchForGoal:
    """Tests for search_memory_for_goal function."""

    def test_searches_with_goal_keywords(self):
        """Test searches for relevant files based on goal keywords."""
        # Arrange
        goal = "Implement OAuth2 authentication with JWT tokens"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        # HybridRetriever returns dicts
        mock_chunk = {
            "file_path": "src/auth/oauth.py",
            "line_start": 1,
            "line_end": 50,
            "final_score": 0.85,
        }
        mock_retriever.retrieve.return_value = [mock_chunk]

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert len(results) > 0
        assert results[0][0] == "src/auth/oauth.py"  # file path
        assert results[0][1] == 0.85  # relevance score
        mock_retriever.retrieve.assert_called_once()

    def test_returns_relevance_scores(self):
        """Test returns relevance scores between 0.0 and 1.0."""
        # Arrange
        goal = "Add caching layer"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_chunks = [
            {
                "file_path": "src/cache/redis.py",
                "line_start": 1,
                "line_end": 100,
                "final_score": 0.92,
            },
            {
                "file_path": "src/cache/memory.py",
                "line_start": 1,
                "line_end": 50,
                "final_score": 0.78,
            },
        ]
        mock_retriever.retrieve.return_value = mock_chunks

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert len(results) == 2
        assert all(0.0 <= score <= 1.0 for _, score in results)
        assert results[0][1] >= results[1][1]  # Sorted by score descending

    def test_handles_no_results_gracefully(self):
        """Test handles no results gracefully."""
        # Arrange
        goal = "Implement feature that doesn't exist in codebase"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_retriever.retrieve.return_value = []

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert results == []

    def test_limits_results_to_top_n(self):
        """Test includes only top N results."""
        # Arrange
        goal = "Add user authentication"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        # Create 15 mock chunks as dicts
        mock_chunks = [
            {
                "file_path": f"src/file_{i}.py",
                "line_start": 1,
                "line_end": 50,
                "final_score": 0.9 - (i * 0.05),  # Decreasing scores
            }
            for i in range(15)
        ]
        mock_retriever.retrieve.return_value = mock_chunks

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert len(results) == 10  # Limited to 10
        assert all(score >= 0.45 for _, score in results)  # Top 10 scores

    def test_excludes_low_relevance_results(self):
        """Test excludes low-relevance results below threshold."""
        # Arrange
        goal = "Add metrics dashboard"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_chunks = [
            {
                "file_path": "src/metrics/dashboard.py",
                "line_start": 1,
                "line_end": 100,
                "final_score": 0.85,
            },
            {
                "file_path": "src/metrics/collector.py",
                "line_start": 1,
                "line_end": 50,
                "final_score": 0.65,
            },
            {
                "file_path": "src/unrelated.py",
                "line_start": 1,
                "line_end": 10,
                "final_score": 0.25,  # Below threshold
            },
        ]
        mock_retriever.retrieve.return_value = mock_chunks

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10, threshold=0.3)

        # Assert
        assert len(results) == 2  # Only 2 above threshold
        assert all(score >= 0.3 for _, score in results)

    def test_handles_memory_not_indexed(self):
        """Test handles memory not indexed gracefully."""
        # Arrange
        goal = "Add new feature"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = False

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert results == []
        mock_retriever.retrieve.assert_not_called()

    def test_handles_retrieval_errors(self):
        """Test handles retrieval errors gracefully."""
        # Arrange
        goal = "Add feature"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_retriever.retrieve.side_effect = Exception("Database error")

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert results == []  # Graceful degradation

    def test_deduplicates_by_file_path(self):
        """Test deduplicates results from same file path."""
        # Arrange
        goal = "Add user authentication"
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_chunks = [
            {
                "file_path": "src/auth.py",
                "line_start": 1,
                "line_end": 50,
                "final_score": 0.85,
            },
            {
                "file_path": "src/auth.py",
                "line_start": 51,
                "line_end": 100,
                "final_score": 0.80,  # Lower score - should be deduplicated
            },
            {
                "file_path": "src/user.py",
                "line_start": 1,
                "line_end": 50,
                "final_score": 0.75,
            },
        ]
        mock_retriever.retrieve.return_value = mock_chunks

        # Act
        with patch("aurora_cli.planning.memory.MemoryRetriever", return_value=mock_retriever):
            results = search_memory_for_goal(goal, limit=10)

        # Assert
        assert len(results) == 2  # Deduplicated to 2 unique files
        file_paths = [path for path, _ in results]
        assert "src/auth.py" in file_paths
        assert "src/user.py" in file_paths
        # Should keep highest score for src/auth.py
        auth_result = next((path, score) for path, score in results if path == "src/auth.py")
        assert auth_result[1] == 0.85

    def test_handles_config_parameter(self):
        """Test accepts and uses config parameter."""
        # Arrange
        goal = "Add feature"
        mock_config = Mock()
        mock_retriever = Mock()
        mock_retriever.has_indexed_memory.return_value = True
        mock_retriever.retrieve.return_value = []

        # Act
        with patch(
            "aurora_cli.planning.memory.MemoryRetriever",
            return_value=mock_retriever,
        ) as MockRetriever:
            search_memory_for_goal(goal, config=mock_config, limit=10)

        # Assert
        MockRetriever.assert_called_once()
        call_kwargs = MockRetriever.call_args[1]
        assert call_kwargs.get("config") == mock_config
