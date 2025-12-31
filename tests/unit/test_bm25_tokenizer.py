"""
Unit Tests for BM25 Tokenizer

Tests the code-aware tokenization functionality for BM25 scoring.
All tests follow TDD approach - written BEFORE implementation.

Test Coverage:
- UT-BM25-01: CamelCase splitting
- UT-BM25-02: snake_case splitting
- UT-BM25-03: Dot notation splitting
- UT-BM25-04: Acronym preservation
- UT-BM25-05: Mixed case handling
"""

import pytest


def test_tokenize_camelcase():
    """
    UT-BM25-01: CamelCase splitting

    Test that camelCase identifiers are split into component words.
    Example: "getUserData" → ["get", "user", "data", "getuserdata"]

    The tokenizer should:
    - Split on case boundaries (lowercase followed by uppercase)
    - Preserve the full original token
    - Return all tokens in lowercase for matching
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("getUserData")
    result_lower = [t.lower() for t in result]

    # Should contain individual components
    assert "get" in result_lower, "Should split 'get' from 'getUserData'"
    assert "user" in result_lower, "Should split 'user' from 'getUserData'"
    assert "data" in result_lower, "Should split 'data' from 'getUserData'"

    # Should also preserve full token
    assert "getuserdata" in result_lower, "Should preserve full token 'getUserData'"


def test_tokenize_snake_case():
    """
    UT-BM25-02: snake_case splitting

    Test that snake_case identifiers are split on underscores.
    Example: "user_manager" → ["user", "manager", "user_manager"]

    The tokenizer should:
    - Split on underscore boundaries
    - Preserve the full original token
    - Handle multiple underscores
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("user_manager")
    result_lower = [t.lower() for t in result]

    # Should contain individual components
    assert "user" in result_lower, "Should split 'user' from 'user_manager'"
    assert "manager" in result_lower, "Should split 'manager' from 'user_manager'"

    # Should also preserve full token
    assert "user_manager" in result_lower, "Should preserve full token 'user_manager'"


def test_tokenize_dot_notation():
    """
    UT-BM25-03: Dot notation splitting

    Test that dot notation (module paths, namespaces) are split.
    Example: "auth.oauth.client" → ["auth", "oauth", "client"]

    The tokenizer should:
    - Split on dot boundaries
    - Extract all individual components
    - Optionally preserve full path
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("auth.oauth.client")
    result_lower = [t.lower() for t in result]

    # Should contain individual components
    assert "auth" in result_lower, "Should split 'auth' from 'auth.oauth.client'"
    assert "oauth" in result_lower, "Should split 'oauth' from 'auth.oauth.client'"
    assert "client" in result_lower, "Should split 'client' from 'auth.oauth.client'"


def test_tokenize_acronyms():
    """
    UT-BM25-04: Acronym preservation

    Test that acronyms (consecutive uppercase letters) are handled correctly.
    Example: "HTTPRequest" → ["http", "request", "httprequest"]

    The tokenizer should:
    - Detect acronyms (consecutive uppercase letters)
    - Split acronym from following word
    - Preserve both acronym and full token
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("HTTPRequest")
    result_lower = [t.lower() for t in result]

    # Should contain acronym
    assert "http" in result_lower, "Should extract 'HTTP' acronym"

    # Should contain following word
    assert "request" in result_lower, "Should extract 'Request' after acronym"

    # Should preserve full token
    assert "httprequest" in result_lower, "Should preserve full token 'HTTPRequest'"


def test_tokenize_mixed_case():
    """
    UT-BM25-05: Mixed case handling

    Test that mixed notation (camelCase + snake_case + dots) works correctly.
    Example: "getUserData.auth_token" → ["get", "user", "data", "auth", "token"]

    The tokenizer should:
    - Apply all splitting rules (camelCase, snake_case, dots)
    - Handle combinations correctly
    - Return all component tokens
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("getUserData.auth_token")
    result_lower = [t.lower() for t in result]

    # Should split camelCase component
    assert "get" in result_lower, "Should split 'get' from camelCase part"
    assert "user" in result_lower, "Should split 'user' from camelCase part"
    assert "data" in result_lower, "Should split 'data' from camelCase part"

    # Should split snake_case component
    assert "auth" in result_lower, "Should split 'auth' from snake_case part"
    assert "token" in result_lower, "Should split 'token' from snake_case part"


def test_tokenize_empty_string():
    """
    UT-BM25-06: Empty string handling

    Test that empty strings are handled gracefully.
    Example: "" → []

    The tokenizer should:
    - Return empty list for empty input
    - Not raise exceptions
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("")

    assert result == [], "Empty string should return empty list"
    assert isinstance(result, list), "Should return list type"


def test_tokenize_special_characters():
    """
    UT-BM25-07: Special character handling

    Test that special characters are handled appropriately.
    Example: "user@email.com" → ["user", "email", "com"]

    The tokenizer should:
    - Split on special characters (@, #, $, etc.)
    - Extract alphanumeric tokens
    - Ignore or remove special characters
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("user@email.com")
    result_lower = [t.lower() for t in result]

    # Should split on special characters
    assert "user" in result_lower, "Should extract 'user' before @"
    assert "email" in result_lower, "Should extract 'email'"
    assert "com" in result_lower, "Should extract 'com'"

    # Should not contain special characters as tokens
    assert "@" not in result_lower, "Should not include @ as token"
    assert "." not in result_lower, "Should not include . as token"


def test_tokenize_whitespace_handling():
    """
    UT-BM25-08: Whitespace handling

    Test that multiple words separated by whitespace are tokenized.
    Example: "authenticate user session" → ["authenticate", "user", "session"]

    The tokenizer should:
    - Split on whitespace
    - Return individual words
    - Handle multiple spaces
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result = tokenize("authenticate user session")
    result_lower = [t.lower() for t in result]

    assert "authenticate" in result_lower, "Should split 'authenticate'"
    assert "user" in result_lower, "Should split 'user'"
    assert "session" in result_lower, "Should split 'session'"
    assert len(result) >= 3, "Should return at least 3 tokens"


def test_tokenize_preserves_case_variations():
    """
    UT-BM25-09: Case preservation for matching

    Test that tokenizer handles case variations appropriately for BM25.

    The tokenizer should:
    - Split based on case boundaries (camelCase)
    - All-lowercase has no boundaries, so kept as single token
    - Case-insensitive matching via lowercase normalization
    """
    from aurora_context_code.semantic.bm25_scorer import tokenize

    result1 = tokenize("SOAROrchestrator")
    result2 = tokenize("soarorchestrator")  # All lowercase - no split markers
    result3 = tokenize("SoarOrchestrator")

    # All variations should produce similar token sets
    result1_lower = [t.lower() for t in result1]
    result2_lower = [t.lower() for t in result2]
    result3_lower = [t.lower() for t in result3]

    # SOAROrchestrator should split: SOAR + Orchestrator
    assert "soar" in result1_lower
    assert "orchestrator" in result1_lower

    # soarorchestrator has no case boundaries, stays as single token
    assert "soarorchestrator" in result2_lower
    # But it won't split into components (correct behavior)

    # SoarOrchestrator should split: Soar + Orchestrator
    assert "soar" in result3_lower
    assert "orchestrator" in result3_lower

    # All should contain the full token in lowercase for matching
    assert "soarorchestrator" in result1_lower
    assert "soarorchestrator" in result2_lower
    assert "soarorchestrator" in result3_lower


def test_bm25_idf_calculation():
    """
    UT-BM25-10: IDF calculation test

    Test that IDF (Inverse Document Frequency) is calculated correctly.
    Formula: IDF = log((N - n(t) + 0.5) / (n(t) + 0.5) + 1)

    Where:
    - N = total number of documents
    - n(t) = number of documents containing term t
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer
    import math

    scorer = BM25Scorer()

    # Build index with 3 documents
    # "auth" appears in 2 documents
    # "config" appears in 1 document
    docs = [
        ("d1", "auth user"),
        ("d2", "auth token"),
        ("d3", "config settings"),
    ]
    scorer.build_index(docs)

    # Calculate expected IDF for "auth" (n(t) = 2, N = 3)
    # IDF = log((3 - 2 + 0.5) / (2 + 0.5) + 1) = log(1.5 / 2.5 + 1) = log(1.6)
    expected_idf_auth = math.log((3 - 2 + 0.5) / (2 + 0.5) + 1)
    actual_idf_auth = scorer.idf.get("auth", 0.0)

    assert abs(actual_idf_auth - expected_idf_auth) < 0.01, \
        f"IDF for 'auth' should be {expected_idf_auth:.3f}, got {actual_idf_auth:.3f}"

    # Calculate expected IDF for "config" (n(t) = 1, N = 3)
    # IDF = log((3 - 1 + 0.5) / (1 + 0.5) + 1) = log(2.5 / 1.5 + 1)
    expected_idf_config = math.log((3 - 1 + 0.5) / (1 + 0.5) + 1)
    actual_idf_config = scorer.idf.get("config", 0.0)

    assert abs(actual_idf_config - expected_idf_config) < 0.01, \
        f"IDF for 'config' should be {expected_idf_config:.3f}, got {actual_idf_config:.3f}"


def test_bm25_term_frequency():
    """
    UT-BM25-11: Term frequency scoring test

    Test that term frequency affects BM25 score correctly.
    Higher frequency should increase score, but with saturation (k1 parameter).
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    scorer = BM25Scorer(k1=1.5, b=0.75)

    # Build index
    docs = [
        ("d1", "auth"),
        ("d2", "auth auth"),
        ("d3", "auth auth auth"),
    ]
    scorer.build_index(docs)

    # Score documents with query "auth"
    score1 = scorer.score("auth", "auth")
    score2 = scorer.score("auth", "auth auth")
    score3 = scorer.score("auth", "auth auth auth")

    # Higher frequency should give higher scores
    assert score2 > score1, "Document with 2 occurrences should score higher than 1"
    assert score3 > score2, "Document with 3 occurrences should score higher than 2"

    # But scores should saturate (not linear)
    # score2/score1 ratio should be > score3/score2 ratio (diminishing returns)
    ratio_1_to_2 = score2 / score1 if score1 > 0 else 0
    ratio_2_to_3 = score3 / score2 if score2 > 0 else 0

    assert ratio_1_to_2 > ratio_2_to_3, "Score increases should saturate (k1 parameter)"


def test_bm25_document_length_normalization():
    """
    UT-BM25-12: Document length normalization test

    Test that BM25 length normalization (b parameter) works correctly.
    Shorter documents with term should score higher than longer documents.
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    scorer = BM25Scorer(k1=1.5, b=0.75)

    # Build index with documents of different lengths
    docs = [
        ("short", "auth"),
        ("long", "auth " + " ".join(["word"] * 50)),
    ]
    scorer.build_index(docs)

    # Score both documents with query "auth"
    score_short = scorer.score("auth", "auth")
    score_long = scorer.score("auth", "auth " + " ".join(["word"] * 50))

    # Shorter document should score higher
    assert score_short > score_long, \
        f"Shorter doc should score higher: short={score_short:.3f}, long={score_long:.3f}"


def test_bm25_multiple_term_scoring():
    """
    UT-BM25-13: Multiple term scoring test

    Test that BM25 correctly scores documents with multiple query terms.
    Documents matching more terms should score higher.
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    scorer = BM25Scorer()

    # Build index
    docs = [
        ("d1", "authenticate user"),
        ("d2", "authenticate"),
        ("d3", "user"),
        ("d4", "config"),
    ]
    scorer.build_index(docs)

    # Score documents with multi-term query
    score_both = scorer.score("authenticate user", "authenticate user session")
    score_one = scorer.score("authenticate user", "authenticate session")
    score_none = scorer.score("authenticate user", "config settings")

    # Document with both terms should score highest
    assert score_both > score_one, "Document matching both terms should score higher"
    assert score_one > score_none, "Document matching one term should score higher than none"
    assert score_none == 0.0, "Document with no matching terms should score 0"


def test_bm25_score_exact_match():
    """
    UT-BM25-14: Exact match scoring test

    Test that exact matches produce positive scores.
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    scorer = BM25Scorer()

    docs = [("d1", "authenticate user session")]
    scorer.build_index(docs)

    score = scorer.score("authenticate", "authenticate user session")

    assert score > 0, f"Exact match should produce positive score, got {score}"


def test_bm25_score_no_match():
    """
    UT-BM25-15: No match scoring test

    Test that documents with no matching terms score 0.
    """
    from aurora_context_code.semantic.bm25_scorer import BM25Scorer

    scorer = BM25Scorer()

    docs = [("d1", "authenticate user")]
    scorer.build_index(docs)

    score = scorer.score("oauth", "authenticate user session")

    assert score == 0.0, f"No match should produce score 0, got {score}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
