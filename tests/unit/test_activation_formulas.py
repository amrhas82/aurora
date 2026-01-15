"""
Pure unit tests for ACT-R activation formulas.

Tests core activation formula calculations including:
- Base-Level Activation (BLA) with power law decay
- Spreading Activation with multi-hop propagation
- Decay penalties with logarithmic time curves

These are pure unit tests: no I/O, no external dependencies, deterministic,
and focus on mathematical correctness and edge case handling.
"""

from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.base_level import (
    AccessHistoryEntry,
    BaseLevelActivation,
    BLAConfig,
    calculate_bla,
)
from aurora_core.activation.decay import DecayCalculator, DecayConfig
from aurora_core.activation.spreading import (
    Relationship,
    RelationshipGraph,
    SpreadingActivation,
    SpreadingConfig,
    calculate_spreading,
)


# ==============================================================================
# Base-Level Activation Tests
# ==============================================================================


def test_bla_empty_history_returns_default():
    """BLA with no access history returns default activation."""
    bla = BaseLevelActivation()
    result = bla.calculate([])

    assert result == bla.config.default_activation
    assert result == -5.0  # Default value


def test_bla_single_access_recent():
    """BLA with single recent access returns high activation."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)

    # Access 1 second ago
    history = [AccessHistoryEntry(timestamp=current_time - timedelta(seconds=1))]
    result = bla.calculate(history, current_time)

    # Should be high (power law sum ≈ 1.0, ln(1) = 0)
    assert result > -1.0
    assert result < 1.0


def test_bla_zero_time_delta_handled():
    """BLA handles zero or negative time delta (same timestamp as current_time)."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)

    # Access at exactly current_time (edge case)
    history = [AccessHistoryEntry(timestamp=current_time)]
    result = bla.calculate(history, current_time)

    # Should not crash and should return reasonable value
    assert result != float("inf")
    assert result != float("-inf")
    assert result > -10.0  # Above minimum


def test_bla_multiple_accesses_higher_than_single():
    """BLA with multiple accesses has higher activation than single access."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)

    # Single access 1 hour ago
    single_history = [AccessHistoryEntry(timestamp=current_time - timedelta(hours=1))]
    single_result = bla.calculate(single_history, current_time)

    # Multiple accesses (1 hour ago, 2 hours ago, 3 hours ago)
    multi_history = [
        AccessHistoryEntry(timestamp=current_time - timedelta(hours=1)),
        AccessHistoryEntry(timestamp=current_time - timedelta(hours=2)),
        AccessHistoryEntry(timestamp=current_time - timedelta(hours=3)),
    ]
    multi_result = bla.calculate(multi_history, current_time)

    # More accesses = higher activation (frequency effect)
    assert multi_result > single_result


def test_bla_recent_access_higher_than_old():
    """BLA with recent access has higher activation than old access."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)

    # Recent access (1 day ago)
    recent_history = [AccessHistoryEntry(timestamp=current_time - timedelta(days=1))]
    recent_result = bla.calculate(recent_history, current_time)

    # Old access (30 days ago)
    old_history = [AccessHistoryEntry(timestamp=current_time - timedelta(days=30))]
    old_result = bla.calculate(old_history, current_time)

    # Recent access = higher activation (recency effect)
    assert recent_result > old_result


def test_bla_decay_rate_effect():
    """BLA decay rate affects activation slope."""
    current_time = datetime.now(timezone.utc)
    history = [AccessHistoryEntry(timestamp=current_time - timedelta(days=7))]

    # Low decay rate (slower forgetting)
    low_decay = BaseLevelActivation(BLAConfig(decay_rate=0.3))
    low_result = low_decay.calculate(history, current_time)

    # High decay rate (faster forgetting)
    high_decay = BaseLevelActivation(BLAConfig(decay_rate=0.7))
    high_result = high_decay.calculate(history, current_time)

    # Higher decay rate = lower activation for same old access
    assert high_result < low_result


def test_bla_minimum_activation_clamp():
    """BLA clamps to minimum activation for very old accesses."""
    bla = BaseLevelActivation(BLAConfig(min_activation=-10.0))
    current_time = datetime.now(timezone.utc)

    # Very old access (1000 days ago)
    history = [AccessHistoryEntry(timestamp=current_time - timedelta(days=1000))]
    result = bla.calculate(history, current_time)

    # Should be at or above minimum (formula may not reach exact minimum)
    assert result >= -10.0
    assert result < -8.0  # Should be quite low for very old access


def test_bla_from_access_counts_approximation():
    """BLA approximation from access count matches expected range."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)
    last_access = current_time - timedelta(hours=1)  # Very recent

    # 10 accesses over last week
    result = bla.calculate_from_access_counts(
        access_count=10, last_access=last_access, current_time=current_time
    )

    # Should be reasonable value (recent + frequent accesses)
    # Note: approximation uses synthetic history with exponential spacing
    assert result > -4.0  # Within reasonable negative range
    assert result < 5.0  # Not unreasonably high
    assert result != bla.config.default_activation  # Should differ from default


def test_bla_from_access_counts_zero_count():
    """BLA approximation with zero access count returns default."""
    bla = BaseLevelActivation()
    current_time = datetime.now(timezone.utc)
    last_access = current_time - timedelta(days=1)

    result = bla.calculate_from_access_counts(
        access_count=0, last_access=last_access, current_time=current_time
    )

    assert result == bla.config.default_activation


def test_bla_convenience_function():
    """Convenience function calculate_bla works correctly."""
    current_time = datetime.now(timezone.utc)
    history = [
        AccessHistoryEntry(timestamp=current_time - timedelta(hours=1)),
        AccessHistoryEntry(timestamp=current_time - timedelta(hours=2)),
    ]

    result = calculate_bla(history, decay_rate=0.5, current_time=current_time)

    # Should match calculator with same config
    bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
    expected = bla.calculate(history, current_time)

    assert abs(result - expected) < 0.001  # Floating point tolerance


# ==============================================================================
# Spreading Activation Tests
# ==============================================================================


def test_spreading_empty_graph():
    """Spreading on empty graph returns empty dict."""
    spreading = SpreadingActivation()
    graph = RelationshipGraph()

    result = spreading.calculate(["chunk_a"], graph)

    assert result == {}


def test_spreading_no_outgoing_edges():
    """Spreading from chunk with no relationships returns empty dict."""
    spreading = SpreadingActivation()
    graph = RelationshipGraph()

    # No edges added
    result = spreading.calculate(["chunk_a"], graph)

    assert result == {}


def test_spreading_one_hop():
    """Spreading calculates correct activation for one-hop relationship."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
    graph = RelationshipGraph()

    # A -> B with weight 1.0
    graph.add_relationship("A", "B", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph)

    # B should get: 1.0 * 0.7^1 = 0.7
    assert "B" in result
    assert abs(result["B"] - 0.7) < 0.001


def test_spreading_two_hops():
    """Spreading calculates correct activation for two-hop chain."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
    graph = RelationshipGraph()

    # A -> B -> C (chain)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("B", "C", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph, bidirectional=False)  # Unidirectional

    # B gets: 1.0 * 0.7^1 = 0.7
    # C gets: 1.0 * 0.7^2 = 0.49
    assert abs(result["B"] - 0.7) < 0.001
    assert abs(result["C"] - 0.49) < 0.01


def test_spreading_multiple_paths_accumulate():
    """Spreading with multiple paths to same chunk accumulates."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
    graph = RelationshipGraph()

    # Diamond pattern: A -> B -> D, A -> C -> D
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("A", "C", "calls", weight=1.0)
    graph.add_relationship("B", "D", "calls", weight=1.0)
    graph.add_relationship("C", "D", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph)

    # D gets activation from two paths: 0.49 + 0.49 = 0.98
    expected_d = 2 * (0.7**2)  # Two paths, each 0.7^2
    assert abs(result["D"] - expected_d) < 0.01


def test_spreading_weight_affects_activation():
    """Relationship weight affects spreading activation amount."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
    graph = RelationshipGraph()

    # A -> B with strong weight (1.0)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    result_strong = spreading.calculate(["A"], graph)

    # A -> B with weak weight (0.3)
    graph.clear()
    graph.add_relationship("A", "B", "calls", weight=0.3)
    result_weak = spreading.calculate(["A"], graph)

    # Strong weight = higher activation
    assert result_strong["B"] > result_weak["B"]


def test_spreading_max_hops_limit():
    """Spreading respects max_hops limit."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7, max_hops=2))
    graph = RelationshipGraph()

    # Chain: A -> B -> C -> D (3 hops from A to D)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("B", "C", "calls", weight=1.0)
    graph.add_relationship("C", "D", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph)

    # B and C should be present (1-2 hops)
    assert "B" in result
    assert "C" in result

    # D should NOT be present (3 hops, exceeds max_hops=2)
    assert "D" not in result


def test_spreading_min_weight_threshold():
    """Spreading ignores relationships below min_weight."""
    spreading = SpreadingActivation(SpreadingConfig(min_weight=0.5))
    graph = RelationshipGraph()

    # A -> B with weight above threshold
    graph.add_relationship("A", "B", "calls", weight=0.8)
    # A -> C with weight below threshold
    graph.add_relationship("A", "C", "calls", weight=0.3)

    result = spreading.calculate(["A"], graph)

    # B should spread (weight 0.8 >= 0.5)
    assert "B" in result
    # C should NOT spread (weight 0.3 < 0.5)
    assert "C" not in result


def test_spreading_source_chunk_gets_zero():
    """Source chunks themselves do not receive spreading activation."""
    spreading = SpreadingActivation()
    graph = RelationshipGraph()

    # A -> B -> A (cycle back to source)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("B", "A", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph)

    # A should not be in result (source chunk)
    assert "A" not in result
    # B should be in result
    assert "B" in result


def test_spreading_bidirectional_mode():
    """Bidirectional spreading follows both incoming and outgoing edges."""
    spreading = SpreadingActivation()
    graph = RelationshipGraph()

    # A -> B (outgoing from A)
    # C -> A (incoming to A)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("C", "A", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph, bidirectional=True)

    # Both B (outgoing) and C (incoming) should spread
    assert "B" in result
    assert "C" in result


def test_spreading_unidirectional_mode():
    """Unidirectional spreading follows only outgoing edges."""
    spreading = SpreadingActivation()
    graph = RelationshipGraph()

    # A -> B (outgoing from A)
    # C -> A (incoming to A)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("C", "A", "calls", weight=1.0)

    result = spreading.calculate(["A"], graph, bidirectional=False)

    # Only B (outgoing) should spread
    assert "B" in result
    # C (incoming) should NOT spread
    assert "C" not in result


def test_spreading_max_edges_limit():
    """Spreading stops at max_edges to prevent runaway spreading."""
    spreading = SpreadingActivation(SpreadingConfig(max_edges=2))
    graph = RelationshipGraph()

    # Star pattern: A connects to B, C, D, E
    for target in ["B", "C", "D", "E"]:
        graph.add_relationship("A", target, "calls", weight=1.0)

    result = spreading.calculate(["A"], graph)

    # Should only traverse 2 edges (max_edges=2)
    assert len(result) == 2


def test_spreading_convenience_function():
    """Convenience function calculate_spreading works correctly."""
    relationships = [
        Relationship(from_chunk="A", to_chunk="B", rel_type="calls", weight=1.0),
        Relationship(from_chunk="B", to_chunk="C", rel_type="calls", weight=1.0),
    ]

    result = calculate_spreading(["A"], relationships, spread_factor=0.7, max_hops=3)

    # Should have both B and C with positive activation
    # Note: bidirectional by default, so values may differ from simple calculation
    assert "B" in result
    assert "C" in result
    assert result["B"] > 0.5  # Should have significant activation
    assert result["C"] > 0.3  # Should have some activation


def test_spreading_get_related_chunks_sorted():
    """get_related_chunks returns chunks sorted by activation."""
    spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
    graph = RelationshipGraph()

    # A -> B (weight 1.0), A -> C (weight 0.5)
    graph.add_relationship("A", "B", "calls", weight=1.0)
    graph.add_relationship("A", "C", "calls", weight=0.5)

    result = spreading.get_related_chunks(["A"], graph)

    # Should return list of tuples sorted by activation (descending)
    assert len(result) == 2
    assert result[0][0] == "B"  # B has higher activation
    assert result[1][0] == "C"  # C has lower activation
    assert result[0][1] > result[1][1]  # Activation values


# ==============================================================================
# Decay Penalty Tests
# ==============================================================================


def test_decay_recent_access_no_penalty():
    """Recent access (within grace period) has no decay penalty."""
    decay = DecayCalculator(DecayConfig(grace_period_hours=1.0))
    current_time = datetime.now(timezone.utc)

    # Access 30 minutes ago (within grace period)
    last_access = current_time - timedelta(minutes=30)
    result = decay.calculate(last_access, current_time)

    # Should have zero or minimal penalty
    assert result >= -0.01  # Close to zero


def test_decay_old_access_penalty():
    """Old access has negative decay penalty."""
    decay = DecayCalculator()
    current_time = datetime.now(timezone.utc)

    # Access 30 days ago
    last_access = current_time - timedelta(days=30)
    result = decay.calculate(last_access, current_time)

    # Should have significant penalty (negative)
    assert result < -0.5


def test_decay_logarithmic_curve():
    """Decay follows logarithmic curve (log10)."""
    decay = DecayCalculator(DecayConfig(decay_factor=0.5))
    current_time = datetime.now(timezone.utc)

    # 10 days vs 100 days (10x difference)
    access_10_days = current_time - timedelta(days=10)
    access_100_days = current_time - timedelta(days=100)

    penalty_10 = decay.calculate(access_10_days, current_time)
    penalty_100 = decay.calculate(access_100_days, current_time)

    # log10(100) - log10(10) = 2 - 1 = 1
    # Penalty difference should be ≈ -0.5 * 1 = -0.5
    expected_diff = -0.5
    actual_diff = penalty_100 - penalty_10

    assert abs(actual_diff - expected_diff) < 0.1


def test_decay_factor_effect():
    """Higher decay factor = steeper penalty."""
    current_time = datetime.now(timezone.utc)
    last_access = current_time - timedelta(days=30)

    # Low decay factor
    low_decay = DecayCalculator(DecayConfig(decay_factor=0.3))
    low_penalty = low_decay.calculate(last_access, current_time)

    # High decay factor
    high_decay = DecayCalculator(DecayConfig(decay_factor=1.0))
    high_penalty = high_decay.calculate(last_access, current_time)

    # Higher decay factor = more negative penalty
    assert high_penalty < low_penalty


def test_decay_max_days_cap():
    """Decay penalty capped at max_days to prevent extreme values."""
    decay = DecayCalculator(DecayConfig(max_days=90.0, decay_factor=0.5))
    current_time = datetime.now(timezone.utc)

    # Access 1000 days ago (should cap at 90)
    access_1000 = current_time - timedelta(days=1000)
    penalty_1000 = decay.calculate(access_1000, current_time)

    # Access 90 days ago (at cap)
    access_90 = current_time - timedelta(days=90)
    penalty_90 = decay.calculate(access_90, current_time)

    # Both should be approximately equal (capped)
    assert abs(penalty_1000 - penalty_90) < 0.1


def test_decay_minimum_penalty_clamp():
    """Decay penalty clamped to min_penalty."""
    decay = DecayCalculator(DecayConfig(min_penalty=-2.0, decay_factor=0.5))
    current_time = datetime.now(timezone.utc)

    # Very old access
    last_access = current_time - timedelta(days=1000)
    result = decay.calculate(last_access, current_time)

    # Should not go below min_penalty
    assert result >= -2.0


def test_decay_zero_time_delta_handled():
    """Decay handles zero time delta gracefully."""
    decay = DecayCalculator()
    current_time = datetime.now(timezone.utc)

    # Access at exactly current time
    result = decay.calculate(current_time, current_time)

    # Should not crash and should return minimal penalty
    assert result >= -0.1


def test_decay_with_creation_time():
    """Decay can use creation_time for newly created chunks."""
    decay = DecayCalculator()
    current_time = datetime.now(timezone.utc)
    creation_time = current_time - timedelta(hours=1)

    # Chunk created 1 hour ago, never accessed
    result = decay.calculate(creation_time, current_time)

    # Should have minimal penalty (recently created)
    assert result >= -0.1


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


def test_bla_config_validation_decay_rate():
    """BLAConfig validates decay_rate is in valid range."""
    # Valid range
    config = BLAConfig(decay_rate=0.5)
    assert config.decay_rate == 0.5

    # Out of range (should raise validation error)
    with pytest.raises(Exception):  # Pydantic validation error
        BLAConfig(decay_rate=-0.1)

    with pytest.raises(Exception):
        BLAConfig(decay_rate=1.5)


def test_spreading_config_validation():
    """SpreadingConfig validates parameters are in valid ranges."""
    # Valid config
    config = SpreadingConfig(spread_factor=0.7, max_hops=3)
    assert config.spread_factor == 0.7
    assert config.max_hops == 3

    # Invalid spread_factor
    with pytest.raises(Exception):
        SpreadingConfig(spread_factor=1.5)

    # Invalid max_hops
    with pytest.raises(Exception):
        SpreadingConfig(max_hops=0)


def test_decay_config_validation():
    """DecayConfig validates parameters are in valid ranges."""
    # Valid config
    config = DecayConfig(decay_factor=0.5, min_penalty=-2.0)
    assert config.decay_factor == 0.5
    assert config.min_penalty == -2.0

    # Invalid min_penalty (positive)
    with pytest.raises(Exception):
        DecayConfig(min_penalty=1.0)


def test_relationship_weight_validation():
    """Relationship validates weight is in [0.0, 1.0]."""
    # Valid weight
    rel = Relationship(from_chunk="A", to_chunk="B", rel_type="calls", weight=0.8)
    assert rel.weight == 0.8

    # Invalid weight
    with pytest.raises(Exception):
        Relationship(from_chunk="A", to_chunk="B", rel_type="calls", weight=1.5)

    with pytest.raises(Exception):
        Relationship(from_chunk="A", to_chunk="B", rel_type="calls", weight=-0.1)


def test_access_history_timestamp_timezone():
    """AccessHistoryEntry handles timezone-naive timestamps."""
    # Naive timestamp (no timezone)
    naive_time = datetime.now()
    entry = AccessHistoryEntry(timestamp=naive_time)

    # Should convert to UTC
    assert entry.timestamp.tzinfo is not None
    assert entry.timestamp.tzinfo == timezone.utc
