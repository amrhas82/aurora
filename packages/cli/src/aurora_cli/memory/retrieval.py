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
        Uses BackgroundModelLoader if model loading was started earlier,
        otherwise creates EmbeddingProvider directly.

        Returns:
            HybridRetriever instance

        Raises:
            ValueError: If no store is configured

        """
        if self._store is None:
            raise ValueError("Cannot retrieve: no memory store configured")

        if self._retriever is None:
            from aurora_context_code.semantic.hybrid_retriever import get_cached_retriever
            from aurora_core.activation.engine import get_cached_engine

            # Use cached engine for performance (tasks/aur-mem-search Epic 1 Task 2.0)
            activation_engine = get_cached_engine(self._store)

            # Try to get embedding provider from background loader or create new one
            embedding_provider = self._get_embedding_provider()

            # Use cached retriever for performance (tasks/aur-mem-search Epic 1 Task 1.0)
            self._retriever = get_cached_retriever(
                self._store,
                activation_engine,
                embedding_provider,  # None = BM25-only mode
            )

        return self._retriever

    def _get_embedding_provider(self, wait_for_model: bool = True) -> Any:
        """Get embedding provider, using background loader if available.

        First checks if BackgroundModelLoader has a ready provider (from
        background loading started earlier). If so, returns it immediately.

        Behavior depends on wait_for_model:
        - True (default): If loading is in progress, waits with progress indicator
        - False: Returns None immediately if not ready, enabling BM25-only fallback

        Args:
            wait_for_model: If True, wait for model loading. If False, return None
                           immediately when model is still loading.

        Returns:
            EmbeddingProvider if available, None for BM25-only mode

        """
        try:
            from aurora_context_code.semantic.model_utils import (
                BackgroundModelLoader,
                is_model_cached,
            )

            loader = BackgroundModelLoader.get_instance()

            # Check if provider is already ready (fastest path)
            provider = loader.get_provider_if_ready()
            if provider is not None:
                logger.debug("Using pre-loaded embedding provider from background loader")
                return provider

            # Check if loading is in progress
            if loader.is_loading():
                if wait_for_model:
                    logger.debug("Waiting for background model loading to complete")
                    return self._wait_for_background_model(loader)
                # Non-blocking: return None, let caller use BM25-only
                logger.debug("Model still loading - using BM25-only for now")
                return None

            # Not loading and not loaded - try to create new provider
            # This happens if background loading wasn't started (e.g., model not cached)
            if not is_model_cached():
                logger.info(
                    "Embedding model not cached. Using BM25-only search. "
                    "Run 'aur mem index .' to download the embedding model.",
                )
                return None

            # Model is cached but wasn't pre-loaded - load now
            import os

            os.environ["HF_HUB_OFFLINE"] = "1"

            from aurora_context_code.semantic import EmbeddingProvider

            return EmbeddingProvider()

        except ImportError:
            logger.debug("sentence-transformers not installed, using BM25-only search")
            return None
        except Exception as e:
            logger.warning(
                "Embedding provider unavailable, using BM25-only search. Error: %s",
                str(e)[:80],
            )
            return None

    def is_embedding_model_ready(self) -> bool:
        """Check if embedding model is loaded and ready (non-blocking).

        Returns:
            True if embedding model is ready for use, False otherwise

        """
        try:
            from aurora_context_code.semantic.model_utils import BackgroundModelLoader

            loader = BackgroundModelLoader.get_instance()
            return loader.is_loaded()
        except ImportError:
            return False
        except Exception:
            return False

    def is_embedding_model_loading(self) -> bool:
        """Check if embedding model is currently loading in background.

        Returns:
            True if model is currently loading, False otherwise

        """
        try:
            from aurora_context_code.semantic.model_utils import BackgroundModelLoader

            loader = BackgroundModelLoader.get_instance()
            return loader.is_loading()
        except ImportError:
            return False
        except Exception:
            return False

    def _wait_for_background_model(self, loader: Any) -> Any:
        """Wait for background model loading with progress display.

        Shows a spinner while waiting for background loading to complete.

        Args:
            loader: BackgroundModelLoader instance

        Returns:
            EmbeddingProvider if loaded successfully, None otherwise

        """
        try:
            import time

            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

            console = Console()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Loading embedding model (first search may be slow)...[/]",
                    total=None,
                )

                # Poll with progress updates showing elapsed time
                start_time = time.time()
                while True:
                    provider = loader.get_provider_if_ready()
                    if provider is not None:
                        elapsed = time.time() - start_time
                        progress.update(
                            task,
                            description=f"[green]✓ Model ready ({elapsed:.1f}s)[/]",
                        )
                        return provider

                    error = loader.get_error()
                    if error is not None:
                        progress.update(
                            task,
                            description="[yellow]Model unavailable - using BM25 only[/]",
                        )
                        return None

                    if not loader.is_loading():
                        progress.update(
                            task,
                            description="[yellow]Model not started - using BM25 only[/]",
                        )
                        return None

                    elapsed = time.time() - start_time
                    if elapsed > 60.0:
                        progress.update(task, description="[yellow]Timeout - using BM25 only[/]")
                        return None

                    time.sleep(0.1)

        except ImportError:
            # Rich not available - wait without progress
            return loader.wait_for_model(timeout=60.0)

    def has_indexed_memory(self) -> bool:
        """Check if the memory store has indexed content.

        This method checks the store directly without triggering embedding model
        loading, avoiding a 30+ second delay on first use.

        Returns:
            True if store has at least one chunk, False otherwise

        Example:
            >>> if retriever.has_indexed_memory():
            ...     chunks = retriever.retrieve("query")

        """
        if self._store is None:
            return False

        try:
            # Check store directly without loading embedding model
            # This avoids the 30+ second model loading delay
            chunk_count = self._store.get_chunk_count()
            return chunk_count > 0
        except AttributeError:
            # Fallback: if store doesn't have get_chunk_count, use retrieve_by_activation
            try:
                results = self._store.retrieve_by_activation(min_activation=0.0, limit=1)
                return len(results) > 0
            except Exception as e:
                logger.warning("Error checking indexed memory: %s", e)
                return False
        except Exception as e:
            logger.warning("Error checking indexed memory: %s", e)
            return False

    def retrieve(
        self,
        query: str,
        limit: int = 20,
        _mode: str = "hybrid",
        min_semantic_score: float | None = None,
        wait_for_model: bool = True,
        chunk_type: str | None = None,
    ) -> list[CodeChunk]:
        """Retrieve relevant code chunks for a query.

        Uses hybrid retrieval combining semantic similarity, BM25,
        and activation scoring.

        Args:
            query: Search query text
            limit: Maximum number of chunks to return (default: 20)
            mode: Retrieval mode - 'hybrid' (default), 'semantic', or 'bm25'
            min_semantic_score: Minimum semantic score threshold (uses config default if None)
            wait_for_model: If True (default), wait for embedding model to load.
                           If False, return BM25+activation results immediately if model
                           is still loading (non-blocking fast path).

        Returns:
            List of CodeChunk objects sorted by relevance

        Example:
            >>> chunks = retriever.retrieve("authentication", limit=10)
            >>> for chunk in chunks:
            ...     print(f"{chunk.file_path}: {chunk.name}")

        """
        start_time = time.time()

        try:
            retriever = self._get_retriever_with_mode(wait_for_model=wait_for_model)

            # Use config threshold if not specified
            threshold = min_semantic_score
            if threshold is None:
                threshold = self._config.search_min_semantic_score if self._config else 0.7

            # Retrieve chunks using hybrid retriever
            results = retriever.retrieve(
                query,
                top_k=limit,
                min_semantic_score=threshold,
                chunk_type=chunk_type,
            )

            elapsed = time.time() - start_time
            if elapsed > RETRIEVE_LATENCY_TARGET:
                logger.debug(
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
            import traceback
            full_trace = traceback.format_exc()
            logger.error("Retrieval failed: %s", e)
            logger.error("Full traceback:\n%s", full_trace)
            # Also print to stderr for debugging
            import sys
            print(f"\nDEBUG ERROR: {type(e).__name__}: {e}", file=sys.stderr)
            print(full_trace, file=sys.stderr)
            return []

    def retrieve_fast(
        self,
        query: str,
        limit: int = 20,
        min_semantic_score: float | None = None,
    ) -> tuple[list[CodeChunk], bool]:
        """Fast retrieval that returns immediately, using BM25-only if model is loading.

        This method provides the fastest possible response time by:
        1. If embedding model is ready: uses full hybrid retrieval
        2. If model is still loading: returns BM25+activation results immediately

        Args:
            query: Search query text
            limit: Maximum number of chunks to return (default: 20)
            min_semantic_score: Minimum semantic score threshold (uses config default if None)

        Returns:
            Tuple of (results, is_full_hybrid):
            - results: List of matching chunks
            - is_full_hybrid: True if semantic embeddings were used, False if BM25-only

        Example:
            >>> results, is_hybrid = retriever.retrieve_fast("authentication", limit=10)
            >>> if not is_hybrid:
            ...     print("Results are BM25-only (model still loading)")

        """
        # Check if model is ready (non-blocking check)
        model_ready = self.is_embedding_model_ready()

        # Perform retrieval (wait_for_model=False for fast path)
        results = self.retrieve(
            query,
            limit=limit,
            min_semantic_score=min_semantic_score,
            wait_for_model=False,  # Don't wait - use BM25-only if needed
        )

        return results, model_ready

    def _get_retriever_with_mode(self, wait_for_model: bool = True) -> Any:
        """Get or create HybridRetriever with specified waiting behavior.

        Args:
            wait_for_model: If True, wait for embedding model. If False, use BM25-only.

        Returns:
            HybridRetriever instance

        """
        if self._store is None:
            raise ValueError("Cannot retrieve: no memory store configured")

        # For non-waiting mode, always create fresh retriever with current embedding state
        # This ensures we use the latest embedding provider state
        if not wait_for_model:
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            from aurora_core.activation.engine import ActivationEngine

            activation_engine = ActivationEngine()
            embedding_provider = self._get_embedding_provider(wait_for_model=False)

            return HybridRetriever(
                self._store,
                activation_engine,
                embedding_provider,  # None = BM25-only mode
            )

        # Standard path: use cached retriever (creates if needed)
        return self._get_retriever()

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
            logger.debug(
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
            return [], "No valid context files found"

        # Priority 2: Indexed memory
        if self.has_indexed_memory():
            chunks = self.retrieve(query, limit=limit)
            if chunks:
                return chunks, ""
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
