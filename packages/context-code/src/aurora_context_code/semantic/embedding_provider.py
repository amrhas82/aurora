"""Embedding generation for semantic code understanding.

This module provides the EmbeddingProvider class for generating vector embeddings
of code chunks and user queries using sentence-transformers.

Classes:
    EmbeddingProvider: Generate embeddings using all-MiniLM-L6-v2 model

Functions:
    cosine_similarity: Calculate cosine similarity between two vectors
"""

from typing import Any, Protocol, cast

import numpy as np
import numpy.typing as npt


class _SentenceTransformerProtocol(Protocol):
    """Protocol for SentenceTransformer model interface used by EmbeddingProvider."""

    def encode(
        self,
        sentences: str | list[str],
        batch_size: int = ...,
        convert_to_numpy: bool = ...,
        normalize_embeddings: bool = ...,
        show_progress_bar: bool = ...,
    ) -> Any: ...

    def get_sentence_embedding_dimension(self) -> int: ...


# Lazy-loaded dependencies - only imported when actually needed
# This avoids 20+ second startup delay from torch/sentence_transformers
_torch = None
_SentenceTransformer = None
_HAS_SENTENCE_TRANSFORMERS: bool | None = None


def _can_import_ml_deps() -> bool:
    """Check if ML dependencies can be imported without actually importing them.

    This is a lightweight check that doesn't trigger heavy imports.
    Uses importlib.util.find_spec() which only checks for importability.

    Returns:
        True if both torch and sentence_transformers are available, False otherwise.

    """
    import importlib.util

    torch_spec = importlib.util.find_spec("torch")
    st_spec = importlib.util.find_spec("sentence_transformers")

    return torch_spec is not None and st_spec is not None


def _lazy_import() -> bool:
    """Lazily import torch and sentence_transformers on first use.

    Returns:
        True if imports succeeded, False otherwise.

    """
    global _torch, _SentenceTransformer, _HAS_SENTENCE_TRANSFORMERS

    if _HAS_SENTENCE_TRANSFORMERS is not None:
        # Already attempted import (success or failure)
        return _HAS_SENTENCE_TRANSFORMERS

    try:
        import torch as torch_module
        from sentence_transformers import SentenceTransformer as ST

        _torch = torch_module
        _SentenceTransformer = ST
        _HAS_SENTENCE_TRANSFORMERS = True
    except ImportError:
        _HAS_SENTENCE_TRANSFORMERS = False

    return _HAS_SENTENCE_TRANSFORMERS


# Public API: Check if sentence-transformers is available
# Uses lightweight importlib.util.find_spec() - doesn't actually import torch/sentence_transformers
# This allows tests to conditionally skip without triggering the 20+ second import
HAS_SENTENCE_TRANSFORMERS = _can_import_ml_deps()


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
            f"Vectors must have same dimension: vec1.shape={vec1.shape}, vec2.shape={vec2.shape}",
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
            "(at least one vector has zero magnitude)",
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

    The model is loaded lazily on first use to avoid 30+ second startup delays.

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

    # Known embedding dimensions for common models (avoid loading model just to get dim)
    _KNOWN_EMBEDDING_DIMS = {
        "all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "sentence-transformers/all-mpnet-base-v2": 768,
        "multi-qa-MiniLM-L6-cos-v1": 384,
        "all-distilroberta-v1": 768,
    }

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str | None = None,
    ):
        """Initialize embedding provider with lazy model loading.

        The model is NOT loaded during initialization - it will be loaded
        on the first call to embed_chunk(), embed_query(), or embed_batch().
        This eliminates the 30+ second startup delay for commands that may
        not need embeddings.

        Args:
            model_name: Sentence-transformers model name
            device: Device for inference (None = auto-detect)

        Raises:
            ImportError: If sentence-transformers is not installed

        """
        if not _can_import_ml_deps():
            raise ImportError(
                "sentence-transformers is required for semantic embeddings. "
                "Install with: pip install aurora-context-code[ml]",
            )

        self.model_name = model_name

        # Store device (will check CUDA availability later when actually loading model)
        # Deferring this check avoids importing torch during initialization
        self._device_hint = device

        # Lazy-loaded model (initialized to None, loaded on first use)
        self._model: _SentenceTransformerProtocol | None = None
        self._device: str | None = None

        # Set embedding dimension from known values (avoids loading model)
        # Will be updated from model if unknown
        self._embedding_dim: int | None = self._KNOWN_EMBEDDING_DIMS.get(model_name)

    @property
    def device(self) -> str:
        """Get device (auto-detects CUDA only when needed)."""
        if self._device is None:
            if self._device_hint is not None:
                self._device = self._device_hint
            else:
                # Lazy check for CUDA - only import torch when actually needed
                _lazy_import()
                if _torch is not None and _torch.cuda.is_available():
                    self._device = "cuda"
                else:
                    self._device = "cpu"
        return self._device

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension, loading model if necessary for unknown models."""
        if self._embedding_dim is not None:
            return self._embedding_dim
        # Unknown model - need to load to get dimension
        self._ensure_model_loaded()
        return self._embedding_dim  # type: ignore[return-value]

    def _ensure_model_loaded(self) -> _SentenceTransformerProtocol:
        """Load the model if not already loaded (lazy initialization).

        Returns:
            The loaded SentenceTransformer model

        Note:
            This method is idempotent - calling it multiple times is safe.

        """
        if self._model is None:
            import logging

            # Ensure dependencies are imported now
            _lazy_import()

            # Suppress verbose HuggingFace Hub warnings during model loading
            # These warnings about network timeouts and retries are noisy
            hf_loggers = [
                "huggingface_hub.utils._http",
                "huggingface_hub.file_download",
                "sentence_transformers.SentenceTransformer",
                "transformers",
            ]
            original_levels = {}
            for logger_name in hf_loggers:
                hf_logger = logging.getLogger(logger_name)
                original_levels[logger_name] = hf_logger.level
                hf_logger.setLevel(logging.ERROR)

            try:
                # Import suppression helper
                from aurora_context_code.semantic.model_utils import (
                    _suppress_model_loading_output,
                )

                # Use the lazily-imported SentenceTransformer class
                # Suppress verbose "Loading weights" progress bars
                with _suppress_model_loading_output():
                    if _SentenceTransformer is None:
                        raise RuntimeError(
                            "SentenceTransformer not loaded. "
                            "Install with: pip install aurora-context-code[ml]"
                        )
                    model = _SentenceTransformer(self.model_name, device=self.device)
                    self._model = cast(_SentenceTransformerProtocol, model)
                    # Update embedding dimension from the actual model
                    self._embedding_dim = self._model.get_sentence_embedding_dimension()
            finally:
                # Restore original logging levels
                for logger_name, level in original_levels.items():
                    logging.getLogger(logger_name).setLevel(level)

        # At this point, self._model is guaranteed to be loaded
        assert self._model is not None
        return self._model

    def is_model_loaded(self) -> bool:
        """Check if the model has been loaded.

        Returns:
            True if model is loaded, False if still lazy (not yet loaded)

        """
        return self._model is not None

    def preload_model(self) -> None:
        """Explicitly load the model (for pre-warming in background threads).

        This method can be called from a background thread to load the model
        before it's needed, avoiding the delay when first embedding is requested.

        Example:
            >>> import threading
            >>> provider = EmbeddingProvider()
            >>> # Load model in background
            >>> thread = threading.Thread(target=provider.preload_model)
            >>> thread.start()
            >>> # ... do other initialization work ...
            >>> thread.join()  # Wait for model to be ready

        """
        self._ensure_model_loaded()

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
                f"(~512 tokens). Consider chunking the code into smaller pieces.",
            )

        # Ensure model is loaded (lazy initialization)
        model = self._ensure_model_loaded()

        # Generate embedding using sentence-transformers
        # The model.encode() returns normalized embeddings by default
        embedding_result = model.encode(
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
                f"(~512 tokens). Please shorten the query.",
            )

        # Ensure model is loaded (lazy initialization)
        model = self._ensure_model_loaded()

        # Generate embedding using sentence-transformers
        # The model.encode() returns normalized embeddings by default
        embedding_result = model.encode(
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

        # Ensure model is loaded (lazy initialization)
        model = self._ensure_model_loaded()

        # Use native batch encoding - this is the key optimization
        # sentence-transformers handles batching internally and efficiently
        embeddings_result = model.encode(
            processed_texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # Cast to numpy array and ensure correct dtype
        embeddings: npt.NDArray[np.float32] = np.asarray(embeddings_result, dtype=np.float32)

        return embeddings
