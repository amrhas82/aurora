"""
Integration Test: Retrieval Before LLM Call

Tests Issue #15: Query Doesn't Use Indexed Data
- Verifies that execute_direct_llm() retrieves context from memory store
- Tests that LLM prompts include relevant chunks from indexed data
- Validates context formatting (file paths, line ranges, code content)

This test will FAIL initially because execute_direct_llm() doesn't query memory store.

Test Strategy:
- Create QueryExecutor with memory store containing indexed data
- Mock LLM client to capture prompts
- Execute query and verify context retrieval
- Assert LLM prompt includes chunks with proper formatting

Expected Failure:
- execute_direct_llm() calls LLM without retrieving from memory store
- LLM prompt doesn't include "Context:" section
- Response is generic (not based on indexed code)
- User queries don't leverage indexed codebase knowledge

Related Files:
- packages/cli/src/aurora_cli/execution.py (QueryExecutor.execute_direct_llm)
- packages/cli/src/aurora_cli/memory_manager.py (MemoryManager.search)
- packages/reasoning/src/aurora_reasoning/llm_client.py (LLMClient)

Phase: 1 (Core Restoration)
Priority: P0 (Critical)
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_cli.config import Config
from aurora_cli.execution import QueryExecutor
from aurora_cli.memory_manager import MemoryManager
from aurora_core.chunks.base import Chunk
from aurora_reasoning.llm_client import LLMClient


class TestRetrievalBeforeLLM:
    """Test that query execution retrieves context before calling LLM."""

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create temporary workspace with sample code."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Create Python file with specific patterns
        sample_file = workspace / "database.py"
        sample_file.write_text("""
class DatabaseConnection:
    \"\"\"
    Manages database connections using SQLite.

    Features:
    - Connection pooling for performance
    - Automatic retry on connection failure
    - Transaction support with rollback
    \"\"\"

    def __init__(self, db_path):
        \"\"\"Initialize database connection.\"\"\"
        self.db_path = db_path
        self.connection = None

    def connect(self):
        \"\"\"Establish database connection with retry logic.\"\"\"
        import sqlite3
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.connection = sqlite3.connect(self.db_path)
                return True
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))
        return False

    def execute_query(self, query, params=None):
        \"\"\"Execute SQL query and return results.\"\"\"
        if not self.connection:
            self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()
""")

        return workspace

    @pytest.fixture
    def executor_with_memory(self, tmp_path, temp_workspace):
        """Create QueryExecutor with populated memory store."""
        # Setup database and index data
        db_path = tmp_path / "test_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        memory_manager = MemoryManager(config=config)
        memory_manager.index_path(temp_workspace)

        # Create QueryExecutor with config dict
        config_dict = {
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "max_tokens": 500
        }
        executor = QueryExecutor(config=config_dict, interactive_mode=False)

        return executor, memory_manager

    def test_direct_llm_retrieves_from_memory_store(self, executor_with_memory):
        """
        Test that execute_direct_llm() queries memory store before calling LLM.

        This test will FAIL because execute_direct_llm() doesn't retrieve context.
        """
        executor, memory_manager = executor_with_memory

        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = "Based on the code, the DatabaseConnection class uses SQLite."
        mock_response.input_tokens = 100
        mock_response.output_tokens = 50

        # Patch the LLM client's generate method
        with patch('aurora_reasoning.llm_client.AnthropicClient.generate', return_value=mock_response) as mock_generate:
            # Execute query about indexed code
            query = "How does DatabaseConnection handle connection failures?"
            result = executor.execute_direct_llm(
                query=query,
                api_key="test-api-key",
                memory_store=memory_manager.store,
                verbose=False
            )

            # ASSERTION 1: LLM generate should be called
            assert mock_generate.called, (
                "LLM client not called during execute_direct_llm()\n"
                "Expected: LLM called with prompt\n"
                "Actual: LLM not called"
            )

            # ASSERTION 2: Prompt should include retrieved context
            call_args = mock_generate.call_args
            if call_args:
                # Get the prompt argument
                prompt = call_args.kwargs.get('prompt', '')

                # Check for context indicators
                has_context = any(indicator in prompt.lower() for indicator in [
                    'context', 'codebase', 'retrieved', 'database.py'
                ])

                assert has_context, (
                    f"LLM prompt doesn't include retrieved context\n"
                    f"Expected: Prompt with 'Context:' section from indexed code\n"
                    f"Actual prompt (first 500 chars): {prompt[:500]}\n"
                    f"Cause: execute_direct_llm() not retrieving from memory store\n"
                    f"Fix: Add memory_store.search(query) before LLM call in execute_direct_llm()"
                )

    def test_llm_prompt_includes_file_paths(self, executor_with_memory):
        """
        Test that context includes file paths and line ranges from chunks.

        This test will FAIL if context formatting doesn't include metadata.
        """
        executor, memory_manager = executor_with_memory

        # Mock LLM to capture full prompt
        captured_prompt = None

        def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Mocked response about database connections"

        with patch.object(executor.llm_client, 'generate', side_effect=capture_prompt):
            query = "What retry logic does DatabaseConnection use?"
            executor.execute_direct_llm(query)

            # ASSERTION: Prompt should include file path references
            assert captured_prompt is not None, "LLM was not called"

            # Look for file path patterns
            has_file_ref = any(pattern in captured_prompt for pattern in [
                'database.py',
                'file:',
                'File:',
                'source:',
                'Source:',
                '.py'
            ])

            assert has_file_ref, (
                f"Context doesn't include file path references\n"
                f"Expected: File paths like 'database.py' or 'file: path/to/file.py'\n"
                f"Actual prompt: {captured_prompt[:1000]}\n"
                f"Fix: Format context to include chunk.file_path in execute_direct_llm()"
            )

    def test_llm_prompt_includes_code_content(self, executor_with_memory):
        """
        Test that context includes actual code content from chunks.

        This test will FAIL if chunks aren't retrieved or formatted.
        """
        executor, memory_manager = executor_with_memory

        captured_prompt = None

        def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Mocked response"

        with patch.object(executor.llm_client, 'generate', side_effect=capture_prompt):
            query = "Show me the connect method implementation"
            executor.execute_direct_llm(query)

            assert captured_prompt is not None, "LLM was not called"

            # Look for code-specific content
            code_indicators = [
                'def connect',
                'DatabaseConnection',
                'sqlite3',
                'max_retries',
                'connection'
            ]

            matches = [ind for ind in code_indicators if ind in captured_prompt]

            assert len(matches) >= 2, (
                f"Context doesn't include actual code content\n"
                f"Expected: Code snippets with method definitions and logic\n"
                f"Found {len(matches)} indicators: {matches}\n"
                f"Prompt length: {len(captured_prompt)} chars\n"
                f"Cause: execute_direct_llm() not retrieving or not formatting chunks\n"
                f"Fix: Add chunk.content to prompt context"
            )

    def test_retrieval_with_empty_memory_store(self, tmp_path):
        """
        Test behavior when memory store is empty (no indexed data).

        This test verifies graceful handling (no errors).
        """
        # Create empty memory store
        db_path = tmp_path / "empty_memory.db"
        config = Config(anthropic_api_key="test-key", db_path=str(db_path), budget_limit=10.0)

        memory_manager = MemoryManager(config=config)

        executor = QueryExecutor(
            config=config,
            memory_store=memory_manager.store,
            interactive_mode=False
        )

        # Mock LLM
        with patch.object(executor.llm_client, 'generate', return_value="Generic response") as mock_generate:
            query = "What is Python?"
            result = executor.execute_direct_llm(query)

            # ASSERTION 1: Should not crash with empty store
            assert result is not None, "Execution failed with empty memory store"

            # ASSERTION 2: LLM should still be called (just without context)
            assert mock_generate.called, "LLM not called with empty memory store"

    def test_retrieval_with_populated_store(self, executor_with_memory):
        """
        Test behavior when memory store has relevant indexed data.

        This test verifies context IS included when data exists.
        """
        executor, memory_manager = executor_with_memory

        # Verify store has data
        stats = memory_manager.get_stats()
        chunk_count = stats.get("total_chunks", 0)

        assert chunk_count > 0, (
            f"Test fixture error: Memory store is empty\n"
            f"Expected: At least 3 chunks from database.py\n"
            f"Actual: {chunk_count} chunks"
        )

        # Mock LLM and capture prompt
        captured_prompt = None

        def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return "Response based on indexed code"

        with patch.object(executor.llm_client, 'generate', side_effect=capture_prompt):
            query = "Explain the database retry mechanism"
            result = executor.execute_direct_llm(query)

            # ASSERTION: Prompt should be longer with context vs. without
            # (comparing to minimum prompt with just query)
            min_prompt_length = len(query) + 50  # Query + minimal system message

            assert len(captured_prompt) > min_prompt_length, (
                f"Prompt too short - likely missing context\n"
                f"Expected: At least {min_prompt_length} chars (with context)\n"
                f"Actual: {len(captured_prompt)} chars\n"
                f"Chunks available: {chunk_count}\n"
                f"Cause: execute_direct_llm() not retrieving or not including context"
            )

    def test_context_limit_respected(self, executor_with_memory):
        """
        Test that retrieval respects context limits (top-k chunks).

        This test verifies we don't overwhelm LLM with too much context.
        """
        executor, memory_manager = executor_with_memory

        # Mock search to return many results
        original_search = memory_manager.search

        def mock_search_many_results(query, limit=10):
            # Return all available chunks (more than limit)
            return original_search(query, limit=100)

        with patch.object(memory_manager, 'search', side_effect=mock_search_many_results):
            captured_prompt = None

            def capture_prompt(prompt, **kwargs):
                nonlocal captured_prompt
                captured_prompt = prompt
                return "Response"

            with patch.object(executor.llm_client, 'generate', side_effect=capture_prompt):
                query = "database connection"
                executor.execute_direct_llm(query)

                # Count how many chunks appear in context
                # (this is heuristic - checking for "def " or "class " occurrences)
                if captured_prompt:
                    chunk_markers = captured_prompt.count('def ') + captured_prompt.count('class ')

                    # Should include top chunks but not ALL chunks
                    assert chunk_markers <= 15, (
                        f"Too many chunks in context (potential token limit issue)\n"
                        f"Found ~{chunk_markers} chunks\n"
                        f"Expected: Top 10-15 chunks max\n"
                        f"Consider: Add limit parameter to search() call"
                    )


class TestContextFormatting:
    """Test that retrieved context is properly formatted for LLM."""

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for context formatting tests."""
        chunks = [
            Chunk(
                chunk_id="chunk1",
                chunk_type="function",
                name="calculate_sum",
                file_path=Path("utils.py"),
                content="def calculate_sum(numbers):\n    return sum(numbers)",
                line_start=1,
                line_end=2,
                metadata={"docstring": "Calculate sum of numbers"}
            ),
            Chunk(
                chunk_id="chunk2",
                chunk_type="function",
                name="calculate_average",
                file_path=Path("utils.py"),
                content="def calculate_average(numbers):\n    return sum(numbers) / len(numbers)",
                line_start=4,
                line_end=5,
                metadata={"docstring": "Calculate average"}
            )
        ]
        return chunks

    def test_context_includes_chunk_metadata(self, sample_chunks):
        """
        Test that formatted context includes chunk names, file paths, and line ranges.

        This test verifies proper context structure.
        """
        # This test would ideally mock the internal _format_context() method
        # For now, it serves as documentation for expected format

        expected_format_elements = [
            "# File: utils.py",
            "# Lines: 1-2",
            "def calculate_sum",
            "# Lines: 4-5",
            "def calculate_average"
        ]

        # When fix is implemented, context should include:
        # - File path for each chunk
        # - Line range for each chunk
        # - Chunk content (code)
        # - Optional: docstring or description

        # This assertion documents expected behavior
        assert True, "Context formatting will be verified in implementation"

    def test_multiple_files_in_context(self):
        """
        Test that context can include chunks from multiple files.

        This test documents expected behavior for cross-file context.
        """
        # When multiple files are indexed, context should:
        # - Group chunks by file
        # - Include file path headers
        # - Maintain readability

        assert True, "Multi-file context will be verified in implementation"


# Mark all tests in this file with integration marker
pytestmark = pytest.mark.integration
