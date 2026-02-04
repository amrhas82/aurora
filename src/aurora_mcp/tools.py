"""AURORA MCP Tools - Implementation of MCP tools for code indexing and search.

This module provides the actual implementation of the MCP tools:
- aurora_search: Search indexed codebase
- aurora_get: Retrieve full chunk by index from last search results

For multi-turn SOAR queries, use: aur soar "your question"
"""

import json
import logging
from typing import Any

from aurora_cli.memory_manager import MemoryManager
from aurora_context_code.registry import get_global_registry
from aurora_context_code.semantic import EmbeddingProvider
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
from aurora_core.activation.engine import ActivationEngine
from aurora_core.store.sqlite import SQLiteStore
from aurora_mcp.config import setup_mcp_logging

logger = logging.getLogger(__name__)

# Setup MCP logging
mcp_logger = setup_mcp_logging()


class AuroraMCPTools:
    """Implementation of AURORA MCP tools."""

    def __init__(self, db_path: str, config_path: str | None = None):
        """Initialize AURORA MCP Tools.

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

    # DEPRECATED: Use /aur:search slash command instead
    # This method is preserved for potential future MCP re-enablement
    def aurora_search(self, query: str, limit: int = 10) -> str:
        """DEPRECATED: Use /aur:search slash command instead.

        This tool has been deprecated in favor of slash commands which provide:
        - Better formatted output (tables, syntax highlighting)
        - Direct user control over execution
        - Lower token usage

        Use instead:
            /aur:search <query>    # Interactive slash command
            aur mem search "query" # CLI command

        Session cache variables (_last_search_results, _last_search_timestamp)
        are preserved for potential future use.
        """
        return json.dumps(
            {
                "error": "Tool deprecated",
                "message": "aurora_search is deprecated. Use /aur:search slash command instead.",
                "alternatives": [
                    "/aur:search <query> - Interactive search with formatted output",
                    "aur mem search 'query' - CLI search command",
                ],
            },
            indent=2,
        )

    # DEPRECATED: Use /aur:get slash command instead
    # This method is preserved for potential future MCP re-enablement
    def aurora_get(self, index: int) -> str:
        """DEPRECATED: Use /aur:get slash command instead.

        This tool has been deprecated in favor of slash commands which provide:
        - Better formatted output (syntax highlighting, metadata display)
        - Direct user control over execution
        - Clearer result presentation

        Use instead:
            /aur:get <N>        # Interactive slash command
            aur mem get <N>     # CLI command

        Session cache variables (_last_search_results, _last_search_timestamp)
        are preserved for potential future use.
        """
        return json.dumps(
            {
                "error": "Tool deprecated",
                "message": "aurora_get is deprecated. Use /aur:get slash command instead.",
                "alternatives": [
                    "/aur:get <N> - Interactive retrieval with formatted output",
                    "aur mem get <N> - CLI retrieval command",
                ],
            },
            indent=2,
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
        """Format error message as JSON.

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
