"""Tests for assess.py type consistency."""

from aurora_soar.phases.assess import AssessmentResult, ComplexityAssessor


def test_complexity_score_type():
    """Test that AssessmentResult.score is properly typed as int.

    The assessor returns scores that should be integers. This test ensures
    the type consistency between the assessor and AssessmentResult.
    """
    # Create assessor
    assessor = ComplexityAssessor()

    # Test simple query
    result = assessor.assess("What is the weather?")

    # Verify score is int
    assert isinstance(result.score, int), f"Expected int, got {type(result.score)}"

    # Verify level is one of the valid literals
    valid_levels = {"simple", "medium", "complex", "critical"}
    assert result.level in valid_levels, f"Invalid level: {result.level}"

    # Verify confidence is float
    assert isinstance(result.confidence, float), f"Expected float, got {type(result.confidence)}"

    # Test complex query
    complex_result = assessor.assess(
        "Explain the security implications of implementing OAuth2 "
        "with multi-factor authentication across distributed systems"
    )
    assert isinstance(complex_result.score, int)
    assert complex_result.level in valid_levels


def test_assessment_result_breakdown_types():
    """Test that breakdown dict has proper types.

    The breakdown should have string keys and numeric values (int or float).
    """
    assessor = ComplexityAssessor()
    result = assessor.assess("How do I implement caching?")

    # breakdown should be a dict
    assert isinstance(result.breakdown, dict)

    # All keys should be strings, all values should be numeric
    for key, value in result.breakdown.items():
        assert isinstance(key, str), f"Key {key} is not str"
        assert isinstance(value, (int, float)), f"Value {value} is not numeric"


def test_assessment_result_to_dict():
    """Test that to_dict() returns properly typed dict."""
    result = AssessmentResult(
        level="simple",
        score=5,
        confidence=0.85,
        signals=["simple_query"],
        breakdown={"base": 5},
    )

    result_dict = result.to_dict()

    # Verify return type
    assert isinstance(result_dict, dict)

    # Verify expected keys
    expected_keys = {"level", "score", "confidence", "signals", "breakdown"}
    assert set(result_dict.keys()) == expected_keys
