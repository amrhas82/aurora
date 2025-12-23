"""
Unit tests for Spreading Activation.

Tests the ACT-R spreading activation calculation including:
- Relationship graph construction and traversal
- BFS-based activation propagation
- Distance-based decay (spread_factor^hop_count)
- Weight-based spreading (stronger relationships contribute more)
- Edge cases (cycles, max_hops, max_edges, bidirectional spreading)
"""


import pytest

from aurora_core.activation.spreading import (
    Relationship,
    RelationshipGraph,
    SpreadingActivation,
    SpreadingConfig,
    calculate_spreading,
)


class TestRelationship:
    """Test Relationship model."""

    def test_create_relationship_minimal(self):
        """Test creating relationship with minimal required fields."""
        rel = Relationship(
            from_chunk="func_a",
            to_chunk="func_b",
            rel_type="calls"
        )
        assert rel.from_chunk == "func_a"
        assert rel.to_chunk == "func_b"
        assert rel.rel_type == "calls"
        assert rel.weight == 1.0  # default

    def test_create_relationship_with_weight(self):
        """Test creating relationship with custom weight."""
        rel = Relationship(
            from_chunk="func_a",
            to_chunk="func_b",
            rel_type="depends_on",
            weight=0.75
        )
        assert rel.weight == 0.75

    def test_weight_validation_valid_range(self):
        """Test weight must be between 0.0 and 1.0."""
        # Valid weights
        Relationship(from_chunk="a", to_chunk="b", rel_type="test", weight=0.0)
        Relationship(from_chunk="a", to_chunk="b", rel_type="test", weight=0.5)
        Relationship(from_chunk="a", to_chunk="b", rel_type="test", weight=1.0)

    def test_weight_validation_negative(self):
        """Test weight cannot be negative."""
        with pytest.raises(Exception):  # Pydantic validation error
            Relationship(
                from_chunk="a",
                to_chunk="b",
                rel_type="test",
                weight=-0.1
            )

    def test_weight_validation_above_one(self):
        """Test weight cannot exceed 1.0."""
        with pytest.raises(Exception):  # Pydantic validation error
            Relationship(
                from_chunk="a",
                to_chunk="b",
                rel_type="test",
                weight=1.5
            )

    def test_relationship_types(self):
        """Test different relationship types are supported."""
        types = ["calls", "imports", "depends_on", "inherits", "uses"]
        for rel_type in types:
            rel = Relationship(
                from_chunk="a",
                to_chunk="b",
                rel_type=rel_type
            )
            assert rel.rel_type == rel_type


class TestSpreadingConfig:
    """Test SpreadingConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SpreadingConfig()
        assert config.spread_factor == 0.7
        assert config.max_hops == 3
        assert config.max_edges == 1000
        assert config.min_weight == 0.1

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SpreadingConfig(
            spread_factor=0.5,
            max_hops=2,
            max_edges=500,
            min_weight=0.2
        )
        assert config.spread_factor == 0.5
        assert config.max_hops == 2
        assert config.max_edges == 500
        assert config.min_weight == 0.2

    def test_spread_factor_validation(self):
        """Test spread_factor must be between 0.0 and 1.0."""
        # Valid values
        SpreadingConfig(spread_factor=0.0)
        SpreadingConfig(spread_factor=0.5)
        SpreadingConfig(spread_factor=1.0)

        # Invalid values
        with pytest.raises(Exception):
            SpreadingConfig(spread_factor=-0.1)
        with pytest.raises(Exception):
            SpreadingConfig(spread_factor=1.5)

    def test_max_hops_validation(self):
        """Test max_hops must be between 1 and 5."""
        # Valid values
        SpreadingConfig(max_hops=1)
        SpreadingConfig(max_hops=3)
        SpreadingConfig(max_hops=5)

        # Invalid values
        with pytest.raises(Exception):
            SpreadingConfig(max_hops=0)
        with pytest.raises(Exception):
            SpreadingConfig(max_hops=6)

    def test_max_edges_validation(self):
        """Test max_edges must be at least 1."""
        # Valid values
        SpreadingConfig(max_edges=1)
        SpreadingConfig(max_edges=1000)

        # Invalid values
        with pytest.raises(Exception):
            SpreadingConfig(max_edges=0)

    def test_min_weight_validation(self):
        """Test min_weight must be between 0.0 and 1.0."""
        # Valid values
        SpreadingConfig(min_weight=0.0)
        SpreadingConfig(min_weight=0.5)
        SpreadingConfig(min_weight=1.0)

        # Invalid values
        with pytest.raises(Exception):
            SpreadingConfig(min_weight=-0.1)
        with pytest.raises(Exception):
            SpreadingConfig(min_weight=1.5)


class TestRelationshipGraph:
    """Test RelationshipGraph construction and operations."""

    def test_empty_graph(self):
        """Test empty graph initialization."""
        graph = RelationshipGraph()
        assert graph.chunk_count() == 0
        assert graph.edge_count() == 0

    def test_add_single_relationship(self):
        """Test adding a single relationship."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        assert graph.edge_count() == 1
        assert graph.chunk_count() == 2

        # Check outgoing edge
        outgoing = graph.get_outgoing("a")
        assert len(outgoing) == 1
        assert outgoing[0] == ("b", "calls", 1.0)

        # Check incoming edge
        incoming = graph.get_incoming("b")
        assert len(incoming) == 1
        assert incoming[0] == ("a", "calls", 1.0)

    def test_add_multiple_relationships(self):
        """Test adding multiple relationships."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 0.8)
        graph.add_relationship("a", "c", "depends_on", 0.6)

        assert graph.edge_count() == 3
        assert graph.chunk_count() == 3

    def test_get_outgoing_no_edges(self):
        """Test get_outgoing for chunk with no outgoing edges."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        # Chunk 'b' has no outgoing edges
        outgoing = graph.get_outgoing("b")
        assert len(outgoing) == 0

    def test_get_incoming_no_edges(self):
        """Test get_incoming for chunk with no incoming edges."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        # Chunk 'a' has no incoming edges
        incoming = graph.get_incoming("a")
        assert len(incoming) == 0

    def test_multiple_outgoing_edges(self):
        """Test chunk with multiple outgoing edges."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("a", "c", "calls", 0.8)
        graph.add_relationship("a", "d", "depends_on", 0.6)

        outgoing = graph.get_outgoing("a")
        assert len(outgoing) == 3

    def test_multiple_incoming_edges(self):
        """Test chunk with multiple incoming edges."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "d", "calls", 1.0)
        graph.add_relationship("b", "d", "calls", 0.8)
        graph.add_relationship("c", "d", "depends_on", 0.6)

        incoming = graph.get_incoming("d")
        assert len(incoming) == 3

    def test_bidirectional_relationships(self):
        """Test that relationships can be bidirectional (separate edges)."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "a", "calls", 0.8)

        assert graph.edge_count() == 2

        # a -> b
        outgoing_a = graph.get_outgoing("a")
        assert len(outgoing_a) == 1
        assert outgoing_a[0][0] == "b"

        # b -> a
        outgoing_b = graph.get_outgoing("b")
        assert len(outgoing_b) == 1
        assert outgoing_b[0][0] == "a"

    def test_clear_graph(self):
        """Test clearing all relationships."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 0.8)

        assert graph.edge_count() == 2

        graph.clear()

        assert graph.edge_count() == 0
        assert graph.chunk_count() == 0
        assert len(graph.get_outgoing("a")) == 0

    def test_self_loop(self):
        """Test that self-loops are allowed in the graph."""
        graph = RelationshipGraph()
        graph.add_relationship("a", "a", "calls", 1.0)

        assert graph.edge_count() == 1
        outgoing = graph.get_outgoing("a")
        assert outgoing[0][0] == "a"


class TestSpreadingActivation:
    """Test SpreadingActivation calculation."""

    def test_no_relationships(self):
        """Test spreading with no relationships returns empty dict."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        activations = spreading.calculate(["a"], graph)
        assert activations == {}

    def test_single_hop_spreading(self):
        """Test spreading activation across single hop."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # b should receive: 1.0 * 0.7^1 = 0.7
        assert "b" in activations
        assert activations["b"] == pytest.approx(0.7, abs=0.001)

        # Source chunk 'a' should not be in activations
        assert "a" not in activations

    def test_two_hop_spreading(self):
        """Test spreading activation across two hops."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)

        # Use unidirectional to avoid backflow from c to b
        activations = spreading.calculate(["a"], graph, bidirectional=False)

        # b receives: 1.0 * 0.7^1 = 0.7
        assert activations["b"] == pytest.approx(0.7, abs=0.001)

        # c receives: 1.0 * 0.7^2 = 0.49
        assert activations["c"] == pytest.approx(0.49, abs=0.001)

    def test_three_hop_spreading(self):
        """Test spreading activation across three hops (max default)."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)
        graph.add_relationship("c", "d", "calls", 1.0)

        # Use unidirectional to avoid backflow
        activations = spreading.calculate(["a"], graph, bidirectional=False)

        # b receives: 1.0 * 0.7^1 = 0.7
        assert activations["b"] == pytest.approx(0.7, abs=0.001)

        # c receives: 1.0 * 0.7^2 = 0.49
        assert activations["c"] == pytest.approx(0.49, abs=0.001)

        # d receives: 1.0 * 0.7^3 = 0.343
        assert activations["d"] == pytest.approx(0.343, abs=0.001)

    def test_max_hops_limits_spreading(self):
        """Test that max_hops parameter limits spreading depth."""
        config = SpreadingConfig(max_hops=2)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)
        graph.add_relationship("c", "d", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # Only b and c should receive activation (max 2 hops)
        assert "b" in activations
        assert "c" in activations
        assert "d" not in activations

    def test_weight_affects_spreading(self):
        """Test that relationship weight affects spreading amount."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Strong relationship
        graph.add_relationship("a", "b", "calls", 1.0)

        # Weak relationship
        graph.add_relationship("a", "c", "calls", 0.5)

        activations = spreading.calculate(["a"], graph)

        # b receives: 1.0 * 0.7 = 0.7
        assert activations["b"] == pytest.approx(0.7, abs=0.001)

        # c receives: 0.5 * 0.7 = 0.35
        assert activations["c"] == pytest.approx(0.35, abs=0.001)

    def test_multiple_paths_accumulate(self):
        """Test that multiple paths to same chunk accumulate activation."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Two paths to 'c': a->b->c and a->c
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)
        graph.add_relationship("a", "c", "depends_on", 0.8)

        activations = spreading.calculate(["a"], graph)

        # c receives:
        # - Direct: 0.8 * 0.7^1 = 0.56
        # - Via b: 1.0 * 0.7^2 = 0.49
        # - Total: 0.56 + 0.49 = 1.05
        expected = 0.56 + 0.49
        assert activations["c"] == pytest.approx(expected, abs=0.001)

    def test_multiple_source_chunks(self):
        """Test spreading from multiple source chunks."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "c", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)

        activations = spreading.calculate(["a", "b"], graph)

        # c receives activation from both a and b
        # - From a: 1.0 * 0.7 = 0.7
        # - From b: 1.0 * 0.7 = 0.7
        # - Total: 1.4
        assert activations["c"] == pytest.approx(1.4, abs=0.001)

    def test_source_chunks_not_in_result(self):
        """Test that source chunks don't receive spreading activation."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "a", "calls", 1.0)  # Cycle back

        activations = spreading.calculate(["a"], graph)

        # Only b should be in result, not a
        assert "a" not in activations
        assert "b" in activations

    def test_bidirectional_spreading(self):
        """Test bidirectional spreading follows both incoming and outgoing edges."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # a -> b (outgoing)
        graph.add_relationship("a", "b", "calls", 1.0)

        # c -> a (incoming to a)
        graph.add_relationship("c", "a", "calls", 1.0)

        # With bidirectional=True, both b and c should receive activation
        activations = spreading.calculate(["a"], graph, bidirectional=True)

        assert "b" in activations  # via outgoing
        assert "c" in activations  # via incoming

    def test_unidirectional_spreading(self):
        """Test unidirectional spreading only follows outgoing edges."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # a -> b (outgoing)
        graph.add_relationship("a", "b", "calls", 1.0)

        # c -> a (incoming to a)
        graph.add_relationship("c", "a", "calls", 1.0)

        # With bidirectional=False, only b should receive activation
        activations = spreading.calculate(["a"], graph, bidirectional=False)

        assert "b" in activations  # via outgoing
        assert "c" not in activations  # incoming ignored

    def test_min_weight_threshold(self):
        """Test that relationships below min_weight are ignored."""
        config = SpreadingConfig(min_weight=0.5)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        # Strong relationship (above threshold)
        graph.add_relationship("a", "b", "calls", 0.8)

        # Weak relationship (below threshold)
        graph.add_relationship("a", "c", "calls", 0.3)

        activations = spreading.calculate(["a"], graph)

        # b should receive activation, c should not
        assert "b" in activations
        assert "c" not in activations

    def test_max_edges_limit(self):
        """Test that max_edges parameter prevents runaway spreading."""
        config = SpreadingConfig(max_edges=2)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        # Create a graph with many edges
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("a", "c", "calls", 1.0)
        graph.add_relationship("a", "d", "calls", 1.0)
        graph.add_relationship("b", "e", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # Only 2 edges should be traversed
        # The exact chunks depend on BFS order, but total should be limited
        total_chunks = len(activations)
        assert total_chunks <= 3  # At most 2 edges + source spreading

    def test_cycle_handling(self):
        """Test that cycles don't cause infinite loops."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Create a cycle: a -> b -> c -> a
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)
        graph.add_relationship("c", "a", "calls", 1.0)

        # Should not hang or crash
        activations = spreading.calculate(["a"], graph)

        # b and c should receive activation, a should not (source)
        assert "b" in activations
        assert "c" in activations
        assert "a" not in activations

    def test_self_loop_ignored(self):
        """Test that self-loops don't cause spreading to self."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Self-loop
        graph.add_relationship("a", "a", "calls", 1.0)

        # Other relationship
        graph.add_relationship("a", "b", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # a should not receive its own activation
        assert "a" not in activations

        # b should receive activation
        assert "b" in activations

    def test_custom_spread_factor(self):
        """Test that custom spread_factor affects decay rate."""
        # Higher spread factor (slower decay)
        config_high = SpreadingConfig(spread_factor=0.9)
        spreading_high = SpreadingActivation(config_high)

        # Lower spread factor (faster decay)
        config_low = SpreadingConfig(spread_factor=0.5)
        spreading_low = SpreadingActivation(config_low)

        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        activations_high = spreading_high.calculate(["a"], graph)
        activations_low = spreading_low.calculate(["a"], graph)

        # Higher spread factor should result in higher activation
        assert activations_high["b"] > activations_low["b"]

    def test_complex_graph(self):
        """Test spreading in a complex graph with multiple patterns."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Build a realistic call graph
        # main -> auth, data, ui
        graph.add_relationship("main", "auth", "calls", 1.0)
        graph.add_relationship("main", "data", "calls", 0.9)
        graph.add_relationship("main", "ui", "calls", 0.8)

        # auth -> validate, token
        graph.add_relationship("auth", "validate", "calls", 1.0)
        graph.add_relationship("auth", "token", "calls", 0.9)

        # data -> db, cache
        graph.add_relationship("data", "db", "calls", 1.0)
        graph.add_relationship("data", "cache", "calls", 0.8)

        # Calculate spreading from main (unidirectional)
        activations = spreading.calculate(["main"], graph, bidirectional=False)

        # Direct connections (1 hop)
        assert activations["auth"] == pytest.approx(1.0 * 0.7, abs=0.001)
        assert activations["data"] == pytest.approx(0.9 * 0.7, abs=0.001)
        assert activations["ui"] == pytest.approx(0.8 * 0.7, abs=0.001)

        # Two-hop connections
        # validate: main->auth (1.0*0.7) then auth->validate (1.0*0.7) = 1.0 * 0.49
        assert activations["validate"] == pytest.approx(1.0 * 0.49, abs=0.001)
        # token: main->auth (1.0*0.7) then auth->token (0.9*0.7) = 0.9 * 0.49
        assert activations["token"] == pytest.approx(0.9 * 0.49, abs=0.001)
        # db: main->data (0.9*0.7) then data->db (1.0*0.7) = 1.0 * 0.49
        assert activations["db"] == pytest.approx(1.0 * 0.49, abs=0.001)


class TestSpreadingActivationConvenienceMethods:
    """Test convenience methods of SpreadingActivation."""

    def test_calculate_from_relationships(self):
        """Test convenience method that takes Relationship list."""
        spreading = SpreadingActivation()

        relationships = [
            Relationship(from_chunk="a", to_chunk="b", rel_type="calls", weight=1.0),
            Relationship(from_chunk="b", to_chunk="c", rel_type="calls", weight=0.8),
        ]

        activations = spreading.calculate_from_relationships(["a"], relationships)

        # Verify spreading works
        assert "b" in activations
        assert "c" in activations

    def test_get_related_chunks(self):
        """Test get_related_chunks returns sorted list."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("a", "c", "calls", 0.5)
        graph.add_relationship("a", "d", "calls", 0.8)

        related = spreading.get_related_chunks(["a"], graph)

        # Should be sorted by activation (descending)
        assert len(related) == 3
        assert related[0][0] == "b"  # highest activation
        assert related[1][0] == "d"  # middle activation
        assert related[2][0] == "c"  # lowest activation

        # Verify it's list of tuples (chunk_id, activation)
        for chunk_id, activation in related:
            assert isinstance(chunk_id, str)
            assert isinstance(activation, float)

    def test_get_related_chunks_with_threshold(self):
        """Test get_related_chunks filters by minimum activation."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        graph.add_relationship("a", "b", "calls", 1.0)  # 0.7 activation
        graph.add_relationship("a", "c", "calls", 0.5)  # 0.35 activation

        # Filter with threshold
        related = spreading.get_related_chunks(["a"], graph, min_activation=0.5)

        # Only b should pass the threshold
        assert len(related) == 1
        assert related[0][0] == "b"

    def test_get_related_chunks_empty_graph(self):
        """Test get_related_chunks with empty graph returns empty list."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        related = spreading.get_related_chunks(["a"], graph)
        assert related == []


class TestCalculateSpreadingFunction:
    """Test standalone calculate_spreading function."""

    def test_calculate_spreading_with_defaults(self):
        """Test standalone function with default parameters."""
        relationships = [
            Relationship(from_chunk="a", to_chunk="b", rel_type="calls", weight=1.0),
            Relationship(from_chunk="b", to_chunk="c", rel_type="calls", weight=1.0),
        ]

        activations = calculate_spreading(["a"], relationships)

        assert "b" in activations
        assert "c" in activations

    def test_calculate_spreading_with_custom_params(self):
        """Test standalone function with custom spread_factor and max_hops."""
        relationships = [
            Relationship(from_chunk="a", to_chunk="b", rel_type="calls", weight=1.0),
            Relationship(from_chunk="b", to_chunk="c", rel_type="calls", weight=1.0),
        ]

        activations = calculate_spreading(
            ["a"],
            relationships,
            spread_factor=0.5,
            max_hops=1
        )

        # Only b should receive activation (max_hops=1)
        assert "b" in activations
        assert "c" not in activations

        # b should receive 1.0 * 0.5^1 = 0.5
        assert activations["b"] == pytest.approx(0.5, abs=0.001)


class TestACTRSpreadingFormula:
    """Test that implementation matches ACT-R spreading activation literature."""

    def test_actr_single_hop_formula(self):
        """Test against ACT-R formula: spreading = weight × spread_factor^hop."""
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # Expected: 1.0 × 0.7^1 = 0.7
        expected = 1.0 * (0.7 ** 1)
        assert activations["b"] == pytest.approx(expected, abs=0.001)

    def test_actr_two_hop_formula(self):
        """Test against ACT-R formula for two-hop spreading."""
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 0.8)

        activations = spreading.calculate(["a"], graph)

        # Expected for c: 0.8 × 0.7^2 = 0.392
        expected = 0.8 * (0.7 ** 2)
        assert activations["c"] == pytest.approx(expected, abs=0.001)

    def test_actr_multiple_paths_accumulation(self):
        """Test ACT-R principle: multiple paths accumulate additively."""
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()

        # Two paths to 'd': a->b->d and a->c->d
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("a", "c", "calls", 1.0)
        graph.add_relationship("b", "d", "calls", 0.9)
        graph.add_relationship("c", "d", "calls", 0.8)

        activations = spreading.calculate(["a"], graph)

        # Path 1: a->b->d = 0.9 × 0.7^2 = 0.441
        # Path 2: a->c->d = 0.8 × 0.7^2 = 0.392
        # Total: 0.441 + 0.392 = 0.833
        path1 = 0.9 * (0.7 ** 2)
        path2 = 0.8 * (0.7 ** 2)
        expected = path1 + path2

        assert activations["d"] == pytest.approx(expected, abs=0.001)

    def test_actr_distance_decay_principle(self):
        """Test ACT-R principle: activation decays exponentially with distance."""
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()

        # Linear chain: a -> b -> c -> d
        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)
        graph.add_relationship("c", "d", "calls", 1.0)

        # Use unidirectional to avoid backflow
        activations = spreading.calculate(["a"], graph, bidirectional=False)

        # Verify exponential decay
        activation_b = activations["b"]  # 0.7^1
        activation_c = activations["c"]  # 0.7^2
        activation_d = activations["d"]  # 0.7^3

        # Each hop should multiply by spread_factor
        assert activation_c == pytest.approx(activation_b * 0.7, abs=0.001)
        assert activation_d == pytest.approx(activation_c * 0.7, abs=0.001)

    def test_actr_relationship_strength_principle(self):
        """Test ACT-R principle: stronger relationships contribute more activation."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Strong relationship
        graph.add_relationship("a", "b", "calls", 1.0)

        # Weak relationship
        graph.add_relationship("a", "c", "calls", 0.3)

        activations = spreading.calculate(["a"], graph)

        # Strong relationship should contribute more
        assert activations["b"] > activations["c"]

        # Ratio should match weight ratio
        ratio = activations["b"] / activations["c"]
        expected_ratio = 1.0 / 0.3
        assert ratio == pytest.approx(expected_ratio, abs=0.01)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_source_list(self):
        """Test spreading with empty source list."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        activations = spreading.calculate([], graph)
        assert activations == {}

    def test_source_not_in_graph(self):
        """Test spreading from chunk not in graph."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()
        graph.add_relationship("a", "b", "calls", 1.0)

        # Source 'x' not in graph
        activations = spreading.calculate(["x"], graph)
        assert activations == {}

    def test_disconnected_components(self):
        """Test graph with disconnected components."""
        spreading = SpreadingActivation()
        graph = RelationshipGraph()

        # Component 1: a -> b
        graph.add_relationship("a", "b", "calls", 1.0)

        # Component 2: c -> d (disconnected)
        graph.add_relationship("c", "d", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # Only component 1 should receive activation
        assert "b" in activations
        assert "c" not in activations
        assert "d" not in activations

    def test_very_large_graph(self):
        """Test spreading in a very large graph respects max_edges."""
        config = SpreadingConfig(max_edges=50)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        # Create a large graph (100 nodes)
        for i in range(99):
            graph.add_relationship(f"node_{i}", f"node_{i+1}", "calls", 1.0)

        # Should stop after max_edges
        activations = spreading.calculate(["node_0"], graph)

        # Should have visited at most 50 edges
        assert len(activations) <= 50

    def test_zero_spread_factor(self):
        """Test spreading with spread_factor=0 (no spreading beyond 1 hop)."""
        config = SpreadingConfig(spread_factor=0.0)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)

        activations = spreading.calculate(["a"], graph)

        # b should receive 0 activation (1.0 * 0.0 = 0.0)
        # c should also receive 0 activation
        # Both should still be in result but with 0 activation
        # Actually, with 0 spread factor, nothing spreads
        assert len(activations) == 0 or all(v == 0.0 for v in activations.values())

    def test_spread_factor_one(self):
        """Test spreading with spread_factor=1.0 (no decay)."""
        config = SpreadingConfig(spread_factor=1.0)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        graph.add_relationship("a", "b", "calls", 1.0)
        graph.add_relationship("b", "c", "calls", 1.0)

        # Use unidirectional to avoid backflow accumulation
        activations = spreading.calculate(["a"], graph, bidirectional=False)

        # No decay: b and c should both receive 1.0
        assert activations["b"] == pytest.approx(1.0, abs=0.001)
        assert activations["c"] == pytest.approx(1.0, abs=0.001)

    def test_all_weights_below_threshold(self):
        """Test when all relationships are below min_weight threshold."""
        config = SpreadingConfig(min_weight=0.9)
        spreading = SpreadingActivation(config)
        graph = RelationshipGraph()

        # All weights below threshold
        graph.add_relationship("a", "b", "calls", 0.5)
        graph.add_relationship("a", "c", "calls", 0.3)

        activations = spreading.calculate(["a"], graph)

        # Nothing should spread
        assert activations == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
