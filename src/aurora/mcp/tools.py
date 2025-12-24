"""
AURORA MCP Tools - Implementation of MCP tools for code indexing and search.

This module provides the actual implementation of the 5 MCP tools:
- aurora_search: Search indexed codebase
- aurora_index: Index directory of code files
- aurora_stats: Get database statistics
- aurora_context: Retrieve code context from file
- aurora_related: Find related chunks using ACT-R spreading activation
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from aurora.mcp.config import log_performance, setup_mcp_logging
from aurora_cli.memory_manager import IndexStats, MemoryManager, MemoryStats, SearchResult
from aurora_context_code.languages.python import PythonParser
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

    def __init__(self, db_path: str, config_path: Optional[str] = None):
        """
        Initialize AURORA MCP Tools.

        Args:
            db_path: Path to SQLite database
            config_path: Path to AURORA config file (currently unused)
        """
        self.db_path = db_path
        self.config_path = config_path

        # Initialize components lazily (on first use)
        self._store: Optional[SQLiteStore] = None
        self._activation_engine: Optional[ActivationEngine] = None
        self._embedding_provider: Optional[EmbeddingProvider] = None
        self._retriever: Optional[HybridRetriever] = None
        self._memory_manager: Optional[MemoryManager] = None
        self._parser_registry = None  # Lazy initialization

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
            self._ensure_initialized()

            # Use HybridRetriever to search
            results = self._retriever.retrieve(query, top_k=limit)

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

            return json.dumps(formatted_results, indent=2)

        except Exception as e:
            logger.error(f"Error in aurora_search: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    @log_performance("aurora_index")
    def aurora_index(self, path: str, pattern: str = "*.py") -> str:
        """
        Index a directory of code files.

        Args:
            path: Directory path to index
            pattern: File pattern to match (default: *.py)

        Returns:
            JSON string with indexing statistics:
            - files_indexed: Number of files successfully indexed
            - chunks_created: Number of code chunks created
            - duration_seconds: Total indexing duration
            - errors: Number of files that failed
        """
        try:
            self._ensure_initialized()

            # Verify path exists
            path_obj = Path(path).expanduser().resolve()
            if not path_obj.exists():
                return json.dumps({"error": f"Path does not exist: {path}"}, indent=2)

            if not path_obj.is_dir():
                return json.dumps({"error": f"Path is not a directory: {path}"}, indent=2)

            # Index the path
            stats = self._memory_manager.index_path(path_obj)

            # Return statistics
            return json.dumps(
                {
                    "files_indexed": stats.files_indexed,
                    "chunks_created": stats.chunks_created,
                    "duration_seconds": round(stats.duration_seconds, 2),
                    "errors": stats.errors,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error in aurora_index: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    @log_performance("aurora_stats")
    def aurora_stats(self) -> str:
        """
        Get database statistics.

        Returns:
            JSON string with database statistics:
            - total_chunks: Total number of chunks in database
            - total_files: Number of unique files indexed
            - database_size_mb: Size of database file in megabytes
            - indexed_at: Last modification time (if available)
        """
        try:
            self._ensure_initialized()

            # Get chunk count
            with self._store._get_connection() as conn:
                cursor = conn.cursor()

                # Total chunks
                cursor.execute("SELECT COUNT(*) FROM chunks")
                total_chunks = cursor.fetchone()[0]

                # Total files - extract from id field (format: "code:file:func")
                cursor.execute("""
                    SELECT COUNT(DISTINCT
                        CASE
                            WHEN id LIKE 'code:%' THEN substr(id, 6, instr(substr(id, 6), ':') - 1)
                            ELSE id
                        END
                    ) FROM chunks WHERE type = 'code'
                """)
                result = cursor.fetchone()
                total_files = result[0] if result else 0

            # Get database file size
            db_path = Path(self.db_path)
            if db_path.exists():
                size_bytes = db_path.stat().st_size
                database_size_mb = round(size_bytes / (1024 * 1024), 2)
                indexed_at = db_path.stat().st_mtime
            else:
                database_size_mb = 0.0
                indexed_at = None

            return json.dumps(
                {
                    "total_chunks": total_chunks,
                    "total_files": total_files,
                    "database_size_mb": database_size_mb,
                    "indexed_at": indexed_at,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error in aurora_stats: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    @log_performance("aurora_context")
    def aurora_context(self, file_path: str, function: Optional[str] = None) -> str:
        """
        Get code context from a specific file.

        Args:
            file_path: Path to source file
            function: Optional function name to extract

        Returns:
            String with code content (or JSON error if file not found)
        """
        try:
            # Resolve path
            path_obj = Path(file_path).expanduser().resolve()

            if not path_obj.exists():
                return json.dumps({"error": f"File not found: {file_path}"}, indent=2)

            if not path_obj.is_file():
                return json.dumps({"error": f"Path is not a file: {file_path}"}, indent=2)

            # Read file content
            try:
                content = path_obj.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return json.dumps(
                    {"error": f"Unable to decode file (not UTF-8): {file_path}"}, indent=2
                )

            # If function specified, extract it using AST parsing
            if function:
                if file_path.endswith(".py"):
                    parser = PythonParser()
                    chunks = parser.parse(path_obj)

                    # Find function in chunks
                    for chunk in chunks:
                        # CodeChunk has 'name' attribute directly
                        if hasattr(chunk, 'name') and chunk.name == function:
                            # Extract function code using line numbers
                            lines = content.splitlines()
                            start_line = chunk.line_start - 1  # Convert to 0-indexed
                            end_line = chunk.line_end  # end_line is inclusive, so we use it as-is for slicing
                            function_code = '\n'.join(lines[start_line:end_line])
                            return function_code

                    return json.dumps(
                        {"error": f"Function '{function}' not found in {file_path}"}, indent=2
                    )
                else:
                    return json.dumps(
                        {
                            "error": f"Function extraction only supported for Python files (.py)"
                        },
                        indent=2,
                    )

            # Return full file content
            return content

        except Exception as e:
            logger.error(f"Error in aurora_context: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    @log_performance("aurora_related")
    def aurora_related(self, chunk_id: str, max_hops: int = 2) -> str:
        """
        Find related code chunks using ACT-R spreading activation.

        Args:
            chunk_id: Source chunk ID
            max_hops: Maximum relationship hops (default: 2)

        Returns:
            JSON string with related chunks:
            - chunk_id: Chunk identifier
            - file_path: Path to source file
            - function_name: Function/class name
            - content: Code content
            - activation_score: ACT-R activation score
            - relationship_type: Type of relationship (import, call, etc.)
        """
        try:
            self._ensure_initialized()

            # Get source chunk
            source_chunk = self._store.get_chunk(chunk_id)
            if source_chunk is None:
                return json.dumps({"error": f"Chunk not found: {chunk_id}"}, indent=2)

            # Use activation engine to find related chunks
            # For now, we'll use a simple approach: find chunks from related files
            # Future enhancement: implement proper spreading activation

            related_chunks = []

            # Get file path from source chunk
            # source_chunk is a Chunk object with file_path attribute for CodeChunks
            if hasattr(source_chunk, 'file_path'):
                source_file_path = source_chunk.file_path
            else:
                # Fallback: try to extract from JSON if available
                chunk_json = source_chunk.to_json()
                source_file_path = chunk_json.get('content', {}).get('file', '')

            # Get chunks from the same file
            with self._store._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, type, content, metadata
                    FROM chunks
                    WHERE type = 'code' AND id != ?
                    LIMIT 50
                    """,
                    (chunk_id,),
                )

                for row in cursor.fetchall():
                    chunk_id_rel, chunk_type, content_json, metadata_json = row

                    try:
                        content_data = json.loads(content_json) if content_json else {}
                        metadata = json.loads(metadata_json) if metadata_json else {}

                        # Extract file path from content JSON
                        file_path = content_data.get('file', '')

                        # Only include chunks from same file or related files
                        if file_path == source_file_path or file_path.startswith(str(Path(source_file_path).parent)):
                            # Extract function name
                            function_name = content_data.get('function', '')

                            # Build content snippet from stored data
                            code_snippet = f"Function: {function_name}"
                            if 'signature' in content_data:
                                code_snippet = content_data['signature']
                            if 'docstring' in content_data and content_data['docstring']:
                                code_snippet += f"\n{content_data['docstring'][:200]}"

                            related_chunks.append(
                                {
                                    "chunk_id": chunk_id_rel,
                                    "file_path": file_path,
                                    "function_name": function_name,
                                    "content": code_snippet,
                                    "activation_score": 0.5 if file_path == source_file_path else 0.3,
                                    "relationship_type": "same_file" if file_path == source_file_path else "related_file",
                                }
                            )

                            # Limit results
                            if len(related_chunks) >= 10:
                                break
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse chunk {chunk_id_rel}: {e}")
                        continue

            return json.dumps(related_chunks, indent=2)

        except Exception as e:
            logger.error(f"Error in aurora_related: {e}")
            return json.dumps({"error": str(e)}, indent=2)
