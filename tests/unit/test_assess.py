"""Unit tests for complexity assessment (assess.py).

Tests the enhanced complexity assessment with:
- Domain-specific keywords (SOAR, ACT-R, agentic, Aurora)
- Multi-question detection
- Confidence scoring
"""

import pytest

from aurora_soar.phases.assess import assess_complexity, _count_questions


class TestCountQuestions:
    """Tests for the _count_questions helper function."""

    def test_single_question(self):
        """Test counting a single question mark."""
        assert _count_questions("What is Python?") == 1

    def test_multiple_questions(self):
        """Test counting multiple question marks."""
        assert _count_questions("What is X? Who are Y? What features Z?") == 3

    def test_no_questions(self):
        """Test query with no question marks."""
        assert _count_questions("Explain Python syntax") == 0

    def test_empty_query(self):
        """Test empty query."""
        assert _count_questions("") == 0


class TestDomainKeywords:
    """Tests for domain-specific keyword detection."""

    def test_soar_keyword(self):
        """Test that SOAR keyword triggers MEDIUM complexity."""
        result = assess_complexity("explain SOAR reasoning phases")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_actr_keyword(self):
        """Test that ACT-R keyword triggers MEDIUM complexity."""
        result = assess_complexity("how does ACT-R activation work?")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_agentic_keyword(self):
        """Test that agentic keyword triggers MEDIUM complexity."""
        result = assess_complexity("research agentic AI systems")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_aurora_keyword(self):
        """Test that Aurora keyword triggers MEDIUM complexity."""
        result = assess_complexity("how does Aurora activation tracking work?")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_orchestration_keyword(self):
        """Test that orchestration keyword triggers MEDIUM complexity."""
        result = assess_complexity("explain orchestration pipeline in Aurora")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_retrieval_keyword(self):
        """Test that retrieval keyword triggers MEDIUM complexity."""
        result = assess_complexity("how does hybrid retrieval work?")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3


class TestMultiQuestionQueries:
    """Tests for multi-question query detection and boosting."""

    def test_multi_question_query_triggers_boost(self):
        """Test that query with 2+ questions gets complexity boost."""
        result = assess_complexity("What is X? Who are Y? What features Z?")
        # Multi-question queries should be at least MEDIUM
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        # Should have reasonable confidence due to multi-question boost
        assert result["confidence"] >= 0.4

    def test_two_question_query(self):
        """Test query with exactly 2 questions."""
        result = assess_complexity("Who are the top AI researchers? What are their contributions?")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.4

    def test_single_question_no_boost(self):
        """Test that single question doesn't get multi-question boost."""
        result1 = assess_complexity("What is Python?")
        result2 = assess_complexity("What is Python")
        # Single question should be SIMPLE (no domain keywords)
        assert result1["complexity"] == "SIMPLE"
        # Same query without question mark should have similar result
        assert result2["complexity"] == "SIMPLE"


class TestScopeIndicators:
    """Tests for scope indicator keywords (research, design, architecture)."""

    def test_research_keyword(self):
        """Test that 'research' triggers MEDIUM complexity."""
        result = assess_complexity("research best practices for memory management")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_design_keyword(self):
        """Test that 'design' triggers MEDIUM complexity."""
        result = assess_complexity("design a retrieval system")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3

    def test_architecture_keyword(self):
        """Test that 'architecture' triggers MEDIUM complexity."""
        result = assess_complexity("explain the architecture of Aurora")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.3


class TestSimpleQueries:
    """Tests that simple queries remain SIMPLE."""

    def test_simple_what_query(self):
        """Test simple 'what' query without domain terms."""
        result = assess_complexity("what is Python?")
        assert result["complexity"] == "SIMPLE"

    def test_simple_who_query(self):
        """Test simple 'who' query without domain terms."""
        result = assess_complexity("who invented Python?")
        assert result["complexity"] == "SIMPLE"

    def test_simple_define_query(self):
        """Test simple definition query."""
        result = assess_complexity("define variable")
        assert result["complexity"] == "SIMPLE"


class TestComplexDomainQueries:
    """Tests for complex queries combining multiple indicators."""

    def test_domain_with_multi_question(self):
        """Test domain query with multiple questions."""
        result = assess_complexity(
            "research agentic AI? who are top players? what features do they offer?"
        )
        # Should be MEDIUM or COMPLEX due to domain keywords + multi-question
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        # Should have high confidence due to multiple indicators
        assert result["confidence"] >= 0.5

    def test_aurora_soar_query(self):
        """Test query about Aurora and SOAR together."""
        result = assess_complexity("how does Aurora use SOAR for orchestration?")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.4

    def test_activation_retrieval_query(self):
        """Test query about activation and retrieval."""
        result = assess_complexity("explain how activation scores affect retrieval")
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]
        assert result["confidence"] >= 0.4


class TestConfidenceScoring:
    """Tests for confidence score calculation."""

    def test_high_confidence_for_clear_match(self):
        """Test that clear keyword matches result in high confidence."""
        result = assess_complexity("create unit test for activation scoring")
        # Should have decent confidence with clear MEDIUM keywords
        assert result["confidence"] >= 0.5

    def test_low_confidence_for_ambiguous(self):
        """Test that ambiguous queries have lower confidence."""
        result = assess_complexity("stuff things")
        # Should have low confidence with no clear keywords
        assert result["confidence"] < 0.5

    def test_multi_question_increases_confidence(self):
        """Test that multi-question queries have higher confidence."""
        result = assess_complexity("what? when? why?")
        # Multi-question should boost confidence
        assert result["confidence"] >= 0.3


class TestMethodField:
    """Tests for the 'method' field in results."""

    def test_keyword_method_for_simple(self):
        """Test that simple queries use keyword method."""
        result = assess_complexity("what is Python?")
        assert result["method"] == "keyword"

    def test_keyword_method_for_high_confidence(self):
        """Test that high-confidence queries use keyword method."""
        result = assess_complexity("research SOAR activation systems")
        # Should use keyword method if confidence is high
        assert result["method"] == "keyword"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_query(self):
        """Test empty query handling."""
        result = assess_complexity("")
        assert result["complexity"] == "SIMPLE"
        assert result["confidence"] < 0.5

    def test_very_long_query(self):
        """Test very long query."""
        long_query = "explain " + " ".join(["soar"] * 50)
        result = assess_complexity(long_query)
        # Should still classify correctly
        assert result["complexity"] in ["MEDIUM", "COMPLEX"]

    def test_special_characters(self):
        """Test query with special characters."""
        result = assess_complexity("what is @aurora's #activation_score?")
        # Should handle special characters gracefully
        assert result["complexity"] in ["SIMPLE", "MEDIUM"]


class TestCriticalKeywords:
    """Tests for CRITICAL keyword detection."""

    def test_security_keyword(self):
        """Test that security keyword triggers CRITICAL."""
        result = assess_complexity("fix security vulnerability in authentication")
        assert result["complexity"] == "CRITICAL"
        assert result["confidence"] >= 0.9

    def test_production_keyword(self):
        """Test that production keyword triggers CRITICAL."""
        result = assess_complexity("deploy to production environment")
        assert result["complexity"] == "CRITICAL"
        assert result["confidence"] >= 0.9
