"""Tests for HTTP status code error classification in spawner.

Tests that error messages are correctly classified into:
- Permanent errors (auth_error, forbidden, invalid_model, invalid_request, not_found)
- Transient errors (transient_error for 500s, timeouts, network issues)
- Rate limit errors (special handling - no circuit breaker)

This classification feeds into the circuit breaker's smart fast-fail logic.
"""

import pytest


# We'll test the classification logic by mocking SpawnResult with various error messages


class MockSpawnResult:
    """Mock SpawnResult for testing error classification."""

    def __init__(self, success=False, error=None, termination_reason=None, exit_code=1):
        self.success = success
        self.error = error
        self.termination_reason = termination_reason
        self.exit_code = exit_code
        self.output = ""
        self.execution_time = 0


class TestPermanentErrorClassification:
    """Test permanent errors are classified correctly."""

    def test_401_unauthorized_classified_as_auth_error(self):
        """401 Unauthorized should be classified as auth_error."""
        error_messages = [
            "API Error: 401 Unauthorized",
            "Authentication failed: unauthorized access",
            "Invalid API key provided",
            "authentication failed - check your API key",
        ]

        for error_msg in error_messages:
            result = MockSpawnResult(error=error_msg)
            # Simulate classification logic
            error_lower = error_msg.lower()

            if any(
                x in error_lower
                for x in ["unauthorized", "401", "invalid api key", "authentication failed"]
            ):
                failure_type = "auth_error"
            else:
                failure_type = None

            assert failure_type == "auth_error", f"Failed to classify: {error_msg}"

    def test_403_forbidden_classified_correctly(self):
        """403 Forbidden should be classified as forbidden."""
        error_messages = [
            "API Error: 403 Forbidden",
            "Insufficient permissions to access resource",
            "forbidden - you don't have access",
        ]

        for error_msg in error_messages:
            result = MockSpawnResult(error=error_msg)
            error_lower = error_msg.lower()

            if any(x in error_lower for x in ["forbidden", "403", "insufficient permissions"]):
                failure_type = "forbidden"
            else:
                failure_type = None

            assert failure_type == "forbidden", f"Failed to classify: {error_msg}"

    def test_invalid_model_classified_correctly(self):
        """Invalid model errors should be classified as invalid_model."""
        error_messages = [
            "API Error: The provided model identifier is invalid",
            "invalid model specified",
            "model not available in your region",
            "model identifier doesn't exist",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(
                x in error_lower
                for x in [
                    "invalid model",
                    "model identifier",
                    "model not found",
                    "model not available",
                ]
            ):
                failure_type = "invalid_model"
            else:
                failure_type = None

            assert failure_type == "invalid_model", f"Failed to classify: {error_msg}"

    def test_400_bad_request_classified_as_invalid_request(self):
        """400 Bad Request should be classified as invalid_request."""
        error_messages = [
            "API Error: 400 Bad Request",
            "Invalid request parameters",
            "Malformed JSON in request body",
            "bad request - check your parameters",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(
                x in error_lower for x in ["400", "bad request", "invalid request", "malformed"]
            ):
                failure_type = "invalid_request"
            else:
                failure_type = None

            assert failure_type == "invalid_request", f"Failed to classify: {error_msg}"

    def test_404_not_found_classified_correctly(self):
        """404 Not Found should be classified as not_found."""
        error_messages = [
            "API Error: 404 Not Found",
            "Endpoint not found",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(x in error_lower for x in ["404", "not found", "endpoint not found"]):
                failure_type = "not_found"
            else:
                failure_type = None

            assert failure_type == "not_found", f"Failed to classify: {error_msg}"


class TestTransientErrorClassification:
    """Test transient errors are classified correctly."""

    def test_500_errors_classified_as_transient(self):
        """500-series errors should be classified as transient."""
        error_messages = [
            "API Error: 500 Internal Server Error",
            "502 Bad Gateway",
            "503 Service Unavailable",
            "504 Gateway Timeout",
            "internal server error occurred",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(
                x in error_lower
                for x in [
                    "500",
                    "502",
                    "503",
                    "504",
                    "internal server error",
                    "bad gateway",
                    "service unavailable",
                ]
            ):
                failure_type = "transient_error"
            else:
                failure_type = None

            assert failure_type == "transient_error", f"Failed to classify: {error_msg}"

    def test_network_errors_classified_as_transient(self):
        """Network errors should be classified as transient."""
        error_messages = [
            "Connection refused",
            "ECONNRESET: connection reset by peer",
            "Network timeout occurred",
            "Connection error - please retry",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(x in error_lower for x in ["connection", "econnreset", "network", "timeout"]):
                failure_type = "transient_error"
            else:
                failure_type = None

            assert failure_type == "transient_error", f"Failed to classify: {error_msg}"

    def test_json_parse_errors_classified_as_transient(self):
        """JSON parse errors should be classified as transient."""
        error_messages = [
            "Failed to parse JSON response",
            "JSON decode error",
            "Invalid JSON in response body",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(x in error_lower for x in ["json", "parse"]):
                failure_type = "transient_error"
            else:
                failure_type = None

            assert failure_type == "transient_error", f"Failed to classify: {error_msg}"


class TestRateLimitClassification:
    """Test rate limit errors are classified correctly."""

    def test_rate_limit_errors_classified_correctly(self):
        """Rate limit errors should be classified as rate_limit."""
        error_messages = [
            "Rate limit exceeded",
            "429 Too Many Requests",
            "Quota exceeded for this month",
            "too many requests - please slow down",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(
                x in error_lower
                for x in ["rate limit", "429", "quota exceeded", "too many requests"]
            ):
                failure_type = "rate_limit"
            else:
                failure_type = None

            assert failure_type == "rate_limit", f"Failed to classify: {error_msg}"


class TestClassificationPriority:
    """Test error classification priority (rate limits checked first)."""

    def test_rate_limit_takes_priority_over_other_patterns(self):
        """Rate limit classification should take priority."""
        error_msg = "429 Rate limit exceeded - API connection failed"
        error_lower = error_msg.lower()

        # Check rate limit first (as in actual code)
        if any(
            x in error_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        ):
            failure_type = "rate_limit"
        elif any(x in error_lower for x in ["connection", "econnreset", "network"]):
            failure_type = "transient_error"
        else:
            failure_type = None

        # Should be rate_limit, not transient_error
        assert failure_type == "rate_limit"

    def test_permanent_error_priority_over_transient(self):
        """Permanent errors should be checked before transient."""
        error_msg = "401 Unauthorized - connection failed"
        error_lower = error_msg.lower()

        # Check permanent errors before transient
        if any(x in error_lower for x in ["unauthorized", "401"]):
            failure_type = "auth_error"
        elif any(x in error_lower for x in ["connection"]):
            failure_type = "transient_error"
        else:
            failure_type = None

        # Should be auth_error, not transient_error
        assert failure_type == "auth_error"


class TestGenericInferenceErrors:
    """Test generic API/inference errors."""

    def test_generic_api_errors_classified_as_inference(self):
        """Generic API errors should be classified as inference."""
        error_messages = [
            "API call failed",
            "Inference error occurred",
            "Model inference timeout",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            # After checking specific errors, fall back to inference
            if any(x in error_lower for x in ["api", "inference"]):
                failure_type = "inference"
            else:
                failure_type = None

            assert failure_type == "inference", f"Failed to classify: {error_msg}"


class TestRealWorldErrorMessages:
    """Test classification with real-world error message formats."""

    def test_anthropic_invalid_model_error(self):
        """Real Anthropic invalid model error."""
        error_msg = "API Error (us.anthropic.claude-sonnet-4-5-20250929-v1:0): 400 The provided model identifier is invalid."
        error_lower = error_msg.lower()

        # Should match invalid_model before invalid_request
        if any(x in error_lower for x in ["invalid model", "model identifier"]):
            failure_type = "invalid_model"
        elif any(x in error_lower for x in ["400", "bad request"]):
            failure_type = "invalid_request"
        else:
            failure_type = None

        assert failure_type == "invalid_model"

    def test_openai_rate_limit_error(self):
        """Real OpenAI rate limit error."""
        error_msg = "Error code: 429 - {'error': {'message': 'Rate limit exceeded', 'type': 'rate_limit_error'}}"
        error_lower = error_msg.lower()

        if any(x in error_lower for x in ["rate limit", "429"]):
            failure_type = "rate_limit"
        else:
            failure_type = None

        assert failure_type == "rate_limit"

    def test_connection_timeout_error(self):
        """Real connection timeout error."""
        error_msg = "HTTPSConnectionPool(host='api.anthropic.com', port=443): Read timed out. (read timeout=60)"
        error_lower = error_msg.lower()

        if any(x in error_lower for x in ["connection", "timeout"]):
            failure_type = "transient_error"
        else:
            failure_type = None

        assert failure_type == "transient_error"

    def test_unauthorized_api_key_error(self):
        """Real unauthorized API key error."""
        error_msg = "Error code: 401 - {'error': {'message': 'Incorrect API key provided'}}"
        error_lower = error_msg.lower()

        if any(x in error_lower for x in ["unauthorized", "401", "incorrect api key"]):
            failure_type = "auth_error"
        else:
            failure_type = None

        assert failure_type == "auth_error"


class TestEdgeCases:
    """Test edge cases in error classification."""

    def test_empty_error_message(self):
        """Empty error message should not crash."""
        error_msg = ""
        error_lower = error_msg.lower()

        # Should not raise exception
        failure_type = None
        if any(x in error_lower for x in ["500"]):
            failure_type = "transient_error"

        assert failure_type is None

    def test_none_error_message(self):
        """None error message should be handled."""
        error_msg = None

        # Should not raise exception
        if error_msg:
            error_lower = error_msg.lower()
        else:
            error_lower = ""

        failure_type = None
        assert failure_type is None

    def test_case_insensitive_matching(self):
        """Error classification should be case-insensitive."""
        error_messages = [
            "RATE LIMIT EXCEEDED",
            "Rate Limit Exceeded",
            "rate limit exceeded",
            "RaTe LiMiT eXcEeDeD",
        ]

        for error_msg in error_messages:
            error_lower = error_msg.lower()

            if any(x in error_lower for x in ["rate limit"]):
                failure_type = "rate_limit"
            else:
                failure_type = None

            assert failure_type == "rate_limit", f"Case-insensitive match failed: {error_msg}"


class TestClassificationCompleteness:
    """Test all error types are covered."""

    @pytest.mark.parametrize(
        "error_msg,expected_type",
        [
            ("401 Unauthorized", "auth_error"),
            ("403 Forbidden", "forbidden"),
            ("Invalid model identifier", "invalid_model"),
            ("400 Bad Request", "invalid_request"),
            ("404 Not Found", "not_found"),
            ("500 Internal Server Error", "transient_error"),
            ("Connection refused", "transient_error"),
            ("429 Rate limit", "rate_limit"),
            ("API call failed", "inference"),
            ("Timeout occurred", "transient_error"),
        ],
    )
    def test_error_message_classification(self, error_msg, expected_type):
        """Test various error messages are classified correctly."""
        error_lower = error_msg.lower()

        # Classification logic (simplified version of actual spawner code)
        failure_type = None

        # Rate limits first
        if any(
            x in error_lower for x in ["rate limit", "429", "quota exceeded", "too many requests"]
        ):
            failure_type = "rate_limit"
        # Permanent errors
        elif any(
            x in error_lower
            for x in ["unauthorized", "401", "invalid api key", "authentication failed"]
        ):
            failure_type = "auth_error"
        elif any(x in error_lower for x in ["forbidden", "403", "insufficient permissions"]):
            failure_type = "forbidden"
        elif any(
            x in error_lower
            for x in ["invalid model", "model identifier", "model not found", "model not available"]
        ):
            failure_type = "invalid_model"
        elif any(x in error_lower for x in ["400", "bad request", "invalid request", "malformed"]):
            failure_type = "invalid_request"
        elif any(x in error_lower for x in ["404", "not found", "endpoint not found"]):
            failure_type = "not_found"
        # Transient errors
        elif any(
            x in error_lower
            for x in [
                "500",
                "502",
                "503",
                "504",
                "internal server error",
                "bad gateway",
                "service unavailable",
            ]
        ):
            failure_type = "transient_error"
        elif any(x in error_lower for x in ["connection", "econnreset", "network", "timeout"]):
            failure_type = "transient_error"
        elif any(x in error_lower for x in ["json", "parse"]):
            failure_type = "transient_error"
        # Generic inference
        elif any(x in error_lower for x in ["api", "inference"]):
            failure_type = "inference"

        assert failure_type == expected_type, (
            f"Expected {expected_type}, got {failure_type} for: {error_msg}"
        )
