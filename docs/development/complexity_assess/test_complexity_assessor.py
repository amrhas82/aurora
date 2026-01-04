#!/usr/bin/env python3
"""
Pytest tests for the keyword-based complexity assessor.

Tests validate:
1. Core functionality and edge cases
2. Accuracy against test corpus (>85% required)
3. Specific pattern detection
"""
import sys
from pathlib import Path

import pytest


# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from complexity_assessor import AssessmentResult, ComplexityAssessor, assess_prompt
from evaluate import evaluate_corpus
from test_corpus import TEST_CORPUS


class TestComplexityAssessor:
    """Tests for ComplexityAssessor class."""

    @pytest.fixture
    def assessor(self):
        return ComplexityAssessor()

    # ==================== Basic Functionality ====================

    def test_empty_prompt(self, assessor):
        """Empty prompts should be classified as simple."""
        result = assessor.assess("")
        assert result.level == "simple"
        assert result.score == 0
        assert "empty_prompt" in result.signals

    def test_whitespace_only(self, assessor):
        """Whitespace-only prompts should be classified as simple."""
        result = assessor.assess("   \n\t  ")
        assert result.level == "simple"

    def test_result_has_all_fields(self, assessor):
        """Result should have all expected fields."""
        result = assessor.assess("test prompt")
        assert hasattr(result, 'level')
        assert hasattr(result, 'score')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'signals')
        assert hasattr(result, 'breakdown')
        assert result.level in ('simple', 'medium', 'complex')
        assert 0 <= result.confidence <= 1

    def test_to_dict_serialization(self, assessor):
        """Result should serialize to dict properly."""
        result = assessor.assess("implement authentication")
        d = result.to_dict()
        assert isinstance(d, dict)
        assert 'level' in d
        assert 'score' in d
        assert 'confidence' in d
        assert 'signals' in d

    # ==================== Simple Prompts ====================

    @pytest.mark.parametrize("prompt", [
        "what is python",
        "show me the readme",
        "list all files",
        "where is the config",
        "run the tests",
        "check if tests pass",
    ])
    def test_simple_prompts(self, assessor, prompt):
        """Basic lookup/display prompts should be simple."""
        result = assessor.assess(prompt)
        assert result.level == "simple", f"'{prompt}' scored {result.score}, expected simple"

    # ==================== Medium Prompts ====================

    @pytest.mark.parametrize("prompt", [
        "explain how the caching works",
        "debug the login issue",
        "compare these two approaches",
        "add logging to the function",
        "fix the authentication bug",
    ])
    def test_medium_prompts(self, assessor, prompt):
        """Analysis and moderate edit prompts should be medium."""
        result = assessor.assess(prompt)
        assert result.level in ("medium", "complex"), f"'{prompt}' scored {result.score}"

    # ==================== Complex Prompts ====================

    @pytest.mark.parametrize("prompt", [
        "implement user authentication with oauth",
        "design a caching system for the api",
        "build a real-time notification system",
        "refactor the entire authentication module",
        "migrate the database from mysql to postgres",
    ])
    def test_complex_prompts(self, assessor, prompt):
        """Major implementation/architecture prompts should be complex."""
        result = assessor.assess(prompt)
        assert result.level == "complex", f"'{prompt}' scored {result.score}, expected complex"

    # ==================== Pattern Detection ====================

    def test_trivial_edit_pattern(self, assessor):
        """Trivial edits should not get medium verb bonus."""
        result = assessor.assess("fix the typo")
        assert "trivial_edit_pattern" in result.signals
        assert result.level == "simple"

    def test_complex_verb_detection(self, assessor):
        """Complex verbs should be detected."""
        result = assessor.assess("implement the feature")
        assert any("complex_verbs" in s for s in result.signals)

    def test_analysis_verb_detection(self, assessor):
        """Analysis verbs should be detected."""
        result = assessor.assess("explain the algorithm")
        assert any("analysis_verbs" in s for s in result.signals)

    def test_scope_expansion_detection(self, assessor):
        """Scope keywords should be detected."""
        result = assessor.assess("update all the files")
        assert any("scope_expansion" in s for s in result.signals)

    def test_constraint_detection(self, assessor):
        """Constraint phrases should be detected."""
        result = assessor.assess("add feature without breaking existing tests")
        assert any("constraint" in s for s in result.signals)

    def test_sequence_marker_detection(self, assessor):
        """Sequence markers should be detected."""
        result = assessor.assess("first run tests, then deploy")
        assert any("sequence_markers" in s for s in result.signals)

    def test_bounded_scope_detection(self, assessor):
        """Bounded scope should reduce complex verb impact."""
        result = assessor.assess("refactor this function")
        assert any("bounded_scope" in s for s in result.signals)

    def test_integration_pattern(self, assessor):
        """Integration patterns should boost complexity."""
        result = assessor.assess("integrate stripe with our api")
        assert any("integration_pattern" in s for s in result.signals)

    def test_complex_feature_pattern(self, assessor):
        """Complex feature keywords should boost complexity."""
        result = assessor.assess("add dark mode support")
        assert any("complex_feature_pattern" in s for s in result.signals)

    # ==================== Scoring Boundaries ====================

    def test_simple_threshold(self, assessor):
        """Score <= 11 should be simple."""
        assert assessor.SIMPLE_THRESHOLD == 11

    def test_medium_threshold(self, assessor):
        """Score 12-28 should be medium."""
        assert assessor.MEDIUM_THRESHOLD == 28

    # ==================== Corpus Accuracy ====================

    def test_corpus_accuracy_above_85_percent(self):
        """Overall accuracy should be >= 85%."""
        result = evaluate_corpus()
        assert result.accuracy >= 0.85, f"Accuracy {result.accuracy:.1%} < 85%"

    def test_corpus_accuracy_above_90_percent(self):
        """Stretch goal: accuracy >= 90%."""
        result = evaluate_corpus()
        # This is a soft assertion - warn but don't fail
        if result.accuracy < 0.90:
            pytest.skip(f"Accuracy {result.accuracy:.1%} < 90% (stretch goal)")

    def test_no_level_has_zero_accuracy(self):
        """Each level should have some correct predictions."""
        result = evaluate_corpus()
        for level, stats in result.by_level.items():
            assert stats['accuracy'] > 0, f"{level} has 0% accuracy"

    # ==================== Convenience Function ====================

    def test_assess_prompt_function(self):
        """assess_prompt convenience function should work."""
        result = assess_prompt("implement auth")
        assert isinstance(result, AssessmentResult)
        assert result.level in ('simple', 'medium', 'complex')


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def assessor(self):
        return ComplexityAssessor()

    def test_very_long_prompt(self, assessor):
        """Very long prompts should handle gracefully."""
        long_prompt = "implement " * 100 + "the feature"
        result = assessor.assess(long_prompt)
        assert result.level == "complex"

    def test_unicode_prompt(self, assessor):
        """Unicode characters should be handled."""
        result = assessor.assess("what is the résumé status")
        assert result.level in ('simple', 'medium', 'complex')

    def test_special_characters(self, assessor):
        """Special characters should be handled."""
        result = assessor.assess("fix bug #123 in src/main.py")
        assert result.level in ('simple', 'medium', 'complex')

    def test_code_block_in_prompt(self, assessor):
        """Code blocks should be detected."""
        result = assessor.assess("fix this code: ```python\nprint('hello')```")
        assert any("code_blocks" in s for s in result.signals)

    def test_numbered_list_detection(self, assessor):
        """Numbered lists should boost complexity."""
        result = assessor.assess("1. do this\n2. do that\n3. do other")
        assert any("numbered_list" in s for s in result.signals)

    def test_multi_question_detection(self, assessor):
        """Multiple questions should boost complexity."""
        result = assessor.assess("what is this? how does it work? why?")
        assert any("multi_question" in s for s in result.signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
