"""Embedding generation for semantic code understanding.

This module provides the EmbeddingProvider class for generating vector embeddings
of code chunks and user queries using sentence-transformers.

Classes:
    EmbeddingProvider: Generate embeddings using all-MiniLM-L6-v2 model

Functions:
    cosine_similarity: Calculate cosine similarity between two vectors
"""

import numpy as np
import numpy.typing as npt

# Optional dependency - only needed for semantic features
# Note: mypy config disables warn_unused_ignores for this module
try:
    import torch
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    SentenceTransformer = None  # type: ignore[misc,assignment]
    torch = None  # type: ignore[assignment]


def cosine_similarity(
    vec1: npt.NDArray[np.float32],
    vec2: npt.NDArray[np.float32],
) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector (normalized or not)
        vec2: Second vector (normalized or not)

    Returns:
        Similarity score in range [-1, 1] where:
        - 1.0 = identical vectors
        - 0.0 = orthogonal (no similarity)
        - -1.0 = opposite vectors

    Raises:
        ValueError: If vectors have different dimensions or are zero-length

    Example:
        >>> vec1 = np.array([1.0, 0.0, 0.0])
        >>> vec2 = np.array([0.0, 1.0, 0.0])
        >>> cosine_similarity(vec1, vec2)
        0.0
    """
    # Validate input dimensions
    if vec1.shape != vec2.shape:
        raise ValueError(
            f"Vectors must have same dimension: vec1.shape={vec1.shape}, vec2.shape={vec2.shape}"
        )

    # Check for zero-length vectors
    if vec1.shape[0] == 0:
        raise ValueError("Cannot compute similarity of zero-length vectors")

    # Calculate L2 norms
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    # Check for zero vectors (would cause division by zero)
    if norm1 == 0.0 or norm2 == 0.0:
        raise ValueError(
            "Cannot compute cosine similarity with zero vector "
            "(at least one vector has zero magnitude)"
        )

    # Calculate cosine similarity: dot product divided by product of magnitudes
    # Formula: similarity = (vec1 · vec2) / (||vec1|| × ||vec2||)
    similarity = np.dot(vec1, vec2) / (norm1 * norm2)

    # Convert to Python float (in case it's a numpy scalar)
    return float(similarity)


class EmbeddingProvider:
    """Generate vector embeddings for code chunks and queries.

    Uses sentence-transformers library with all-MiniLM-L6-v2 model by default.
    This model provides:
    - 384-dimensional embeddings
    - Fast inference (<50ms per chunk target)
    - Good semantic understanding for code

    Attributes:
        model_name: Name of the sentence-transformers model
        embedding_dim: Dimension of output vectors (384 for default model)
        device: Device for inference ("cpu" or "cuda")

    Example:
        >>> provider = EmbeddingProvider()
        >>> embedding = provider.embed_chunk("def calculate(x): return x * 2")
        >>> embedding.shape
        (384,)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
    ):
        """Initialize embedding provider.

        Args:
            model_name: Sentence-transformers model name
            device: Device for inference (None = auto-detect)

        Raises:
            ImportError: If sentence-transformers is not installed
        """
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError(
                "sentence-transformers is required for semantic embeddings. "
                "Install with: pip install aurora-context-code[ml]"
            )

        self.model_name = model_name

        # Auto-detect device if not specified
        if device is None:
            self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load the sentence-transformers model
        self._model = SentenceTransformer(model_name, device=self.device)

        # Get embedding dimension from the model
        self.embedding_dim = self._model.get_sentence_embedding_dimension()

    def embed_chunk(self, text: str) -> npt.NDArray[np.float32]:
        """Generate embedding for a code chunk.

        Combines name + docstring + signature for rich semantic representation.

        Args:
            text: Code chunk text to embed

        Returns:
            Embedding vector (384-dim for default model)

        Raises:
            ValueError: If text is empty or too long (>512 tokens)
            TypeError: If text is not a string

        Example:
            >>> provider = EmbeddingProvider()
            >>> text = "def add(a, b): return a + b"
            >>> embedding = provider.embed_chunk(text)
        """
        # Validate input type
        if not isinstance(text, str):
            raise TypeError(f"Expected str, got {type(text).__name__}")

        # Strip whitespace and validate not empty
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text")

        # Check token limit (rough estimate: 1 token ≈ 4 chars for code)
        # sentence-transformers default max is 512 tokens
        max_chars = 512 * 4  # ~2048 characters
        if len(text) > max_chars:
            raise ValueError(
                f"Text too long: {len(text)} chars exceeds limit of {max_chars} "
                f"(~512 tokens). Consider chunking the code into smaller pieces."
            )

        # Generate embedding using sentence-transformers
        # The model.encode() returns normalized embeddings by default
        embedding_result = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalization for cosine similarity
            show_progress_bar=False,
        )

        # Cast to numpy array and ensure correct dtype
        embedding: npt.NDArray[np.float32] = np.asarray(embedding_result, dtype=np.float32)

        return embedding

    def embed_query(self, query: str) -> npt.NDArray[np.float32]:
        """Generate embedding for a user query.

        Args:
            query: User query text

        Returns:
            Embedding vector (same dimension as chunks)

        Raises:
            ValueError: If query is empty or too long
            TypeError: If query is not a string

        Example:
            >>> provider = EmbeddingProvider()
            >>> query_embedding = provider.embed_query("how to calculate total price")
        """
        # Validate input type
        if not isinstance(query, str):
            raise TypeError(f"Expected str, got {type(query).__name__}")

        # Strip whitespace and validate not empty
        query = query.strip()
        if not query:
            raise ValueError("Cannot embed empty query")

        # Check token limit (same as embed_chunk)
        max_chars = 512 * 4  # ~2048 characters
        if len(query) > max_chars:
            raise ValueError(
                f"Query too long: {len(query)} chars exceeds limit of {max_chars} "
                f"(~512 tokens). Please shorten the query."
            )

        # Generate embedding using sentence-transformers
        # The model.encode() returns normalized embeddings by default
        embedding_result = self._model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalization for cosine similarity
            show_progress_bar=False,
        )

        # Cast to numpy array and ensure correct dtype
        embedding: npt.NDArray[np.float32] = np.asarray(embedding_result, dtype=np.float32)

        return embedding

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> npt.NDArray[np.float32]:
        """Generate embeddings for multiple texts efficiently using native batching.

        Uses sentence-transformers native batch encoding which is significantly
        faster than encoding one at a time, especially on GPU.

        Args:
            texts: List of text chunks to embed
            batch_size: Number of texts to encode at once (default 32)

        Returns:
            Array of embeddings, shape (len(texts), embedding_dim)

        Raises:
            ValueError: If any text is empty or too long

        Example:
            >>> provider = EmbeddingProvider()
            >>> texts = ["def add(a, b): return a + b", "def multiply(x, y): return x * y"]
            >>> embeddings = provider.embed_batch(texts)
            >>> embeddings.shape
            (2, 384)
        """
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.embedding_dim)

        # Validate and preprocess all texts
        max_chars = 512 * 4  # ~2048 characters
        processed_texts = []

        for i, text in enumerate(texts):
            if not isinstance(text, str):
                raise TypeError(f"Expected str at index {i}, got {type(text).__name__}")

            text = text.strip()
            if not text:
                raise ValueError(f"Cannot embed empty text at index {i}")

            # Truncate if too long (instead of raising error in batch mode)
            if len(text) > max_chars:
                text = text[:max_chars]

            processed_texts.append(text)

        # Use native batch encoding - this is the key optimization
        # sentence-transformers handles batching internally and efficiently
        embeddings_result = self._model.encode(
            processed_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Cast to numpy array and ensure correct dtype
        embeddings: npt.NDArray[np.float32] = np.asarray(embeddings_result, dtype=np.float32)

        return embeddings
