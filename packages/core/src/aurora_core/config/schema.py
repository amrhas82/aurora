"""
JSON schema for AURORA configuration validation.

Defines the JSON Schema Draft 7 specification for validating
configuration files according to PRD Section 4.6.
"""

from typing import Any

# JSON Schema Draft 7 for AURORA Configuration
CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AURORA Configuration",
    "description": "Configuration schema for AURORA agent system",
    "type": "object",
    "required": ["version", "storage", "llm"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": "^[0-9]+\\.[0-9]+(\\.[0-9]+)?$",
            "description": "Configuration schema version (e.g., '1.0' or '1.1.0')",
        },
        "mode": {
            "type": "string",
            "enum": ["standalone", "mcp_integrated"],
            "default": "standalone",
            "description": "Operating mode: standalone or integrated with MCP",
        },
        "storage": {
            "type": "object",
            "required": ["type", "path"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["sqlite", "memory"],
                    "description": "Storage backend type",
                },
                "path": {
                    "type": "string",
                    "description": "Path to storage file (supports ~ expansion)",
                },
                "max_connections": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum database connections",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 5,
                    "description": "Database operation timeout in seconds",
                },
            },
            "additionalProperties": False,
        },
        "llm": {
            "type": "object",
            "required": ["reasoning_provider", "api_key_env"],
            "properties": {
                "reasoning_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "custom"],
                    "description": "LLM provider for reasoning operations",
                },
                "reasoning_model": {
                    "type": "string",
                    "default": "claude-3-5-sonnet-20241022",
                    "description": "Model name for reasoning",
                },
                "solving_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "custom"],
                    "description": "LLM provider for solving operations (optional)",
                },
                "solving_model": {
                    "type": "string",
                    "description": "Model name for solving (optional)",
                },
                "api_key_env": {
                    "type": "string",
                    "pattern": "^[A-Z_][A-Z0-9_]*$",
                    "description": "Environment variable name containing API key",
                },
                "base_url": {
                    "type": ["string", "null"],
                    "format": "uri",
                    "description": "Custom API base URL (optional)",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 600,
                    "default": 30,
                    "description": "LLM API timeout in seconds",
                },
                "provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "custom"],
                    "description": "Legacy field - use reasoning_provider instead",
                },
                "model": {
                    "type": "string",
                    "description": "Legacy field - use reasoning_model instead",
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "default": 0.7,
                    "description": "LLM temperature parameter (0.0-2.0)",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "default": 4096,
                    "description": "Maximum tokens for LLM response",
                },
                "anthropic_api_key": {
                    "type": ["string", "null"],
                    "description": "Legacy field - use api_key_env instead",
                },
            },
            "additionalProperties": False,
        },
        "context": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "default": True,
                            "description": "Enable code context provider",
                        },
                        "languages": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["python", "javascript", "typescript", "go", "rust"],
                            },
                            "minItems": 1,
                            "default": ["python"],
                            "description": "Supported programming languages",
                        },
                        "max_file_size_kb": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10000,
                            "default": 500,
                            "description": "Maximum file size to parse in KB",
                        },
                        "cache_ttl_hours": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 168,
                            "default": 24,
                            "description": "Cache TTL in hours",
                        },
                        "hybrid_weights": {
                            "type": "object",
                            "properties": {
                                "activation": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                    "default": 0.6,
                                    "description": "Weight for activation-based scoring (0.0-1.0)",
                                },
                                "semantic": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                    "default": 0.4,
                                    "description": "Weight for semantic similarity scoring (0.0-1.0)",
                                },
                                "top_k": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 1000,
                                    "default": 100,
                                    "description": "Number of top chunks to retrieve by activation before hybrid scoring",
                                },
                                "fallback_to_activation": {
                                    "type": "boolean",
                                    "default": True,
                                    "description": "Fall back to activation-only if embeddings unavailable",
                                },
                            },
                            "additionalProperties": False,
                            "description": "Configuration for hybrid retrieval (activation + semantic)",
                        },
                    },
                    "additionalProperties": False,
                }
            },
            "additionalProperties": False,
        },
        "agents": {
            "type": "object",
            "properties": {
                "discovery_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [".aurora/agents.json", "~/.aurora/agents.json"],
                    "description": "Paths to search for agent configurations",
                },
                "refresh_interval_days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "default": 15,
                    "description": "Days between agent registry refreshes",
                },
                "fallback_mode": {
                    "type": "string",
                    "enum": ["llm_only", "error", "none"],
                    "default": "llm_only",
                    "description": "Behavior when no agents found",
                },
            },
            "additionalProperties": False,
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "default": "INFO",
                    "description": "Logging level",
                },
                "path": {
                    "type": "string",
                    "default": "~/.aurora/logs/",
                    "description": "Log file directory",
                },
                "max_size_mb": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100,
                    "description": "Maximum log file size in MB",
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum number of log files to keep",
                },
                "file": {
                    "type": "string",
                    "description": "Log file path (legacy field, use path instead)",
                },
            },
            "additionalProperties": False,
        },
        "escalation": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7,
                    "description": "Confidence threshold for escalation (0.0-1.0)",
                },
                "enable_keyword_only": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable keyword-only escalation mode",
                },
                "force_mode": {
                    "type": ["string", "null"],
                    "enum": ["aurora", "direct", None],
                    "default": None,
                    "description": "Force specific escalation mode (aurora/direct/none)",
                },
            },
            "additionalProperties": False,
            "description": "Escalation configuration for complex queries",
        },
        "mcp": {
            "type": "object",
            "properties": {
                "always_on": {
                    "type": "boolean",
                    "default": True,
                    "description": "Keep MCP server always active",
                },
                "log_file": {
                    "type": "string",
                    "default": "~/.aurora/mcp.log",
                    "description": "MCP server log file path",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 10,
                    "description": "Maximum number of results to return",
                },
            },
            "additionalProperties": False,
            "description": "Model Context Protocol server configuration",
        },
        "memory": {
            "type": "object",
            "properties": {
                "auto_index": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically index code on changes",
                },
                "index_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["."],
                    "description": "Paths to index for code search",
                },
                "chunk_size": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 10000,
                    "default": 1000,
                    "description": "Text chunk size for indexing",
                },
                "overlap": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 1000,
                    "default": 200,
                    "description": "Overlap between chunks in characters",
                },
            },
            "additionalProperties": False,
            "description": "Memory and indexing configuration",
        },
        "budget": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "minimum": 0,
                    "default": 5.0,
                    "description": "Budget limit in dollars",
                },
                "tracker_path": {
                    "type": "string",
                    "default": "~/.aurora/budget_tracker.json",
                    "description": "Path to budget tracker file",
                },
            },
            "additionalProperties": False,
            "description": "Budget tracking configuration",
        },
        "database": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "default": "~/.aurora/memory.db",
                    "description": "Path to SQLite database file",
                },
            },
            "additionalProperties": False,
            "description": "Database configuration",
        },
    },
    "additionalProperties": False,
}


def get_schema() -> dict[str, Any]:
    """
    Get the JSON schema for configuration validation.

    Returns:
        JSON Schema Draft 7 specification for AURORA configuration
    """
    return CONFIG_SCHEMA
