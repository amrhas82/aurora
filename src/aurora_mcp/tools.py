"""
AURORA MCP Tools - Implementation of MCP tools for code indexing and search.

This module provides the actual implementation of the MCP tools:
- aurora_search: Search indexed codebase
- aurora_get: Retrieve full chunk by index from last search results

For multi-turn SOAR queries, use: aur soar "your question"
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from aurora_cli.memory_manager import MemoryManager

from aurora_mcp.config import log_performance, setup_mcp_logging
from aurora_context_code.registry import get_global_registry
from aurora_context_code.semantic import EmbeddingProvider
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
from aurora_core.activation.engine import ActivationEngine
from aurora_core.store.sqlite import SQLiteStore


logger = logging.getLogger(__name__)

# Setup MCP logging
mcp_logger = setup_mcp_logging()


class AuroraMCPTools:
    """Implementation of AURORA MCP tools."""

    def __init__(self, db_path: str, config_path: str | None = None):
        """
        Initialize AURORA MCP Tools.

        Args:
            db_path: Path to SQLite database
            config_path: Path to AURORA config file (currently unused)
        """
        self.db_path = db_path
        self.config_path = config_path

        # Initialize components lazily (on first use)
        self._store: SQLiteStore | None = None
        self._activation_engine: ActivationEngine | None = None
        self._embedding_provider: EmbeddingProvider | None = None
        self._retriever: HybridRetriever | None = None
        self._memory_manager: MemoryManager | None = None
        self._parser_registry = None  # Lazy initialization

        # Session cache for aurora_get (Task 7.1, 7.2)
        self._last_search_results: list = []
        self._last_search_timestamp: float | None = None

    def _ensure_initialized(self) -> None:
        """Ensure all components are initialized."""
        if self._store is None:
            self._store = SQLiteStore(self.db_path)

        if self._activation_engine is None:
            self._activation_engine = ActivationEngine()

        if self._embedding_provider is None:
            self._embedding_provider = EmbeddingProvider()

        if self._retriever is None:
            self._retriever = HybridRetriever(
                self._store, self._activation_engine, self._embedding_provider
            )

        if self._parser_registry is None:
            self._parser_registry = get_global_registry()

        if self._memory_manager is None:
            self._memory_manager = MemoryManager(
                self._store, self._parser_registry, self._embedding_provider
            )

    @log_performance("aurora_search")
    def aurora_search(self, query: str, limit: int = 10) -> str:
        """
        Search AURORA indexed codebase using hybrid retrieval.

        No API key required. Uses local index only.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 10)

        Returns:
            JSON string with search results containing:
            - file_path: Path to source file
            - function_name: Name of function/class (if applicable)
            - content: Code content
            - score: Hybrid relevance score
            - chunk_id: Unique chunk identifier
        """
        try:
            import time

            self._ensure_initialized()

            # Use HybridRetriever to search
            results = self._retriever.retrieve(query, top_k=limit)

            # Record access for ACT-R activation tracking (CRITICAL FIX)
            access_time = datetime.now(timezone.utc)
            for result in results:
                chunk_id = result.get("chunk_id")
                if chunk_id:
                    try:
                        self._store.record_access(
                            chunk_id=chunk_id, access_time=access_time, context=query
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record access for chunk {chunk_id}: {e}")

            # Format results
            # HybridRetriever returns list of dicts with keys:
            # chunk_id, content, activation_score, semantic_score, hybrid_score, metadata
            # metadata contains: type, name, file_path
            formatted_results = []
            for result in results:
                metadata = result.get("metadata", {})
                formatted_results.append(
                    {
                        "file_path": metadata.get("file_path", ""),
                        "function_name": metadata.get("name", ""),
                        "content": result.get("content", ""),
                        "score": float(result.get("hybrid_score", 0.0)),
                        "chunk_id": result.get("chunk_id", ""),
                        "line_range": metadata.get("line_range", [0, 0]),
                    }
                )

            # Store results in session cache for aurora_get (Task 7.3)
            self._last_search_results = formatted_results
            self._last_search_timestamp = time.time()

            return json.dumps(formatted_results, indent=2)

        except Exception as e:
            logger.error(f"Error in aurora_search: {e}")
            return json.dumps({"error": str(e)}, indent=2)




    @log_performance("aurora_get")
    def aurora_get(self, index: int) -> str:
        """
        Retrieve a full chunk by index from the last search results.

        No API key required. Retrieves from session cache only.

        This tool allows you to get the complete content of a specific result
        from your last aurora_search or aurora_query call. Results are numbered
        starting from 1 (1-indexed).

        Workflow:
        1. Call aurora_search or aurora_query to get numbered results
        2. Review the list and choose which result you want
        3. Call aurora_get(N) to retrieve the full chunk for result N

        Args:
            index: 1-indexed position in last search results (must be >= 1)

        Returns:
            JSON string with full chunk including:
            - chunk: Complete chunk with all metadata
            - metadata: Index position and total count

        Note:
            - Results are cached for 10 minutes after search
            - Index must be >= 1 and <= total results count
            - Returns error if no previous search or cache expired
        """
        try:
            import time

            # Check if there's a previous search (Task 7.10)
            if not self._last_search_results or self._last_search_timestamp is None:
                return self._format_error(
                    error_type="NoSearchResults",
                    message="No previous search results found. Please run aurora_search or aurora_query first.",
                    suggestion="Use aurora_search or aurora_query to search for code, then use aurora_get to retrieve specific results by index.",
                )

            # Check cache expiry (10 minutes = 600 seconds) (Task 7.6)
            cache_age_seconds = time.time() - self._last_search_timestamp
            if cache_age_seconds > 600:
                return self._format_error(
                    error_type="CacheExpired",
                    message="Search results cache has expired (older than 10 minutes). Please search again.",
                    suggestion="Run aurora_search or aurora_query again to refresh the results cache.",
                )

            # Validate index (Task 7.7)
            # Must be >= 1 (1-indexed)
            if index < 1:
                return self._format_error(
                    error_type="InvalidParameter",
                    message=f"Index must be >= 1 (1-indexed system). Got: {index}",
                    suggestion="Use index starting from 1. For example: aurora_get(1) for the first result.",
                )

            # Must be <= length of results
            total_results = len(self._last_search_results)
            if index > total_results:
                return self._format_error(
                    error_type="InvalidParameter",
                    message=f"Index {index} is out of range. Only {total_results} results available (valid range: 1-{total_results}).",
                    suggestion=f"Choose an index between 1 and {total_results}.",
                )

            # Get the chunk (convert 1-indexed to 0-indexed)
            chunk = self._last_search_results[index - 1]

            # Build response per FR-11.4 (Task 7.8)
            response = {
                "chunk": chunk,
                "metadata": {
                    "index": index,
                    "total_results": total_results,
                    "retrieved_from": "session_cache",
                    "cache_age_seconds": round(cache_age_seconds, 1),
                },
            }

            return json.dumps(response, indent=2)

        except Exception as e:
            logger.error(f"Error in aurora_get: {e}", exc_info=True)
            return self._format_error(
                error_type="UnexpectedError",
                message=f"An unexpected error occurred: {str(e)}",
                suggestion="Please check the logs at ~/.aurora/logs/mcp.log for details.",
            )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _format_error(
        self,
        error_type: str,
        message: str,
        suggestion: str,
        details: dict[str, Any] | None = None,
    ) -> str:
        """
        Format error message as JSON.

        Args:
            error_type: Error type identifier
            message: Error message
            suggestion: Suggestion for fixing the error
            details: Optional additional details

        Returns:
            JSON string with error structure
        """
        # Log error before returning
        logger.error(f"{error_type}: {message}")

        error_dict: dict[str, Any] = {
            "error": {
                "type": error_type,
                "message": message,
                "suggestion": suggestion,
            }
        }

        if details:
            error_dict["error"]["details"] = details

        return json.dumps(error_dict, indent=2)



