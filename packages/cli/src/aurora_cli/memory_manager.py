"""Memory manager for AURORA CLI.

This module provides the MemoryManager class for indexing code files into the
memory store and searching the indexed content. It handles progress reporting,
file discovery, parsing, and embedding generation.

Performance Optimizations:
- Parallel file parsing with ThreadPoolExecutor
- Batch embedding generation (32+ chunks at a time)
- File-level git blame caching (one git call per file)
- Incremental indexing with content hashing (skip unchanged files)
- Git-based fast path for change detection in repositories
- Automatic cleanup of deleted files from index
- Connection pooling with WAL mode for concurrent writes
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from aurora_cli.config import Config
from aurora_cli.errors import ErrorHandler, MemoryStoreError
from aurora_cli.ignore_patterns import load_ignore_patterns, should_ignore
from aurora_context_code.git import GitSignalExtractor
from aurora_context_code.registry import ParserRegistry, get_global_registry
from aurora_core.chunks import Chunk
from aurora_core.store import SQLiteStore
from aurora_core.types import ChunkID

if TYPE_CHECKING:
    from aurora_context_code.semantic import EmbeddingProvider
    from aurora_core.store.base import Store


logger = logging.getLogger(__name__)


# Global background access recorder (singleton pattern)
_access_recorder: BackgroundAccessRecorder | None = None
_access_recorder_lock = threading.Lock()


def get_access_recorder(store: Any) -> BackgroundAccessRecorder:
    """Get or create the singleton background access recorder.

    Args:
        store: Memory store for recording access

    Returns:
        BackgroundAccessRecorder instance

    """
    global _access_recorder
    with _access_recorder_lock:
        if _access_recorder is None or _access_recorder._store != store:
            if _access_recorder is not None:
                _access_recorder.shutdown()
            _access_recorder = BackgroundAccessRecorder(store)
        return _access_recorder


class BackgroundAccessRecorder:
    """Background worker for async access recording.

    Records chunk accesses in a background thread to avoid blocking search results.
    This improves search latency by ~13ms per search (for 10 results).

    Access records are queued and processed asynchronously, with the worker
    draining the queue in batches for efficiency.
    """

    def __init__(self, store: Any, max_queue_size: int = 1000):
        """Initialize the background access recorder.

        Args:
            store: Memory store instance (SQLiteStore)
            max_queue_size: Maximum items in queue before dropping oldest

        """
        self._store = store
        self._queue: Queue[tuple[ChunkID, datetime, str | None]] = Queue(maxsize=max_queue_size)
        self._shutdown = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_worker()

    def _start_worker(self) -> None:
        """Start the background worker thread."""
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.debug("Started background access recorder thread")

    def _worker_loop(self) -> None:
        """Worker loop that processes access records from the queue."""
        while not self._shutdown.is_set():
            try:
                # Wait for items with timeout to allow shutdown check
                chunk_id, access_time, context = self._queue.get(timeout=0.5)
                try:
                    self._store.record_access(
                        chunk_id=chunk_id,
                        access_time=access_time,
                        context=context,
                    )
                except Exception as e:
                    logger.debug(f"Background access recording failed for {chunk_id}: {e}")
                finally:
                    self._queue.task_done()
            except Empty:
                # Timeout - check shutdown flag and continue
                continue

    def record_access(
        self,
        chunk_id: ChunkID,
        access_time: datetime,
        context: str | None = None,
    ) -> None:
        """Queue an access record for background processing.

        Args:
            chunk_id: Chunk that was accessed
            access_time: When the access occurred
            context: Optional context (e.g., query string)

        """
        try:
            # Non-blocking put with drop-oldest semantics
            if self._queue.full():
                try:
                    self._queue.get_nowait()  # Drop oldest
                except Empty:
                    pass
            self._queue.put_nowait((chunk_id, access_time, context))
        except Exception as e:
            logger.debug(f"Failed to queue access record: {e}")

    def shutdown(self, timeout: float = 2.0) -> None:
        """Shutdown the background worker.

        Args:
            timeout: Maximum time to wait for queue drain

        """
        self._shutdown.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.debug("Background access recorder shutdown")


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file to hash

    Returns:
        Hex-encoded SHA-256 hash string

    """
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read in 64KB chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        # Return empty hash if file can't be read
        return ""


def get_git_changed_files(root: Path) -> set[str] | None:
    """Get files changed in git working directory.

    Uses git status to identify modified, added, and untracked files.
    This provides a fast path for incremental indexing in git repos.

    Args:
        root: Root directory of git repository

    Returns:
        Set of relative file paths that have changes, or None if not a git repo

    """
    import subprocess

    try:
        # Check if this is a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        # Get modified and untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None

        changed = set()
        for line in result.stdout.splitlines():
            if len(line) < 4:
                continue
            # Status is first two chars, path starts at char 3
            status = line[:2].strip()
            path = line[3:]
            # Include modified (M), added (A), untracked (??), and renamed (R)
            if status in ("M", "A", "??", "AM", "MM", "R", "RM"):
                # Handle renamed files (format: "R  old -> new")
                if " -> " in path:
                    path = path.split(" -> ")[1]
                changed.add(path)

        return changed
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


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
class IndexProgress:
    """Progress information for indexing operation.

    Attributes:
        phase: Current phase name ("discovering", "parsing", "git_blame", "embedding", "storing")
        current: Current item number within phase
        total: Total items in phase
        file_path: Current file being processed (if applicable)
        detail: Additional detail string (e.g., function name)

    """

    phase: str
    current: int
    total: int
    file_path: str | None = None
    detail: str | None = None


@dataclass
class IndexStats:
    """Statistics from indexing operation.

    Attributes:
        files_indexed: Number of files successfully indexed
        chunks_created: Number of code chunks created
        duration_seconds: Total indexing duration
        errors: Number of files that failed to parse
        warnings: Number of files with parse warnings (partial results)
        files_skipped: Number of files skipped (unchanged in incremental mode)
        files_deleted: Number of deleted files cleaned up from index
        parallel_workers: Number of parallel workers used

    """

    files_indexed: int
    chunks_created: int
    duration_seconds: float
    errors: int = 0
    warnings: int = 0
    files_skipped: int = 0
    files_deleted: int = 0
    parallel_workers: int = 1


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
        bm25_score: BM25 keyword matching score
        hybrid_score: Combined hybrid score
        metadata: Additional metadata dictionary

    """

    chunk_id: str
    file_path: str
    line_range: tuple[int, int]
    content: str
    activation_score: float
    semantic_score: float
    bm25_score: float
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
        last_indexed: Last indexing timestamp (ISO format) or None
        failed_files: List of (file_path, error_message) tuples
        warnings: List of warning messages
        success_rate: Percentage of parseable files successfully indexed (0.0-1.0)
        files_by_language: Dictionary mapping language to indexed file count
        total_parseable: Total parseable files discovered

    """

    total_chunks: int
    total_files: int
    languages: dict[str, int]
    database_size_mb: float
    last_indexed: str | None = None
    failed_files: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    success_rate: float = 1.0
    files_by_language: dict[str, int] = field(default_factory=dict)
    total_parseable: int = 0


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
            embedding_provider: Optional embedding provider (lazy-loaded if None)

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
        self._embedding_provider = embedding_provider  # Lazy-loaded via property
        self.error_handler = ErrorHandler()
        logger.info("MemoryManager initialized")

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        """Get embedding provider (lazy-loaded on first access).

        Sets HF_HUB_OFFLINE=1 if model is cached to prevent network requests.
        """
        if self._embedding_provider is None:
            from aurora_context_code.semantic.model_utils import is_model_cached

            if is_model_cached():
                os.environ["HF_HUB_OFFLINE"] = "1"
            from aurora_context_code.semantic import EmbeddingProvider

            self._embedding_provider = EmbeddingProvider()
        return self._embedding_provider

    def index_path(
        self,
        path: str | Path,
        progress_callback: (
            Callable[[int, int], None] | Callable[[IndexProgress], None] | None
        ) = None,
        batch_size: int = 32,
        max_workers: int | None = None,
        incremental: bool = True,
    ) -> IndexStats:
        """Index all code files in the given path.

        Recursively discovers code files, parses them, generates embeddings,
        and stores chunks in the memory store. Reports progress via callback.

        Uses optimized pipeline:
        1. Parallel file parsing with ThreadPoolExecutor
        2. File-level git blame caching (one git call per file, not per function)
        3. Batch embedding generation (32 chunks at a time by default)
        4. Incremental indexing (skip unchanged files based on mtime)
        5. Batched database writes

        Args:
            path: Directory or file path to index
            progress_callback: Optional callback. Can be either:
                - Simple: callback(files_processed, total_files) - legacy
                - Rich: callback(IndexProgress) - shows phases
            batch_size: Number of chunks to embed at once (default 32)
            max_workers: Maximum parallel workers for parsing (None = auto: min(8, cpu_count))
            incremental: Skip unchanged files based on mtime (default True)

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
        stats = {"files": 0, "chunks": 0, "errors": 0, "warnings": 0, "skipped": 0}
        files_by_language: dict[str, int] = {}  # Track indexed files by language
        failed_files: list[tuple[str, str]] = []  # (file_path, error_message)
        warning_messages: list[str] = []
        skipped_files: list[tuple[str, str]] = []  # (file_path, reason)

        # Determine worker count: default to min(8, cpu_count) for I/O-bound work
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            actual_workers = min(8, cpu_count)
        else:
            actual_workers = max_workers

        # Detect callback type (rich vs simple)
        def report_progress(progress: IndexProgress) -> None:
            """Report progress, adapting to callback type."""
            if progress_callback is None:
                return
            try:
                # Try rich callback first (IndexProgress)
                progress_callback(progress)  # type: ignore
            except TypeError:
                # Fall back to simple callback (current, total)
                progress_callback(progress.current, progress.total)  # type: ignore

        try:
            # Phase 1: Discover files
            report_progress(IndexProgress("discovering", 0, 0, detail="Scanning directory..."))

            if path_obj.is_file():
                files = [path_obj]
            else:
                files = self._discover_files(path_obj)

            # Note: _discover_files only returns files with parsers, so total_files
            # equals parseable files. Success rate = indexed / parseable.
            total_files = len(files)
            logger.info(f"Discovered {total_files} code files in {path}")

            # Incremental indexing with content hashing and git integration
            files_to_process: list[Path] = []
            deleted_count = 0

            if incremental:
                report_progress(
                    IndexProgress("checking", 0, total_files, detail="Checking for changes..."),
                )

                # Load file index from database (content hashes and mtimes)
                file_index = self._load_file_index()

                # Try git-based fast path first (much faster for git repos)
                git_changed = get_git_changed_files(path_obj) if path_obj.is_dir() else None

                # Build set of current file paths for cleanup detection
                current_file_set = {str(f) for f in files}

                for file_path in files:
                    file_key = str(file_path)
                    rel_key = (
                        str(file_path.relative_to(path_obj)) if path_obj.is_dir() else file_key
                    )

                    try:
                        current_mtime = file_path.stat().st_mtime
                        cached_info = file_index.get(file_key)

                        # Fast path 1: Git says file unchanged and we have it indexed
                        if git_changed is not None and cached_info is not None:
                            if rel_key not in git_changed:
                                # Git says unchanged, trust it
                                stats["skipped"] += 1
                                skipped_files.append((file_key, "Unchanged (git)"))
                                continue

                        # Fast path 2: mtime unchanged
                        if cached_info is not None and current_mtime <= cached_info["mtime"]:
                            stats["skipped"] += 1
                            skipped_files.append((file_key, "Unchanged (mtime)"))
                            continue

                        # Medium path: mtime changed, check content hash
                        if cached_info is not None:
                            current_hash = compute_file_hash(file_path)
                            if current_hash and current_hash == cached_info.get("hash"):
                                # Content unchanged (file touched but not modified)
                                stats["skipped"] += 1
                                skipped_files.append((file_key, "Unchanged (hash)"))
                                # Update mtime in cache so next check is faster
                                self._update_file_index_mtime(file_key, current_mtime)
                                continue

                    except OSError:
                        pass  # Process file if we can't stat it

                    files_to_process.append(file_path)

                # Cleanup: find and remove chunks from deleted files
                deleted_count = self._cleanup_deleted_files(file_index, current_file_set)
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} deleted files from index")

                logger.info(
                    f"Incremental: {len(files_to_process)} changed, {stats['skipped']} unchanged, {deleted_count} deleted",
                )
            else:
                files_to_process = files

            stats["deleted"] = deleted_count

            # Track file info for successfully indexed files (hash + mtime)
            new_file_info: dict[str, dict[str, Any]] = {}

            # Initialize Git signal extractor for this directory
            # The extractor now uses file-level blame caching for efficiency
            try:
                git_extractor = GitSignalExtractor()
                logger.debug(f"Initialized GitSignalExtractor for {path}")
            except Exception as e:
                logger.warning(
                    f"Could not initialize Git extractor: {e}. Using default BLA values.",
                )
                git_extractor = None

            # Batch accumulator for embedding generation
            pending_chunks: list[tuple[Any, str, float, int, str]] = (
                []
            )  # (chunk, content, bla, commit_count, file_path)
            total_chunks_processed = 0

            def flush_batch() -> None:
                """Process accumulated chunks with batch embedding."""
                nonlocal pending_chunks, total_chunks_processed
                if not pending_chunks:
                    return

                batch_len = len(pending_chunks)

                report_progress(
                    IndexProgress(
                        "embedding",
                        total_chunks_processed,
                        total_chunks_processed + batch_len,
                        detail=f"Batch of {batch_len} chunks",
                    ),
                )

                # Extract texts for batch embedding
                texts = [content for _, content, _, _, _ in pending_chunks]

                # Batch embed all chunks at once
                embeddings = self.embedding_provider.embed_batch(texts, batch_size=batch_size)

                report_progress(
                    IndexProgress(
                        "storing",
                        total_chunks_processed,
                        total_chunks_processed + batch_len,
                        detail=f"Writing {batch_len} chunks to database",
                    ),
                )

                # Store each chunk with its embedding
                for i, (chunk, _, initial_bla, commit_count, _) in enumerate(pending_chunks):
                    chunk.embeddings = embeddings[i].tobytes()
                    self._save_chunk_with_retry(chunk)
                    chunk_id = chunk.id

                    # Update activation with Git-derived values
                    if initial_bla != 0.0 or commit_count > 0:
                        try:
                            if hasattr(self.memory_store, "_transaction"):
                                with self.memory_store._transaction() as conn:
                                    conn.execute(
                                        """
                                        UPDATE activations
                                        SET base_level = ?, access_count = ?
                                        WHERE chunk_id = ?
                                        """,
                                        (initial_bla, commit_count, chunk_id),
                                    )
                        except Exception as e:
                            logger.debug(f"Could not update activation for {chunk.name}: {e}")

                    stats["chunks"] += 1
                    total_chunks_processed += 1

                pending_chunks = []

            # Phase 2: Parallel file parsing
            # Parse files in parallel using ThreadPoolExecutor
            # This is safe because parsing is stateless and read-only
            processed_count = 0
            total_to_process = len(files_to_process)

            if actual_workers > 1 and total_to_process > 1:
                logger.info(f"Using {actual_workers} parallel workers for parsing")
                report_progress(
                    IndexProgress(
                        "parsing",
                        0,
                        total_to_process,
                        detail=f"Parallel parsing ({actual_workers} workers)",
                    ),
                )

                # Define the parsing function for parallel execution
                def parse_single_file(file_path: Path) -> dict[str, Any]:
                    """Parse a single file and return results (thread-safe)."""
                    result: dict[str, Any] = {
                        "file_path": file_path,
                        "chunks": [],
                        "language": None,
                        "error": None,
                        "warning": False,
                    }

                    try:
                        parser = self.parser_registry.get_parser_for_file(file_path)
                        if not parser:
                            result["error"] = "No parser available"
                            return result

                        result["language"] = parser.language

                        # Parse the file (tree-sitter is thread-safe)
                        chunks = parser.parse(file_path)

                        if not chunks:
                            result["error"] = "No extractable elements"
                            return result

                        result["chunks"] = chunks
                        return result

                    except Exception as e:
                        result["error"] = str(e).split("\n")[0][:100]
                        return result

                # Execute parsing in parallel
                with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                    # Submit all parsing tasks
                    future_to_file = {
                        executor.submit(parse_single_file, fp): fp for fp in files_to_process
                    }

                    # Process results as they complete
                    for future in as_completed(future_to_file):
                        file_path = future_to_file[future]
                        processed_count += 1

                        # Update progress
                        report_progress(
                            IndexProgress(
                                "parsing",
                                processed_count,
                                total_to_process,
                                file_path=str(file_path.name),
                                detail=f"Parsed {processed_count}/{total_to_process}",
                            ),
                        )

                        try:
                            result = future.result()

                            if result["error"]:
                                if result["error"] == "No extractable elements":
                                    skipped_files.append((str(file_path), result["error"]))
                                else:
                                    stats["errors"] += 1
                                    failed_files.append((str(file_path), result["error"]))
                                continue

                            chunks = result["chunks"]
                            lang = result["language"]

                            # Git blame phase (sequential, uses cache)
                            if git_extractor and chunks:
                                report_progress(
                                    IndexProgress(
                                        "git_blame",
                                        processed_count,
                                        total_to_process,
                                        file_path=str(file_path.name),
                                        detail=f"Git history for {file_path.name}",
                                    ),
                                )

                            # Process all chunks for this file
                            for chunk in chunks:
                                initial_bla = 0.5
                                commit_count = 0

                                if (
                                    git_extractor
                                    and hasattr(chunk, "line_start")
                                    and hasattr(chunk, "line_end")
                                ):
                                    try:
                                        commit_times = git_extractor.get_function_commit_times(
                                            file_path=str(file_path),
                                            line_start=chunk.line_start,
                                            line_end=chunk.line_end,
                                        )

                                        if commit_times:
                                            initial_bla = git_extractor.calculate_bla(
                                                commit_times,
                                                decay=0.5,
                                            )
                                            commit_count = len(commit_times)

                                            if (
                                                not hasattr(chunk, "metadata")
                                                or chunk.metadata is None
                                            ):
                                                chunk.metadata = {}

                                            chunk.metadata["git_hash"] = commit_times[0]
                                            chunk.metadata["last_modified"] = commit_times[0]
                                            chunk.metadata["commit_count"] = commit_count
                                    except Exception as e:
                                        logger.debug(
                                            f"Could not extract Git signals for {chunk.name}: {e}",
                                        )

                                # Build content and add to batch
                                content_to_embed = self._build_chunk_content(chunk)
                                pending_chunks.append(
                                    (
                                        chunk,
                                        content_to_embed,
                                        initial_bla,
                                        commit_count,
                                        str(file_path),
                                    ),
                                )

                                # Flush batch when it reaches batch_size
                                if len(pending_chunks) >= batch_size:
                                    flush_batch()

                            stats["files"] += 1
                            files_by_language[lang] = files_by_language.get(lang, 0) + 1

                            # Record file info for incremental indexing (hash + mtime + chunk count)
                            try:
                                file_key = str(file_path)
                                new_file_info[file_key] = {
                                    "hash": compute_file_hash(file_path),
                                    "mtime": file_path.stat().st_mtime,
                                    "chunk_count": len(chunks),
                                }
                            except OSError:
                                pass

                            logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")

                        except Exception as e:
                            logger.debug(f"Failed to index {file_path}: {e}")
                            stats["errors"] += 1
                            error_msg = str(e).split("\n")[0][:100]
                            failed_files.append((str(file_path), error_msg))

            else:
                # Sequential processing (single worker or single file)
                for i, file_path in enumerate(files_to_process):
                    try:
                        # Report parsing progress
                        report_progress(
                            IndexProgress(
                                "parsing",
                                i,
                                total_to_process,
                                file_path=str(file_path.name),
                                detail=f"Parsing {file_path.name}",
                            ),
                        )

                        # Parse file
                        parser = self.parser_registry.get_parser_for_file(file_path)
                        if not parser:
                            logger.debug(f"No parser for {file_path}, skipping")
                            continue

                        chunks = parser.parse(file_path)

                        if not chunks:
                            logger.debug(f"No chunks extracted from {file_path}")
                            skipped_files.append((str(file_path), "No extractable elements"))
                            continue

                        # Report git blame phase
                        if git_extractor and chunks:
                            report_progress(
                                IndexProgress(
                                    "git_blame",
                                    i,
                                    total_to_process,
                                    file_path=str(file_path.name),
                                    detail=f"Git history for {file_path.name}",
                                ),
                            )

                        # Process all chunks for this file
                        for chunk in chunks:
                            initial_bla = 0.5
                            commit_count = 0

                            if (
                                git_extractor
                                and hasattr(chunk, "line_start")
                                and hasattr(chunk, "line_end")
                            ):
                                try:
                                    commit_times = git_extractor.get_function_commit_times(
                                        file_path=str(file_path),
                                        line_start=chunk.line_start,
                                        line_end=chunk.line_end,
                                    )

                                    if commit_times:
                                        initial_bla = git_extractor.calculate_bla(
                                            commit_times,
                                            decay=0.5,
                                        )
                                        commit_count = len(commit_times)

                                        if not hasattr(chunk, "metadata") or chunk.metadata is None:
                                            chunk.metadata = {}

                                        chunk.metadata["git_hash"] = commit_times[0]
                                        chunk.metadata["last_modified"] = commit_times[0]
                                        chunk.metadata["commit_count"] = commit_count
                                except Exception as e:
                                    logger.debug(
                                        f"Could not extract Git signals for {chunk.name}: {e}",
                                    )

                            # Build content and add to batch
                            content_to_embed = self._build_chunk_content(chunk)
                            pending_chunks.append(
                                (
                                    chunk,
                                    content_to_embed,
                                    initial_bla,
                                    commit_count,
                                    str(file_path),
                                ),
                            )

                            # Flush batch when it reaches batch_size
                            if len(pending_chunks) >= batch_size:
                                flush_batch()

                        stats["files"] += 1
                        lang = parser.language if parser else "unknown"
                        files_by_language[lang] = files_by_language.get(lang, 0) + 1

                        # Record file info for incremental indexing (hash + mtime + chunk count)
                        try:
                            file_key = str(file_path)
                            new_file_info[file_key] = {
                                "hash": compute_file_hash(file_path),
                                "mtime": file_path.stat().st_mtime,
                                "chunk_count": len(chunks),
                            }
                        except OSError:
                            pass

                        logger.debug(f"Indexed {file_path}: {len(chunks)} chunks")

                    except MemoryStoreError:
                        raise
                    except Exception as e:
                        logger.debug(f"Failed to index {file_path}: {e}")
                        stats["errors"] += 1
                        error_msg = str(e).split("\n")[0][:100]
                        failed_files.append((str(file_path), error_msg))
                        continue

            # Flush any remaining chunks
            flush_batch()

            # Save file index for incremental indexing (content hashes + mtimes)
            if incremental and new_file_info:
                self._save_file_index(new_file_info)

            # Build and save BM25 index for faster search (eliminates 51% of search time)
            if stats["chunks"] > 0:
                report_progress(
                    IndexProgress(
                        "bm25_index",
                        stats["chunks"],
                        stats["chunks"],
                        detail="Building BM25 index",
                    ),
                )
                self._build_bm25_index()

            # Final progress
            report_progress(IndexProgress("complete", total_files, total_files, detail="Done"))

            duration = time.time() - start_time
            logger.info(
                f"Indexing complete: {stats['files']} files, "
                f"{stats['chunks']} chunks, {stats['errors']} errors, "
                f"{stats['warnings']} warnings, {stats['skipped']} skipped, "
                f"{duration:.2f}s ({actual_workers} workers)",
            )

            # Calculate success rate (indexed / parseable files)
            # total_files already only includes files with parsers
            success_rate = stats["files"] / total_files if total_files > 0 else 1.0

            # Save indexing metadata for stats command
            self._save_indexing_metadata(
                failed_files,
                warning_messages,
                success_rate,
                files_by_language,
                total_files,
            )

            # Write detailed log file
            self._write_index_log(
                path_obj,
                stats,
                failed_files,
                warning_messages,
                skipped_files,
                files_by_language,
                total_files,
                duration,
            )

            return IndexStats(
                files_indexed=stats["files"],
                chunks_created=stats["chunks"],
                duration_seconds=duration,
                errors=stats["errors"],
                warnings=stats["warnings"],
                files_skipped=stats["skipped"],
                files_deleted=stats.get("deleted", 0),
                parallel_workers=actual_workers,
            )

        except MemoryStoreError:
            # Re-raise memory store errors with formatted messages
            raise
        except Exception as e:
            logger.error(f"Indexing failed: {e}", exc_info=True)
            error_msg = self.error_handler.handle_memory_error(e, "indexing")
            raise MemoryStoreError(error_msg) from e

    def search(
        self,
        query: str,
        limit: int = 5,
        min_semantic_score: float | None = None,
    ) -> list[SearchResult]:
        """Search memory store for relevant chunks.

        Uses hybrid retrieval (keyword + semantic) to find the most relevant
        code chunks for the query.

        Args:
            query: Search query string
            limit: Maximum number of results to return
            min_semantic_score: Minimum semantic score threshold (0.0-1.0).
                If None, uses config value or no filtering.

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

            # Use config value as default if min_semantic_score not provided
            threshold = min_semantic_score
            if threshold is None and self.config is not None:
                threshold = self.config.search_min_semantic_score

            # Perform search
            results = retriever.retrieve(query, top_k=limit, min_semantic_score=threshold)

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
                        bm25_score=result.get("bm25_score", 0.0),
                        hybrid_score=result["hybrid_score"],
                        metadata=metadata,
                    ),
                )

            # Record access asynchronously in background thread (Issue #4: Activation Tracking)
            # This improves search latency by ~13ms by not blocking on DB writes
            access_time = datetime.now(timezone.utc)
            access_recorder = get_access_recorder(self.memory_store)
            for search_result in search_results:
                access_recorder.record_access(
                    chunk_id=ChunkID(search_result.chunk_id),
                    access_time=access_time,
                    context=query,
                )

            logger.info(f"Search returned {len(search_results)} results for '{query}'")
            logger.debug(f"Queued access recording for {len(search_results)} chunks")
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

            # Load indexing metadata (errors, warnings, timestamp)
            metadata = self._load_indexing_metadata()

            return MemoryStats(
                total_chunks=total_chunks,
                total_files=unique_files,
                languages=languages,
                database_size_mb=db_size_mb,
                last_indexed=metadata.get("last_indexed"),
                failed_files=metadata.get("failed_files", []),
                warnings=metadata.get("warnings", []),
                success_rate=metadata.get("success_rate", 1.0),
                files_by_language=metadata.get("files_by_language", {}),
                total_parseable=metadata.get("total_parseable", 0),
            )

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}", exc_info=True)
            raise RuntimeError(f"Failed to get memory stats: {e}") from e

    def _discover_files(self, root_path: Path) -> list[Path]:
        """Recursively discover all code files in directory.

        Respects .auroraignore file for custom exclusions.

        Args:
            root_path: Root directory to search

        Returns:
            List of file paths that can be parsed

        """
        files = []

        # Load ignore patterns (defaults + .auroraignore)
        ignore_patterns = load_ignore_patterns(root_path)

        for item in root_path.rglob("*"):
            # Skip directories in SKIP_DIRS
            if any(skip_dir in item.parts for skip_dir in SKIP_DIRS):
                continue

            # Skip files matching ignore patterns
            if should_ignore(item, root_path, ignore_patterns):
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
            Number of chunks in the database

        """
        try:
            # Use _transaction() context manager for direct SQL access
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM chunks")
                    result = cursor.fetchone()
                    return result[0] if result else 0
            else:
                logger.warning("Store does not support _transaction(), cannot count chunks")
                return 0
        except Exception as e:
            logger.warning(f"Failed to count chunks: {e}")
            return 0

    def _count_unique_files(self) -> int:
        """Count unique files in memory store.

        Returns:
            Number of unique files indexed

        """
        try:
            # Use _transaction() context manager for direct SQL access
            # file_path is stored in content JSON as content->>'$.file'
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    cursor = conn.execute(
                        "SELECT COUNT(DISTINCT json_extract(content, '$.file')) FROM chunks WHERE type = 'code'",
                    )
                    result = cursor.fetchone()
                    return result[0] if result else 0
            else:
                logger.warning("Store does not support _transaction(), cannot count files")
                return 0
        except Exception as e:
            logger.warning(f"Failed to count files: {e}")
            return 0

    def _get_language_distribution(self) -> dict[str, int]:
        """Get distribution of chunks by language.

        Returns:
            Dictionary mapping language name to chunk count

        """
        try:
            # Use _transaction() context manager for direct SQL access
            # language is stored in metadata JSON as metadata->>'$.language'
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    cursor = conn.execute(
                        """
                        SELECT json_extract(metadata, '$.language') as lang, COUNT(*) as count
                        FROM chunks
                        WHERE type = 'code'
                        GROUP BY lang
                        """,
                    )
                    results = cursor.fetchall()
                    return {row[0]: row[1] for row in results if row[0] is not None}
            else:
                logger.warning(
                    "Store does not support _transaction(), cannot get language distribution",
                )
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
                            f"(attempt {attempt + 1}/{max_retries})",
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

    def _get_metadata_path(self) -> Path:
        """Get path to indexing metadata file.

        Returns:
            Path to .aurora/.indexing_metadata.json

        """
        db_path = Path(self.config.get_db_path())
        return db_path.parent / ".indexing_metadata.json"

    def _get_mtime_cache_path(self) -> Path:
        """Get path to mtime cache file for incremental indexing.

        Returns:
            Path to .aurora/.mtime_cache.json

        """
        db_path = Path(self.config.get_db_path())
        return db_path.parent / ".mtime_cache.json"

    def _load_mtime_cache(self) -> dict[str, float]:
        """Load file modification time cache for incremental indexing.

        Returns:
            Dictionary mapping file paths to last indexed mtime

        """
        cache_path = self._get_mtime_cache_path()
        if not cache_path.exists():
            return {}

        try:
            data = json.loads(cache_path.read_text())
            # Validate cache structure
            if isinstance(data, dict):
                return {k: float(v) for k, v in data.items() if isinstance(v, (int, float))}
            return {}
        except Exception as e:
            logger.warning(f"Failed to load mtime cache: {e}")
            return {}

    def _save_mtime_cache(self, cache: dict[str, float]) -> None:
        """Save file modification time cache for incremental indexing.

        Args:
            cache: Dictionary mapping file paths to mtime

        """
        cache_path = self._get_mtime_cache_path()
        try:
            cache_path.write_text(json.dumps(cache))
        except Exception as e:
            logger.warning(f"Failed to save mtime cache: {e}")

    def _load_file_index(self) -> dict[str, dict[str, Any]]:
        """Load file index from database for incremental indexing.

        Returns:
            Dictionary mapping file paths to {"hash": str, "mtime": float, "chunk_count": int}

        """
        file_index: dict[str, dict[str, Any]] = {}

        try:
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    # Check if file_index table exists
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='file_index'",
                    )
                    if cursor.fetchone() is None:
                        # Table doesn't exist yet, return empty (will be created on save)
                        return {}

                    cursor = conn.execute(
                        "SELECT file_path, content_hash, mtime, chunk_count FROM file_index",
                    )
                    for row in cursor:
                        file_index[row[0]] = {
                            "hash": row[1],
                            "mtime": row[2],
                            "chunk_count": row[3] or 0,
                        }
        except Exception as e:
            logger.warning(f"Failed to load file index from database: {e}")
            # Fall back to mtime cache for backward compatibility
            mtime_cache = self._load_mtime_cache()
            for path, mtime in mtime_cache.items():
                file_index[path] = {"hash": "", "mtime": mtime, "chunk_count": 0}

        return file_index

    def _save_file_index(self, file_info: dict[str, dict[str, Any]]) -> None:
        """Save file index to database for incremental indexing.

        Args:
            file_info: Dictionary mapping file paths to {"hash": str, "mtime": float, "chunk_count": int}

        """
        try:
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    # Ensure table exists
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS file_index (
                            file_path TEXT PRIMARY KEY,
                            content_hash TEXT NOT NULL,
                            mtime REAL NOT NULL,
                            indexed_at TIMESTAMP NOT NULL,
                            chunk_count INTEGER DEFAULT 0
                        )
                    """,
                    )

                    now = datetime.now(timezone.utc).isoformat()
                    for file_path, info in file_info.items():
                        conn.execute(
                            """INSERT OR REPLACE INTO file_index
                               (file_path, content_hash, mtime, indexed_at, chunk_count)
                               VALUES (?, ?, ?, ?, ?)""",
                            (
                                file_path,
                                info["hash"],
                                info["mtime"],
                                now,
                                info.get("chunk_count", 0),
                            ),
                        )
        except Exception as e:
            logger.warning(f"Failed to save file index to database: {e}")

    def _update_file_index_mtime(self, file_path: str, mtime: float) -> None:
        """Update just the mtime for a file in the index (for touched-but-unchanged files).

        Args:
            file_path: Path to the file
            mtime: New modification time

        """
        try:
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    conn.execute(
                        "UPDATE file_index SET mtime = ? WHERE file_path = ?",
                        (mtime, file_path),
                    )
        except Exception as e:
            logger.debug(f"Failed to update mtime in file index: {e}")

    def _cleanup_deleted_files(
        self,
        file_index: dict[str, dict[str, Any]],
        current_files: set[str],
    ) -> int:
        """Remove chunks from files that no longer exist.

        Args:
            file_index: Current file index from database
            current_files: Set of file paths that currently exist

        Returns:
            Number of files cleaned up

        """
        deleted_count = 0

        # Find files in index that are no longer present
        indexed_paths = set(file_index.keys())
        deleted_paths = indexed_paths - current_files

        if not deleted_paths:
            return 0

        try:
            if hasattr(self.memory_store, "_transaction"):
                with self.memory_store._transaction() as conn:
                    for deleted_path in deleted_paths:
                        # Delete chunks associated with this file
                        # Chunks have file path stored in content JSON as content->>'$.file'
                        conn.execute(
                            """DELETE FROM chunks
                               WHERE type = 'code'
                               AND json_extract(content, '$.file') = ?""",
                            (deleted_path,),
                        )

                        # Delete from file_index
                        conn.execute(
                            "DELETE FROM file_index WHERE file_path = ?",
                            (deleted_path,),
                        )

                        deleted_count += 1
                        logger.debug(f"Cleaned up deleted file: {deleted_path}")

        except Exception as e:
            logger.warning(f"Failed to cleanup deleted files: {e}")

        return deleted_count

    def _load_indexing_metadata(self) -> dict:
        """Load indexing metadata from JSON file.

        Returns:
            Dictionary with metadata or empty dict if not found

        """
        import json

        metadata_path = self._get_metadata_path()
        if not metadata_path.exists():
            return {}

        try:
            return json.loads(metadata_path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load indexing metadata: {e}")
            return {}

    def _save_indexing_metadata(
        self,
        failed_files: list[tuple[str, str]],
        warnings: list[str],
        success_rate: float,
        files_by_language: dict[str, int] | None = None,
        total_parseable: int = 0,
    ) -> None:
        """Save indexing metadata to JSON file.

        Args:
            failed_files: List of (file_path, error_message) tuples
            warnings: List of warning messages
            success_rate: Success rate (0.0-1.0) - indexed / parseable files
            files_by_language: Dict mapping language to indexed file count
            total_parseable: Total parseable files discovered

        """
        import json

        metadata = {
            "last_indexed": datetime.now(timezone.utc).isoformat(),
            "failed_files": failed_files,
            "warnings": warnings,
            "success_rate": success_rate,
            "files_by_language": files_by_language or {},
            "total_parseable": total_parseable,
        }

        metadata_path = self._get_metadata_path()
        try:
            metadata_path.write_text(json.dumps(metadata, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save indexing metadata: {e}")

    def _write_index_log(
        self,
        indexed_path: Path,
        stats: dict,
        failed_files: list[tuple[str, str]],
        warnings: list[str],
        skipped_files: list[tuple[str, str]],
        files_by_language: dict[str, int],
        total_parseable: int,
        duration: float,
    ) -> None:
        """Write detailed indexing log to .aurora/logs/index.log.

        Args:
            indexed_path: Path that was indexed
            stats: Statistics dictionary
            failed_files: List of (file_path, error_message) tuples
            warnings: List of warning messages
            skipped_files: List of (file_path, reason) tuples
            files_by_language: Dict mapping language to file count
            total_parseable: Total parseable files discovered
            duration: Indexing duration in seconds

        """
        # Determine log directory (next to db or in indexed path)
        if self.config:
            db_path = Path(self.config.get_db_path())
            log_dir = db_path.parent / "logs"
        else:
            log_dir = indexed_path / ".aurora" / "logs"

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "index.log"

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            success_rate = stats["files"] / total_parseable * 100 if total_parseable > 0 else 100

            lines = [
                f"# Index Log - {timestamp}",
                f"# Path: {indexed_path}",
                "",
                "## Summary",
                f"Files indexed:    {stats['files']}",
                f"Total parseable:  {total_parseable}",
                f"Success rate:     {success_rate:.1f}%",
                f"Chunks created:   {stats['chunks']}",
                f"Duration:         {duration:.1f}s",
                "",
                "## Files by Language",
            ]

            for lang, count in sorted(files_by_language.items(), key=lambda x: -x[1]):
                lines.append(f"  {lang}: {count}")

            if failed_files:
                lines.append("")
                lines.append(f"## Failed Files ({len(failed_files)})")
                for file_path, error in failed_files:
                    lines.append(f"  {file_path}")
                    lines.append(f"    Error: {error}")

            if warnings:
                lines.append("")
                lines.append(f"## Warnings ({len(warnings)})")
                for warning in warnings:
                    lines.append(f"  {warning}")

            if skipped_files:
                lines.append("")
                lines.append(f"## Skipped Files ({len(skipped_files)})")
                lines.append(
                    "# Files with parsers but no extractable elements (empty or only comments)",
                )
                for file_path, reason in skipped_files:
                    lines.append(f"  {file_path}")

            lines.append("")

            log_path.write_text("\n".join(lines))
            logger.debug(f"Wrote index log to {log_path}")

        except Exception as e:
            logger.warning(f"Failed to write index log: {e}")

    def _build_bm25_index(self) -> bool:
        """Build and save BM25 index for faster search.

        This eliminates ~51% of search time by pre-building the BM25 index
        during indexing instead of rebuilding it on every query.

        Returns:
            True if index was built successfully, False otherwise

        """
        try:
            from aurora_context_code.semantic.hybrid_retriever import HybridRetriever
            from aurora_core.activation import ActivationEngine

            # Initialize retriever (embedding provider not needed for BM25 index)
            activation_engine = ActivationEngine()
            retriever = HybridRetriever(
                self.memory_store,
                activation_engine,
                embedding_provider=None,  # Not needed for BM25 indexing
            )

            # Build and save the BM25 index
            success = retriever.build_and_save_bm25_index()
            if success:
                logger.info("BM25 index built and saved successfully")
            else:
                logger.warning("Failed to build BM25 index")
            return success

        except Exception as e:
            logger.warning(f"Failed to build BM25 index: {e}")
            return False


__all__ = ["MemoryManager", "IndexStats", "IndexProgress", "SearchResult", "MemoryStats"]
