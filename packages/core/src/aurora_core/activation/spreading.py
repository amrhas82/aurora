"""Spreading Activation Implementation

This module implements spreading activation, a core component of ACT-R memory.
Spreading activation propagates activation along relationship edges in the
chunk network, allowing related chunks to receive activation boosts.

Spreading Activation Formula:
    Spreading = Σ (weight × spread_factor^hop_count)

Where:
    - weight: Relationship strength (0.0 to 1.0)
    - spread_factor: Decay per hop (default 0.7, ACT-R standard)
    - hop_count: Distance from source chunk (1, 2, or 3 hops max)

The formula ensures that:
1. Direct relationships contribute more than indirect ones
2. Activation decays exponentially with distance (0.7^1, 0.7^2, 0.7^3)
3. Multiple paths to the same chunk accumulate additively
4. Strong relationships (higher weight) contribute more activation

Reference:
    Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
    Oxford University Press. Chapter 4: Spreading Activation.
"""

from collections import defaultdict, deque

from pydantic import BaseModel, Field, field_validator


class Relationship(BaseModel):
    """Represents a relationship between two chunks.

    Attributes:
        from_chunk: Source chunk ID
        to_chunk: Target chunk ID
        rel_type: Type of relationship (e.g., "calls", "imports", "depends_on")
        weight: Strength of the relationship (0.0 to 1.0)

    """

    from_chunk: str = Field(description="Source chunk ID")
    to_chunk: str = Field(description="Target chunk ID")
    rel_type: str = Field(description="Type of relationship")
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relationship strength (0.0 to 1.0)",
    )

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """Ensure weight is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v


class SpreadingConfig(BaseModel):
    """Configuration for spreading activation calculation.

    Attributes:
        spread_factor: Decay factor per hop (default 0.7, ACT-R standard)
        max_hops: Maximum relationship traversal depth (default 3)
        max_edges: Maximum edges to traverse (prevents runaway spreading)
        min_weight: Minimum relationship weight to consider

    """

    spread_factor: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Decay factor per hop (standard ACT-R value is 0.7)",
    )
    max_hops: int = Field(default=3, ge=1, le=5, description="Maximum relationship traversal depth")
    max_edges: int = Field(
        default=1000,
        ge=1,
        description="Maximum edges to traverse (prevents infinite loops)",
    )
    min_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum relationship weight to consider",
    )


class RelationshipGraph:
    """Represents the relationship graph between chunks.

    This class provides efficient graph traversal for spreading activation.
    It uses an adjacency list representation and supports BFS traversal.
    """

    def __init__(self) -> None:
        """Initialize an empty relationship graph."""
        # Adjacency list: chunk_id -> [(target_id, rel_type, weight), ...]
        self._outgoing: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        self._incoming: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        self._edge_count = 0

    def add_relationship(
        self,
        from_chunk: str,
        to_chunk: str,
        rel_type: str,
        weight: float = 1.0,
    ) -> None:
        """Add a relationship to the graph.

        Args:
            from_chunk: Source chunk ID
            to_chunk: Target chunk ID
            rel_type: Type of relationship
            weight: Relationship strength (0.0 to 1.0)

        """
        # Add to outgoing edges
        self._outgoing[from_chunk].append((to_chunk, rel_type, weight))
        # Add to incoming edges (for bidirectional traversal)
        self._incoming[to_chunk].append((from_chunk, rel_type, weight))
        self._edge_count += 1

    def get_outgoing(self, chunk_id: str) -> list[tuple[str, str, float]]:
        """Get outgoing relationships from a chunk.

        Args:
            chunk_id: Source chunk ID

        Returns:
            List of (target_id, rel_type, weight) tuples

        """
        return self._outgoing.get(chunk_id, [])

    def get_incoming(self, chunk_id: str) -> list[tuple[str, str, float]]:
        """Get incoming relationships to a chunk.

        Args:
            chunk_id: Target chunk ID

        Returns:
            List of (source_id, rel_type, weight) tuples

        """
        return self._incoming.get(chunk_id, [])

    def chunk_count(self) -> int:
        """Get the number of chunks with relationships."""
        return len(set(self._outgoing.keys()) | set(self._incoming.keys()))

    def edge_count(self) -> int:
        """Get the total number of edges."""
        return self._edge_count

    def clear(self) -> None:
        """Clear all relationships."""
        self._outgoing.clear()
        self._incoming.clear()
        self._edge_count = 0


class SpreadingActivation:
    """Calculates spreading activation using BFS graph traversal.

    Spreading activation propagates from source chunks to related chunks,
    with activation decaying exponentially based on relationship distance.

    Examples:
        >>> spreading = SpreadingActivation()
        >>> graph = RelationshipGraph()
        >>> graph.add_relationship("func_a", "func_b", "calls", weight=1.0)
        >>> graph.add_relationship("func_b", "func_c", "calls", weight=0.8)
        >>>
        >>> # Calculate spreading from func_a
        >>> activations = spreading.calculate(
        ...     source_chunks=["func_a"],
        ...     graph=graph
        ... )
        >>> print(activations)  # {'func_b': 0.7, 'func_c': 0.392}

    """

    def __init__(self, config: SpreadingConfig | None = None):
        """Initialize the spreading activation calculator.

        Args:
            config: Configuration for spreading calculation (uses defaults if None)

        """
        self.config = config or SpreadingConfig()

    def calculate(
        self,
        source_chunks: list[str],
        graph: RelationshipGraph,
        bidirectional: bool = True,
    ) -> dict[str, float]:
        """Calculate spreading activation from source chunks.

        Uses BFS to traverse the relationship graph, accumulating activation
        as it spreads along edges. Activation decays exponentially with distance.

        Args:
            source_chunks: List of chunk IDs to start spreading from
            graph: Relationship graph to traverse
            bidirectional: If True, spread along both incoming and outgoing edges

        Returns:
            Dictionary mapping chunk_id -> spreading_activation_score

        Notes:
            - Source chunks themselves receive 0.0 spreading activation
            - Multiple paths accumulate additively
            - Traversal stops at max_hops or max_edges
            - Only relationships with weight >= min_weight are followed

        """
        # Track activation for each chunk
        activations: dict[str, float] = defaultdict(float)

        # Track visited edges to prevent infinite loops
        visited_edges: set[tuple[str, str]] = set()

        # BFS queue: (chunk_id, hop_count)
        queue: deque[tuple[str, int]] = deque()

        # Initialize queue with source chunks at hop 0
        visited_chunks: set[str] = set()
        for chunk_id in source_chunks:
            queue.append((chunk_id, 0))
            visited_chunks.add(chunk_id)

        edges_traversed = 0

        while queue and edges_traversed < self.config.max_edges:
            current_chunk, current_hop = queue.popleft()

            # Stop if we've reached max hops
            if current_hop >= self.config.max_hops:
                continue

            # Get relationships to traverse
            edges_to_traverse: list[tuple[str, str, float]] = []

            # Add outgoing edges
            edges_to_traverse.extend(graph.get_outgoing(current_chunk))

            # Add incoming edges if bidirectional
            if bidirectional:
                edges_to_traverse.extend(graph.get_incoming(current_chunk))

            # Process each edge
            for target_chunk, _rel_type, weight in edges_to_traverse:
                # Skip if edge already visited
                edge_key = (current_chunk, target_chunk)
                if edge_key in visited_edges:
                    continue

                # Skip if weight below threshold
                if weight < self.config.min_weight:
                    continue

                # Skip if target is a source chunk (no self-spreading)
                if target_chunk in source_chunks:
                    continue

                # Mark edge as visited
                visited_edges.add(edge_key)
                edges_traversed += 1

                # Calculate spreading activation for this hop
                # Formula: weight × spread_factor^hop_count
                hop_count = current_hop + 1
                spreading_amount = weight * (self.config.spread_factor**hop_count)

                # Accumulate activation
                activations[target_chunk] += spreading_amount

                # Add to queue for further spreading if not visited
                if target_chunk not in visited_chunks:
                    visited_chunks.add(target_chunk)
                    queue.append((target_chunk, hop_count))

                # Check if we've hit the edge limit
                if edges_traversed >= self.config.max_edges:
                    break

        return dict(activations)

    def calculate_from_relationships(
        self,
        source_chunks: list[str],
        relationships: list[Relationship],
        bidirectional: bool = True,
    ) -> dict[str, float]:
        """Convenience method to calculate spreading from a list of relationships.

        Builds a graph from the relationships and calculates spreading activation.

        Args:
            source_chunks: List of chunk IDs to start spreading from
            relationships: List of Relationship objects
            bidirectional: If True, spread along both directions

        Returns:
            Dictionary mapping chunk_id -> spreading_activation_score

        """
        # Build graph from relationships
        graph = RelationshipGraph()
        for rel in relationships:
            graph.add_relationship(rel.from_chunk, rel.to_chunk, rel.rel_type, rel.weight)

        return self.calculate(source_chunks, graph, bidirectional)

    def get_related_chunks(
        self,
        source_chunks: list[str],
        graph: RelationshipGraph,
        min_activation: float = 0.0,
        bidirectional: bool = True,
    ) -> list[tuple[str, float]]:
        """Get related chunks sorted by spreading activation.

        Args:
            source_chunks: List of chunk IDs to start spreading from
            graph: Relationship graph to traverse
            min_activation: Minimum activation threshold
            bidirectional: If True, spread along both directions

        Returns:
            List of (chunk_id, activation) tuples, sorted by activation (descending)

        """
        activations = self.calculate(source_chunks, graph, bidirectional)

        # Filter by minimum activation and sort
        filtered = [
            (chunk_id, activation)
            for chunk_id, activation in activations.items()
            if activation >= min_activation
        ]

        return sorted(filtered, key=lambda x: x[1], reverse=True)


def calculate_spreading(
    source_chunks: list[str],
    relationships: list[Relationship],
    spread_factor: float = 0.7,
    max_hops: int = 3,
) -> dict[str, float]:
    """Convenience function for calculating spreading activation.

    Args:
        source_chunks: List of chunk IDs to start spreading from
        relationships: List of Relationship objects
        spread_factor: Decay factor per hop (default 0.7)
        max_hops: Maximum traversal depth (default 3)

    Returns:
        Dictionary mapping chunk_id -> spreading_activation_score

    """
    config = SpreadingConfig(spread_factor=spread_factor, max_hops=max_hops)
    calculator = SpreadingActivation(config)
    return calculator.calculate_from_relationships(source_chunks, relationships)
