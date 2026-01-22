"""Database schema definitions for AURORA storage.

This module contains SQL DDL statements for creating and managing the
database schema used by SQLiteStore and potentially other SQL-based
storage implementations.
"""

# Schema version for migration tracking
SCHEMA_VERSION = 4  # Incremented for file_index table (incremental indexing)

# SQL statements for creating tables and indexes
CREATE_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,              -- Format: "code:file:func" or "reas:pattern-id"
    type TEXT NOT NULL,               -- "code" | "reasoning" | "knowledge"
    content JSON NOT NULL,            -- Chunk-specific JSON structure
    metadata JSON,                    -- Optional metadata
    embeddings BLOB,                  -- Embedding vector as serialized numpy array (for semantic retrieval)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_access TIMESTAMP,           -- First time chunk was accessed
    last_access TIMESTAMP             -- Most recent access time
);
"""

CREATE_CHUNKS_TYPE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_chunks_type ON chunks(type);
"""

CREATE_CHUNKS_CREATED_INDEX = """
CREATE INDEX IF NOT EXISTS idx_chunks_created ON chunks(created_at);
"""

CREATE_ACTIVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS activations (
    chunk_id TEXT PRIMARY KEY,
    base_level REAL NOT NULL,         -- Base-level activation (BLA)
    last_access TIMESTAMP NOT NULL,   -- Most recent access timestamp
    access_count INTEGER DEFAULT 1,   -- Total number of accesses
    access_history JSON,              -- Full access history as JSON array
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
"""

CREATE_ACTIVATIONS_BASE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_activations_base ON activations(base_level DESC);
"""

CREATE_ACTIVATIONS_LAST_ACCESS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_activations_last_access ON activations(last_access DESC);
"""

CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_chunk TEXT NOT NULL,
    to_chunk TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- "depends_on" | "calls" | "imports"
    weight REAL DEFAULT 1.0,
    FOREIGN KEY (from_chunk) REFERENCES chunks(id) ON DELETE CASCADE,
    FOREIGN KEY (to_chunk) REFERENCES chunks(id) ON DELETE CASCADE
);
"""

CREATE_RELATIONSHIPS_FROM_INDEX = """
CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_chunk);
"""

CREATE_RELATIONSHIPS_TO_INDEX = """
CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_chunk);
"""

# File index for incremental indexing (tracks indexed files with content hash)
CREATE_FILE_INDEX_TABLE = """
CREATE TABLE IF NOT EXISTS file_index (
    file_path TEXT PRIMARY KEY,       -- Relative path from project root
    content_hash TEXT NOT NULL,       -- SHA-256 of file content
    mtime REAL NOT NULL,              -- File modification time (seconds since epoch)
    indexed_at TIMESTAMP NOT NULL,    -- When this file was last indexed
    chunk_count INTEGER DEFAULT 0     -- Number of chunks extracted from this file
);
"""

CREATE_FILE_INDEX_HASH = """
CREATE INDEX IF NOT EXISTS idx_file_index_hash ON file_index(content_hash);
"""

# Schema version tracking table
CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Combined initialization script
INIT_SCHEMA = [
    CREATE_CHUNKS_TABLE,
    CREATE_CHUNKS_TYPE_INDEX,
    CREATE_CHUNKS_CREATED_INDEX,
    CREATE_ACTIVATIONS_TABLE,
    CREATE_ACTIVATIONS_BASE_INDEX,
    CREATE_ACTIVATIONS_LAST_ACCESS_INDEX,
    CREATE_RELATIONSHIPS_TABLE,
    CREATE_RELATIONSHIPS_FROM_INDEX,
    CREATE_RELATIONSHIPS_TO_INDEX,
    CREATE_FILE_INDEX_TABLE,
    CREATE_FILE_INDEX_HASH,
    CREATE_SCHEMA_VERSION_TABLE,
]


def get_schema_version_insert(version: int = SCHEMA_VERSION) -> str:
    """Generate SQL to record schema version.

    Args:
        version: Schema version number to record

    Returns:
        SQL INSERT statement

    """
    return f"INSERT OR REPLACE INTO schema_version (version) VALUES ({version});"


def get_init_statements() -> list[str]:
    """Get all initialization SQL statements including version tracking.

    Returns:
        List of SQL statements to initialize the database schema

    """
    return INIT_SCHEMA + [get_schema_version_insert()]


__all__ = [
    "SCHEMA_VERSION",
    "CREATE_CHUNKS_TABLE",
    "CREATE_ACTIVATIONS_TABLE",
    "CREATE_RELATIONSHIPS_TABLE",
    "CREATE_FILE_INDEX_TABLE",
    "INIT_SCHEMA",
    "get_schema_version_insert",
    "get_init_statements",
]
