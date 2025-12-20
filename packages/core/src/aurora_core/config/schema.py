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
            "pattern": "^[0-9]+\\.[0-9]+$",
            "description": "Configuration schema version (e.g., '1.0')"
        },
        "mode": {
            "type": "string",
            "enum": ["standalone", "mcp_integrated"],
            "default": "standalone",
            "description": "Operating mode: standalone or integrated with MCP"
        },
        "storage": {
            "type": "object",
            "required": ["type", "path"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["sqlite", "memory"],
                    "description": "Storage backend type"
                },
                "path": {
                    "type": "string",
                    "description": "Path to storage file (supports ~ expansion)"
                },
                "max_connections": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum database connections"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 5,
                    "description": "Database operation timeout in seconds"
                }
            },
            "additionalProperties": False
        },
        "llm": {
            "type": "object",
            "required": ["reasoning_provider", "api_key_env"],
            "properties": {
                "reasoning_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "custom"],
                    "description": "LLM provider for reasoning operations"
                },
                "reasoning_model": {
                    "type": "string",
                    "default": "claude-3-5-sonnet-20241022",
                    "description": "Model name for reasoning"
                },
                "solving_provider": {
                    "type": "string",
                    "enum": ["anthropic", "openai", "custom"],
                    "description": "LLM provider for solving operations (optional)"
                },
                "solving_model": {
                    "type": "string",
                    "description": "Model name for solving (optional)"
                },
                "api_key_env": {
                    "type": "string",
                    "pattern": "^[A-Z_][A-Z0-9_]*$",
                    "description": "Environment variable name containing API key"
                },
                "base_url": {
                    "type": ["string", "null"],
                    "format": "uri",
                    "description": "Custom API base URL (optional)"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 600,
                    "default": 30,
                    "description": "LLM API timeout in seconds"
                }
            },
            "additionalProperties": False
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
                            "description": "Enable code context provider"
                        },
                        "languages": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["python", "javascript", "typescript", "go", "rust"]
                            },
                            "minItems": 1,
                            "default": ["python"],
                            "description": "Supported programming languages"
                        },
                        "max_file_size_kb": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10000,
                            "default": 500,
                            "description": "Maximum file size to parse in KB"
                        },
                        "cache_ttl_hours": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 168,
                            "default": 24,
                            "description": "Cache TTL in hours"
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        },
        "agents": {
            "type": "object",
            "properties": {
                "discovery_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "default": [".aurora/agents.json", "~/.aurora/agents.json"],
                    "description": "Paths to search for agent configurations"
                },
                "refresh_interval_days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "default": 15,
                    "description": "Days between agent registry refreshes"
                },
                "fallback_mode": {
                    "type": "string",
                    "enum": ["llm_only", "error", "none"],
                    "default": "llm_only",
                    "description": "Behavior when no agents found"
                }
            },
            "additionalProperties": False
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "default": "INFO",
                    "description": "Logging level"
                },
                "path": {
                    "type": "string",
                    "default": "~/.aurora/logs/",
                    "description": "Log file directory"
                },
                "max_size_mb": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100,
                    "description": "Maximum log file size in MB"
                },
                "max_files": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 10,
                    "description": "Maximum number of log files to keep"
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False
}


def get_schema() -> dict[str, Any]:
    """
    Get the JSON schema for configuration validation.

    Returns:
        JSON Schema Draft 7 specification for AURORA configuration
    """
    return CONFIG_SCHEMA
