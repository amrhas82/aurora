"""Tests for fuzzy matching utilities."""

import pytest
from aurora_planning.utils.match import nearest_matches, levenshtein


class TestLevenshtein:
    """Tests for Levenshtein distance calculation."""

    def test_identical_strings(self):
        """Test distance between identical strings is 0."""
        assert levenshtein("hello", "hello") == 0

    def test_empty_strings(self):
        """Test distance with empty strings."""
        assert levenshtein("", "") == 0
        assert levenshtein("abc", "") == 3
        assert levenshtein("", "xyz") == 3

    def test_single_character_difference(self):
        """Test distance with single character difference."""
        assert levenshtein("cat", "bat") == 1
        assert levenshtein("cat", "car") == 1
        assert levenshtein("cat", "cats") == 1

    def test_multiple_differences(self):
        """Test distance with multiple differences."""
        assert levenshtein("kitten", "sitting") == 3
        assert levenshtein("sunday", "saturday") == 3


class TestNearestMatches:
    """Tests for finding nearest matches."""

    def test_exact_match_first(self):
        """Test that exact match appears first."""
        candidates = ["apple", "application", "apply", "apricot"]
        matches = nearest_matches("apple", candidates)

        assert matches[0] == "apple"

    def test_returns_max_results(self):
        """Test that max parameter limits results."""
        candidates = ["a", "b", "c", "d", "e", "f", "g"]
        matches = nearest_matches("x", candidates, max=3)

        assert len(matches) == 3

    def test_sorts_by_distance(self):
        """Test that results are sorted by distance."""
        candidates = ["test", "testing", "tester", "tested", "toast"]
        matches = nearest_matches("test", candidates)

        # "test" should be first (exact match)
        assert matches[0] == "test"
        # Closer matches should come before "toast"
        assert matches.index("toast") > matches.index("tested")

    def test_empty_candidates(self):
        """Test with empty candidates list."""
        matches = nearest_matches("test", [])
        assert matches == []
