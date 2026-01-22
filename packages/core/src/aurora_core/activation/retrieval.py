"""Activation-Based Retrieval

This module implements retrieval of chunks based on ACT-R activation scores.
Chunks are ranked by total activation and filtered by threshold, ensuring
that only the most relevant and recently accessed chunks are retrieved.

Retrieval Strategy:
1. Calculate activation for all candidate chunks
2. Filter by activation threshold
3. Sort by activation (descending)
4. Return top N results

This mirrors human memory retrieval where only sufficiently activated
memories are accessible for recall.

Reference:
    Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
    Oxford University Press. Chapter 6: Memory Retrieval.
"""

from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import BaseModel, Field

from aurora_core.activation.base_level import AccessHistoryEntry
from aurora_core.activation.engine import ActivationComponents, ActivationEngine
from aurora_core.activation.spreading import RelationshipGraph
from aurora_core.types import ChunkID


class ChunkData(Protocol):
    """Protocol for chunk data required for activation calculation.

    This allows the retriever to work with different chunk implementations
    without tight coupling.
    """

    @property
    def id(self) -> ChunkID:
        """Chunk unique identifier."""
        ...

    @property
    def access_history(self) -> list[AccessHistoryEntry]:
        """List of past accesses."""
        ...

    @property
    def last_access(self) -> datetime | None:
        """Most recent access timestamp."""
        ...

    @property
    def keywords(self) -> set[str]:
        """Keywords extracted from chunk content."""
        ...


class RetrievalConfig(BaseModel):
    """Configuration for activation-based retrieval.

    Attributes:
        threshold: Minimum activation for retrieval (default 0.3)
        max_results: Maximum number of results to return (default 10)
        include_components: Include component breakdown in results
        sort_by_activation: Sort results by activation (default True)

    """

    threshold: float = Field(default=0.3, description="Minimum activation threshold for retrieval")
    max_results: int = Field(default=10, ge=1, description="Maximum number of results to return")
    include_components: bool = Field(
        default=False,
        description="Include activation component breakdown",
    )
    sort_by_activation: bool = Field(default=True, description="Sort results by activation score")


class RetrievalResult(BaseModel):
    """Result from activation-based retrieval.

    Attributes:
        chunk_id: Unique identifier for the chunk
        activation: Total activation score
        components: Optional breakdown of activation components
        rank: Result rank (1-indexed)

    """

    chunk_id: ChunkID = Field(description="Chunk identifier")
    activation: float = Field(description="Total activation score")
    components: ActivationComponents | None = Field(
        default=None,
        description="Activation component breakdown",
    )
    rank: int = Field(default=0, ge=0, description="Result rank (1-indexed)")

    class Config:
        frozen = False  # Allow rank updates


class ActivationRetriever:
    """Retrieves chunks based on ACT-R activation scores.

    This retriever calculates activation for candidate chunks and returns
    those above a threshold, sorted by activation. It integrates with the
    ActivationEngine to compute full ACT-R activation.

    Examples:
        >>> from aurora_core.activation import ActivationEngine
        >>>
        >>> engine = ActivationEngine()
        >>> retriever = ActivationRetriever(engine)
        >>>
        >>> # Retrieve chunks
        >>> results = retriever.retrieve(
        ...     candidates=candidate_chunks,
        ...     query_keywords={'database', 'optimize'},
        ...     spreading_scores={'chunk_1': 0.5, 'chunk_2': 0.3},
        ...     threshold=0.3,
        ...     max_results=5
        ... )
        >>>
        >>> for result in results:
        ...     print(f"{result.rank}. {result.chunk_id}: {result.activation:.3f}")

    """

    def __init__(self, engine: ActivationEngine, config: RetrievalConfig | None = None):
        """Initialize the activation retriever.

        Args:
            engine: ActivationEngine for calculating activation
            config: Configuration for retrieval (uses defaults if None)

        """
        self.engine = engine
        self.config = config or RetrievalConfig()

    def retrieve(
        self,
        candidates: list[ChunkData],
        query_keywords: set[str] | None = None,
        spreading_scores: dict[ChunkID, float] | None = None,
        threshold: float | None = None,
        max_results: int | None = None,
        current_time: datetime | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve chunks based on activation scores.

        Args:
            candidates: List of candidate chunks to consider
            query_keywords: Keywords from the query for context boost
            spreading_scores: Pre-calculated spreading activation scores
            threshold: Override default activation threshold
            max_results: Override default max results
            current_time: Current time for calculations (defaults to now)

        Returns:
            List of RetrievalResult objects, sorted by activation

        Notes:
            - Only chunks above threshold are returned
            - Results are sorted by activation (highest first)
            - Rank is 1-indexed

        """
        if threshold is None:
            threshold = self.config.threshold
        if max_results is None:
            max_results = self.config.max_results
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        if spreading_scores is None:
            spreading_scores = {}

        # Calculate activation for all candidates
        results: list[RetrievalResult] = []

        for chunk in candidates:
            # Get spreading activation for this chunk
            spreading = spreading_scores.get(chunk.id, 0.0)

            # Calculate total activation
            activation = self.engine.calculate_total(
                access_history=chunk.access_history,
                last_access=chunk.last_access,
                spreading_activation=spreading,
                query_keywords=query_keywords,
                chunk_keywords=chunk.keywords,
                current_time=current_time,
            )

            # Filter by threshold
            if activation.total >= threshold:
                result = RetrievalResult(
                    chunk_id=chunk.id,
                    activation=activation.total,
                    components=activation if self.config.include_components else None,
                )
                results.append(result)

        # Sort by activation if enabled
        if self.config.sort_by_activation:
            results.sort(key=lambda r: r.activation, reverse=True)

        # Limit to max_results
        results = results[:max_results]

        # Assign ranks
        for i, result in enumerate(results, start=1):
            result.rank = i

        return results

    def retrieve_with_graph(
        self,
        candidates: list[ChunkData],
        query_keywords: set[str] | None = None,
        source_chunks: list[ChunkID] | None = None,
        relationship_graph: RelationshipGraph | None = None,
        threshold: float | None = None,
        max_results: int | None = None,
        current_time: datetime | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve chunks with automatic spreading activation calculation.

        This is a convenience method that calculates spreading activation
        from the relationship graph before retrieval.

        Args:
            candidates: List of candidate chunks
            query_keywords: Keywords from the query
            source_chunks: Starting chunks for spreading activation
            relationship_graph: Graph of chunk relationships
            threshold: Override default threshold
            max_results: Override default max results
            current_time: Current time for calculations

        Returns:
            List of RetrievalResult objects

        Notes:
            - If source_chunks is None, no spreading is calculated
            - If relationship_graph is None, no spreading is calculated

        """
        spreading_scores = {}

        # Calculate spreading activation if we have the necessary data
        if source_chunks and relationship_graph:
            # Convert ChunkIDs to strings for spreading calculation
            source_chunk_strs: list[str] = [str(chunk_id) for chunk_id in source_chunks]
            raw_scores = self.engine.calculate_spreading_only(
                source_chunks=source_chunk_strs,
                graph=relationship_graph,
                bidirectional=True,
            )
            # Convert back to ChunkID keys
            spreading_scores = {ChunkID(k): v for k, v in raw_scores.items()}

        return self.retrieve(
            candidates=candidates,
            query_keywords=query_keywords,
            spreading_scores=spreading_scores,
            threshold=threshold,
            max_results=max_results,
            current_time=current_time,
        )

    def retrieve_top_n(
        self,
        candidates: list[ChunkData],
        query_keywords: set[str] | None = None,
        spreading_scores: dict[ChunkID, float] | None = None,
        n: int = 10,
        current_time: datetime | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve top N chunks by activation (no threshold filtering).

        Args:
            candidates: List of candidate chunks
            query_keywords: Keywords from the query
            spreading_scores: Pre-calculated spreading scores
            n: Number of results to return
            current_time: Current time for calculations

        Returns:
            Top N chunks by activation score

        """
        return self.retrieve(
            candidates=candidates,
            query_keywords=query_keywords,
            spreading_scores=spreading_scores,
            threshold=-float("inf"),  # No threshold filtering
            max_results=n,
            current_time=current_time,
        )

    def calculate_activations(
        self,
        candidates: list[ChunkData],
        query_keywords: set[str] | None = None,
        spreading_scores: dict[ChunkID, float] | None = None,
        current_time: datetime | None = None,
    ) -> dict[ChunkID, ActivationComponents]:
        """Calculate activation for all candidates without filtering.

        Useful for debugging and analysis.

        Args:
            candidates: List of candidate chunks
            query_keywords: Keywords from the query
            spreading_scores: Pre-calculated spreading scores
            current_time: Current time for calculations

        Returns:
            Dictionary mapping chunk_id -> ActivationComponents

        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        if spreading_scores is None:
            spreading_scores = {}

        activations = {}

        for chunk in candidates:
            spreading = spreading_scores.get(chunk.id, 0.0)

            activation = self.engine.calculate_total(
                access_history=chunk.access_history,
                last_access=chunk.last_access,
                spreading_activation=spreading,
                query_keywords=query_keywords,
                chunk_keywords=chunk.keywords,
                current_time=current_time,
            )

            activations[chunk.id] = activation

        return activations

    def explain_retrieval(
        self,
        chunk: ChunkData,
        query_keywords: set[str] | None = None,
        spreading_score: float = 0.0,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Explain why a chunk was or wasn't retrieved.

        Args:
            chunk: Chunk to explain
            query_keywords: Keywords from the query
            spreading_score: Spreading activation score
            current_time: Current time for calculations

        Returns:
            Dictionary with detailed explanation:
                - chunk_id: Chunk identifier
                - activation: Total activation
                - components: Component breakdown
                - above_threshold: Whether above retrieval threshold
                - threshold: Current threshold value
                - explanation: Human-readable explanation

        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        explanation = self.engine.explain_activation(
            access_history=chunk.access_history,
            last_access=chunk.last_access,
            spreading_activation=spreading_score,
            query_keywords=query_keywords,
            chunk_keywords=chunk.keywords,
            current_time=current_time,
        )

        total_activation = explanation["components"]["total"]
        above_threshold = total_activation >= self.config.threshold

        # Generate human-readable explanation
        if above_threshold:
            reason = f"Chunk retrieved (activation {total_activation:.3f} ≥ threshold {self.config.threshold:.3f})"
        else:
            reason = f"Chunk filtered out (activation {total_activation:.3f} < threshold {self.config.threshold:.3f})"

        return {
            "chunk_id": chunk.id,
            "activation": total_activation,
            "components": explanation["components"],
            "above_threshold": above_threshold,
            "threshold": self.config.threshold,
            "explanation": reason,
            "details": explanation,
        }


class BatchRetriever:
    """Retrieves chunks in batches for better performance.

    This retriever processes chunks in batches to optimize database
    queries and reduce overhead for large-scale retrieval.
    """

    def __init__(
        self,
        engine: ActivationEngine,
        config: RetrievalConfig | None = None,
        batch_size: int = 100,
    ):
        """Initialize the batch retriever.

        Args:
            engine: ActivationEngine for calculations
            config: Retrieval configuration
            batch_size: Number of chunks to process per batch

        """
        self.retriever = ActivationRetriever(engine, config)
        self.batch_size = batch_size

    def retrieve_batched(
        self,
        candidates: list[ChunkData],
        query_keywords: set[str] | None = None,
        spreading_scores: dict[ChunkID, float] | None = None,
        threshold: float | None = None,
        max_results: int | None = None,
        current_time: datetime | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve chunks in batches.

        Args:
            candidates: List of all candidate chunks
            query_keywords: Keywords from the query
            spreading_scores: Pre-calculated spreading scores
            threshold: Override default threshold
            max_results: Override default max results
            current_time: Current time for calculations

        Returns:
            Combined results from all batches, sorted by activation

        """
        all_results: list[RetrievalResult] = []

        # Process in batches
        for i in range(0, len(candidates), self.batch_size):
            batch = candidates[i : i + self.batch_size]

            batch_results = self.retriever.retrieve(
                candidates=batch,
                query_keywords=query_keywords,
                spreading_scores=spreading_scores,
                threshold=threshold,
                max_results=max_results,
                current_time=current_time,
            )

            all_results.extend(batch_results)

        # Sort all results by activation
        if self.retriever.config.sort_by_activation:
            all_results.sort(key=lambda r: r.activation, reverse=True)

        # Limit to max_results
        if max_results is None:
            max_results = self.retriever.config.max_results
        all_results = all_results[:max_results]

        # Reassign ranks
        for i, result in enumerate(all_results, start=1):
            result.rank = i

        return all_results


__all__ = [
    "ChunkData",
    "RetrievalConfig",
    "RetrievalResult",
    "ActivationRetriever",
    "BatchRetriever",
]
