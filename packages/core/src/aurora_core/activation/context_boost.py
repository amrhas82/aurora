"""Context Boost Implementation

This module implements context boost, a component of ACT-R activation that
increases activation for chunks matching the current query context. Context
boost captures the relevance of a chunk to the current retrieval goal.

Context Boost Formula:
    Context Boost = keyword_overlap × boost_factor

Where:
    - keyword_overlap: Fraction of query keywords present in chunk (0.0 to 1.0)
    - boost_factor: Maximum boost value (default 0.5)

The context boost ensures that chunks semantically related to the current
query receive additional activation, even if they haven't been accessed recently.

Reference:
    Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
    Oxford University Press. Chapter 5: Context and Activation.
"""

import re
from typing import Any

from pydantic import BaseModel, Field


class ContextBoostConfig(BaseModel):
    """Configuration for context boost calculation.

    Attributes:
        boost_factor: Maximum boost value (default 0.5)
        min_keyword_length: Minimum keyword length to consider (default 3)
        case_sensitive: Whether keyword matching is case-sensitive
        stemming_enabled: Whether to use basic stemming (not implemented yet)

    """

    boost_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Maximum context boost value",
    )
    min_keyword_length: int = Field(
        default=3,
        ge=1,
        description="Minimum keyword length to consider",
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether keyword matching is case-sensitive",
    )
    stemming_enabled: bool = Field(
        default=False,
        description="Whether to use basic stemming (future feature)",
    )


class KeywordExtractor:
    """Extracts keywords from text for context matching.

    This class provides simple but effective keyword extraction using
    regular expressions and basic text processing. It filters out common
    stop words and short tokens.

    Examples:
        >>> extractor = KeywordExtractor()
        >>> keywords = extractor.extract("optimize database queries")
        >>> print(keywords)
        {'optimize', 'database', 'queries'}

    """

    # Common English stop words to filter out
    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "that",
        "the",
        "to",
        "was",
        "will",
        "with",
        "this",
        "but",
        "they",
        "have",
        "had",
        "what",
        "when",
        "where",
        "who",
        "which",
        "why",
        "how",
        "or",
        "can",
        "do",
        "does",
        "did",
        "should",
        "could",
        "would",
        "may",
        "might",
        "must",
        "shall",
        "not",
        "no",
        "nor",
        "if",
        "then",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "only",
        "both",
        "either",
        "neither",
    }

    # Programming-specific terms that should NOT be filtered
    PROGRAMMING_TERMS = {
        "api",
        "app",
        "aws",
        "cli",
        "cpu",
        "csv",
        "css",
        "db",
        "dev",
        "dto",
        "end",
        "env",
        "etc",
        "git",
        "gpu",
        "gui",
        "html",
        "http",
        "id",
        "ide",
        "io",
        "ip",
        "jar",
        "js",
        "json",
        "jwt",
        "key",
        "lib",
        "log",
        "mac",
        "max",
        "min",
        "npm",
        "null",
        "os",
        "pdf",
        "php",
        "png",
        "py",
        "ram",
        "ref",
        "rgb",
        "row",
        "run",
        "sdk",
        "sql",
        "ssh",
        "ssl",
        "std",
        "svg",
        "tcp",
        "tls",
        "tmp",
        "ttl",
        "ui",
        "uri",
        "url",
        "usb",
        "utc",
        "var",
        "vm",
        "vpn",
        "web",
        "www",
        "xml",
        "yml",
        "zip",
        "add",
        "all",
        "any",
        "bin",
        "bit",
        "buf",
        "cmd",
        "get",
        "len",
        "map",
        "new",
        "old",
        "out",
        "put",
        "raw",
        "set",
        "src",
        "sum",
        "tag",
        "top",
        "use",
        "val",
    }

    def __init__(self, config: ContextBoostConfig | None = None):
        """Initialize the keyword extractor.

        Args:
            config: Configuration for keyword extraction

        """
        self.config = config or ContextBoostConfig()

    def extract(self, text: str) -> set[str]:
        """Extract keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            Set of extracted keywords

        Notes:
            - Splits on non-alphanumeric characters
            - Filters stop words (unless they're programming terms)
            - Filters short words (< min_keyword_length)
            - Converts to lowercase (unless case_sensitive=True)

        """
        if not text:
            return set()

        # Convert to lowercase unless case-sensitive
        if not self.config.case_sensitive:
            text = text.lower()

        # Split on non-alphanumeric characters, keeping underscores
        tokens = re.findall(r"\b\w+\b", text)

        # Filter keywords
        keywords = set()
        for token in tokens:
            # Skip if too short
            if len(token) < self.config.min_keyword_length:
                # But keep if it's a known programming term
                if token.lower() not in self.PROGRAMMING_TERMS:
                    continue

            # Skip stop words unless they're programming terms
            token_lower = token.lower()
            if token_lower in self.STOP_WORDS:
                if token_lower not in self.PROGRAMMING_TERMS:
                    continue

            keywords.add(token)

        return keywords

    def extract_from_chunks(self, chunks: list[str]) -> set[str]:
        """Extract keywords from multiple text chunks.

        Args:
            chunks: List of text chunks

        Returns:
            Combined set of keywords from all chunks

        """
        all_keywords = set()
        for chunk in chunks:
            all_keywords.update(self.extract(chunk))
        return all_keywords


class ContextBoost:
    """Calculates context boost based on keyword overlap.

    Context boost increases activation for chunks that match the current
    query context, making them more likely to be retrieved even if they
    haven't been accessed recently.

    Examples:
        >>> boost = ContextBoost()
        >>> query_keywords = {'database', 'query', 'optimize'}
        >>> chunk_keywords = {'database', 'query', 'performance'}
        >>> score = boost.calculate(query_keywords, chunk_keywords)
        >>> print(f"Context boost: {score:.3f}")
        Context boost: 0.333

    """

    def __init__(self, config: ContextBoostConfig | None = None):
        """Initialize the context boost calculator.

        Args:
            config: Configuration for context boost calculation

        """
        self.config = config or ContextBoostConfig()
        self.extractor = KeywordExtractor(config)

    def calculate(self, query_keywords: set[str], chunk_keywords: set[str]) -> float:
        """Calculate context boost based on keyword overlap.

        Args:
            query_keywords: Keywords from the query
            chunk_keywords: Keywords from the chunk

        Returns:
            Context boost value (0.0 to boost_factor)

        Notes:
            - Returns 0.0 if no query keywords
            - Calculates fraction of query keywords present in chunk
            - Multiplies by boost_factor to get final boost

        """
        if not query_keywords:
            return 0.0

        # Calculate overlap
        overlap = query_keywords & chunk_keywords
        overlap_fraction = len(overlap) / len(query_keywords)

        # Apply boost factor
        return overlap_fraction * self.config.boost_factor

    def calculate_from_text(self, query_text: str, chunk_text: str) -> float:
        """Calculate context boost from raw text.

        Convenience method that extracts keywords and calculates boost.

        Args:
            query_text: Query text
            chunk_text: Chunk text

        Returns:
            Context boost value

        """
        query_keywords = self.extractor.extract(query_text)
        chunk_keywords = self.extractor.extract(chunk_text)
        return self.calculate(query_keywords, chunk_keywords)

    def calculate_from_chunk_fields(
        self,
        query_text: str,
        chunk_name: str,
        chunk_docstring: str | None = None,
        chunk_signature: str | None = None,
        chunk_body: str | None = None,
    ) -> float:
        """Calculate context boost from chunk fields.

        Combines multiple chunk fields (name, docstring, signature, body)
        to extract keywords and calculate boost.

        Args:
            query_text: Query text
            chunk_name: Chunk name (e.g., function name)
            chunk_docstring: Optional docstring
            chunk_signature: Optional function signature
            chunk_body: Optional function body

        Returns:
            Context boost value

        Notes:
            - Weights fields differently (name and docstring more important)
            - Name keywords count 2x
            - Docstring keywords count 1.5x
            - Signature and body keywords count 1x

        """
        query_keywords = self.extractor.extract(query_text)

        if not query_keywords:
            return 0.0

        # Extract keywords from different fields with weights
        name_keywords = self.extractor.extract(chunk_name)
        docstring_keywords = self.extractor.extract(chunk_docstring) if chunk_docstring else set()
        signature_keywords = self.extractor.extract(chunk_signature) if chunk_signature else set()
        body_keywords = self.extractor.extract(chunk_body) if chunk_body else set()

        # Calculate weighted overlap
        total_overlap = 0.0
        total_weight = 0.0

        # Name keywords (weight: 2.0)
        if name_keywords:
            overlap = len(query_keywords & name_keywords)
            total_overlap += overlap * 2.0
            total_weight += len(query_keywords) * 2.0

        # Docstring keywords (weight: 1.5)
        if docstring_keywords:
            overlap = len(query_keywords & docstring_keywords)
            total_overlap += overlap * 1.5
            total_weight += len(query_keywords) * 1.5

        # Signature keywords (weight: 1.0)
        if signature_keywords:
            overlap = len(query_keywords & signature_keywords)
            total_overlap += overlap * 1.0
            total_weight += len(query_keywords) * 1.0

        # Body keywords (weight: 1.0, but limit to avoid overwhelming)
        if body_keywords:
            overlap = len(query_keywords & body_keywords)
            total_overlap += min(overlap, len(query_keywords)) * 1.0
            total_weight += len(query_keywords) * 1.0

        # Calculate weighted overlap fraction
        if total_weight > 0:
            weighted_fraction = total_overlap / total_weight
            return weighted_fraction * self.config.boost_factor
        return 0.0

    def get_matching_keywords(self, query_keywords: set[str], chunk_keywords: set[str]) -> set[str]:
        """Get the keywords that match between query and chunk.

        Args:
            query_keywords: Keywords from the query
            chunk_keywords: Keywords from the chunk

        Returns:
            Set of matching keywords

        """
        return query_keywords & chunk_keywords

    def explain_boost(self, query_text: str, chunk_text: str) -> dict[str, Any]:
        """Explain how context boost was calculated.

        Args:
            query_text: Query text
            chunk_text: Chunk text

        Returns:
            Dictionary with explanation:
                - boost_value: Final boost value
                - query_keywords: Keywords extracted from query
                - chunk_keywords: Keywords extracted from chunk
                - matching_keywords: Keywords that matched
                - overlap_fraction: Fraction of query keywords that matched

        """
        query_keywords = self.extractor.extract(query_text)
        chunk_keywords = self.extractor.extract(chunk_text)
        matching = self.get_matching_keywords(query_keywords, chunk_keywords)

        overlap_fraction = len(matching) / len(query_keywords) if query_keywords else 0.0

        boost_value = overlap_fraction * self.config.boost_factor

        return {
            "boost_value": boost_value,
            "query_keywords": sorted(query_keywords),
            "chunk_keywords": sorted(chunk_keywords),
            "matching_keywords": sorted(matching),
            "overlap_fraction": overlap_fraction,
        }


def calculate_context_boost(query_text: str, chunk_text: str, boost_factor: float = 0.5) -> float:
    """Convenience function for calculating context boost.

    Args:
        query_text: Query text
        chunk_text: Chunk text
        boost_factor: Maximum boost value (default 0.5)

    Returns:
        Context boost value

    """
    config = ContextBoostConfig(boost_factor=boost_factor)
    calculator = ContextBoost(config)
    return calculator.calculate_from_text(query_text, chunk_text)


__all__ = [
    "ContextBoostConfig",
    "KeywordExtractor",
    "ContextBoost",
    "calculate_context_boost",
]
