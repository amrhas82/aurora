"""Memory infrastructure module for AURORA CLI.

This module provides a shared MemoryRetriever API for accessing indexed
code memory with support for:
- Hybrid retrieval (semantic + BM25 + activation)
- Direct file context loading
- Formatted output for LLM consumption

Main Components:
    MemoryRetriever: Primary API for memory retrieval operations

Example:
    >>> from aurora_cli.memory import MemoryRetriever
    >>> from aurora_cli.config import load_config
    >>> from aurora_core.store import SQLiteStore
    >>>
    >>> config = load_config()
    >>> store = SQLiteStore(config.get_db_path())
    >>> retriever = MemoryRetriever(store, config)
    >>>
    >>> # Check if memory is available
    >>> if retriever.has_indexed_memory():
    ...     chunks = retriever.retrieve("authentication", limit=10)
    ...     formatted = retriever.format_for_prompt(chunks)

"""

from aurora_cli.memory.retrieval import MemoryRetriever


__all__ = ["MemoryRetriever"]
