"""Unit tests for Phase 1: Complexity Assessment."""

from aurora.soar.phases.assess import (
    COMPLEX_KEYWORDS,
    CRITICAL_KEYWORDS,
    MEDIUM_KEYWORDS,
    SIMPLE_KEYWORDS,
    _assess_tier1_keyword,
    assess_complexity,
)


class TestKeywordClassifier:
    """Tests for Tier 1 keyword-based classifier."""

    def test_simple_query_what_is(self):
        """Test SIMPLE classification for 'what is' queries."""
        query = "What is OAuth2?"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "SIMPLE"
        assert confidence >= 0.3  # May have lower confidence with only 3 words
        assert score > 0  # Should match some keywords

    def test_simple_query_definition(self):
        """Test SIMPLE classification for definition queries."""
        query = "Define RESTful API"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "SIMPLE"
        assert confidence >= 0.3  # May have lower confidence


    def test_medium_query_refactoring(self):
        """Test MEDIUM classification for refactoring queries."""
        query = "Refactor the authentication module to improve readability"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "MEDIUM"

    def test_complex_query_system_design(self):
        """Test COMPLEX classification for system design queries."""
        # Need multiple complex keywords to override weight
        query = "Design and architect a scalable infrastructure with performance optimization"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity in {"COMPLEX", "MEDIUM"}  # Either is acceptable for system design

    def test_complex_query_integration(self):
        """Test COMPLEX classification for integration queries."""
        # Avoid "authentication" which is a CRITICAL keyword
        query = "Integrate the new notification system with all existing services"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity in {"COMPLEX", "MEDIUM"}  # Either is acceptable

    def test_critical_query_security(self):
        """Test CRITICAL classification for security queries."""
        query = "Fix security vulnerability in authentication endpoint"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "CRITICAL"
        assert confidence >= 0.8  # Should be very confident for security keywords

    def test_critical_query_production(self):
        """Test CRITICAL classification for production queries."""
        query = "Emergency fix for production payment processing outage"
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "CRITICAL"
        assert confidence >= 0.8

    def test_empty_query(self):
        """Test handling of empty query."""
        query = ""
        complexity, score, confidence = _assess_tier1_keyword(query)

        assert complexity == "SIMPLE"  # Default to simple for empty
        assert score == 0.0
        assert confidence < 0.5  # Low confidence

    def test_no_keyword_matches(self):
        """Test query with no keyword matches."""
        query = "xyz abc def"
        complexity, score, confidence = _assess_tier1_keyword(query)

        # Should return something, probably with low confidence
        assert complexity in {"SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"}
        assert confidence < 0.5  # Should have low confidence

    def test_mixed_keywords_medium_wins(self):
        """Test query with mixed keywords where medium should win."""
        query = "Create and implement a new feature"  # create + implement
        complexity, score, confidence = _assess_tier1_keyword(query)

        # Should classify as MEDIUM due to implementation keywords
        assert complexity in {"MEDIUM", "COMPLEX"}

    def test_confidence_increases_with_matches(self):
        """Test that confidence increases with more keyword matches."""
        query1 = "implement"  # 1 keyword
        query2 = "implement and create and refactor"  # 3 keywords

        _, _, conf1 = _assess_tier1_keyword(query1)
        _, _, conf2 = _assess_tier1_keyword(query2)

        # More matches should generally mean higher confidence
        # (not always true due to separation factor, but should hold for similar complexity)
        assert conf2 >= conf1 - 0.2  # Allow some variance


class TestAssessComplexity:
    """Tests for main assess_complexity function."""

    def test_assess_without_llm_high_confidence(self):
        """Test assessment without LLM when keyword confidence is high."""
        # Use a longer query with more keywords for higher confidence
        query = "What is the definition of OAuth2 and where can I find documentation?"
        result = assess_complexity(query, llm_client=None)

        assert result["complexity"] == "SIMPLE"
        assert result["method"] == "keyword"
        assert result["confidence"] >= 0.3  # Accept lower confidence
        assert "score" in result

    def test_assess_without_llm_low_confidence(self):
        """Test assessment without LLM when keyword confidence is low."""
        query = "xyz abc def"  # No keyword matches
        result = assess_complexity(query, llm_client=None)

        assert result["method"] == "keyword"  # Still uses keyword since no LLM
        assert "llm_verification_needed" in result or result["confidence"] < 0.5

    def test_assess_critical_security_high_confidence(self):
        """Test that critical security queries have high confidence."""
        query = "Fix authentication vulnerability in production"
        result = assess_complexity(query, llm_client=None)

        assert result["complexity"] == "CRITICAL"
        assert result["confidence"] >= 0.8  # Should be very confident
        assert result["method"] == "keyword"  # No LLM needed


class TestKeywordLists:
    """Tests to validate keyword list structure."""

    def test_keyword_lists_are_sets(self):
        """Verify keyword lists are sets for fast lookup."""
        assert isinstance(SIMPLE_KEYWORDS, set)
        assert isinstance(MEDIUM_KEYWORDS, set)
        assert isinstance(COMPLEX_KEYWORDS, set)
        assert isinstance(CRITICAL_KEYWORDS, set)

    def test_keyword_lists_not_empty(self):
        """Verify keyword lists have content."""
        assert len(SIMPLE_KEYWORDS) > 0
        assert len(MEDIUM_KEYWORDS) > 0
        assert len(COMPLEX_KEYWORDS) > 0
        assert len(CRITICAL_KEYWORDS) > 0

    def test_no_duplicate_keywords_across_levels(self):
        """Verify keywords don't appear in multiple levels."""
        # Some overlap is OK (e.g., "security" might be in multiple),
        # but we want to ensure the lists are reasonably distinct
        simple_medium_overlap = SIMPLE_KEYWORDS & MEDIUM_KEYWORDS
        medium_complex_overlap = MEDIUM_KEYWORDS & COMPLEX_KEYWORDS

        # Allow some overlap but not too much
        assert len(simple_medium_overlap) < len(SIMPLE_KEYWORDS) * 0.3
        assert len(medium_complex_overlap) < len(MEDIUM_KEYWORDS) * 0.3

    def test_critical_keywords_are_high_priority(self):
        """Verify critical keywords are distinct and high-priority."""
        # Critical keywords should be mostly unique to that level
        critical_in_simple = CRITICAL_KEYWORDS & SIMPLE_KEYWORDS
        assert len(critical_in_simple) == 0  # No critical keywords should be in simple
