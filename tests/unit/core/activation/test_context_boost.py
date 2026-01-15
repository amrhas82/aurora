"""Unit tests for Context Boost calculation.

Tests the ACT-R context boost component including:
- Keyword extraction from text
- Keyword overlap calculation
- Context boost formula: boost = (overlap / query_keywords) * boost_factor
- Weighted field scoring (name, docstring, signature, body)
- Edge cases (empty queries, no overlap, etc.)
"""

import pytest

from aurora_core.activation.context_boost import (
    ContextBoost,
    ContextBoostConfig,
    KeywordExtractor,
    calculate_context_boost,
)


class TestContextBoostConfig:
    """Test ContextBoostConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ContextBoostConfig()
        assert config.boost_factor == 0.5
        assert config.min_keyword_length == 3
        assert config.case_sensitive is False
        assert config.stemming_enabled is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ContextBoostConfig(
            boost_factor=1.0, min_keyword_length=2, case_sensitive=True, stemming_enabled=True
        )
        assert config.boost_factor == 1.0
        assert config.min_keyword_length == 2
        assert config.case_sensitive is True
        assert config.stemming_enabled is True

    def test_boost_factor_validation(self):
        """Test boost factor must be in valid range."""
        # Valid values
        ContextBoostConfig(boost_factor=0.0)
        ContextBoostConfig(boost_factor=1.0)
        ContextBoostConfig(boost_factor=2.0)

        # Invalid values should be caught by Pydantic
        with pytest.raises(Exception):
            ContextBoostConfig(boost_factor=-0.1)
        with pytest.raises(Exception):
            ContextBoostConfig(boost_factor=2.5)

    def test_min_keyword_length_validation(self):
        """Test min_keyword_length must be positive."""
        # Valid values
        ContextBoostConfig(min_keyword_length=1)
        ContextBoostConfig(min_keyword_length=5)

        # Invalid values should be caught by Pydantic
        with pytest.raises(Exception):
            ContextBoostConfig(min_keyword_length=0)
        with pytest.raises(Exception):
            ContextBoostConfig(min_keyword_length=-1)


class TestKeywordExtractor:
    """Test KeywordExtractor functionality."""

    def test_extract_basic_keywords(self):
        """Test extracting simple keywords from text."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("optimize database queries")
        assert keywords == {"optimize", "database", "queries"}

    def test_extract_filters_short_words(self):
        """Test that short words are filtered out."""
        config = ContextBoostConfig(min_keyword_length=3)
        extractor = KeywordExtractor(config)
        keywords = extractor.extract("a database is good")
        # 'a' and 'is' should be filtered (too short or stop words)
        assert "database" in keywords
        assert "good" in keywords
        assert "a" not in keywords

    def test_extract_filters_stop_words(self):
        """Test that common stop words are filtered out."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("the database and the queries")
        # 'the' and 'and' are stop words
        assert keywords == {"database", "queries"}

    def test_programming_terms_not_filtered(self):
        """Test that programming terms are kept even if short."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("api db id ui")
        # These should all be kept as programming terms
        assert "api" in keywords
        assert "db" in keywords
        assert "id" in keywords
        assert "ui" in keywords

    def test_case_insensitive_by_default(self):
        """Test that extraction is case-insensitive by default."""
        extractor = KeywordExtractor()
        keywords1 = extractor.extract("Database Query")
        keywords2 = extractor.extract("database query")
        assert keywords1 == keywords2

    def test_case_sensitive_mode(self):
        """Test case-sensitive keyword extraction."""
        config = ContextBoostConfig(case_sensitive=True)
        extractor = KeywordExtractor(config)
        keywords = extractor.extract("Database database")
        # Should keep both versions
        assert "Database" in keywords
        assert "database" in keywords

    def test_extract_from_empty_string(self):
        """Test extracting from empty string."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("")
        assert keywords == set()

    def test_extract_with_special_characters(self):
        """Test extraction with special characters."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("user_id, task-name, file.py")
        # Should extract words around special characters
        assert "user" in keywords or "user_id" in keywords
        assert "task" in keywords or "name" in keywords
        assert "file" in keywords

    def test_extract_from_chunks(self):
        """Test extracting keywords from multiple chunks."""
        extractor = KeywordExtractor()
        chunks = ["database query", "optimize performance", "database connection"]
        keywords = extractor.extract_from_chunks(chunks)
        assert "database" in keywords
        assert "query" in keywords
        assert "optimize" in keywords
        assert "performance" in keywords
        assert "connection" in keywords

    def test_extract_from_empty_chunks(self):
        """Test extracting from empty chunk list."""
        extractor = KeywordExtractor()
        keywords = extractor.extract_from_chunks([])
        assert keywords == set()

    def test_min_keyword_length_respected(self):
        """Test that min_keyword_length setting is respected."""
        config = ContextBoostConfig(min_keyword_length=6)
        extractor = KeywordExtractor(config)
        keywords = extractor.extract("query database optimization")
        # Only 'database' (8) and 'optimization' (12) are >= 6 chars
        assert "database" in keywords
        assert "optimization" in keywords
        assert "query" not in keywords  # Only 5 chars, too short


class TestContextBoost:
    """Test ContextBoost calculation."""

    def test_calculate_perfect_match(self):
        """Test boost when all query keywords match."""
        boost = ContextBoost()
        query_keywords = {"database", "query", "optimize"}
        chunk_keywords = {"database", "query", "optimize", "performance"}

        score = boost.calculate(query_keywords, chunk_keywords)
        # All 3 query keywords match, so overlap_fraction = 1.0
        # boost = 1.0 * 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=0.001)

    def test_calculate_partial_match(self):
        """Test boost with partial keyword overlap."""
        boost = ContextBoost()
        query_keywords = {"database", "query", "optimize"}
        chunk_keywords = {"database", "performance"}

        score = boost.calculate(query_keywords, chunk_keywords)
        # 1 out of 3 query keywords match, so overlap_fraction = 1/3
        # boost = (1/3) * 0.5 ≈ 0.167
        assert score == pytest.approx(0.167, abs=0.001)

    def test_calculate_no_match(self):
        """Test boost when no keywords match."""
        boost = ContextBoost()
        query_keywords = {"database", "query"}
        chunk_keywords = {"network", "socket"}

        score = boost.calculate(query_keywords, chunk_keywords)
        # No matches, so boost = 0.0
        assert score == 0.0

    def test_calculate_empty_query(self):
        """Test that empty query returns zero boost."""
        boost = ContextBoost()
        query_keywords = set()
        chunk_keywords = {"database", "query"}

        score = boost.calculate(query_keywords, chunk_keywords)
        assert score == 0.0

    def test_calculate_empty_chunk(self):
        """Test boost when chunk has no keywords."""
        boost = ContextBoost()
        query_keywords = {"database", "query"}
        chunk_keywords = set()

        score = boost.calculate(query_keywords, chunk_keywords)
        assert score == 0.0

    def test_calculate_with_custom_boost_factor(self):
        """Test boost calculation with custom boost factor."""
        config = ContextBoostConfig(boost_factor=1.0)
        boost = ContextBoost(config)
        query_keywords = {"database", "query"}
        chunk_keywords = {"database", "query", "optimize"}

        score = boost.calculate(query_keywords, chunk_keywords)
        # All 2 query keywords match, so overlap_fraction = 1.0
        # boost = 1.0 * 1.0 = 1.0
        assert score == pytest.approx(1.0, abs=0.001)

    def test_calculate_from_text(self):
        """Test convenience method that extracts keywords from text."""
        boost = ContextBoost()
        query_text = "optimize database queries"
        chunk_text = "database optimization and query performance"

        score = boost.calculate_from_text(query_text, chunk_text)
        # Should find some overlap and return positive boost
        assert score > 0.0
        assert score <= 0.5  # Max boost factor

    def test_calculate_from_text_no_overlap(self):
        """Test calculate_from_text with no keyword overlap."""
        boost = ContextBoost()
        query_text = "database queries"
        chunk_text = "network sockets"

        score = boost.calculate_from_text(query_text, chunk_text)
        assert score == 0.0

    def test_get_matching_keywords(self):
        """Test getting the list of matching keywords."""
        boost = ContextBoost()
        query_keywords = {"database", "query", "optimize"}
        chunk_keywords = {"database", "query", "performance"}

        matching = boost.get_matching_keywords(query_keywords, chunk_keywords)
        assert matching == {"database", "query"}

    def test_explain_boost(self):
        """Test boost explanation feature."""
        boost = ContextBoost()
        query_text = "optimize database"
        chunk_text = "database optimization techniques"

        explanation = boost.explain_boost(query_text, chunk_text)

        assert "boost_value" in explanation
        assert "query_keywords" in explanation
        assert "chunk_keywords" in explanation
        assert "matching_keywords" in explanation
        assert "overlap_fraction" in explanation

        # Check values are reasonable
        assert explanation["boost_value"] > 0.0
        assert len(explanation["query_keywords"]) > 0
        assert len(explanation["chunk_keywords"]) > 0
        assert len(explanation["matching_keywords"]) > 0
        assert 0.0 <= explanation["overlap_fraction"] <= 1.0

    def test_explain_boost_no_match(self):
        """Test explanation when there's no match."""
        boost = ContextBoost()
        query_text = "database"
        chunk_text = "network"

        explanation = boost.explain_boost(query_text, chunk_text)

        assert explanation["boost_value"] == 0.0
        assert explanation["overlap_fraction"] == 0.0
        assert len(explanation["matching_keywords"]) == 0


class TestCalculateFromChunkFields:
    """Test weighted field scoring for code chunks."""

    def test_calculate_with_name_match(self):
        """Test that name matches are weighted heavily."""
        boost = ContextBoost()
        query_text = "database query"
        chunk_name = "database query handler"  # Space-separated so keywords split

        score = boost.calculate_from_chunk_fields(query_text=query_text, chunk_name=chunk_name)

        # Name has high weight (2.0)
        # Keywords from "database query" = {database, query}
        # Keywords from "database query handler" = {database, query, handler}
        # All 2 query keywords match, so weighted_fraction = 1.0
        # boost = 1.0 * 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=0.001)

    def test_calculate_with_docstring_match(self):
        """Test that docstring matches are weighted moderately."""
        boost = ContextBoost()
        query_text = "optimize database"
        chunk_name = "handler"
        docstring = "Optimize database queries for performance"

        score = boost.calculate_from_chunk_fields(
            query_text=query_text, chunk_name=chunk_name, chunk_docstring=docstring
        )

        # Should find matches in docstring
        assert score > 0.0

    def test_calculate_with_all_fields(self):
        """Test combining all chunk fields."""
        boost = ContextBoost()
        query_text = "database query optimize"
        chunk_name = "database_handler"
        docstring = "Handle database queries"
        signature = "def handle_query(db_connection)"
        body = "optimize the query execution"

        score = boost.calculate_from_chunk_fields(
            query_text=query_text,
            chunk_name=chunk_name,
            chunk_docstring=docstring,
            chunk_signature=signature,
            chunk_body=body,
        )

        # Should have high score due to matches across all fields
        assert score > 0.0

    def test_calculate_name_weighted_higher_than_body(self):
        """Test that name matches have higher weight than body matches."""
        boost = ContextBoost()
        query_text = "special"

        # Score with name match only (weight 2.0)
        score_name = boost.calculate_from_chunk_fields(
            query_text=query_text,
            chunk_name="special handler",  # Space-separated
            chunk_body="generic function",
        )

        # Score with body match only (weight 1.0)
        score_body = boost.calculate_from_chunk_fields(
            query_text=query_text,
            chunk_name="generic handler",  # Space-separated
            chunk_body="special function implementation",
        )

        # Name has 2x weight, so should score higher
        # Name: 1 match out of 1 query keyword, weight 2.0 → weighted_fraction = 2/2 = 1.0 → but also has body with no match...
        # Actually: name(2.0) + body(1.0) = total_weight 3.0, overlap_name=2.0, overlap_body=0 → 2.0/3.0 = 0.667 * 0.5 = 0.333
        # Body: name(2.0) + body(1.0) = total_weight 3.0, overlap_name=0, overlap_body=1.0 → 1.0/3.0 = 0.333 * 0.5 = 0.167
        assert score_name > score_body  # Name weighted higher
        assert score_name == pytest.approx(0.333, abs=0.001)
        assert score_body == pytest.approx(0.167, abs=0.001)

    def test_calculate_with_empty_fields(self):
        """Test handling of None/empty optional fields."""
        boost = ContextBoost()
        query_text = "database"
        chunk_name = "database handler"  # Space-separated

        # Should not crash with None fields
        score = boost.calculate_from_chunk_fields(
            query_text=query_text,
            chunk_name=chunk_name,
            chunk_docstring=None,
            chunk_signature=None,
            chunk_body=None,
        )

        # Keywords: query={database}, name={database, handler}
        # 100% overlap, boost = 1.0 * 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=0.001)

    def test_calculate_with_empty_query(self):
        """Test that empty query returns zero."""
        boost = ContextBoost()
        query_text = ""
        chunk_name = "handler"

        score = boost.calculate_from_chunk_fields(query_text=query_text, chunk_name=chunk_name)

        assert score == 0.0

    def test_realistic_code_chunk_example(self):
        """Test with realistic code chunk data."""
        boost = ContextBoost()
        query_text = "parse SQL query"

        chunk_name = "parse_sql_statement"
        docstring = "Parse SQL query into AST representation"
        signature = "def parse_sql_statement(query: str) -> AST"
        body = """
        parser = SQLParser()
        tokens = tokenize(query)
        ast = parser.parse(tokens)
        return ast
        """

        score = boost.calculate_from_chunk_fields(
            query_text=query_text,
            chunk_name=chunk_name,
            chunk_docstring=docstring,
            chunk_signature=signature,
            chunk_body=body,
        )

        # Should have good overlap: 'parse', 'sql', 'query'
        # Query keywords: {parse, sql, query}
        # All match across different fields with different weights
        assert score > 0.2  # Expect reasonable boost from weighted scoring
        assert score <= 0.5  # Max boost factor


class TestCalculateContextBoostFunction:
    """Test standalone calculate_context_boost function."""

    def test_calculate_with_defaults(self):
        """Test standalone function with default parameters."""
        score = calculate_context_boost(
            query_text="database query", chunk_text="database connection and query execution"
        )

        assert score > 0.0
        assert score <= 0.5  # Default boost_factor

    def test_calculate_with_custom_boost_factor(self):
        """Test standalone function with custom boost factor."""
        score = calculate_context_boost(
            query_text="database query", chunk_text="database query", boost_factor=1.0
        )

        # Perfect match with boost_factor=1.0 should give 1.0
        assert score == pytest.approx(1.0, abs=0.001)

    def test_calculate_no_match(self):
        """Test standalone function with no match."""
        score = calculate_context_boost(query_text="database", chunk_text="network")

        assert score == 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_text(self):
        """Test that very long text is handled efficiently."""
        boost = ContextBoost()
        query_text = "database"
        # Create very long chunk text
        chunk_text = " ".join(["word" + str(i) for i in range(10000)])

        # Should not crash or hang
        score = boost.calculate_from_text(query_text, chunk_text)
        assert score >= 0.0

    def test_unicode_text(self):
        """Test handling of unicode characters."""
        boost = ContextBoost()
        query_text = "データベース"  # Japanese for "database"
        chunk_text = "データベース クエリ"

        # Should handle unicode without crashing
        score = boost.calculate_from_text(query_text, chunk_text)
        assert score >= 0.0

    def test_numbers_in_text(self):
        """Test handling of numbers in text."""
        extractor = KeywordExtractor()
        keywords = extractor.extract("python3 version123 test")

        # Should extract words with numbers
        assert any("python" in k or "version" in k for k in keywords)

    def test_mixed_case_matching(self):
        """Test that mixed case text matches correctly."""
        boost = ContextBoost()
        query_text = "Database Query"
        chunk_text = "DATABASE query handler"

        # Case-insensitive by default, should match
        score = boost.calculate_from_text(query_text, chunk_text)
        assert score > 0.0

    def test_repeated_keywords(self):
        """Test that repeated keywords don't inflate boost."""
        boost = ContextBoost()
        query_keywords = {"database", "query"}
        chunk_keywords = {"database", "query"}

        # Boost should be based on unique keyword overlap
        score = boost.calculate(query_keywords, chunk_keywords)
        # All query keywords match, boost = 1.0 * 0.5 = 0.5
        assert score == pytest.approx(0.5, abs=0.001)


class TestRealWorldScenarios:
    """Test realistic use cases."""

    def test_function_search_by_purpose(self):
        """Test finding function by its purpose."""
        boost = ContextBoost()
        query_text = "validate user input"

        # Relevant function
        relevant_name = "validate_user_input"
        relevant_doc = "Validate user input for security"
        relevant_score = boost.calculate_from_chunk_fields(
            query_text=query_text, chunk_name=relevant_name, chunk_docstring=relevant_doc
        )

        # Irrelevant function
        irrelevant_name = "database_connect"
        irrelevant_doc = "Connect to database"
        irrelevant_score = boost.calculate_from_chunk_fields(
            query_text=query_text, chunk_name=irrelevant_name, chunk_docstring=irrelevant_doc
        )

        # Relevant should score higher
        assert relevant_score > irrelevant_score

    def test_search_with_technical_terms(self):
        """Test search with programming terminology."""
        boost = ContextBoost()
        query_text = "parse json api response"
        chunk_text = "json parser for api responses"

        score = boost.calculate_from_text(query_text, chunk_text)

        # Should find good overlap in technical terms
        # Query: {parse, json, api, response}
        # Chunk: {json, parser, api, responses}
        # Matches: json, api (2 out of 4 = 50%)
        # Note: "parser" != "parse", "responses" != "response" after stemming
        assert score > 0.2  # Expect reasonable boost
        assert score <= 0.5  # Max boost factor

    def test_search_filters_stop_words(self):
        """Test that stop words don't affect relevance."""
        boost = ContextBoost()
        query_text = "the database and the query"
        chunk_text = "database query"

        score = boost.calculate_from_text(query_text, chunk_text)

        # Should get full boost despite stop words in query
        assert score == pytest.approx(0.5, abs=0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
