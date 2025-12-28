"""Memory manager for AURORA CLI.

This module provides the MemoryManager class for indexing code files into the
memory store and searching the indexed content. It handles progress reporting,
file discovery, parsing, and embedding generation.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aurora_cli.config import Config
from aurora_cli.errors import ErrorHandler, MemoryStoreError
from aurora_context_code.languages.python import PythonParser
from aurora_context_code.registry import ParserRegistry, get_global_registry
from aurora_context_code.semantic import EmbeddingProvider
from aurora_core.chunks import Chunk
from aurora_core.store import SQLiteStore


if TYPE_CHECKING:
    from aurora_core.store.base import Store


logger = logging.getLogger(__name__)


# Directory names to skip during indexing
SKIP_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    "env",
    ".venv",
    ".env",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
    ".DS_Store",
}


@dataclass
class IndexStats:
    """Statistics from indexing operation.

    Attributes:
        files_indexed: Number of files successfully indexed
        chunks_created: Number of code chunks created
        duration_seconds: Total indexing duration
        errors: Number of files that failed to parse
    """

    files_indexed: int
    chunks_created: int
    duration_seconds: float
    errors: int = 0


@dataclass
class SearchResult:
    """Search result from memory store.

    Attributes:
        chunk_id: Unique chunk identifier
        file_path: Path to source file
        line_range: Tuple of (start_line, end_line)
        content: Code content
        activation_score: ACT-R activation score
        semantic_score: Semantic similarity score
        hybrid_score: Combined hybrid score
        metadata: Additional metadata dictionary
    """

    chunk_id: str
    file_path: str
    line_range: tuple[int, int]
    content: str
    activation_score: float
    semantic_score: float
    hybrid_score: float
    metadata: dict[str, str]


@dataclass
class MemoryStats:
    """Statistics about memory store contents.

    Attributes:
        total_chunks: Total number of chunks in memory
        total_files: Number of unique files indexed
        languages: Dictionary mapping language to chunk count
        database_size_mb: Size of database file in megabytes
    """

    total_chunks: int
    total_files: int
    languages: dict[str, int]
    database_size_mb: float


class MemoryManager:
    """Manager for memory store operations.

    This class provides high-level operations for indexing code files
    and searching the memory store. It handles file discovery, parsing,
    embedding generation, and progress reporting.

    Attributes:
        memory_store: Store instance for persisting chunks
        parser_registry: Registry of code parsers
        embedding_provider: Provider for generating embeddings
    """

    def __init__(
        self,
        config: Config | None = None,
        memory_store: Store | None = None,
        parser_registry: ParserRegistry | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        """Initialize MemoryManager.

        Args:
            config: Configuration with db_path (preferred way to initialize)
            memory_store: Optional store instance (for backward compatibility)
            parser_registry: Optional parser registry (uses global if None)
            embedding_provider: Optional embedding provider (creates new if None)

        Note:
            Either config or memory_store must be provided.
            If both provided, memory_store takes precedence.
            New code should use config parameter.
        """
        # Create store from config if needed
        if memory_store is None:
            if config is None:
                raise ValueError("Either config or memory_store must be provided")
            db_path = config.get_db_path()
            logger.info(f"Creating SQLiteStore at {db_path}")
            memory_store = SQLiteStore(db_path)

        self.memory_store = memory_store
        self.store = memory_store  # Alias for compatibility
        self.config = config
        self.parser_registry = parser_registry or get_global_registry()
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.error_handler = ErrorHandler()
        logger.info("MemoryManager initialized")

    def index_path(
        self,
        path: str | Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IndexStats:
        """Index all code files in the given path.

        Recursively discovers code files, parses them, generates embeddings,
        and stores chunks in the memory store. Reports progress via callback.

        Args:
            path: Directory or file path to index
            progress_callback: Optional callback(files_processed, total_files)

        Returns:
            IndexStats with indexing results

        Raises:
            ValueError: If path does not exist
            RuntimeError: If indexing fails catastrophically
        """
        path_obj = Path(path).resolve()

        if not path_obj.exists():
            raise ValueError(f"Path does not exist: {path}")

        start_time = time.time()
        stats = {"files": 0, "chunks": 0, "errors": 0}

        try:
            # Discover all code files
            if path_obj.is_file():
                files = [path_obj]
            else:
                files = self._discover_files(path_obj)

            total_files = len(files)
            logger.info(f"Discovered {total_files} code files in {path}")

            # Process each file
            for i, file_path in enumerate(files):
                try:
                    # Call progress callback
                    if progress_callback:
                        progress_callback(i, total_files)

                    # Parse file
                    parser = self.parser_registry.get_parser_for_file(file_path)
                    if not parser:
                        logger.debug(f"No parser for {file_path}, skipping")
                        continue

                    chunks = parser.parse(file_path)
                    if not chunks:
                        logger.debug(f"No chunks extracted from {file_path}")
                        continue

                    # Generate embeddings and store chunks
                    for chunk in chunks:
                        # Generate embedding for chunk content
                        # Use chunk's full content (signature + docstring + code)
                        content_to_embed = self._build_chunk_content(chunk)
                        embedding = self.embedding_provider.embed_chunk(content_to_embed)

                        # Set embedding on the chunk object (numpy array -> bytes)
                        chunk.embeddings = embedding.tobytes()

                        # Store chunk with embedding (with retry for database locks)
                        self._save_chunk_with_retry(chunk)

                        stats["chunks"] += 1

                    stats["files"] += 1
                    logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")

                except MemoryStoreError:
                    # Re-raise memory store errors (already formatted)
                    raise
                except Exception as e:
                    # Log parse errors but continue with other files
                    logger.warning(f"Failed to index {file_path}: {e}")
                    stats["errors"] += 1
                    continue

            # Final progress callback
            if progress_callback:
                progress_callback(total_files, total_files)

            duration = time.time() - start_time
            logger.info(
                f"Indexing complete: {stats['files']} files, "
                f"{stats['chunks']} chunks, {stats['errors']} errors, "
                f"{duration:.2f}s"
            )

            return IndexStats(
                files_indexed=stats["files"],
                chunks_created=stats["chunks"],
                duration_seconds=duration,
                errors=stats["errors"],
            )

        except MemoryStoreError:
            # Re-raise memory store errors with formatted messages
            raise
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            error_msg = self.error_handler.handle_memory_error(e, "indexing")
            raise MemoryStoreError(error_msg) from e

    def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        """Search memory store for relevant chunks.

        Uses hybrid retrieval (keyword + semantic) to find the most relevant
        code chunks for the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of SearchResult objects sorted by relevance

        Raises:
            RuntimeError: If search fails
        """
        try:
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            from aurora_core.activation import ActivationEngine

            # Initialize retriever
            activation_engine = ActivationEngine()
            retriever = HybridRetriever(
                self.memory_store,
                activation_engine,
                self.embedding_provider,
            )

            # Perform search
            results = retriever.retrieve(query, top_k=limit)

            # Convert to SearchResult objects
            search_results = []
            for result in results:
                metadata = result.get("metadata", {})
                search_results.append(
                    SearchResult(
                        chunk_id=result["chunk_id"],
                        file_path=metadata.get("file_path", ""),
                        line_range=(
                            metadata.get("line_start", 0),
                            metadata.get("line_end", 0),
                        ),
                        content=result.get("content", ""),
                        activation_score=result["activation_score"],
                        semantic_score=result["semantic_score"],
                        hybrid_score=result["hybrid_score"],
                        metadata=metadata,
                    )
                )

            logger.info(f"Search returned {len(search_results)} results for '{query}'")
            return search_results

        except MemoryStoreError:
            # Re-raise memory store errors
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            error_msg = self.error_handler.handle_memory_error(e, "search")
            raise MemoryStoreError(error_msg) from e

    def get_stats(self) -> MemoryStats:
        """Get statistics about memory store contents.

        Returns:
            MemoryStats with memory store information

        Raises:
            RuntimeError: If stats retrieval fails
        """
        try:
            # Query memory store for statistics
            # Note: This requires the store to support these queries
            # For now, we'll implement basic stats

            # Get total chunk count
            # This is a simplified implementation - actual implementation
            # would depend on Store API
            total_chunks = self._count_total_chunks()

            # Get unique files
            unique_files = self._count_unique_files()

            # Get language distribution
            languages = self._get_language_distribution()

            # Get database size
            db_size_mb = self._get_database_size()

            return MemoryStats(
                total_chunks=total_chunks,
                total_files=unique_files,
                languages=languages,
                database_size_mb=db_size_mb,
            )

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}", exc_info=True)
            raise RuntimeError(f"Failed to get memory stats: {e}") from e

    def _discover_files(self, root_path: Path) -> list[Path]:
        """Recursively discover all code files in directory.

        Args:
            root_path: Root directory to search

        Returns:
            List of file paths that can be parsed
        """
        files = []

        for item in root_path.rglob("*"):
            # Skip directories in SKIP_DIRS
            if any(skip_dir in item.parts for skip_dir in SKIP_DIRS):
                continue

            # Check if any parser can handle this file
            if item.is_file() and self.parser_registry.get_parser_for_file(item):
                files.append(item)

        return files

    def _should_skip_path(self, path: Path) -> bool:
        """Check if path should be skipped during indexing.

        Args:
            path: Path to check

        Returns:
            True if path should be skipped
        """
        # Check if any part of the path matches skip list
        for part in path.parts:
            if part in SKIP_DIRS:
                return True
        return False

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to source file

        Returns:
            Language identifier (e.g., "python", "javascript")
        """
        # Get parser for this file
        parser = self.parser_registry.get_parser_for_file(file_path)
        if parser:
            return parser.language

        # Fallback: guess from extension
        extension_map = {
            ".py": "python",
            ".pyi": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".go": "go",
        }

        return extension_map.get(file_path.suffix, "unknown")

    def _build_chunk_content(self, chunk: Any) -> str:
        """Build content string for embedding from code chunk.

        Args:
            chunk: CodeChunk instance

        Returns:
            Content string combining signature, docstring, and metadata
        """
        parts = []

        # Add signature if available
        if chunk.signature:
            parts.append(chunk.signature)

        # Add docstring if available
        if chunk.docstring:
            parts.append(chunk.docstring)

        # Add element type and name for context
        parts.append(f"{chunk.element_type} {chunk.name}")

        return "\n\n".join(parts)

    def _count_total_chunks(self) -> int:
        """Count total chunks in memory store.

        Returns:
            Number of chunks
        """
        try:
            # This is a simplified implementation
            # In reality, we'd query the store's database
            # For now, return 0 as placeholder
            # TODO: Implement proper chunk counting based on Store API
            return 0
        except Exception as e:
            logger.warning(f"Failed to count chunks: {e}")
            return 0

    def _count_unique_files(self) -> int:
        """Count unique files in memory store.

        Returns:
            Number of unique files
        """
        try:
            # TODO: Implement proper file counting based on Store API
            return 0
        except Exception as e:
            logger.warning(f"Failed to count files: {e}")
            return 0

    def _get_language_distribution(self) -> dict[str, int]:
        """Get distribution of chunks by language.

        Returns:
            Dictionary mapping language to chunk count
        """
        try:
            # TODO: Implement proper language distribution based on Store API
            return {}
        except Exception as e:
            logger.warning(f"Failed to get language distribution: {e}")
            return {}

    def _get_database_size(self) -> float:
        """Get size of database file in megabytes.

        Returns:
            Database size in MB
        """
        try:
            # Check if store has a database file path
            if hasattr(self.memory_store, "db_path"):
                db_path = Path(self.memory_store.db_path)
                if db_path.exists():
                    size_bytes = db_path.stat().st_size
                    return size_bytes / (1024 * 1024)
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to get database size: {e}")
            return 0.0

    def _save_chunk_with_retry(
        self,
        chunk: Chunk,
        max_retries: int = 5,
    ) -> None:
        """Save chunk in memory with retry logic for database locks.

        Implements retry logic specifically for SQLite database locked errors.
        Uses exponential backoff to wait for lock to be released.

        Args:
            chunk: Chunk object to save (with embeddings already set)
            max_retries: Maximum retry attempts for database locks (default: 5)

        Raises:
            MemoryStoreError: If all retries exhausted or non-retryable error
        """
        base_delay = 0.1  # Start with 100ms
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                self.memory_store.save_chunk(chunk)
                return  # Success

            except sqlite3.OperationalError as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a database locked error
                if "locked" in error_str or "busy" in error_str:
                    if attempt < max_retries - 1:
                        # Calculate delay with exponential backoff
                        delay = base_delay * (2**attempt)
                        logger.debug(
                            f"Database locked, retrying in {delay:.2f}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        # All retries exhausted for lock error
                        error_msg = self.error_handler.handle_memory_error(e, "storing chunk")
                        raise MemoryStoreError(error_msg) from e
                else:
                    # Non-lock operational error - raise immediately
                    error_msg = self.error_handler.handle_memory_error(e, "storing chunk")
                    raise MemoryStoreError(error_msg) from e

            except PermissionError as e:
                # Permission errors are not retryable
                error_msg = self.error_handler.handle_memory_error(e, "storing chunk")
                raise MemoryStoreError(error_msg) from e

            except OSError as e:
                # OS errors like disk full are not retryable
                error_msg = self.error_handler.handle_memory_error(e, "storing chunk")
                raise MemoryStoreError(error_msg) from e

            except Exception as e:
                # Other errors - raise immediately
                last_error = e
                error_msg = self.error_handler.handle_memory_error(e, "storing chunk")
                raise MemoryStoreError(error_msg) from e

        # Should never reach here, but just in case
        if last_error:
            error_msg = self.error_handler.handle_memory_error(last_error, "storing chunk")
            raise MemoryStoreError(error_msg)


__all__ = ["MemoryManager", "IndexStats", "SearchResult", "MemoryStats"]
