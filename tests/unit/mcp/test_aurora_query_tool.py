"""Unit tests for aurora_query MCP tool (simplified after PRD-0008).

This module tests the simplified aurora_query tool that returns structured
context instead of calling LLM APIs directly.

Test Coverage:
- Basic parameter validation (empty query checks)
- Configuration loading (non-API-key aspects)

ARCHIVED TESTS: See tests/archive/2025-01-mcp-simplification/ for removed
LLM-related tests (API key handling, budget enforcement, auto-escalation,
retry logic, SOAR execution, etc.)

NEW TESTS: See test_aurora_query_simplified.py for new simplified behavior tests.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora_mcp.tools import AuroraMCPTools


# ==============================================================================
# Task 1.1: Basic Parameter Validation Tests
# ==============================================================================


class TestParameterValidation:
    """Test basic parameter validation for aurora_query tool."""

    @pytest.mark.mcp
    def test_empty_query_returns_error(self):
        """Empty query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()
        assert "suggestion" in response["error"]

    @pytest.mark.mcp
    def test_whitespace_only_query_returns_error(self):
        """Whitespace-only query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("   \n  \t  ")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()


# ==============================================================================
# Configuration Loading Tests (Non-API-Key Aspects)
# ==============================================================================


class TestConfigurationLoading:
    """Test configuration loading from file and environment (non-API-key aspects)."""

    def test_config_loaded_from_file(self, tmp_path):
        """Config should be loaded from ~/.aurora/config.json if exists."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Create .aurora directory and config file
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir(exist_ok=True)
        config_file = aurora_dir / "config.json"
        config_data = {"memory": {"default_limit": 20}}
        config_file.write_text(json.dumps(config_data), encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            # Clear any cached config
            if hasattr(tools, "_config_cache"):
                del tools._config_cache
            config = tools._load_config()
            assert config["memory"]["default_limit"] == 20

    def test_config_defaults_applied_when_missing(self):
        """Config defaults should be applied when file doesn't exist."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch("pathlib.Path.exists", return_value=False):
            config = tools._load_config()

            # Should have defaults
            assert "memory" in config

    def test_invalid_json_uses_defaults(self, tmp_path):
        """Invalid JSON in config file should use defaults (with warning)."""
        tools = AuroraMCPTools(db_path=":memory:")

        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }", encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("pathlib.Path.exists", return_value=True):
                config = tools._load_config()

                # Should fall back to defaults
                assert "memory" in config

    def test_config_cached_only_loaded_once(self):
        """Config should be cached and only loaded once per instance."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch("pathlib.Path.exists", return_value=False):
            # Load config twice
            config1 = tools._load_config()
            config2 = tools._load_config()

            # Should be same object (cached)
            assert config1 is config2
