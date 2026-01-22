"""CodeContextProvider implementation for code-based context retrieval.

This module provides a concrete implementation of ContextProvider that
retrieves relevant code chunks based on keyword queries.
"""

import logging
from pathlib import Path

# Import ParserRegistry with TYPE_CHECKING to avoid circular dependency
from typing import TYPE_CHECKING

from aurora_core.chunks.base import Chunk
from aurora_core.context.provider import ContextProvider
from aurora_core.store.base import Store
from aurora_core.types import ChunkID


if TYPE_CHECKING:
    from aurora_context_code.registry import ParserRegistry


logger = logging.getLogger(__name__)


class CodeContextProvider(ContextProvider):
    """Context provider for code-based retrieval.

    Retrieves code chunks from a Store based on keyword matching against:
    - Function/class names
    - Docstrings
    - Source code content
    - File paths

    Features:
    - Keyword-based query parsing with stopword removal
    - Relevance scoring based on keyword matches
    - Caching with file modification time tracking
    - Activation tracking for spreading activation algorithm

    Example:
        >>> from aurora_core.store.memory import MemoryStore
        >>> from aurora_context_code.registry import get_global_registry
        >>> store = MemoryStore()
        >>> registry = get_global_registry()
        >>> provider = CodeContextProvider(store, registry)
        >>> results = provider.retrieve("parse json data", limit=5)

    """

    # Common English stopwords to filter out from queries
    STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "will",
        "with",
        "this",
        "but",
        "or",
        "not",
    }

    @staticmethod
    def _parse_query(query: str) -> list[str]:
        """Parse query into keywords.

        Extracts keywords by:
        1. Converting to lowercase
        2. Splitting on whitespace
        3. Stripping punctuation
        4. Removing stopwords
        5. Filtering empty strings

        Args:
            query: Natural language query string

        Returns:
            List of keywords extracted from query

        """
        if not query:
            return []

        # Convert to lowercase and split on whitespace
        words = query.lower().split()

        # Strip common punctuation from each word
        punctuation = ".,!?;:'\"()[]{}/"
        cleaned_words = []
        for word in words:
            # Strip leading/trailing punctuation
            cleaned = word.strip(punctuation)
            if cleaned:  # Only include non-empty strings
                cleaned_words.append(cleaned)

        # Remove stopwords and empty strings
        return [w for w in cleaned_words if w and w not in CodeContextProvider.STOPWORDS]

    @staticmethod
    def _score_chunk(chunk: Chunk, keywords: list[str]) -> float:
        """Score a chunk based on keyword matches.

        Calculates relevance score as:
            score = (number of matching keywords) / (total keywords)

        Keywords are checked against (case-insensitive):
        - Chunk name (for CodeChunk)
        - Docstring (if present)
        - File path

        Args:
            chunk: Chunk to score
            keywords: List of query keywords

        Returns:
            Relevance score between 0.0 and 1.0

        """
        if not keywords:
            return 0.0

        # Build searchable text from chunk attributes
        searchable_parts = []

        # For CodeChunk, include name and docstring
        if hasattr(chunk, "name"):
            searchable_parts.append(chunk.name.lower())

        if hasattr(chunk, "docstring") and chunk.docstring:
            searchable_parts.append(chunk.docstring.lower())

        if hasattr(chunk, "file_path"):
            searchable_parts.append(str(chunk.file_path).lower())

        # Combine all searchable text
        searchable_text = " ".join(searchable_parts)

        # Count how many keywords match
        matches = sum(1 for keyword in keywords if keyword.lower() in searchable_text)

        # Calculate score as ratio
        return matches / len(keywords)

    def __init__(self, store: Store, parser_registry: "ParserRegistry"):
        """Initialize CodeContextProvider.

        Args:
            store: Storage backend for chunks
            parser_registry: Registry of code parsers for file indexing

        """
        self._store = store
        self._parser_registry = parser_registry
        self._file_mtimes: dict[Path, float] = {}
        logger.debug("CodeContextProvider initialized")

    def retrieve(self, query: str, limit: int = 10) -> list[Chunk]:
        """Retrieve relevant code chunks based on query.

        Args:
            query: Natural language query or keywords
            limit: Maximum number of chunks to return

        Returns:
            List of relevant code chunks, ordered by relevance (highest first)

        Raises:
            ValueError: If query is empty or limit is invalid

        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if limit <= 0:
            raise ValueError("Limit must be positive")

        logger.debug(f"Retrieving chunks for query: {query!r}, limit={limit}")

        # Step 1: Parse query into keywords
        keywords = self._parse_query(query)
        if not keywords:
            logger.debug("No keywords extracted from query")
            return []

        logger.debug(f"Extracted keywords: {keywords}")

        # Step 2: Retrieve all chunks from store
        # Use retrieve_by_activation with min_activation=0.0 to get all chunks
        # Set high limit to get all chunks, then we'll filter and rank
        all_chunks = self._store.retrieve_by_activation(min_activation=0.0, limit=10000)

        if not all_chunks:
            logger.debug("No chunks in store")
            return []

        # Step 3: Score each chunk
        scored_chunks = []
        for chunk in all_chunks:
            score = self._score_chunk(chunk, keywords)
            if score > 0:  # Only include chunks with some relevance
                scored_chunks.append((chunk, score))

        # Step 4: Sort by score (descending)
        scored_chunks.sort(key=lambda x: x[1], reverse=True)

        # Step 5: Return top N chunks
        results = [chunk for chunk, score in scored_chunks[:limit]]

        logger.debug(f"Returning {len(results)} chunks (scored {len(scored_chunks)} total)")

        return results

    def update(self, chunk_id: ChunkID, activation_delta: float) -> None:
        """Update activation score for a chunk.

        Currently stub - full implementation in subtask 5.7.

        Args:
            chunk_id: Chunk to update
            activation_delta: Amount to adjust activation

        Raises:
            ChunkNotFoundError: If chunk does not exist

        """
        logger.debug(f"Updating activation for {chunk_id}: delta={activation_delta}")

        # TODO: Implement activation tracking (subtask 5.7)
        # For now, just update the store
        self._store.update_activation(chunk_id, activation_delta)

    def refresh(self) -> None:
        """Refresh cached data and re-index changed files.

        Currently stub - full implementation in subtask 5.6.

        Raises:
            StorageError: If refresh fails

        """
        logger.debug("Refreshing CodeContextProvider cache")

        # TODO: Implement caching strategy (subtask 5.6)
        # - Check file mtimes
        # - Invalidate changed files
        # - Re-parse and re-index


__all__ = ["CodeContextProvider"]
