"""BM25 scoring for code-aware keyword retrieval.

This module implements BM25 (Okapi BM25) scoring with code-aware tokenization
to enable exact keyword matching in hybrid retrieval.

Key Features:
    - Code-aware tokenization (camelCase, snake_case, dot notation, acronyms)
    - Okapi BM25 scoring algorithm
    - Index persistence (save/load)
    - Configurable parameters (k1, b)

Classes:
    BM25Scorer: Main BM25 implementation

Functions:
    tokenize: Code-aware tokenization for identifiers

References:
    - Okapi BM25: https://en.wikipedia.org/wiki/Okapi_BM25
    - Robertson et al., "Okapi at TREC-3" (1994)

"""

import logging
import math
import pickle
import re
from collections import Counter, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


def tokenize(text: str, _recursion_level: int = 0) -> list[str]:
    """Tokenize text with code-aware splitting.

    Splits identifiers using multiple strategies:
    - camelCase: "getUserData" → ["get", "User", "Data", "getuserdata"]
    - snake_case: "user_manager" → ["user", "manager", "user_manager"]
    - Dot notation: "auth.oauth" → ["auth", "oauth"]
    - Acronyms: "HTTPRequest" → ["HTTP", "Request", "httprequest"]
    - Whitespace: "authenticate user" → ["authenticate", "user"]
    - Special chars: "user@email.com" → ["user", "email", "com"]

    Args:
        text: Input text to tokenize
        _recursion_level: Internal recursion depth guard (default 0)

    Returns:
        List of tokens (includes both split tokens and original)

    Example:
        >>> tokenize("getUserData")
        ['get', 'User', 'Data', 'getuserdata']

        >>> tokenize("user_manager.auth_token")
        ['user', 'manager', 'user_manager', 'auth', 'token', 'auth_token']

    """
    if not text:
        return []

    # Recursion guard (prevent infinite recursion)
    if _recursion_level > 5:
        return [text]

    tokens = []

    # Step 1: Split by whitespace and special characters (except _ and .)
    # This handles: "user@email.com" → ["user", "email.com"]
    parts = re.split(r"[^\w\.\-]+", text)

    for part in parts:
        if not part:
            continue

        # Step 2: Split by dots (but preserve original)
        # "auth.oauth.client" → ["auth", "oauth", "client"]
        if "." in part:
            dot_parts = part.split(".")
            # Recursively tokenize each dot part
            for dot_part in dot_parts:
                if dot_part:
                    # Recursively tokenize this part to handle camelCase/snake_case
                    sub_tokens = tokenize(dot_part, _recursion_level + 1)
                    tokens.extend(sub_tokens)
            # Also preserve the full dotted name
            tokens.append(part)
        elif "_" in part:
            # Step 3: Handle snake_case (preserve original)
            snake_parts = part.split("_")
            # Recursively tokenize each snake_case part
            for snake_part in snake_parts:
                if snake_part:
                    # Recursively tokenize to handle camelCase within snake_case
                    sub_tokens = tokenize(snake_part, _recursion_level + 1)
                    tokens.extend(sub_tokens)
            # Preserve full snake_case token
            tokens.append(part)
        else:
            # Step 4: Handle camelCase and acronyms
            # Pattern explanation:
            # - [A-Z]+(?=[A-Z][a-z]|\b) : Acronyms like "HTTP" in "HTTPRequest"
            # - [A-Z][a-z]+ : Capitalized words like "Request"
            # - [a-z]+ : Lowercase words like "get", "user"
            # - [0-9]+ : Numbers
            camel_pattern = r"([A-Z]+(?=[A-Z][a-z]|\b)|[A-Z][a-z]+|[a-z]+|[0-9]+)"
            camel_parts = re.findall(camel_pattern, part)

            if camel_parts and len(camel_parts) > 1:
                # camelCase or acronyms detected
                tokens.extend(camel_parts)
                # Preserve full token
                tokens.append(part)
            elif camel_parts:
                # Single word
                tokens.extend(camel_parts)
            else:
                # No pattern matched, just add the part
                if part not in tokens:
                    tokens.append(part)

    # Step 5: Normalize to lowercase for case-insensitive matching
    # Convert all tokens to lowercase for BM25 matching
    lowercase_tokens = [t.lower() for t in tokens]

    # Step 6: Filter out empty strings (but KEEP duplicates for term frequency)
    # BM25 needs to count term frequency, so duplicates are important!
    final_tokens = [t for t in lowercase_tokens if t]

    logger.debug(f"Tokenized '{text}' → {final_tokens}")
    return final_tokens


class BM25Scorer:
    """BM25 scorer with code-aware tokenization.

    Implements Okapi BM25 algorithm for keyword scoring:
        score(Q, D) = Σ IDF(qi) · (f(qi, D) · (k1 + 1)) / (f(qi, D) + k1 · (1 - b + b · |D| / avgdl))

    Where:
        - IDF(qi) = log((N - n(qi) + 0.5) / (n(qi) + 0.5) + 1)
        - f(qi, D) = frequency of term qi in document D
        - |D| = length of document D in tokens
        - avgdl = average document length in corpus
        - k1 = term frequency saturation (default 1.5)
        - b = length normalization (default 0.75)

    Attributes:
        k1: Term frequency saturation parameter (default 1.5)
        b: Length normalization parameter (default 0.75)
        idf: IDF scores for all terms in corpus
        doc_lengths: Token counts for each document
        avg_doc_length: Average document length in corpus
        corpus_size: Number of documents in corpus

    Example:
        >>> scorer = BM25Scorer(k1=1.5, b=0.75)
        >>> docs = [("d1", "authenticate user"), ("d2", "user session")]
        >>> scorer.build_index(docs)
        >>> score = scorer.score("authenticate", "authenticate user token")
        >>> print(f"BM25 score: {score:.3f}")

    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 scorer.

        Args:
            k1: Term frequency saturation parameter (typically 1.2-2.0)
            b: Length normalization parameter (0.0-1.0)

        Raises:
            ValueError: If k1 < 0 or b not in [0, 1]

        """
        if k1 < 0:
            raise ValueError(f"k1 must be >= 0, got {k1}")
        if not (0.0 <= b <= 1.0):
            raise ValueError(f"b must be in [0, 1], got {b}")

        self.k1 = k1
        self.b = b

        # Index data structures
        self.idf: dict[str, float] = {}
        self.doc_lengths: dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.corpus_size: int = 0
        self.term_doc_counts: dict[str, int] = {}  # n(t): number of docs containing term t

        logger.info(f"Initialized BM25Scorer with k1={k1}, b={b}")

    def build_index(self, documents: list[tuple[str, str]]) -> None:
        """Build BM25 index from documents.

        Args:
            documents: List of (doc_id, doc_content) tuples

        Example:
            >>> docs = [("d1", "auth user"), ("d2", "user session")]
            >>> scorer.build_index(docs)

        """
        logger.info(f"Building BM25 index for {len(documents)} documents...")

        self.corpus_size = len(documents)

        # Calculate document lengths
        self.doc_lengths = {}
        total_length = 0

        for doc_id, doc_content in documents:
            tokens = tokenize(doc_content)
            doc_length = len(tokens)
            self.doc_lengths[doc_id] = doc_length
            total_length += doc_length

        # Calculate average document length
        self.avg_doc_length = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

        # Count documents containing each term
        self.term_doc_counts = defaultdict(int)
        for doc_id, doc_content in documents:
            tokens = tokenize(doc_content)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.term_doc_counts[token] += 1

        # Calculate IDF scores
        self.idf = {}
        for term, doc_count in self.term_doc_counts.items():
            # IDF formula: log((N - n(t) + 0.5) / (n(t) + 0.5) + 1)
            idf_score = math.log((self.corpus_size - doc_count + 0.5) / (doc_count + 0.5) + 1)
            self.idf[term] = idf_score

        logger.info(
            f"BM25 index built: {len(self.idf)} unique terms, "
            f"avg_doc_length={self.avg_doc_length:.2f}",
        )

    def score(self, query: str, document: str) -> float:
        """Calculate BM25 score for document given query.

        Args:
            query: Search query
            document: Document content to score

        Returns:
            BM25 score (unbounded, typically 0-20 range)

        Example:
            >>> score = scorer.score("authenticate user", "authenticate user session")
            >>> print(f"Score: {score:.3f}")

        """
        query_tokens = tokenize(query)
        doc_tokens = tokenize(document)
        doc_length = len(doc_tokens)

        # Count term frequencies in document
        term_freqs = Counter(doc_tokens)

        bm25_score = 0.0

        for query_term in query_tokens:
            # Skip if term not in document
            if query_term not in term_freqs:
                continue

            # Get IDF score (0 if term not in corpus)
            idf_score = self.idf.get(query_term, 0.0)

            # Get term frequency in document
            freq = term_freqs[query_term]

            # BM25 formula
            numerator = freq * (self.k1 + 1)
            denominator = freq + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)

            term_score = idf_score * (numerator / denominator)
            bm25_score += term_score

        logger.debug(
            f"BM25 score for query='{query}': {bm25_score:.3f} "
            f"(doc_length={doc_length}, query_terms={len(query_tokens)})",
        )

        return bm25_score

    def save_index(self, path: Path) -> None:
        """Save BM25 index to file.

        Args:
            path: Path to save index file (will be pickle format)

        Example:
            >>> scorer.save_index(Path("~/.aurora/indexes/bm25_index.pkl"))

        """
        index_data = {
            "version": "1.0",
            "k1": self.k1,
            "b": self.b,
            "idf": self.idf,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "corpus_size": self.corpus_size,
            "term_doc_counts": dict(self.term_doc_counts),
        }

        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(index_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        logger.info(f"Saved BM25 index to {path} ({self.corpus_size} documents)")

    def load_index(self, path: Path) -> None:
        """Load BM25 index from file.

        Args:
            path: Path to index file

        Raises:
            FileNotFoundError: If index file doesn't exist
            pickle.UnpicklingError: If index file is corrupted

        Example:
            >>> scorer.load_index(Path("~/.aurora/indexes/bm25_index.pkl"))

        """
        if not path.exists():
            raise FileNotFoundError(f"BM25 index not found: {path}")

        with open(path, "rb") as f:
            index_data = pickle.load(f)

        # Validate version
        version = index_data.get("version", "unknown")
        if version != "1.0":
            logger.warning(f"BM25 index version mismatch: got {version}, expected 1.0")

        # Restore index data
        self.k1 = index_data["k1"]
        self.b = index_data["b"]
        self.idf = index_data["idf"]
        self.doc_lengths = index_data["doc_lengths"]
        self.avg_doc_length = index_data["avg_doc_length"]
        self.corpus_size = index_data["corpus_size"]
        self.term_doc_counts = defaultdict(int, index_data["term_doc_counts"])

        logger.info(
            f"Loaded BM25 index from {path} ({self.corpus_size} documents, {len(self.idf)} terms)",
        )


def calculate_idf(_term: str, corpus_size: int, term_doc_count: int) -> float:
    """Calculate IDF (Inverse Document Frequency) for a term.

    IDF formula: log((N - n(t) + 0.5) / (n(t) + 0.5) + 1)

    Args:
        _term: The term to calculate IDF for (reserved for future term-specific logic)
        corpus_size: Total number of documents (N)
        term_doc_count: Number of documents containing the term (n(t))

    Returns:
        IDF score

    Example:
        >>> idf = calculate_idf("auth", corpus_size=100, term_doc_count=10)
        >>> print(f"IDF: {idf:.3f}")

    """
    if corpus_size == 0:
        return 0.0

    idf = math.log((corpus_size - term_doc_count + 0.5) / (term_doc_count + 0.5) + 1)
    return idf


def calculate_bm25(
    query_terms: list[str],
    doc_terms: list[str],
    doc_length: int,
    avg_doc_length: float,
    idf_scores: dict[str, float],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Calculate BM25 score for a document.

    Args:
        query_terms: Tokenized query terms
        doc_terms: Tokenized document terms
        doc_length: Length of document in tokens
        avg_doc_length: Average document length in corpus
        idf_scores: IDF scores for terms
        k1: Term frequency saturation parameter
        b: Length normalization parameter

    Returns:
        BM25 score

    Example:
        >>> query = ["auth", "user"]
        >>> doc = ["auth", "user", "session", "token"]
        >>> idfs = {"auth": 2.0, "user": 1.5}
        >>> score = calculate_bm25(query, doc, len(doc), 5.0, idfs)

    """
    term_freqs = Counter(doc_terms)
    score = 0.0

    for term in query_terms:
        if term not in term_freqs:
            continue

        idf = idf_scores.get(term, 0.0)
        freq = term_freqs[term]

        numerator = freq * (k1 + 1)
        denominator = freq + k1 * (1 - b + b * doc_length / avg_doc_length)

        score += idf * (numerator / denominator)

    return score
