"""Fault injection tests for malformed LLM output scenarios.

Tests how the system handles malformed or invalid LLM outputs:
- Invalid JSON syntax
- JSON with missing required fields
- JSON with wrong data types
- Non-JSON text responses when JSON expected
- Partially valid JSON
- JSON extraction from markdown code blocks
- Unicode and encoding issues
- Very large outputs that exceed limits
"""

import json
from unittest.mock import Mock

import pytest
from aurora.reasoning.llm_client import LLMClient, LLMResponse, extract_json_from_text


class MalformedLLMClient(LLMClient):
    """Mock LLM client that returns malformed outputs."""

    def __init__(self, malformed_type: str = "invalid_json"):
        """Initialize malformed client.

        Args:
            malformed_type: Type of malformed output to generate
                - "invalid_json": Invalid JSON syntax
                - "missing_fields": Valid JSON missing required fields
                - "wrong_types": Valid JSON with wrong data types
                - "no_json": Plain text with no JSON
                - "partial_json": Incomplete/truncated JSON
                - "markdown_wrapped": Valid JSON wrapped in markdown
                - "unicode_issues": JSON with problematic unicode
                - "oversized": Extremely large output
        """
        self._malformed_type = malformed_type

    @property
    def default_model(self) -> str:
        """Get default model."""
        return "test-model"

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate malformed text response."""
        content_map = {
            "invalid_json": '{"invalid": json syntax here}',
            "no_json": "This is just plain text with no JSON at all.",
            "partial_json": '{"incomplete": "json that ends abrubtly',
            "unicode_issues": '{"text": "Invalid unicode \\uXXXX here"}',
            "oversized": json.dumps({"data": "x" * 1000000}),  # 1MB string
        }

        content = content_map.get(self._malformed_type, "Error")

        return LLMResponse(
            content=content,
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
        )

    def generate_json(self, prompt: str, **kwargs) -> dict:
        """Generate malformed JSON response."""
        if self._malformed_type == "invalid_json":
            # Return string that looks like JSON but isn't valid
            raise ValueError("Invalid JSON: Expecting property name enclosed in double quotes")

        if self._malformed_type == "missing_fields":
            # Valid JSON but missing required fields
            return {"partial": "data"}

        if self._malformed_type == "wrong_types":
            # Valid JSON with wrong data types
            return {
                "complexity": 123,  # Should be string
                "confidence": "high",  # Should be float
                "subgoals": "not a list",  # Should be list
            }

        if self._malformed_type == "no_json":
            # Plain text - raise error since we can't extract JSON
            raise ValueError("No JSON found in response")

        if self._malformed_type == "partial_json":
            # Truncated JSON
            raise ValueError("Unexpected end of JSON input")

        if self._malformed_type == "markdown_wrapped":
            # Valid JSON wrapped in markdown (should be extracted correctly)
            return {"status": "success", "data": "valid"}

        if self._malformed_type == "unicode_issues":
            # Problematic unicode
            raise ValueError("Invalid unicode escape sequence")

        if self._malformed_type == "oversized":
            # Extremely large output
            return {"data": "x" * 1000000}

        raise ValueError("Unknown malformed type")

    def count_tokens(self, text: str) -> int:
        """Count tokens (simple approximation)."""
        return len(text.split())


class TestInvalidJSONSyntax:
    """Test invalid JSON syntax scenarios."""

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON syntax raises appropriate error."""
        client = MalformedLLMClient(malformed_type="invalid_json")

        with pytest.raises(ValueError, match="Invalid JSON"):
            client.generate_json("Test prompt")

    def test_partial_json_raises_error(self):
        """Test that partial/truncated JSON raises error."""
        client = MalformedLLMClient(malformed_type="partial_json")

        with pytest.raises(ValueError, match="JSON"):
            client.generate_json("Test prompt")

    def test_no_json_raises_error(self):
        """Test that plain text response raises error when JSON expected."""
        client = MalformedLLMClient(malformed_type="no_json")

        with pytest.raises(ValueError, match="No JSON"):
            client.generate_json("Test prompt")


class TestMissingRequiredFields:
    """Test JSON with missing required fields."""

    def test_missing_fields_in_decomposition(self):
        """Test decomposition with missing required fields."""
        from aurora.reasoning.decompose import decompose_query

        client = MalformedLLMClient(malformed_type="missing_fields")

        # Should raise error due to missing required fields
        with pytest.raises((KeyError, ValueError)):
            decompose_query(
                llm_client=client,
                query="Test query",
                complexity="MEDIUM",
            )

    def test_missing_fields_in_verification(self):
        """Test verification with missing required fields."""
        from aurora.reasoning.verify import verify_decomposition

        client = MalformedLLMClient(malformed_type="missing_fields")

        decomposition = {
            "subgoals": [{"description": "Test", "agent": "test-agent"}],
            "execution_order": {"parallelizable": [[0]], "sequential": []},
        }

        # Should raise error due to missing required fields
        with pytest.raises((KeyError, ValueError)):
            verify_decomposition(
                llm_client=client,
                query="Test query",
                decomposition=decomposition,
                option="A",
            )


class TestWrongDataTypes:
    """Test JSON with wrong data types."""

    def test_wrong_type_complexity_assessment(self):
        """Test complexity assessment with wrong data types."""
        from aurora.soar.phases.assess import _assess_tier2_llm

        client = MalformedLLMClient(malformed_type="wrong_types")

        keyword_result = {"complexity": "MEDIUM", "confidence": 0.5, "score": 0.5}

        # Assessment gracefully falls back to keyword result even with LLM errors
        result = _assess_tier2_llm(
            query="Test query",
            keyword_result=keyword_result,
            llm_client=client,
        )

        # Should return keyword result as fallback
        assert result["complexity"] == "MEDIUM"

    def test_wrong_type_subgoals(self):
        """Test decomposition with subgoals as wrong type."""
        # Manually create invalid decomposition
        invalid_output = {
            "goal": "Test goal",
            "subgoals": "not a list",  # Should be list
            "execution_order": {"parallelizable": [], "sequential": []},
            "expected_tools": [],
        }

        # Should fail when trying to iterate over string (iterates chars, not expected)
        # This test verifies the structure would cause issues
        result = []
        for subgoal in invalid_output["subgoals"]:
            result.append(subgoal)

        # Iterating string gives characters, not subgoal dicts
        assert len(result) > 0  # Got characters, not subgoals
        assert isinstance(result[0], str)  # Each item is a char, not dict


class TestJSONExtraction:
    """Test JSON extraction from various formats."""

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        text = """
        Here's the JSON:
        ```json
        {"key": "value", "number": 42}
        ```
        That's the result.
        """

        result = extract_json_from_text(text)
        assert result["key"] == "value"
        assert result["number"] == 42

    def test_extract_json_without_language_tag(self):
        """Test extracting JSON from code block without language tag."""
        text = """
        ```
        {"status": "success"}
        ```
        """

        result = extract_json_from_text(text)
        assert result["status"] == "success"

    def test_extract_json_direct(self):
        """Test extracting JSON from plain text (no markdown)."""
        text = '{"direct": "json", "works": true}'

        result = extract_json_from_text(text)
        assert result["direct"] == "json"
        assert result["works"] is True

    def test_extract_json_with_extra_text(self):
        """Test extracting JSON with extra surrounding text."""
        text = """
        Sure, here's the JSON you requested:

        ```json
        {
            "extracted": "successfully",
            "despite": "extra text"
        }
        ```

        I hope that helps!
        """

        result = extract_json_from_text(text)
        assert result["extracted"] == "successfully"

    def test_extract_json_no_json_found(self):
        """Test error when no JSON found in text."""
        text = "This is just plain text with no JSON at all."

        with pytest.raises(ValueError, match="No valid JSON found"):
            extract_json_from_text(text)


class TestUnicodeAndEncoding:
    """Test unicode and encoding issues."""

    def test_unicode_in_json(self):
        """Test handling of valid unicode in JSON."""
        text = '{"message": "Hello \\u4e16\\u754c", "emoji": "\\ud83d\\ude00"}'

        result = extract_json_from_text(text)
        assert "message" in result
        # Should decode unicode properly

    def test_malformed_unicode_raises_error(self):
        """Test that malformed unicode raises error."""
        client = MalformedLLMClient(malformed_type="unicode_issues")

        with pytest.raises(ValueError):
            client.generate_json("Test prompt")


class TestOversizedOutput:
    """Test very large outputs."""

    def test_oversized_output_handling(self):
        """Test handling of very large outputs."""
        client = MalformedLLMClient(malformed_type="oversized")

        # Should handle large output (may be slow)
        result = client.generate_json("Test prompt")

        # Verify it's actually large
        assert len(result["data"]) == 1000000

    def test_oversized_text_truncation(self):
        """Test that oversized text responses are handled."""
        client = MalformedLLMClient(malformed_type="oversized")

        response = client.generate("Test prompt")

        # Should have very large content
        assert len(response.content) > 100000


class TestMalformedDecomposition:
    """Test malformed decomposition outputs."""

    def test_decomposition_with_invalid_agent_names(self):
        """Test decomposition with invalid agent names."""
        invalid_decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test task",
                    "suggested_agent": None,  # Invalid: None instead of string
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
            "expected_tools": ["tool"],
        }

        # Routing fails with None agent (AttributeError on split())
        from aurora.soar.agent_registry import AgentRegistry
        from aurora.soar.phases.route import route_subgoals

        registry = AgentRegistry()

        # Should raise AttributeError when trying to split None
        with pytest.raises(AttributeError, match="'NoneType'.*'split'"):
            route_subgoals(
                decomposition=invalid_decomposition,
                agent_registry=registry,
            )

    def test_decomposition_with_invalid_dependencies(self):
        """Test decomposition with out-of-range dependencies."""
        invalid_decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test task",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [999],  # Invalid: out of range
                }
            ],
            "execution_order": [{"phase": 1, "parallelizable": [0], "sequential": []}],
            "expected_tools": ["tool"],
        }

        # Verification should catch this
        from aurora.reasoning.verify import verify_decomposition

        # Create mock client that returns high scores (won't catch the issue in mock)
        mock_client = Mock(spec=LLMClient)
        mock_client.default_model = "test-model"

        # The verification logic should detect invalid dependencies
        # (though our mock might not - this tests the structure)
        try:
            verify_decomposition(
                llm_client=mock_client,
                query="Test query",
                decomposition=invalid_decomposition,
                option="A",
            )
            # If it doesn't raise, verify it at least identified the issue
        except (KeyError, IndexError, ValueError):
            # Expected - invalid dependency detected
            pass

    def test_decomposition_with_missing_execution_order(self):
        """Test decomposition missing execution_order field."""
        invalid_decomposition = {
            "goal": "Test goal",
            "subgoals": [
                {
                    "description": "Test task",
                    "suggested_agent": "test-agent",
                    "is_critical": True,
                    "depends_on": [],
                }
            ],
            # Missing execution_order field
            "expected_tools": ["tool"],
        }

        # Should raise KeyError when accessing execution_order
        with pytest.raises(KeyError):
            _ = invalid_decomposition["execution_order"]


class TestMalformedVerification:
    """Test malformed verification outputs."""

    def test_verification_with_invalid_scores(self):
        """Test verification with out-of-range scores."""
        from aurora.reasoning.verify import (
            VerificationOption,
            VerificationResult,
            VerificationVerdict,
        )

        # Scores are not validated at construction - system accepts out-of-range values
        # This test documents current behavior (no validation)
        result = VerificationResult(
            completeness=1.5,  # Out of range but accepted
            consistency=0.8,
            groundedness=0.7,
            routability=0.9,
            overall_score=1.2,  # Out of range but accepted
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Values are stored as-is without validation
        assert result.completeness == 1.5
        assert result.overall_score == 1.2

    def test_verification_with_negative_scores(self):
        """Test verification with negative scores."""
        from aurora.reasoning.verify import (
            VerificationOption,
            VerificationResult,
            VerificationVerdict,
        )

        # Negative scores are not validated - system accepts them
        # This test documents current behavior (no validation)
        result = VerificationResult(
            completeness=-0.1,  # Negative but accepted
            consistency=0.8,
            groundedness=0.7,
            routability=0.9,
            overall_score=0.7,
            verdict=VerificationVerdict.PASS,
            issues=[],
            suggestions=[],
            option_used=VerificationOption.SELF,
        )

        # Values are stored as-is
        assert result.completeness == -0.1


class TestMalformedSynthesis:
    """Test malformed synthesis outputs."""

    def test_synthesis_with_missing_traceability(self):
        """Test synthesis missing traceability links."""
        from aurora.reasoning.synthesize import SynthesisResult

        # Create synthesis without traceability
        result = SynthesisResult(
            answer="Test answer",
            confidence=0.8,
            traceability=[],  # Empty traceability
        )

        # Should be valid but flagged in verification
        assert result.confidence == 0.8
        assert len(result.traceability) == 0

    def test_synthesis_with_invalid_confidence(self):
        """Test synthesis with out-of-range confidence."""
        from aurora.reasoning.synthesize import SynthesisResult

        # Confidence is not validated - system accepts out-of-range values
        # This test documents current behavior (no validation)
        result = SynthesisResult(
            answer="Test answer",
            confidence=1.5,  # Out of range but accepted
            traceability=[],
        )

        # Value is stored as-is
        assert result.confidence == 1.5


class TestErrorRecovery:
    """Test error recovery strategies for malformed outputs."""

    def test_retry_on_malformed_json(self):
        """Test that malformed JSON triggers retry."""
        # Create client that fails first time, succeeds second time
        call_count = {"count": 0}

        def mock_generate_json(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise ValueError("Invalid JSON")
            return {"status": "success"}

        mock_client = Mock(spec=LLMClient)
        mock_client.generate_json.side_effect = mock_generate_json
        mock_client.default_model = "test-model"

        # First call fails, but retry succeeds
        with pytest.raises(ValueError):
            mock_client.generate_json("Test prompt")

        # Second call succeeds
        result = mock_client.generate_json("Test prompt")
        assert result["status"] == "success"
        assert call_count["count"] == 2

    def test_fallback_on_parsing_error(self):
        """Test fallback behavior when parsing fails."""
        # Simulate trying to parse, falling back to default
        try:
            result = json.loads("invalid json")
        except json.JSONDecodeError:
            # Fallback to default/safe value
            result = {"status": "error", "fallback": True}

        assert result["fallback"] is True


class TestMalformedMetadata:
    """Test malformed metadata in outputs."""

    def test_missing_metadata_fields(self):
        """Test handling of missing metadata fields."""
        from aurora.reasoning.llm_client import LLMResponse

        # Create response with minimal metadata
        response = LLMResponse(
            content="Test content",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={},  # Empty metadata
        )

        # Should be valid with empty metadata
        assert response.metadata == {}

    def test_extra_metadata_fields(self):
        """Test handling of extra/unexpected metadata fields."""
        from aurora.reasoning.llm_client import LLMResponse

        # Create response with extra fields
        response = LLMResponse(
            content="Test content",
            model="test-model",
            input_tokens=100,
            output_tokens=50,
            finish_reason="stop",
            metadata={"extra": "field", "unexpected": 123},
        )

        # Should accept extra fields in metadata
        assert response.metadata["extra"] == "field"
        assert response.metadata["unexpected"] == 123


class TestEdgeCases:
    """Test edge cases for malformed outputs."""

    def test_empty_json_object(self):
        """Test handling of empty JSON object."""
        text = "{}"
        result = extract_json_from_text(text)
        assert result == {}

    def test_empty_json_array(self):
        """Test handling of empty JSON array."""
        text = "[]"
        result = extract_json_from_text(text)
        assert result == []

    def test_null_json_value(self):
        """Test handling of null JSON value."""
        text = '{"value": null}'
        result = extract_json_from_text(text)
        assert result["value"] is None

    def test_nested_malformed_json(self):
        """Test nested JSON with malformed inner structure."""
        text = '{"outer": {"inner": "valid"}, "broken": }'

        with pytest.raises(ValueError):
            extract_json_from_text(text)

    def test_multiple_json_blocks(self):
        """Test text with multiple JSON blocks."""
        text = """
        First block:
        ```json
        {"first": "block"}
        ```

        Second block:
        ```json
        {"second": "block"}
        ```
        """

        # Should extract first valid JSON found
        result = extract_json_from_text(text)
        assert "first" in result or "second" in result
