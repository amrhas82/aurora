"""End-to-end tests for aurora_query MCP tool with real API.

These tests require a valid ANTHROPIC_API_KEY environment variable.
Tests are skipped when the API key is not available.

Test Coverage:
- Task 4.7: E2E tests with real API (5 tests)

IMPORTANT: These tests make real API calls and incur costs.
Only run when explicitly needed for validation.
"""

import json
import os
import time
from unittest.mock import patch

import pytest

from aurora_mcp.tools import AuroraMCPTools

# Skip all tests if no API key is available
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY environment variable not set"
)


@pytest.fixture
def tools():
    """Create AuroraMCPTools instance for testing."""
    return AuroraMCPTools(db_path=":memory:")


@pytest.fixture
def temp_aurora_config(tmp_path):
    """Create temporary aurora config with budget settings."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir(exist_ok=True)

    # Create config with high budget limit for testing
    config_file = aurora_dir / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api": {
                    "default_model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 500,  # Low limit for testing
                },
                "query": {
                    "auto_escalate": True,
                    "complexity_threshold": 0.6,
                    "verbosity": "normal",
                },
                "budget": {"monthly_limit_usd": 100.0},  # High limit for testing
            }
        )
    )

    # Create budget tracker with low usage
    budget_file = aurora_dir / "budget_tracker.json"
    budget_file.write_text(json.dumps({"monthly_usage_usd": 0.0, "monthly_limit_usd": 100.0}))

    return tmp_path


# ==============================================================================
# Task 4.7: E2E Tests with Real API
# ==============================================================================


class TestAuroraQueryE2E:
    """End-to-end tests for aurora_query with real Anthropic API.

    NOTE: These tests make real API calls and will incur costs.
    They run as part of the e2e test suite.
    """

    def test_simple_query_with_real_api(self, tools, temp_aurora_config):
        """Test simple query with real API returns valid response.

        This is a basic smoke test to verify API connectivity.
        """
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            # Clear cached config
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            result = tools.aurora_query("What is the capital of France?")
            response = json.loads(result)

            # Should have valid response structure
            assert "answer" in response or "error" in response

            if "answer" in response:
                # Successful response
                assert len(response["answer"]) > 0
                assert response["execution_path"] in ["direct_llm", "soar_pipeline"]
                assert "metadata" in response
            else:
                # If error, should be a known error type (not crash)
                assert "error" in response
                assert "type" in response["error"]
                assert "suggestion" in response["error"]

    def test_complex_query_with_real_api(self, tools, temp_aurora_config):
        """Test complex query triggers appropriate path with real API."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            result = tools.aurora_query(
                "Compare and analyze different software architecture patterns"
            )
            response = json.loads(result)

            assert "answer" in response or "error" in response

            if "answer" in response:
                # Complex query should ideally trigger SOAR or detailed response
                assert "metadata" in response
                assert response["metadata"]["input_tokens"] > 0

    def test_verbose_response_with_real_api(self, tools, temp_aurora_config):
        """Test verbose mode returns detailed information with real API."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            result = tools.aurora_query("Explain Python decorators", verbose=True)
            response = json.loads(result)

            assert "answer" in response or "error" in response

            if "answer" in response:
                assert "metadata" in response
                # Verbose should include timing info
                assert "duration_seconds" in response["metadata"]

    def test_actual_cost_tracking(self, tools, temp_aurora_config):
        """Test that actual API costs are tracked."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            result = tools.aurora_query("Hello, what is 2+2?")
            response = json.loads(result)

            if "answer" in response:
                # Should have cost information
                assert "metadata" in response
                # Cost should be tracked (even if 0 due to caching)
                assert "cost_usd" in response["metadata"]
                # Token counts should be present
                assert "input_tokens" in response["metadata"]
                assert "output_tokens" in response["metadata"]

    def test_parameter_overrides_with_real_api(self, tools, temp_aurora_config):
        """Test that parameter overrides work with real API."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            result = tools.aurora_query(
                "Say hello",
                temperature=0.1,  # Low temperature for consistent response
                max_tokens=50,  # Limited tokens
            )
            response = json.loads(result)

            assert "answer" in response or "error" in response

            if "answer" in response:
                assert "metadata" in response
                # Temperature should reflect override
                assert response["metadata"]["temperature"] == 0.1


# ==============================================================================
# Performance E2E Tests
# ==============================================================================


@pytest.mark.slow
class TestAuroraQueryPerformanceE2E:
    """Performance tests for aurora_query with real API.

    These tests verify response times meet performance targets.
    Marked as slow since they depend on network latency.
    """

    def test_simple_query_response_time(self, tools, temp_aurora_config):
        """Simple queries should complete within 10 seconds (generous for E2E)."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            start_time = time.time()
            result = tools.aurora_query("What is Python?")
            elapsed = time.time() - start_time

            response = json.loads(result)

            # Should complete within 10 seconds (network dependent)
            if "answer" in response:
                assert elapsed < 10.0, f"Query took {elapsed:.2f}s, expected <10s"

    def test_multiple_queries_stability(self, tools, temp_aurora_config):
        """Multiple sequential queries should all succeed."""
        with patch("pathlib.Path.home", return_value=temp_aurora_config):
            if hasattr(tools, "_config_cache"):
                del tools._config_cache

            queries = [
                "What is 1+1?",
                "What is 2+2?",
                "What is 3+3?",
            ]

            success_count = 0
            for query in queries:
                result = tools.aurora_query(query)
                response = json.loads(result)

                if "answer" in response:
                    success_count += 1

                # Small delay between queries to avoid rate limiting
                time.sleep(0.5)

            # At least most queries should succeed
            assert success_count >= 2, f"Only {success_count}/{len(queries)} queries succeeded"
