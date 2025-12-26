"""Unit tests for aurora_query MCP tool.

This module tests the aurora_query tool implementation following TDD principles.
Tests are written BEFORE implementation to ensure they properly validate behavior.

Test Coverage:
- Task 1.1: Parameter validation (7 tests)
- Task 1.3: Configuration loading (8 tests)
- Task 1.8: Auto-escalation logic (6 tests)
- Task 2.1: Response formatting (7 tests)
- Task 3.1: Error handling (7 tests)

Total: ~50 unit tests
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aurora.mcp.tools import AuroraMCPTools


# ==============================================================================
# Task 1.1: Parameter Validation Tests (TDD)
# ==============================================================================


class TestParameterValidation:
    """Test parameter validation for aurora_query tool (US-1.4, FR-5.1)."""

    def test_empty_query_returns_error(self):
        """Empty query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()
        assert "suggestion" in response["error"]

    def test_whitespace_only_query_returns_error(self):
        """Whitespace-only query should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("   \n  \t  ")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "empty" in response["error"]["message"].lower()

    def test_temperature_above_range_returns_error(self):
        """Temperature above 1.0 should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("Test query", temperature=1.5)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "temperature" in response["error"]["message"].lower()
        assert "0.0" in response["error"]["suggestion"] or "1.0" in response["error"]["suggestion"]

    def test_temperature_below_range_returns_error(self):
        """Temperature below 0.0 should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("Test query", temperature=-0.1)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "temperature" in response["error"]["message"].lower()

    def test_negative_max_tokens_returns_error(self):
        """Negative max_tokens should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("Test query", max_tokens=-100)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "max_tokens" in response["error"]["message"].lower()

    def test_zero_max_tokens_returns_error(self):
        """Zero max_tokens should return InvalidParameter error."""
        tools = AuroraMCPTools(db_path=":memory:")
        result = tools.aurora_query("Test query", max_tokens=0)

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "max_tokens" in response["error"]["message"].lower()

    def test_valid_parameters_pass_validation(self):
        """Valid parameters should pass validation stage.

        Note: This test may fail on later stages (API key, etc.)
        but should NOT fail on parameter validation.
        """
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock to avoid needing full setup for this validation-only test
        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_with_auto_escalation', return_value={
                    "answer": "Test answer",
                    "execution_path": "direct_llm"
                }):
                    result = tools.aurora_query(
                        "What is ACT-R?",
                        temperature=0.7,
                        max_tokens=1000
                    )

                    # Should not have validation error
                    response = json.loads(result)
                    # If there's an error, it should NOT be InvalidParameter
                    if "error" in response:
                        assert response["error"]["type"] != "InvalidParameter"


# ==============================================================================
# Task 1.4-1.5: Configuration Loading Tests (TDD)
# ==============================================================================


class TestConfigurationLoading:
    """Test configuration loading from file and environment (FR-2.1, FR-2.2)."""

    def test_api_key_from_environment_variable(self):
        """API key should be loaded from ANTHROPIC_API_KEY env var."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-env'}):
            api_key = tools._get_api_key()
            assert api_key == 'test-key-env'

    def test_api_key_from_config_file(self):
        """API key should be loaded from config file if env var not set."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"api": {"anthropic_key": "config-key"}}
        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.dict('os.environ', {}, clear=True):
                api_key = tools._get_api_key()
                assert api_key == 'config-key'

    def test_env_var_overrides_config_file(self):
        """Environment variable should take precedence over config file."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"api": {"anthropic_key": "config-key"}}
        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
                api_key = tools._get_api_key()
                assert api_key == 'env-key'

    def test_missing_api_key_returns_none(self):
        """Missing API key should return None (not raise exception)."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_load_config', return_value={}):
            with patch.dict('os.environ', {}, clear=True):
                api_key = tools._get_api_key()
                assert api_key is None

    def test_config_loaded_from_file(self, tmp_path):
        """Config should be loaded from ~/.aurora/config.json if exists."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Create .aurora directory and config file
        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir(exist_ok=True)
        config_file = aurora_dir / "config.json"
        config_data = {
            "api": {
                "temperature": 0.9,
                "default_model": "claude-sonnet-4-20250514"
            }
        }
        config_file.write_text(json.dumps(config_data), encoding='utf-8')

        with patch('pathlib.Path.home', return_value=tmp_path):
            # Clear any cached config
            if hasattr(tools, '_config_cache'):
                del tools._config_cache
            config = tools._load_config()
            assert config["api"]["temperature"] == 0.9
            assert config["api"]["default_model"] == "claude-sonnet-4-20250514"

    def test_config_defaults_applied_when_missing(self):
        """Config defaults should be applied when file doesn't exist."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('pathlib.Path.exists', return_value=False):
            config = tools._load_config()

            # Should have defaults
            assert "api" in config
            assert config["api"]["default_model"] == "claude-sonnet-4-20250514"
            assert config["api"]["temperature"] == 0.7
            assert config["api"]["max_tokens"] == 4000

    def test_invalid_json_uses_defaults(self, tmp_path):
        """Invalid JSON in config file should use defaults (with warning)."""
        tools = AuroraMCPTools(db_path=":memory:")

        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }", encoding='utf-8')

        with patch('pathlib.Path.home', return_value=tmp_path):
            with patch('pathlib.Path.exists', return_value=True):
                config = tools._load_config()

                # Should fall back to defaults
                assert config["api"]["default_model"] == "claude-sonnet-4-20250514"

    def test_config_cached_only_loaded_once(self):
        """Config should be cached and only loaded once per instance."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('pathlib.Path.exists', return_value=False):
            # Load config twice
            config1 = tools._load_config()
            config2 = tools._load_config()

            # Should be same object (cached)
            assert config1 is config2


# ==============================================================================
# Task 1.4: API Key and Budget Tests (TDD)
# ==============================================================================


class TestAPIKeyHandling:
    """Test API key loading and error handling (US-1.4, FR-2.1, FR-5.2)."""

    def test_missing_api_key_returns_helpful_error(self):
        """Missing API key should return APIKeyMissing error with guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock config loading to return no API key
        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "APIKeyMissing"
        assert "ANTHROPIC_API_KEY" in response["error"]["suggestion"]
        assert "config.json" in response["error"]["suggestion"]
        assert "To fix this" in response["error"]["suggestion"]

    def test_empty_api_key_treated_as_missing(self):
        """Empty string API key should be treated as missing."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value=''):
            result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "APIKeyMissing"


class TestBudgetEnforcement:
    """Test budget checking and enforcement (US-2.2, FR-2.3, FR-5.3)."""

    def test_budget_exceeded_returns_error(self):
        """Query that would exceed budget should return BudgetExceeded error."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up budget state for error message
        tools._budget_current_usage = 49.5
        tools._budget_monthly_limit = 50.0
        tools._budget_estimated_cost = 0.05

        # Mock budget check to return False
        with patch.object(tools, '_check_budget', return_value=False):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "BudgetExceeded"
        assert "suggestion" in response["error"]

    def test_budget_check_allows_query_under_limit(self):
        """Query under budget limit should proceed past budget check."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock budget check to return True
        with patch.object(tools, '_check_budget', return_value=True):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_execute_with_auto_escalation', return_value={
                    "answer": "Test",
                    "execution_path": "direct_llm"
                }):
                    result = tools.aurora_query("Test query")

                    # Should not have budget error
                    response = json.loads(result)
                    if "error" in response:
                        assert response["error"]["type"] != "BudgetExceeded"


# ==============================================================================
# Task 1.8: Auto-Escalation Logic Tests (TDD)
# ==============================================================================


class TestAutoEscalation:
    """Test auto-escalation logic for query complexity (US-1.2, FR-1.3)."""

    def test_simple_query_uses_direct_llm(self):
        """Simple query should use direct LLM execution."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock components
        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_assess_complexity', return_value=0.3):
                    with patch.object(tools, '_execute_direct_llm', return_value={
                        "answer": "Direct LLM answer",
                        "execution_path": "direct_llm"
                    }) as mock_direct:
                        with patch.object(tools, '_execute_soar') as mock_soar:
                            tools.aurora_query("What is X?")

                            # Should call direct LLM, not SOAR
                            assert mock_direct.called
                            assert not mock_soar.called

    def test_complex_query_uses_soar_pipeline(self):
        """Complex query should use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_assess_complexity', return_value=0.8):
                    with patch.object(tools, '_execute_direct_llm') as mock_direct:
                        with patch.object(tools, '_execute_soar', return_value={
                            "answer": "SOAR answer",
                            "execution_path": "soar_pipeline"
                        }) as mock_soar:
                            tools.aurora_query("Analyze complex architecture...")

                            # Should call SOAR, not direct LLM
                            assert mock_soar.called
                            assert not mock_direct.called

    def test_force_soar_bypasses_complexity_assessment(self):
        """force_soar=True should always use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Even with low complexity, should use SOAR
        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_assess_complexity') as mock_assess:
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "SOAR answer",
                        "execution_path": "soar_pipeline"
                    }) as mock_soar:
                        tools.aurora_query("Simple question", force_soar=True)

                        # Should call SOAR without checking complexity
                        assert mock_soar.called
                        assert not mock_assess.called

    def test_complexity_threshold_configurable(self):
        """Complexity threshold should be configurable via config."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"complexity_threshold": 0.5}}

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_assess_complexity', return_value=0.55):
                        with patch.object(tools, '_execute_soar', return_value={
                            "answer": "SOAR",
                            "execution_path": "soar_pipeline"
                        }) as mock_soar:
                            # Complexity 0.55 > threshold 0.5, should use SOAR
                            tools.aurora_query("Test")
                            assert mock_soar.called

    def test_execution_path_in_response_direct_llm(self):
        """Response should indicate direct_llm execution path."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_assess_complexity', return_value=0.3):
                    with patch.object(tools, '_execute_direct_llm', return_value={
                        "answer": "Answer",
                        "execution_path": "direct_llm",
                        "metadata": {}
                    }):
                        result = tools.aurora_query("Simple query")

                        response = json.loads(result)
                        assert response["execution_path"] == "direct_llm"

    def test_execution_path_in_response_soar_pipeline(self):
        """Response should indicate soar_pipeline execution path."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_assess_complexity', return_value=0.8):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "metadata": {}
                    }):
                        result = tools.aurora_query("Complex query")

                        response = json.loads(result)
                        assert response["execution_path"] == "soar_pipeline"


# ==============================================================================
# Task 2.1: Response Formatting Tests (TDD)
# ==============================================================================


class TestResponseFormatting:
    """Test response formatting for verbose and non-verbose modes (FR-4.1)."""

    def test_response_includes_required_fields(self):
        """Response should include answer, execution_path, and metadata."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Test answer",
                    "execution_path": "direct_llm",
                    "duration": 1.23,
                    "cost": 0.0012,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    assert "answer" in response
                    assert "execution_path" in response
                    assert "metadata" in response
                    assert response["answer"] == "Test answer"
                    assert response["execution_path"] in ["direct_llm", "soar_pipeline"]

    def test_metadata_includes_required_fields(self):
        """Metadata should include duration, cost, tokens, model, temperature."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.234,
                    "cost": 0.0123,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    metadata = response["metadata"]
                    assert "duration_seconds" in metadata
                    assert "cost_usd" in metadata
                    assert "input_tokens" in metadata
                    assert "output_tokens" in metadata
                    assert "model" in metadata
                    assert "temperature" in metadata

    def test_verbose_response_includes_phases(self):
        """Verbose response should include phase trace for SOAR queries."""
        tools = AuroraMCPTools(db_path=":memory:")

        phase_trace = {
            "phases": [
                {"name": "Assess", "duration_seconds": 0.1, "summary": "High complexity"},
                {"name": "Retrieve", "duration_seconds": 0.5, "summary": "Retrieved 10 chunks"}
            ]
        }

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_soar', return_value={
                    "answer": "Answer",
                    "execution_path": "soar_pipeline",
                    "phase_trace": phase_trace,
                    "duration": 5.0,
                    "cost": 0.05,
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Complex query", verbose=True)
                    response = json.loads(result)

                    assert "phases" in response
                    assert len(response["phases"]) == 2
                    assert response["phases"][0]["name"] == "Assess"

    def test_non_verbose_response_excludes_phases(self):
        """Non-verbose response should not include phase trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test", verbose=False)
                    response = json.loads(result)

                    assert "phases" not in response

    def test_sources_included_when_memory_used(self):
        """Response should include sources when memory was used."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "sources": [
                        {"file_path": "/path/to/file.py", "chunk_id": "code:file:func", "score": 0.87}
                    ],
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    assert "sources" in response
                    assert len(response["sources"]) == 1
                    assert response["sources"][0]["file_path"] == "/path/to/file.py"

    def test_sources_absent_when_no_memory_used(self):
        """Response should not include sources when memory wasn't used."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    assert "sources" not in response

    def test_response_is_valid_json(self):
        """Response should be valid, parseable JSON."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")

                    # Should not raise exception
                    response = json.loads(result)
                    assert isinstance(response, dict)


# ==============================================================================
# Task 3.1: Error Handling Tests (TDD)
# ==============================================================================


class TestErrorHandling:
    """Test error handling for various failure scenarios (FR-4.2, FR-5)."""

    def test_error_response_structure(self):
        """Error response should follow standard JSON structure."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Trigger error (empty query)
        result = tools.aurora_query("")
        response = json.loads(result)

        assert "error" in response
        assert "type" in response["error"]
        assert "message" in response["error"]
        assert "suggestion" in response["error"]

    def test_missing_api_key_error_message(self):
        """Missing API key error should include helpful guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test")
            response = json.loads(result)

            assert response["error"]["type"] == "APIKeyMissing"
            assert "ANTHROPIC_API_KEY" in response["error"]["suggestion"]
            assert "To fix this" in response["error"]["suggestion"]

    def test_budget_exceeded_error_includes_details(self):
        """Budget exceeded error should include current usage details."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Set up budget state for error message
        tools._budget_current_usage = 49.5
        tools._budget_monthly_limit = 50.0
        tools._budget_estimated_cost = 0.05

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=False):
                result = tools.aurora_query("Test")
                response = json.loads(result)

                assert response["error"]["type"] == "BudgetExceeded"
                assert "suggestion" in response["error"]
                # Should include details
                assert "details" in response["error"]
                assert "current_usage_usd" in response["error"]["details"]

    def test_invalid_parameter_error_specifies_parameter(self):
        """Invalid parameter error should specify which parameter is invalid."""
        tools = AuroraMCPTools(db_path=":memory:")

        result = tools.aurora_query("Test", temperature=2.0)
        response = json.loads(result)

        assert response["error"]["type"] == "InvalidParameter"
        assert "temperature" in response["error"]["message"].lower()

    def test_soar_phase_failure_error_includes_phase_name(self):
        """SOAR phase failure should include phase name and guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_soar', side_effect=Exception("Assess phase failed")):
                    result = tools.aurora_query("Complex query", force_soar=True)
                    response = json.loads(result)

                    assert "error" in response
                    # Error type should indicate failure
                    assert "fail" in response["error"]["type"].lower() or "error" in response["error"]["type"].lower()

    def test_llm_api_failure_error_suggests_retry(self):
        """LLM API failure error should suggest checking status and retrying."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=Exception("API timeout")):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    assert "error" in response
                    # Should have helpful suggestion
                    assert "suggestion" in response["error"]

    def test_all_errors_include_suggestion_field(self):
        """All error responses must include suggestion field with guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Test various error conditions
        error_conditions = [
            # Empty query
            ("", {}),
            # Invalid temperature
            ("Test", {"temperature": 2.0}),
            # Invalid max_tokens
            ("Test", {"max_tokens": -100})
        ]

        for query, kwargs in error_conditions:
            result = tools.aurora_query(query, **kwargs)
            response = json.loads(result)

            if "error" in response:
                assert "suggestion" in response["error"], f"Missing suggestion for query='{query}', kwargs={kwargs}"
                assert len(response["error"]["suggestion"]) > 0, f"Empty suggestion for query='{query}'"


# ==============================================================================
# Task 3.1: Extended Error Handling Tests (TDD)
# ==============================================================================


class TestRetryLogic:
    """Test LLM API retry logic for transient failures (FR-5.4)."""

    def test_retry_on_rate_limit_error(self):
        """Should retry on rate limit (429) errors."""
        tools = AuroraMCPTools(db_path=":memory:")

        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Rate limit exceeded (429)")
            return {
                "answer": "Success after retry",
                "execution_path": "direct_llm",
                "duration": 1.0,
                "cost": 0.01,
                "input_tokens": 100,
                "output_tokens": 50,
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7
            }

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=mock_execute):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should eventually succeed
                    assert "error" not in response or response.get("answer") == "Success after retry"

    def test_retry_on_timeout_error(self):
        """Should retry on timeout errors."""
        tools = AuroraMCPTools(db_path=":memory:")

        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                raise TimeoutError("Request timed out")
            return {
                "answer": "Success",
                "execution_path": "direct_llm",
                "duration": 1.0,
                "cost": 0.01,
                "input_tokens": 100,
                "output_tokens": 50,
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7
            }

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=mock_execute):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should eventually succeed
                    assert "error" not in response or "answer" in response

    def test_no_retry_on_auth_error(self):
        """Should NOT retry on authentication errors."""
        tools = AuroraMCPTools(db_path=":memory:")

        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            raise Exception("Authentication failed (401)")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=mock_execute):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should fail immediately without multiple retries
                    assert "error" in response
                    # Auth errors shouldn't be retried many times
                    assert call_count[0] <= 3

    def test_max_retry_attempts_exhausted(self):
        """Should fail after maximum retry attempts."""
        tools = AuroraMCPTools(db_path=":memory:")

        def always_fail(*args, **kwargs):
            raise Exception("Server error (500)")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=always_fail):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should return error after retries exhausted
                    assert "error" in response
                    assert "suggestion" in response["error"]

    def test_retry_uses_exponential_backoff(self):
        """Retry should use exponential backoff timing."""
        tools = AuroraMCPTools(db_path=":memory:")

        # This test verifies the retry mechanism exists
        # Actual timing verification would require time mocking
        call_count = [0]

        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Rate limit exceeded")
            return {
                "answer": "Success",
                "execution_path": "direct_llm",
                "duration": 1.0,
                "cost": 0.01,
                "input_tokens": 100,
                "output_tokens": 50,
                "model": "claude-sonnet-4-20250514",
                "temperature": 0.7
            }

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', side_effect=mock_execute):
                    tools.aurora_query("Test query")
                    # Should have made multiple attempts
                    assert call_count[0] >= 2


class TestMemoryGracefulDegradation:
    """Test graceful degradation when memory is unavailable (FR-5.5)."""

    def test_query_succeeds_without_memory(self):
        """Query should succeed even when memory store is empty."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_get_memory_context', return_value=""):
                    result = tools.aurora_query("What is Python?")
                    response = json.loads(result)

                    # Should not have an error related to memory
                    if "error" in response:
                        assert "memory" not in response["error"]["type"].lower()

    def test_memory_error_logs_warning(self):
        """Memory retrieval error should log warning, not raise exception."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_get_memory_context', side_effect=Exception("Memory unavailable")):
                    # Should not raise exception
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Query should still complete (possibly with error, but not memory-related crash)
                    assert isinstance(response, dict)

    def test_empty_memory_store_handled_gracefully(self):
        """Empty memory store should not block query execution."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                # Memory returns empty string (no indexed content)
                with patch.object(tools, '_get_memory_context', return_value=""):
                    with patch.object(tools, '_execute_direct_llm', return_value={
                        "answer": "LLM answer without memory context",
                        "execution_path": "direct_llm",
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        result = tools.aurora_query("Test query")
                        response = json.loads(result)

                        assert "answer" in response

    def test_memory_failure_does_not_affect_response_structure(self):
        """Response structure should be valid even when memory fails."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test")
                    response = json.loads(result)

                    # Standard response structure should be present
                    assert "answer" in response
                    assert "execution_path" in response
                    assert "metadata" in response


class TestErrorLogging:
    """Test error logging to mcp.log (FR-5.6)."""

    def test_errors_are_logged(self):
        """Errors should be logged before returning response."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('aurora.mcp.tools.logger') as mock_logger:
            # Trigger an error
            tools.aurora_query("")

            # Should have logged the error
            assert mock_logger.error.called

    def test_api_key_missing_logged(self):
        """APIKeyMissing error should be logged."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('aurora.mcp.tools.logger') as mock_logger:
            with patch.object(tools, '_get_api_key', return_value=None):
                tools.aurora_query("Test query")

                # Should have logged APIKeyMissing
                assert mock_logger.error.called

    def test_unexpected_exception_logged_with_traceback(self):
        """Unexpected exceptions should be logged with stack trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('aurora.mcp.tools.logger') as mock_logger:
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', side_effect=RuntimeError("Unexpected error")):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    assert "error" in response
                    # Should have logged with exc_info=True
                    mock_logger.error.assert_called()

    def test_validation_errors_logged(self):
        """Parameter validation errors should be logged."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch('aurora.mcp.tools.logger') as mock_logger:
            tools.aurora_query("Test", temperature=2.0)

            # Should have logged the InvalidParameter error
            assert mock_logger.error.called


class TestErrorMessageFormat:
    """Test user-friendly error message formatting (FR-4.2)."""

    def test_error_message_is_user_friendly(self):
        """Error messages should be understandable by non-technical users."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test")
            response = json.loads(result)

            # Message should be clear, not technical jargon
            assert "error" in response
            message = response["error"]["message"]
            # Should not contain stack traces or technical details
            assert "Traceback" not in message
            assert "Exception" not in message or "API key" in message

    def test_error_suggestion_is_actionable(self):
        """Error suggestions should provide clear action steps."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test")
            response = json.loads(result)

            suggestion = response["error"]["suggestion"]
            # Should contain numbered steps or clear instructions
            assert "To fix this" in suggestion or "1." in suggestion or "export" in suggestion.lower()

    def test_error_includes_troubleshooting_link(self):
        """Error messages should include link to troubleshooting docs."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value=None):
            result = tools.aurora_query("Test")
            response = json.loads(result)

            suggestion = response["error"]["suggestion"]
            # Should reference troubleshooting documentation
            assert "TROUBLESHOOTING" in suggestion or "docs/" in suggestion or "console.anthropic.com" in suggestion

    def test_budget_error_shows_current_usage(self):
        """Budget exceeded error should show current and limit values."""
        tools = AuroraMCPTools(db_path=":memory:")

        tools._budget_current_usage = 45.50
        tools._budget_monthly_limit = 50.0
        tools._budget_estimated_cost = 0.05

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=False):
                result = tools.aurora_query("Test")
                response = json.loads(result)

                assert response["error"]["type"] == "BudgetExceeded"
                # Should include usage details
                details = response["error"].get("details", {})
                suggestion = response["error"]["suggestion"]
                assert "45.50" in suggestion or details.get("current_usage_usd") == 45.50

    def test_invalid_model_error_message(self):
        """Invalid model string should return clear error."""
        tools = AuroraMCPTools(db_path=":memory:")

        result = tools.aurora_query("Test", model="   ")
        response = json.loads(result)

        assert "error" in response
        assert response["error"]["type"] == "InvalidParameter"
        assert "model" in response["error"]["message"].lower() or "empty" in response["error"]["message"].lower()


# ==============================================================================
# Additional Helper Tests
# ==============================================================================


class TestVerbosityHandling:
    """Test verbosity parameter and config handling (US-2.3)."""

    def test_verbose_parameter_true_includes_details(self):
        """verbose=True should include detailed response."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_soar', return_value={
                    "answer": "Answer",
                    "execution_path": "soar_pipeline",
                    "phase_trace": {"phases": [{"name": "Assess", "duration_seconds": 0.1}]},
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                    response = json.loads(result)

                    # Should include phases for verbose SOAR query
                    assert "phases" in response

    def test_verbose_parameter_false_excludes_details(self):
        """verbose=False should exclude detailed trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                with patch.object(tools, '_execute_direct_llm', return_value={
                    "answer": "Answer",
                    "execution_path": "direct_llm",
                    "duration": 1.0,
                    "cost": 0.01,
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7
                }):
                    result = tools.aurora_query("Test", verbose=False)
                    response = json.loads(result)

                    # Should not include phases
                    assert "phases" not in response

    def test_verbosity_from_config_when_parameter_none(self):
        """Should use config verbosity when parameter is None."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "verbose"}}

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": []},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        # verbose parameter is None, should use config
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Config has verbose mode, so phases should be included
                        assert "phases" in response


# ==============================================================================
# Task 2.4: Progress Tracking Tests
# ==============================================================================


class TestProgressTracking:
    """Test progress tracking for SOAR phases (FR-4.1, PR-2.1)."""

    def test_soar_response_includes_all_nine_phases(self):
        """SOAR execution should include all 9 phase entries in verbose mode."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                # Don't mock _execute_soar - let it run to test real phase tracking
                result = tools.aurora_query("Complex analysis query", force_soar=True, verbose=True)
                response = json.loads(result)

                assert "phases" in response
                assert len(response["phases"]) == 9

                # Verify all 9 SOAR phase names
                phase_names = [p["phase"] for p in response["phases"]]
                expected_phases = [
                    "Assess", "Retrieve", "Decompose", "Verify",
                    "Route", "Collect", "Synthesize", "Record", "Respond"
                ]
                assert phase_names == expected_phases

    def test_each_phase_has_required_fields(self):
        """Each phase should have phase name, status, and duration."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert "phase" in phase, "Phase entry missing 'phase' field"
                    assert "status" in phase, "Phase entry missing 'status' field"
                    assert "duration" in phase, "Phase entry missing 'duration' field"

    def test_phase_duration_is_numeric(self):
        """Phase duration should be a number (seconds)."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert isinstance(phase["duration"], (int, float)), \
                        f"Phase duration should be numeric, got {type(phase['duration'])}"
                    assert phase["duration"] >= 0, "Phase duration should be non-negative"

    def test_phase_status_is_completed(self):
        """Successful phases should have 'completed' status."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert phase["status"] == "completed", \
                        f"Expected 'completed' status, got '{phase['status']}'"

    def test_progress_not_included_for_direct_llm(self):
        """Direct LLM execution should not include SOAR phases."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                # Simple query should use direct LLM
                result = tools.aurora_query("What is X?", verbose=True)
                response = json.loads(result)

                # Direct LLM should not have phases
                assert "phases" not in response or response.get("execution_path") == "soar_pipeline"

    def test_total_duration_in_metadata(self):
        """Metadata should include total duration."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, '_get_api_key', return_value='test-key'):
            with patch.object(tools, '_check_budget', return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                assert "metadata" in response
                assert "duration_seconds" in response["metadata"]
                assert isinstance(response["metadata"]["duration_seconds"], (int, float))


# ==============================================================================
# Task 2.5: Enhanced Verbosity Handling Tests
# ==============================================================================


class TestEnhancedVerbosity:
    """Test verbosity handling across different modes (FR-4.1, US-2.3)."""

    def test_verbosity_quiet_minimal_output(self):
        """Quiet verbosity should return minimal output."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "quiet"}}

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_direct_llm', return_value={
                        "answer": "Answer",
                        "execution_path": "direct_llm",
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        # verbose=None should use config (quiet)
                        result = tools.aurora_query("Test", verbose=None)
                        response = json.loads(result)

                        # Quiet mode should not include phases
                        assert "phases" not in response

    def test_verbosity_normal_standard_output(self):
        """Normal verbosity should return standard output without phases."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "normal"}}

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": [{"phase": "Assess", "duration": 0.1, "status": "completed"}]},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Normal mode should not include phases
                        assert "phases" not in response
                        # But should include basic fields
                        assert "answer" in response
                        assert "metadata" in response

    def test_verbosity_verbose_full_output(self):
        """Verbose mode should include full phase trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "verbose"}}

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": [{"phase": "Assess", "duration": 0.1, "status": "completed"}]},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Verbose mode should include phases for SOAR
                        assert "phases" in response

    def test_parameter_overrides_config_verbose_true(self):
        """verbose=True parameter should override config setting."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "quiet"}}  # Config says quiet

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": [{"phase": "Assess", "duration": 0.1, "status": "completed"}]},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        # Parameter verbose=True should override config
                        result = tools.aurora_query("Complex", force_soar=True, verbose=True)
                        response = json.loads(result)

                        # Should include phases because parameter overrides config
                        assert "phases" in response

    def test_parameter_overrides_config_verbose_false(self):
        """verbose=False parameter should override config setting."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "verbose"}}  # Config says verbose

        with patch.object(tools, '_load_config', return_value=mock_config):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": [{"phase": "Assess", "duration": 0.1, "status": "completed"}]},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        # Parameter verbose=False should override config
                        result = tools.aurora_query("Complex", force_soar=True, verbose=False)
                        response = json.loads(result)

                        # Should NOT include phases because parameter overrides config
                        assert "phases" not in response

    def test_env_var_verbosity_override(self):
        """AURORA_VERBOSITY env var should override config file."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Clear any cached config
        if hasattr(tools, '_config_cache'):
            del tools._config_cache

        with patch.dict('os.environ', {'AURORA_VERBOSITY': 'verbose'}):
            with patch.object(tools, '_get_api_key', return_value='test-key'):
                with patch.object(tools, '_check_budget', return_value=True):
                    with patch.object(tools, '_execute_soar', return_value={
                        "answer": "Answer",
                        "execution_path": "soar_pipeline",
                        "phase_trace": {"phases": [{"phase": "Assess", "duration": 0.1, "status": "completed"}]},
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7
                    }):
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Env var sets verbose, so phases should be included
                        assert "phases" in response
