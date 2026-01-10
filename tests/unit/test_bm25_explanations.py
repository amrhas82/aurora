"""Unit tests for BM25 score explanations.

Tests the logic for generating human-readable explanations of BM25 scores
based on query term matching patterns.
"""

import pytest


def test_explain_bm25_exact_match():
    """Single exact match: query term found verbatim in chunk content."""
    from aurora_cli.commands.memory import _explain_bm25_score

    query = "authenticate"
    chunk_content = "authenticate_user() function implementation"
    bm25_score = 0.95

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    assert "exact keyword match" in explanation.lower()
    assert "authenticate" in explanation.lower()


def test_explain_bm25_exact_match_multiple_terms():
    """Multiple exact matches: multiple query terms found verbatim."""
    from aurora_cli.commands.memory import _explain_bm25_score

    query = "get user"
    chunk_content = "getUserData() retrieves user information from database"
    bm25_score = 0.88

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    assert "exact keyword match" in explanation.lower()
    # Should mention both terms (but order may vary)
    assert "get" in explanation.lower() or "user" in explanation.lower()


def test_explain_bm25_strong_overlap():
    """Strong term overlap: ≥50% query terms present in content."""
    from aurora_cli.commands.memory import _explain_bm25_score

    # Use query where 2 of 3 terms match (user, authentication match; flow does not)
    query = "user authentication flow"
    chunk_content = "User authentication system implementation"
    bm25_score = 0.75

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    assert "strong term overlap" in explanation.lower()
    # Should show ratio like "2/3 terms"
    assert "2/3" in explanation


def test_explain_bm25_partial_match():
    """Partial match: <50% query terms present in content."""
    from aurora_cli.commands.memory import _explain_bm25_score

    query = "oauth token refresh"
    chunk_content = "OAuth implementation and configuration details"
    bm25_score = 0.45

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    assert "partial match" in explanation.lower()
    # Should show ratio like "1/3 terms"
    assert "/" in explanation


def test_explain_bm25_no_match():
    """No match: no query terms found in content."""
    from aurora_cli.commands.memory import _explain_bm25_score

    query = "database"
    chunk_content = "Frontend UI component rendering logic"
    bm25_score = 0.0

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    # Should return empty string or "no keyword match"
    assert len(explanation) == 0 or "no keyword match" in explanation.lower()


def test_explain_bm25_camelcase_tokenization():
    """CamelCase tokenization: query split correctly, all parts found."""
    from aurora_cli.commands.memory import _explain_bm25_score

    query = "getUserData"
    chunk_content = "getUserData() implementation for user data retrieval"
    bm25_score = 0.92

    explanation = _explain_bm25_score(query, chunk_content, bm25_score)

    # Should recognize camelCase splitting and find matches
    # Could be exact match on full term OR strong overlap on split terms
    assert (
        "exact keyword match" in explanation.lower() or "strong term overlap" in explanation.lower()
    )
