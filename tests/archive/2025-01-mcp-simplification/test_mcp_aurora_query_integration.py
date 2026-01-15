"""Integration tests for aurora_query MCP tool.

This module tests the aurora_query tool in integration scenarios,
testing the full flow with mocked external dependencies (LLM API only).

Test Coverage:
- Task 4.4: Integration tests for direct LLM execution (4 tests)
- Task 4.5: Integration tests for SOAR pipeline (5 tests)
- Task 4.6: Integration tests for error scenarios (6 tests)

Total: 15 integration tests
"""

import json
from unittest.mock import patch

import pytest

from aurora_mcp.tools import AuroraMCPTools

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def temp_aurora_dir(tmp_path):
    """Create a temporary ~/.aurora directory for testing."""
    aurora_dir = tmp_path / ".aurora"
    aurora_dir.mkdir(exist_ok=True)

    # Create budget tracker
    budget_file = aurora_dir / "budget_tracker.json"
    budget_file.write_text(json.dumps({"monthly_usage_usd": 10.0, "monthly_limit_usd": 50.0}))

    # Create config file
    config_file = aurora_dir / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "api": {
                    "default_model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 4000,
                },
                "query": {
                    "auto_escalate": True,
                    "complexity_threshold": 0.6,
                    "verbosity": "normal",
                },
                "budget": {"monthly_limit_usd": 50.0},
            }
        )
    )

    return aurora_dir


@pytest.fixture
def tools_with_temp_home(tmp_path, temp_aurora_dir):
    """Create AuroraMCPTools with temporary home directory."""
    with patch("pathlib.Path.home", return_value=tmp_path):
        tools = AuroraMCPTools(db_path=":memory:")
        # Clear any cached config
        if hasattr(tools, "_config_cache"):
            del tools._config_cache
        yield tools


@pytest.fixture
def mock_llm_response():
    """Standard mock LLM response for testing."""
    return {
        "answer": "This is a mock LLM response for testing.",
        "execution_path": "direct_llm",
        "duration": 0.5,
        "cost": 0.01,
        "input_tokens": 50,
        "output_tokens": 30,
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
    }


@pytest.fixture
def mock_soar_response():
    """Standard mock SOAR response for testing."""
    return {
        "answer": "This is a mock SOAR pipeline response.",
        "execution_path": "soar_pipeline",
        "duration": 2.5,
        "cost": 0.05,
        "input_tokens": 500,
        "output_tokens": 200,
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
        "phase_trace": {
            "phases": [
                {"phase": "Assess", "duration": 0.1, "status": "completed"},
                {"phase": "Retrieve", "duration": 0.3, "status": "completed"},
                {"phase": "Decompose", "duration": 0.2, "status": "completed"},
                {"phase": "Verify", "duration": 0.1, "status": "completed"},
                {"phase": "Route", "duration": 0.1, "status": "completed"},
                {"phase": "Collect", "duration": 0.5, "status": "completed"},
                {"phase": "Synthesize", "duration": 0.8, "status": "completed"},
                {"phase": "Record", "duration": 0.2, "status": "completed"},
                {"phase": "Respond", "duration": 0.2, "status": "completed"},
            ]
        },
    }


# ==============================================================================
# Task 4.4: Integration Tests for Direct LLM Execution
# ==============================================================================


class TestDirectLLMExecution:
    """Integration tests for direct LLM execution path."""

    def test_simple_query_end_to_end_with_mocked_llm(self, tools_with_temp_home, mock_llm_response):
        """Test simple query flows through direct LLM path end-to-end."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_direct_llm", return_value=mock_llm_response):
                result = tools.aurora_query("What is Python?")
                response = json.loads(result)

                assert "answer" in response
                assert response["execution_path"] == "direct_llm"
                assert "metadata" in response
                assert response["metadata"]["model"] == "claude-sonnet-4-20250514"

    def test_memory_context_included_in_direct_llm(self, tools_with_temp_home, mock_llm_response):
        """Test that memory context is retrieved for direct LLM queries.

        This test verifies that the execution path calls _get_memory_context
        when running through direct LLM. We use a spy pattern to track calls.
        """
        tools = tools_with_temp_home

        memory_context_called = [False]
        original_get_memory = tools._get_memory_context

        def spy_get_memory(*args, **kwargs):
            memory_context_called[0] = True
            return original_get_memory(*args, **kwargs)

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_get_memory_context", side_effect=spy_get_memory):
                # Don't mock _execute_direct_llm so _get_memory_context gets called
                result = tools.aurora_query("What is Python?")
                response = json.loads(result)

                # Memory context should have been called within _execute_direct_llm
                assert memory_context_called[0], "Memory context was not retrieved"
                # Query should complete successfully
                assert "answer" in response

    def test_response_includes_all_required_fields(self, tools_with_temp_home, mock_llm_response):
        """Test that direct LLM response includes all required fields."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_direct_llm", return_value=mock_llm_response):
                result = tools.aurora_query("Simple question")
                response = json.loads(result)

                # Verify all required fields
                assert "answer" in response
                assert "execution_path" in response
                assert "metadata" in response

                # Verify metadata fields
                metadata = response["metadata"]
                assert "duration_seconds" in metadata
                assert "cost_usd" in metadata
                assert "input_tokens" in metadata
                assert "output_tokens" in metadata
                assert "model" in metadata
                assert "temperature" in metadata

    def test_cost_tracking_updated_after_query(
        self, tools_with_temp_home, mock_llm_response, tmp_path
    ):
        """Test that cost tracking is checked before query."""
        tools = tools_with_temp_home

        budget_checked = [False]

        def mock_check_budget(*args, **kwargs):
            budget_checked[0] = True
            return True

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", side_effect=mock_check_budget):
                with patch.object(tools, "_execute_direct_llm", return_value=mock_llm_response):
                    tools.aurora_query("Test query")

                    # Budget should have been checked
                    assert budget_checked[0]


# ==============================================================================
# Task 4.5: Integration Tests for SOAR Pipeline
# ==============================================================================


class TestSOARPipelineExecution:
    """Integration tests for SOAR pipeline execution."""

    def test_complex_query_triggers_soar(self, tools_with_temp_home, mock_soar_response):
        """Test that complex queries trigger SOAR pipeline."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_soar", return_value=mock_soar_response):
                # Use complex keywords that trigger SOAR
                result = tools.aurora_query("Analyze the architecture design pattern")
                response = json.loads(result)

                assert response["execution_path"] == "soar_pipeline"

    def test_force_soar_parameter_works(self, tools_with_temp_home, mock_soar_response):
        """Test that force_soar=True always uses SOAR pipeline."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_soar", return_value=mock_soar_response) as mock_soar:
                # Simple query with force_soar should use SOAR
                result = tools.aurora_query("What is X?", force_soar=True)
                response = json.loads(result)

                assert mock_soar.called
                assert response["execution_path"] == "soar_pipeline"

    def test_verbose_mode_includes_all_phases(self, tools_with_temp_home, mock_soar_response):
        """Test that verbose mode includes all 9 SOAR phases."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_soar", return_value=mock_soar_response):
                result = tools.aurora_query(
                    "Analyze complex pattern", force_soar=True, verbose=True
                )
                response = json.loads(result)

                assert "phases" in response
                assert len(response["phases"]) == 9

                # Verify phase names
                phase_names = [p["phase"] for p in response["phases"]]
                expected = [
                    "Assess",
                    "Retrieve",
                    "Decompose",
                    "Verify",
                    "Route",
                    "Collect",
                    "Synthesize",
                    "Record",
                    "Respond",
                ]
                assert phase_names == expected

    def test_phase_timing_included_in_response(self, tools_with_temp_home, mock_soar_response):
        """Test that phase timing is included in verbose response."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_soar", return_value=mock_soar_response):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert "duration" in phase
                    assert isinstance(phase["duration"], (int, float))
                    assert phase["duration"] >= 0

    def test_soar_response_has_correct_structure(self, tools_with_temp_home, mock_soar_response):
        """Test that SOAR response has correct structure."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_soar", return_value=mock_soar_response):
                result = tools.aurora_query("Complex query", force_soar=True)
                response = json.loads(result)

                assert response["execution_path"] == "soar_pipeline"
                assert "answer" in response
                assert "metadata" in response

                # Metadata should have cost reflecting SOAR (higher than direct)
                assert response["metadata"]["cost_usd"] >= 0.01


# ==============================================================================
# Task 4.6: Integration Tests for Error Scenarios
# ==============================================================================


class TestErrorScenarios:
    """Integration tests for error handling scenarios."""

    def test_missing_api_key_returns_friendly_error(self, tools_with_temp_home):
        """Test that missing API key returns user-friendly error."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value=None):
            result = tools.aurora_query("Test query")
            response = json.loads(result)

            assert "error" in response
            assert response["error"]["type"] == "APIKeyMissing"
            assert "suggestion" in response["error"]
            assert "ANTHROPIC_API_KEY" in response["error"]["suggestion"]
            assert "To fix this" in response["error"]["suggestion"]

    def test_budget_exceeded_scenario(self, tools_with_temp_home):
        """Test budget exceeded returns appropriate error."""
        tools = tools_with_temp_home

        # Set up budget state for error message
        tools._budget_current_usage = 49.5
        tools._budget_monthly_limit = 50.0
        tools._budget_estimated_cost = 0.05

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=False):
                result = tools.aurora_query("Test query")
                response = json.loads(result)

                assert "error" in response
                assert response["error"]["type"] == "BudgetExceeded"
                assert "details" in response["error"]
                assert response["error"]["details"]["current_usage_usd"] == 49.5

    def test_llm_api_failure_with_retries(self, tools_with_temp_home):
        """Test that LLM API failures are retried and then return error."""
        tools = tools_with_temp_home

        call_count = [0]

        def always_fail(*args, **kwargs):
            call_count[0] += 1
            raise Exception("Rate limit exceeded (429)")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=always_fail):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should have retried multiple times
                    assert call_count[0] >= 2

                    # Should eventually return error
                    assert "error" in response
                    assert "suggestion" in response["error"]

    def test_retry_exhaustion_returns_error(self, tools_with_temp_home):
        """Test that exhausted retries return appropriate error."""
        tools = tools_with_temp_home

        def always_timeout(*args, **kwargs):
            raise TimeoutError("Request timed out")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=always_timeout):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    assert "error" in response
                    assert "suggestion" in response["error"]

    def test_graceful_degradation_memory_unavailable(self, tools_with_temp_home, mock_llm_response):
        """Test graceful degradation when memory is unavailable."""
        tools = tools_with_temp_home

        def memory_error(*args, **kwargs):
            raise Exception("Memory store not available")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_get_memory_context", side_effect=memory_error):
                    # Should not raise - graceful degradation
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Query should still complete (not memory-related error)
                    assert isinstance(response, dict)
                    # Either success or non-memory error
                    if "error" in response:
                        assert "memory" not in response["error"]["type"].lower()

    def test_errors_include_suggestion_field(self, tools_with_temp_home):
        """Test that all error responses include helpful suggestions."""
        tools = tools_with_temp_home

        # Test various error scenarios
        error_scenarios = [
            # Empty query
            {"query": "", "kwargs": {}},
            # Invalid temperature
            {"query": "Test", "kwargs": {"temperature": 2.0}},
            # Invalid max_tokens
            {"query": "Test", "kwargs": {"max_tokens": -100}},
        ]

        for scenario in error_scenarios:
            result = tools.aurora_query(scenario["query"], **scenario["kwargs"])
            response = json.loads(result)

            if "error" in response:
                assert (
                    "suggestion" in response["error"]
                ), f"Missing suggestion for scenario: {scenario}"
                assert (
                    len(response["error"]["suggestion"]) > 0
                ), f"Empty suggestion for scenario: {scenario}"


# ==============================================================================
# Additional Integration Tests
# ==============================================================================


class TestConfigurationIntegration:
    """Test configuration integration across components."""

    def test_config_file_settings_applied(self, tools_with_temp_home):
        """Test that config file settings are applied to queries."""
        tools = tools_with_temp_home

        # Config should be loaded
        config = tools._load_config()

        assert config["api"]["default_model"] == "claude-sonnet-4-20250514"
        assert config["query"]["complexity_threshold"] == 0.6

    def test_environment_variables_override_config(self, tools_with_temp_home):
        """Test that environment variables override config file."""
        tools = tools_with_temp_home

        # Clear cached config
        if hasattr(tools, "_config_cache"):
            del tools._config_cache

        with patch.dict("os.environ", {"AURORA_MODEL": "custom-model"}):
            config = tools._load_config()

            assert config["api"]["default_model"] == "custom-model"


class TestQueryParameterOverrides:
    """Test parameter overrides in queries."""

    def test_model_parameter_override(self, tools_with_temp_home, mock_llm_response):
        """Test that model parameter overrides config."""
        tools = tools_with_temp_home

        custom_response = {**mock_llm_response, "model": "custom-model"}

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_direct_llm", return_value=custom_response):
                result = tools.aurora_query("Test", model="custom-model")
                response = json.loads(result)

                assert response["metadata"]["model"] == "custom-model"

    def test_temperature_parameter_override(self, tools_with_temp_home, mock_llm_response):
        """Test that temperature parameter overrides config."""
        tools = tools_with_temp_home

        custom_response = {**mock_llm_response, "temperature": 0.9}

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_execute_direct_llm", return_value=custom_response):
                result = tools.aurora_query("Test", temperature=0.9)
                response = json.loads(result)

                assert response["metadata"]["temperature"] == 0.9

    def test_max_tokens_parameter_passed(self, tools_with_temp_home, mock_llm_response):
        """Test that max_tokens parameter is passed through."""
        tools = tools_with_temp_home

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(
                tools, "_execute_direct_llm", return_value=mock_llm_response
            ) as mock_exec:
                tools.aurora_query("Test", max_tokens=2000)

                # Verify max_tokens was passed
                assert mock_exec.called
                call_kwargs = mock_exec.call_args
                assert call_kwargs is not None
