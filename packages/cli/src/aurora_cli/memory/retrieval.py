"""Memory retrieval API for AURORA CLI.

This module provides the MemoryRetriever class, a unified API for accessing
indexed code memory with support for:
- Hybrid retrieval (semantic + BM25 + activation scoring)
- Direct file context loading
- Formatted output for LLM consumption

The MemoryRetriever is the primary interface for consumers needing
code context, used by both `aur query` and future planning commands.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aurora_core.chunks import CodeChunk

if TYPE_CHECKING:
    from aurora_cli.config import Config
    from aurora_core.store.sqlite import SQLiteStore

logger = logging.getLogger(__name__)

# Performance targets
RETRIEVE_LATENCY_TARGET = 2.0  # seconds
FILE_LOAD_LATENCY_TARGET = 2.0  # seconds for 10 files


class MemoryRetriever:
    """Unified memory retrieval API for AURORA CLI.

    Provides access to indexed code memory with hybrid retrieval
    (semantic + BM25 + activation) and direct file loading.

    Attributes:
        store: SQLite memory store (optional for file-only usage)
        config: CLI configuration

    Example:
        >>> retriever = MemoryRetriever(store, config)
        >>> chunks = retriever.retrieve("authentication", limit=10)
        >>> formatted = retriever.format_for_prompt(chunks)

        >>> # File-only usage (no store needed)
        >>> retriever = MemoryRetriever(config=config)
        >>> chunks = retriever.load_context_files([Path("auth.py")])
    """

    def __init__(
        self,
        store: SQLiteStore | None = None,
        config: Config | None = None,
    ) -> None:
        """Initialize the MemoryRetriever.

        Args:
            store: SQLite memory store with indexed chunks (optional for file-only usage)
            config: CLI configuration with retrieval settings (optional)
        """
        self._store = store
        self._config = config
        self._retriever: Any = None  # Lazy-loaded HybridRetriever

    def _get_retriever(self) -> Any:
        """Get or create the HybridRetriever instance.

        Lazy-loads the retriever to avoid import overhead until needed.

        Returns:
            HybridRetriever instance

        Raises:
            ValueError: If no store is configured
        """
        if self._store is None:
            raise ValueError("Cannot retrieve: no memory store configured")

        if self._retriever is None:
            from aurora_context_code.semantic import EmbeddingProvider
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            from aurora_core.activation.engine import ActivationEngine

            activation_engine = ActivationEngine()
            embedding_provider = EmbeddingProvider()
            self._retriever = HybridRetriever(
                self._store,
                activation_engine,
                embedding_provider,
            )

        return self._retriever

    def has_indexed_memory(self) -> bool:
        """Check if the memory store has indexed content.

        Returns:
            True if store has at least one chunk, False otherwise

        Example:
            >>> if retriever.has_indexed_memory():
            ...     chunks = retriever.retrieve("query")
        """
        if self._store is None:
            return False

        try:
            # Try to retrieve one chunk to check if memory exists
            results = self._get_retriever().retrieve("test", top_k=1)
            return len(results) > 0
        except Exception as e:
            logger.warning("Error checking indexed memory: %s", e)
            return False

    def retrieve(
        self,
        query: str,
        limit: int = 20,
        mode: str = "hybrid",
        min_semantic_score: float | None = None,
    ) -> list[CodeChunk]:
        """Retrieve relevant code chunks for a query.

        Uses hybrid retrieval combining semantic similarity, BM25,
        and activation scoring.

        Args:
            query: Search query text
            limit: Maximum number of chunks to return (default: 20)
            mode: Retrieval mode - 'hybrid' (default), 'semantic', or 'bm25'
            min_semantic_score: Minimum semantic score threshold (uses config default if None)

        Returns:
            List of CodeChunk objects sorted by relevance

        Example:
            >>> chunks = retriever.retrieve("authentication", limit=10)
            >>> for chunk in chunks:
            ...     print(f"{chunk.file_path}: {chunk.name}")
        """
        start_time = time.time()

        try:
            retriever = self._get_retriever()

            # Use config threshold if not specified
            threshold = min_semantic_score
            if threshold is None:
                threshold = self._config.search_min_semantic_score if self._config else 0.7

            # Retrieve chunks using hybrid retriever
            results = retriever.retrieve(
                query,
                top_k=limit,
                min_semantic_score=threshold,
            )

            elapsed = time.time() - start_time
            if elapsed > RETRIEVE_LATENCY_TARGET:
                logger.warning(
                    "Retrieval took %.2fs (target: %.2fs)",
                    elapsed,
                    RETRIEVE_LATENCY_TARGET,
                )

            logger.debug(
                "Retrieved %d chunks for query '%s' in %.2fs",
                len(results),
                query[:50],
                elapsed,
            )

            return results

        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            return []

    def load_context_files(self, paths: list[Path]) -> list[CodeChunk]:
        """Load context directly from files (not from index).

        Reads files directly and creates CodeChunk objects. This is used
        for the --context option to bypass indexed memory.

        Args:
            paths: List of file paths to load

        Returns:
            List of CodeChunk objects with file contents

        Example:
            >>> chunks = retriever.load_context_files([
            ...     Path("src/auth.py"),
            ...     Path("src/config.py"),
            ... ])
        """
        start_time = time.time()
        chunks: list[CodeChunk] = []
        skipped = 0

        for path in paths:
            resolved_path = Path(path).expanduser().resolve()

            if not resolved_path.exists():
                logger.warning("Context file not found (skipping): %s", path)
                skipped += 1
                continue

            if not resolved_path.is_file():
                logger.warning("Path is not a file (skipping): %s", path)
                skipped += 1
                continue

            try:
                content = resolved_path.read_text(encoding="utf-8")

                # Create a CodeChunk from file content
                # CodeChunk stores content in the docstring field
                chunk = CodeChunk(
                    chunk_id=f"file:{resolved_path}",
                    file_path=str(resolved_path),
                    element_type="document",
                    name=resolved_path.name,
                    line_start=1,
                    line_end=content.count("\n") + 1,
                    docstring=content,  # Content goes in docstring field
                    language=_detect_language(resolved_path),
                    metadata={
                        "source": "context_file",
                        "file_path": str(resolved_path),
                    },
                )
                chunks.append(chunk)

            except UnicodeDecodeError:
                logger.warning(
                    "Cannot read file (binary or encoding issue): %s",
                    path,
                )
                skipped += 1
            except PermissionError:
                logger.warning("Permission denied reading file: %s", path)
                skipped += 1
            except Exception as e:
                logger.warning("Error reading file %s: %s", path, e)
                skipped += 1

        elapsed = time.time() - start_time
        if elapsed > FILE_LOAD_LATENCY_TARGET:
            logger.warning(
                "File loading took %.2fs (target: %.2fs for 10 files)",
                elapsed,
                FILE_LOAD_LATENCY_TARGET,
            )

        logger.debug(
            "Loaded %d context files (%d skipped) in %.2fs",
            len(chunks),
            skipped,
            elapsed,
        )

        return chunks

    def format_for_prompt(self, chunks: list[CodeChunk]) -> str:
        """Format chunks for LLM prompt consumption.

        Creates a structured text format with file path headers
        and content blocks suitable for inclusion in LLM prompts.

        Args:
            chunks: List of CodeChunk objects to format

        Returns:
            Formatted string with file headers and content

        Example:
            >>> formatted = retriever.format_for_prompt(chunks)
            >>> print(formatted[:200])
            ### File: src/auth.py (lines 10-45)
            ```python
            def authenticate(user, password):
                ...
        """
        if not chunks:
            return ""

        sections = []

        for chunk in chunks:
            # Build header
            file_path = chunk.file_path or "unknown"
            line_range = f"lines {chunk.line_start}-{chunk.line_end}"
            header = f"### File: {file_path} ({line_range})"

            # Build content block with language hint
            # CodeChunk stores content in docstring field
            language = chunk.language or ""
            content = chunk.docstring or ""
            content_block = f"```{language}\n{content}\n```"

            sections.append(f"{header}\n{content_block}")

        return "\n\n".join(sections)

    def get_context(
        self,
        query: str,
        context_files: list[Path] | None = None,
        limit: int = 20,
    ) -> tuple[list[CodeChunk], str]:
        """Get context for a query using priority strategy.

        Context priority:
        1. If context_files provided, use those (bypass index)
        2. If indexed memory available, use hybrid retrieval
        3. If neither available, return empty with error message

        Args:
            query: Search query text
            context_files: Optional list of files to use as context
            limit: Maximum chunks to retrieve from index

        Returns:
            Tuple of (chunks, error_message). error_message is empty on success.

        Example:
            >>> chunks, error = retriever.get_context("auth", limit=10)
            >>> if error:
            ...     print(f"Error: {error}")
            >>> else:
            ...     formatted = retriever.format_for_prompt(chunks)
        """
        # Priority 1: Explicit context files
        if context_files:
            chunks = self.load_context_files(context_files)
            if chunks:
                logger.info(
                    "Using %d context files (bypassing indexed memory)",
                    len(chunks),
                )
                return chunks, ""
            else:
                return [], "No valid context files found"

        # Priority 2: Indexed memory
        if self.has_indexed_memory():
            chunks = self.retrieve(query, limit=limit)
            if chunks:
                return chunks, ""
            else:
                return [], "No relevant chunks found in indexed memory"

        # Priority 3: Neither available
        return [], (
            "No context available. Either:\n"
            "  - Index your codebase: aur mem index .\n"
            "  - Provide context files: --context file1.py file2.py"
        )


def _detect_language(path: Path) -> str:
    """Detect programming language from file extension.

    Args:
        path: File path

    Returns:
        Language identifier string
    """
    extension_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".r": "r",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "zsh",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
        ".rst": "rst",
        ".txt": "text",
    }

    suffix = path.suffix.lower()
    return extension_map.get(suffix, "text")
