"""Archived LLM-related tests for aurora_query MCP tool.

These tests were archived on 2025-12-26 as part of PRD-0008 (MCP Simplification).
They test functionality that was removed from MCP tools:
- API key handling
- Budget enforcement
- Auto-escalation between direct LLM and SOAR
- LLM API retry logic
- Memory graceful degradation
- Error logging for LLM failures
- SOAR progress tracking
- Enhanced verbosity for SOAR phases

See README.md in this directory for full context.

Original file: tests/unit/mcp/test_aurora_query_tool.py
"""

import json
from unittest.mock import patch

from aurora_mcp.tools import AuroraMCPTools


# ==============================================================================
# Task 1.4: API Key and Budget Tests (TDD)
# ==============================================================================


class TestAPIKeyHandling:
    """Test API key loading and error handling (US-1.4, FR-2.1, FR-5.2)."""

    def test_missing_api_key_returns_helpful_error(self):
        """Missing API key should return APIKeyMissing error with guidance."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock config loading to return no API key
        with patch.object(tools, "_get_api_key", return_value=None):
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

        with patch.object(tools, "_get_api_key", return_value=""):
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
        with patch.object(tools, "_check_budget", return_value=False):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                result = tools.aurora_query("Test query")

        response = json.loads(result)
        assert "error" in response
        assert response["error"]["type"] == "BudgetExceeded"
        assert "suggestion" in response["error"]

    def test_budget_check_allows_query_under_limit(self):
        """Query under budget limit should proceed past budget check."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Mock budget check to return True
        with patch.object(tools, "_check_budget", return_value=True):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(
                    tools,
                    "_execute_with_auto_escalation",
                    return_value={"answer": "Test", "execution_path": "direct_llm"},
                ):
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
        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_assess_complexity", return_value=0.3):
                    with patch.object(
                        tools,
                        "_execute_direct_llm",
                        return_value={
                            "answer": "Direct LLM answer",
                            "execution_path": "direct_llm",
                        },
                    ) as mock_direct:
                        with patch.object(tools, "_execute_soar") as mock_soar:
                            tools.aurora_query("What is X?")

                            # Should call direct LLM, not SOAR
                            assert mock_direct.called
                            assert not mock_soar.called

    def test_complex_query_uses_soar_pipeline(self):
        """Complex query should use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_assess_complexity", return_value=0.8):
                    with patch.object(tools, "_execute_direct_llm") as mock_direct:
                        with patch.object(
                            tools,
                            "_execute_soar",
                            return_value={
                                "answer": "SOAR answer",
                                "execution_path": "soar_pipeline",
                            },
                        ) as mock_soar:
                            tools.aurora_query("Analyze complex architecture...")

                            # Should call SOAR, not direct LLM
                            assert mock_soar.called
                            assert not mock_direct.called

    def test_force_soar_bypasses_complexity_assessment(self):
        """force_soar=True should always use SOAR pipeline."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Even with low complexity, should use SOAR
        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_assess_complexity") as mock_assess:
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={"answer": "SOAR answer", "execution_path": "soar_pipeline"},
                    ) as mock_soar:
                        tools.aurora_query("Simple question", force_soar=True)

                        # Should call SOAR without checking complexity
                        assert mock_soar.called
                        assert not mock_assess.called

    def test_complexity_threshold_configurable(self):
        """Complexity threshold should be configurable via config."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"complexity_threshold": 0.5}}

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(tools, "_assess_complexity", return_value=0.55):
                        with patch.object(
                            tools,
                            "_execute_soar",
                            return_value={"answer": "SOAR", "execution_path": "soar_pipeline"},
                        ) as mock_soar:
                            # Complexity 0.55 > threshold 0.5, should use SOAR
                            tools.aurora_query("Test")
                            assert mock_soar.called

    def test_execution_path_in_response_direct_llm(self):
        """Response should indicate direct_llm execution path."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_assess_complexity", return_value=0.3):
                    with patch.object(
                        tools,
                        "_execute_direct_llm",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "direct_llm",
                            "metadata": {},
                        },
                    ):
                        result = tools.aurora_query("Simple query")

                        response = json.loads(result)
                        assert response["execution_path"] == "direct_llm"

    def test_execution_path_in_response_soar_pipeline(self):
        """Response should indicate soar_pipeline execution path."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_assess_complexity", return_value=0.8):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "metadata": {},
                        },
                    ):
                        result = tools.aurora_query("Complex query")

                        response = json.loads(result)
                        assert response["execution_path"] == "soar_pipeline"


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
                "temperature": 0.7,
            }

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=mock_execute):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Should eventually succeed
                    assert (
                        "error" not in response or response.get("answer") == "Success after retry"
                    )

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
                "temperature": 0.7,
            }

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=mock_execute):
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

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=mock_execute):
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

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=always_fail):
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
                "temperature": 0.7,
            }

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_execute_direct_llm", side_effect=mock_execute):
                    tools.aurora_query("Test query")
                    # Should have made multiple attempts
                    assert call_count[0] >= 2


class TestMemoryGracefulDegradation:
    """Test graceful degradation when memory is unavailable (FR-5.5)."""

    def test_query_succeeds_without_memory(self):
        """Query should succeed even when memory store is empty."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(tools, "_get_memory_context", return_value=""):
                    result = tools.aurora_query("What is Python?")
                    response = json.loads(result)

                    # Should not have an error related to memory
                    if "error" in response:
                        assert "memory" not in response["error"]["type"].lower()

    def test_memory_error_logs_warning(self):
        """Memory retrieval error should log warning, not raise exception."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(
                    tools, "_get_memory_context", side_effect=Exception("Memory unavailable")
                ):
                    # Should not raise exception
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    # Query should still complete (possibly with error, but not memory-related crash)
                    assert isinstance(response, dict)

    def test_empty_memory_store_handled_gracefully(self):
        """Empty memory store should not block query execution."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                # Memory returns empty string (no indexed content)
                with patch.object(tools, "_get_memory_context", return_value=""):
                    with patch.object(
                        tools,
                        "_execute_direct_llm",
                        return_value={
                            "answer": "LLM answer without memory context",
                            "execution_path": "direct_llm",
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        result = tools.aurora_query("Test query")
                        response = json.loads(result)

                        assert "answer" in response

    def test_memory_failure_does_not_affect_response_structure(self):
        """Response structure should be valid even when memory fails."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                with patch.object(
                    tools,
                    "_execute_direct_llm",
                    return_value={
                        "answer": "Answer",
                        "execution_path": "direct_llm",
                        "duration": 1.0,
                        "cost": 0.01,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7,
                    },
                ):
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

        with patch("aurora.mcp.tools.logger") as mock_logger:
            # Trigger an error
            tools.aurora_query("")

            # Should have logged the error
            assert mock_logger.error.called

    def test_api_key_missing_logged(self):
        """APIKeyMissing error should be logged."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch("aurora.mcp.tools.logger") as mock_logger:
            with patch.object(tools, "_get_api_key", return_value=None):
                tools.aurora_query("Test query")

                # Should have logged APIKeyMissing
                assert mock_logger.error.called

    def test_unexpected_exception_logged_with_traceback(self):
        """Unexpected exceptions should be logged with stack trace."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch("aurora.mcp.tools.logger") as mock_logger:
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(
                    tools, "_check_budget", side_effect=RuntimeError("Unexpected error")
                ):
                    result = tools.aurora_query("Test query")
                    response = json.loads(result)

                    assert "error" in response
                    # Should have logged with exc_info=True
                    mock_logger.error.assert_called()

    def test_validation_errors_logged(self):
        """Parameter validation errors should be logged."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch("aurora.mcp.tools.logger") as mock_logger:
            tools.aurora_query("Test", temperature=2.0)

            # Should have logged the InvalidParameter error
            assert mock_logger.error.called


# ==============================================================================
# Task 2.4: Progress Tracking Tests
# ==============================================================================


class TestProgressTracking:
    """Test progress tracking for SOAR phases (FR-4.1, PR-2.1)."""

    def test_soar_response_includes_all_nine_phases(self):
        """SOAR execution should include all 9 phase entries in verbose mode."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                # Don't mock _execute_soar - let it run to test real phase tracking
                result = tools.aurora_query("Complex analysis query", force_soar=True, verbose=True)
                response = json.loads(result)

                assert "phases" in response
                assert len(response["phases"]) == 9

                # Verify all 9 SOAR phase names
                phase_names = [p["phase"] for p in response["phases"]]
                expected_phases = [
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
                assert phase_names == expected_phases

    def test_each_phase_has_required_fields(self):
        """Each phase should have phase name, status, and duration."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert "phase" in phase, "Phase entry missing 'phase' field"
                    assert "status" in phase, "Phase entry missing 'status' field"
                    assert "duration" in phase, "Phase entry missing 'duration' field"

    def test_phase_duration_is_numeric(self):
        """Phase duration should be a number (seconds)."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert isinstance(
                        phase["duration"], (int, float)
                    ), f"Phase duration should be numeric, got {type(phase['duration'])}"
                    assert phase["duration"] >= 0, "Phase duration should be non-negative"

    def test_phase_status_is_completed(self):
        """Successful phases should have 'completed' status."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                result = tools.aurora_query("Complex query", force_soar=True, verbose=True)
                response = json.loads(result)

                for phase in response["phases"]:
                    assert (
                        phase["status"] == "completed"
                    ), f"Expected 'completed' status, got '{phase['status']}'"

    def test_progress_not_included_for_direct_llm(self):
        """Direct LLM execution should not include SOAR phases."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
                # Simple query should use direct LLM
                result = tools.aurora_query("What is X?", verbose=True)
                response = json.loads(result)

                # Direct LLM should not have phases
                assert "phases" not in response or response.get("execution_path") == "soar_pipeline"

    def test_total_duration_in_metadata(self):
        """Metadata should include total duration."""
        tools = AuroraMCPTools(db_path=":memory:")

        with patch.object(tools, "_get_api_key", return_value="test-key"):
            with patch.object(tools, "_check_budget", return_value=True):
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

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_direct_llm",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "direct_llm",
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        # verbose=None should use config (quiet)
                        result = tools.aurora_query("Test", verbose=None)
                        response = json.loads(result)

                        # Quiet mode should not include phases
                        assert "phases" not in response

    def test_verbosity_normal_standard_output(self):
        """Normal verbosity should return standard output without phases."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "normal"}}

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "phase_trace": {
                                "phases": [
                                    {"phase": "Assess", "duration": 0.1, "status": "completed"}
                                ]
                            },
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
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

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "phase_trace": {
                                "phases": [
                                    {"phase": "Assess", "duration": 0.1, "status": "completed"}
                                ]
                            },
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Verbose mode should include phases for SOAR
                        assert "phases" in response

    def test_parameter_overrides_config_verbose_true(self):
        """verbose=True parameter should override config setting."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "quiet"}}  # Config says quiet

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "phase_trace": {
                                "phases": [
                                    {"phase": "Assess", "duration": 0.1, "status": "completed"}
                                ]
                            },
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        # Parameter verbose=True should override config
                        result = tools.aurora_query("Complex", force_soar=True, verbose=True)
                        response = json.loads(result)

                        # Should include phases because parameter overrides config
                        assert "phases" in response

    def test_parameter_overrides_config_verbose_false(self):
        """verbose=False parameter should override config setting."""
        tools = AuroraMCPTools(db_path=":memory:")

        mock_config = {"query": {"verbosity": "verbose"}}  # Config says verbose

        with patch.object(tools, "_load_config", return_value=mock_config):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "phase_trace": {
                                "phases": [
                                    {"phase": "Assess", "duration": 0.1, "status": "completed"}
                                ]
                            },
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        # Parameter verbose=False should override config
                        result = tools.aurora_query("Complex", force_soar=True, verbose=False)
                        response = json.loads(result)

                        # Should NOT include phases because parameter overrides config
                        assert "phases" not in response

    def test_env_var_verbosity_override(self):
        """AURORA_VERBOSITY env var should override config file."""
        tools = AuroraMCPTools(db_path=":memory:")

        # Clear any cached config
        if hasattr(tools, "_config_cache"):
            del tools._config_cache

        with patch.dict("os.environ", {"AURORA_VERBOSITY": "verbose"}):
            with patch.object(tools, "_get_api_key", return_value="test-key"):
                with patch.object(tools, "_check_budget", return_value=True):
                    with patch.object(
                        tools,
                        "_execute_soar",
                        return_value={
                            "answer": "Answer",
                            "execution_path": "soar_pipeline",
                            "phase_trace": {
                                "phases": [
                                    {"phase": "Assess", "duration": 0.1, "status": "completed"}
                                ]
                            },
                            "duration": 1.0,
                            "cost": 0.01,
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "model": "claude-sonnet-4-20250514",
                            "temperature": 0.7,
                        },
                    ):
                        result = tools.aurora_query("Complex", force_soar=True, verbose=None)
                        response = json.loads(result)

                        # Env var sets verbose, so phases should be included
                        assert "phases" in response
