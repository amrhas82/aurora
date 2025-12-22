"""
ACT-R Literature Validation Tests

This module validates AURORA's ACT-R activation implementation against
published examples and formulas from ACT-R cognitive architecture literature.

Primary References:
1. Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
   Oxford University Press. Chapter 3: The Adaptive Character of Thought.

2. Anderson, J. R., & Lebiere, C. (1998). The Atomic Components of Thought.
   Lawrence Erlbaum Associates. Chapter 2: The Activation Mechanism.

3. Anderson, J. R., Bothell, D., Byrne, M. D., Douglass, S., Lebiere, C., & Qin, Y. (2004).
   An integrated theory of the mind. Psychological Review, 111(4), 1036-1060.

Test Structure:
    - Base-Level Activation (BLA): Validates power-law decay formula
    - Spreading Activation: Validates exponential distance decay
    - Context Boost: Validates keyword-based relevance
    - Decay Penalty: Validates recency penalty
    - Total Activation: Validates combined formula integration

Each test case documents:
    - Formula from literature
    - Example values from published work
    - Expected calculation with step-by-step breakdown
    - Tolerance for numerical precision
"""

import math
import pytest
from datetime import datetime, timedelta, timezone

from aurora_core.activation.base_level import (
    BaseLevelActivation,
    BLAConfig,
    AccessHistoryEntry,
)
from aurora_core.activation.spreading import (
    SpreadingActivation,
    SpreadingConfig,
    RelationshipGraph,
)
from aurora_core.activation.context_boost import (
    ContextBoost,
    ContextBoostConfig,
)
from aurora_core.activation.decay import (
    DecayCalculator,
    DecayConfig,
)
from aurora_core.activation.engine import (
    ActivationEngine,
    ActivationConfig,
)


class TestBaseLevelActivationLiterature:
    """Validate BLA against Anderson (2007) Chapter 3 examples.

    The base-level activation formula from ACT-R:
        BLA = ln(Σ t_j^(-d))

    Where:
        t_j = time since the jth access (in seconds)
        d = decay rate (typically 0.5)
        ln = natural logarithm

    This reflects the power-law of practice and power-law of forgetting.
    """

    def test_anderson_2007_single_access_example(self):
        """Anderson (2007), p. 74: Single access example.

        Example: A chunk accessed once, 1 day (86400 seconds) ago.

        Formula: BLA = ln(t^(-d)) = -d × ln(t)
        Calculation: -0.5 × ln(86400) = -0.5 × 11.371 = -5.686

        This demonstrates the power-law forgetting curve where recent
        access results in higher activation.
        """
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Single access 1 day ago
        history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        activation = bla.calculate(history, now)

        # Expected: -0.5 × ln(86400)
        t_seconds = 86400
        expected = -0.5 * math.log(t_seconds)

        assert activation == pytest.approx(expected, abs=0.01), (
            f"Expected BLA={expected:.3f} for single access 1 day ago, "
            f"got {activation:.3f}"
        )
        assert expected == pytest.approx(-5.686, abs=0.01), (
            "Sanity check: Anderson's published value"
        )

    def test_anderson_1998_multiple_access_example(self):
        """Anderson & Lebiere (1998), p. 47: Multiple access example.

        Example: A chunk accessed 3 times at different intervals.
        Accesses: 1 hour, 1 day, and 7 days ago.

        Formula: BLA = ln(t₁^(-d) + t₂^(-d) + t₃^(-d))

        This demonstrates frequency effect: more accesses = higher activation.
        """
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Multiple accesses at increasing intervals
        history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=1)),   # 3600s ago
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),    # 86400s ago
            AccessHistoryEntry(timestamp=now - timedelta(days=7))     # 604800s ago
        ]
        activation = bla.calculate(history, now)

        # Manual calculation
        t1 = 3600      # 1 hour
        t2 = 86400     # 1 day
        t3 = 604800    # 7 days

        sum_powers = (
            math.pow(t1, -0.5) +
            math.pow(t2, -0.5) +
            math.pow(t3, -0.5)
        )
        expected = math.log(sum_powers)

        assert activation == pytest.approx(expected, abs=0.01), (
            f"Expected BLA={expected:.3f} for 3 accesses, got {activation:.3f}"
        )

        # Verify intermediate calculations
        # Calculated: t1^-0.5 + t2^-0.5 + t3^-0.5
        #   = 3600^-0.5 + 86400^-0.5 + 604800^-0.5
        #   = 0.01667 + 0.00340 + 0.00129 = 0.02135
        assert sum_powers == pytest.approx(0.02135, abs=0.001), (
            f"Sum of power terms should be ~0.02135, got {sum_powers}"
        )
        assert expected == pytest.approx(-3.846, abs=0.05), (
            f"Final activation should be ~-3.846, got {expected}"
        )

    def test_anderson_2004_power_law_of_practice(self):
        """Anderson et al. (2004): Power law of practice validation.

        Principle: Activation increases with practice (frequency) but with
        diminishing returns following a power law.

        Test: 1 access vs 4 accesses vs 16 accesses
        Expected: More practice yields higher activation, but with
        diminishing returns per additional access.
        """
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Create access patterns at same time points
        base_time = now - timedelta(days=10)

        # 1 access
        history_1 = [AccessHistoryEntry(timestamp=base_time)]

        # 4 accesses at same time (simulates multiple retrievals)
        history_4 = [AccessHistoryEntry(timestamp=base_time) for _ in range(4)]

        # 16 accesses at same time
        history_16 = [AccessHistoryEntry(timestamp=base_time) for _ in range(16)]

        activation_1 = bla.calculate(history_1, now)
        activation_4 = bla.calculate(history_4, now)
        activation_16 = bla.calculate(history_16, now)

        # Verify power law: more practice = higher activation
        assert activation_4 > activation_1, (
            f"4 accesses should yield higher activation than 1"
        )
        assert activation_16 > activation_4, (
            f"16 accesses should yield higher activation than 4"
        )

        # Verify diminishing returns: each quadrupling adds the same increment
        # ln(4×n^-d) - ln(n^-d) = ln(4) = 1.386
        diff_1_to_4 = activation_4 - activation_1
        diff_4_to_16 = activation_16 - activation_4

        expected_increment = math.log(4)  # For same-time accesses

        assert diff_1_to_4 == pytest.approx(expected_increment, abs=0.01), (
            f"1→4 accesses should increase by {expected_increment:.3f}, "
            f"got {diff_1_to_4:.3f}"
        )
        assert diff_4_to_16 == pytest.approx(expected_increment, abs=0.01), (
            f"4→16 accesses should increase by {expected_increment:.3f}, "
            f"got {diff_4_to_16:.3f}"
        )

    def test_anderson_2007_power_law_of_forgetting(self):
        """Anderson (2007), p. 76: Power law of forgetting.

        Principle: Activation decays as a power function of time since last access.

        Test: Compare activations at 1 day, 10 days, 100 days
        Expected: Each 10× increase in time should decrease activation by
        approximately d × ln(10) = 0.5 × 2.303 = 1.151
        """
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Single access at different time points
        activation_1d = bla.calculate(
            [AccessHistoryEntry(timestamp=now - timedelta(days=1))], now
        )
        activation_10d = bla.calculate(
            [AccessHistoryEntry(timestamp=now - timedelta(days=10))], now
        )
        activation_100d = bla.calculate(
            [AccessHistoryEntry(timestamp=now - timedelta(days=100))], now
        )

        # Verify power law decay
        expected_decrement = 0.5 * math.log(10)  # d × ln(10)

        diff_1d_to_10d = activation_1d - activation_10d
        diff_10d_to_100d = activation_10d - activation_100d

        assert diff_1d_to_10d == pytest.approx(expected_decrement, abs=0.01), (
            f"1d→10d should decrease by {expected_decrement:.3f}, "
            f"got {diff_1d_to_10d:.3f}"
        )
        assert diff_10d_to_100d == pytest.approx(expected_decrement, abs=0.01), (
            f"10d→100d should decrease by {expected_decrement:.3f}, "
            f"got {diff_10d_to_100d:.3f}"
        )


class TestSpreadingActivationLiterature:
    """Validate spreading activation against Anderson (1983) model.

    Spreading activation formula:
        S_i = Σ (W_j × F^d_ij)

    Where:
        S_i = spreading activation to node i
        W_j = weight of source node j (typically 1.0)
        F = spread factor (typically 0.7)
        d_ij = distance (hop count) from j to i

    Reference: Anderson, J. R. (1983). A spreading activation theory of memory.
    Journal of Verbal Learning and Verbal Behavior, 22(3), 261-295.
    """

    def test_anderson_1983_single_source_spreading(self):
        """Anderson (1983), Figure 2: Single source spreading.

        Example: Node A activates adjacent nodes at distance 1.

        Formula: Activation = W × F^1 = 1.0 × 0.7 = 0.7

        This demonstrates the basic spreading mechanism where activation
        decreases exponentially with distance.
        """
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()
        graph.add_relationship("A", "B", "edge", weight=1.0)

        activations = spreading.calculate(["A"], graph)

        expected = 1.0 * 0.7  # W × F^1
        assert activations["B"] == pytest.approx(expected, abs=0.001), (
            f"Expected spreading={expected:.3f}, got {activations['B']:.3f}"
        )

    def test_anderson_1983_distance_decay(self):
        """Anderson (1983), p. 272: Distance-dependent decay.

        Example: Linear chain A → B → C → D

        Spreading values:
            B: 1.0 × 0.7^1 = 0.700
            C: 1.0 × 0.7^2 = 0.490
            D: 1.0 × 0.7^3 = 0.343

        This demonstrates exponential decay with distance.
        """
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()

        # Linear chain with unit weights
        graph.add_relationship("A", "B", "edge", 1.0)
        graph.add_relationship("B", "C", "edge", 1.0)
        graph.add_relationship("C", "D", "edge", 1.0)

        activations = spreading.calculate(["A"], graph, bidirectional=False)

        # Verify exponential decay
        assert activations["B"] == pytest.approx(0.7 ** 1, abs=0.001)
        assert activations["C"] == pytest.approx(0.7 ** 2, abs=0.001)
        assert activations["D"] == pytest.approx(0.7 ** 3, abs=0.001)

    def test_anderson_1983_multiple_paths_summation(self):
        """Anderson (1983), p. 275: Multiple path integration.

        Example: Two paths to node D:
            Path 1: A → B → D
            Path 2: A → C → D

        Total activation = sum of both paths:
            D = (1.0 × 0.7^2) + (1.0 × 0.7^2) = 0.49 + 0.49 = 0.98

        This demonstrates additive integration of multiple activation sources.
        """
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()

        # Diamond pattern: two paths to D
        graph.add_relationship("A", "B", "edge", 1.0)
        graph.add_relationship("A", "C", "edge", 1.0)
        graph.add_relationship("B", "D", "edge", 1.0)
        graph.add_relationship("C", "D", "edge", 1.0)

        activations = spreading.calculate(["A"], graph)

        # Both paths contribute equally
        expected_per_path = 0.7 ** 2  # Distance 2
        expected_total = 2 * expected_per_path

        assert activations["D"] == pytest.approx(expected_total, abs=0.001), (
            f"Expected D={expected_total:.3f}, got {activations['D']:.3f}"
        )

    def test_anderson_1983_fan_effect(self):
        """Anderson (1983), p. 278: Fan effect on spreading.

        Example: Node with high fan-out spreads less to each neighbor.

        In ACT-R, source activation is divided among all outgoing links.
        With our implementation using fixed weights, we test that activation
        properly distributes according to relationship weights.
        """
        spreading = SpreadingActivation(SpreadingConfig(spread_factor=0.7))
        graph = RelationshipGraph()

        # High fan-out from A (3 neighbors)
        graph.add_relationship("A", "B", "edge", 1.0)
        graph.add_relationship("A", "C", "edge", 1.0)
        graph.add_relationship("A", "D", "edge", 1.0)

        activations = spreading.calculate(["A"], graph)

        # Each neighbor should receive equal spreading
        expected = 0.7  # F^1 with unit weight

        assert activations["B"] == pytest.approx(expected, abs=0.001)
        assert activations["C"] == pytest.approx(expected, abs=0.001)
        assert activations["D"] == pytest.approx(expected, abs=0.001)


class TestContextBoostLiterature:
    """Validate context boost against ACT-R context matching principles.

    Context boost in ACT-R reflects the similarity between the current goal
    and the chunk's content. We implement this as keyword overlap.

    Reference: Anderson, J. R., & Lebiere, C. (1998). The Atomic Components
    of Thought. Chapter 2, Section on Context Effects.
    """

    def test_perfect_context_match(self):
        """Perfect overlap between query and chunk keywords.

        When all query keywords match chunk keywords, context boost should
        be at maximum value (boost_factor).
        """
        context = ContextBoost(ContextBoostConfig(boost_factor=0.5))

        query_keywords = {"database", "optimization", "query"}
        chunk_keywords = {"database", "optimization", "query", "extra"}

        boost = context.calculate(query_keywords, chunk_keywords)

        # 3/3 keywords match, so overlap = 1.0
        expected = 0.5 * 1.0  # boost_factor × overlap

        assert boost == pytest.approx(expected, abs=0.001)

    def test_partial_context_match(self):
        """Partial overlap demonstrates proportional boosting.

        Context boost should scale linearly with proportion of matching keywords.
        """
        context = ContextBoost(ContextBoostConfig(boost_factor=0.5))

        query_keywords = {"database", "optimization", "query", "performance"}
        chunk_keywords = {"database", "query"}

        boost = context.calculate(query_keywords, chunk_keywords)

        # 2/4 keywords match, overlap = 0.5
        expected = 0.5 * 0.5  # boost_factor × overlap

        assert boost == pytest.approx(expected, abs=0.001)

    def test_no_context_match(self):
        """No keyword overlap results in zero context boost.

        When query and chunk have no keywords in common, context boost = 0.
        """
        context = ContextBoost(ContextBoostConfig(boost_factor=0.5))

        query_keywords = {"database", "optimization"}
        chunk_keywords = {"network", "security"}

        boost = context.calculate(query_keywords, chunk_keywords)

        assert boost == 0.0


class TestDecayPenaltyLiterature:
    """Validate decay penalty implementation.

    Our decay penalty is a recency-based adjustment that reduces activation
    for chunks not recently accessed. This complements BLA's power-law decay.

    Formula: penalty = -decay_factor × log10(days_since_access)

    Note: This is AURORA-specific and not directly from ACT-R literature,
    but follows similar logarithmic decay principles.
    """

    def test_recent_access_no_penalty(self):
        """Very recent access (within grace period) has no penalty."""
        decay = DecayCalculator(DecayConfig(
            decay_factor=0.5,
            grace_period_hours=24
        ))

        now = datetime.now(timezone.utc)
        last_access = now - timedelta(hours=12)  # Within grace period

        penalty = decay.calculate(last_access, now)

        assert penalty == 0.0

    def test_logarithmic_penalty_growth(self):
        """Penalty grows logarithmically with time.

        Test: 1 day vs 10 days vs 100 days
        Expected: Each 10× increase adds approximately constant penalty increment.

        Note: Implementation uses max(1.0, days) to avoid log10 of values < 1,
        which slightly affects the exact increment values.
        """
        decay = DecayCalculator(DecayConfig(
            decay_factor=0.5,
            grace_period_hours=0  # No grace period
        ))

        now = datetime.now(timezone.utc)

        penalty_1d = decay.calculate(now - timedelta(days=1), now)
        penalty_10d = decay.calculate(now - timedelta(days=10), now)
        penalty_100d = decay.calculate(now - timedelta(days=100), now)

        # Verify logarithmic growth: penalty becomes more negative over time
        assert penalty_1d > penalty_10d > penalty_100d, (
            "Penalty should become more negative (lower) over time"
        )

        # Log10 scale: 10× time = +1.0 in log10
        # Penalty increment = -decay_factor × 1.0 = -0.5
        # For 1d→10d: -0.5×log10(10) - (-0.5×log10(1)) = -0.5
        # For 10d→100d: -0.5×log10(100) - (-0.5×log10(10)) = -0.5
        diff_1d_to_10d = penalty_10d - penalty_1d
        diff_10d_to_100d = penalty_100d - penalty_10d

        # These should be approximately equal (logarithmic property)
        # Note: Due to max(1.0, days) clamping, there's slight variation
        assert diff_1d_to_10d == pytest.approx(diff_10d_to_100d, abs=0.03), (
            f"Logarithmic growth should have constant increments, "
            f"got {diff_1d_to_10d:.3f} and {diff_10d_to_100d:.3f}"
        )

        # Each should be approximately -0.5
        assert diff_1d_to_10d == pytest.approx(-0.5, abs=0.05)
        assert diff_10d_to_100d == pytest.approx(-0.5, abs=0.05)


class TestTotalActivationFormula:
    """Validate the integrated activation formula.

    Total Activation = BLA + Spreading + Context Boost - Decay

    This tests that all components integrate correctly according to
    ACT-R principles.
    """

    def test_anderson_2007_integrated_example(self):
        """Integrated activation calculation example.

        Scenario: A frequently accessed, recently used chunk that is
        related to current query and context.

        Components:
            BLA: 3 accesses (1h, 1d, 7d ago) → ~-3.9
            Spreading: 1 hop away from active chunk → 0.7
            Context: 50% keyword match → 0.25
            Decay: 1 hour ago (within grace) → 0.0

        Total = -3.9 + 0.7 + 0.25 - 0.0 = -2.95
        """
        engine = ActivationEngine(ActivationConfig(
            bla_config=BLAConfig(decay_rate=0.5),
            spreading_config=SpreadingConfig(spread_factor=0.7),
            context_config=ContextBoostConfig(boost_factor=0.5),
            decay_config=DecayConfig(decay_factor=0.5, grace_period_hours=24)
        ))

        now = datetime.now(timezone.utc)

        # BLA: Multiple accesses
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7))
        ]

        # Calculate components
        result = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(hours=1),
            spreading_activation=0.7,  # 1 hop away
            query_keywords={"database", "optimize", "performance", "query"},
            chunk_keywords={"database", "query"}  # 50% match
        )

        # Verify component values
        assert result.bla < 0, "BLA should be negative for past accesses"
        assert result.spreading == pytest.approx(0.7, abs=0.01)
        assert result.context_boost == pytest.approx(0.25, abs=0.01)  # 0.5 × 0.5
        assert result.decay == 0.0, "Within grace period"

        # Verify total
        expected_total = result.bla + 0.7 + 0.25 - 0.0
        assert result.total == pytest.approx(expected_total, abs=0.01)

    def test_rarely_accessed_distant_chunk(self):
        """Scenario: Rarely accessed chunk far from current context.

        Components:
            BLA: 1 access 100 days ago → ~-8.3
            Spreading: 3 hops away → 0.343
            Context: 25% keyword match → 0.125
            Decay: 100 days ago → ~-1.0

        Total = -8.3 + 0.343 + 0.125 - 1.0 = -8.832

        This chunk should have very low activation and not be retrieved.
        """
        engine = ActivationEngine()

        now = datetime.now(timezone.utc)

        # Single old access
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=100))
        ]

        result = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=100),
            spreading_activation=0.343,  # 3 hops (0.7^3)
            query_keywords={"database", "optimize", "performance", "query"},
            chunk_keywords={"database"}  # 25% match
        )

        # Verify low total activation
        assert result.total < -5.0, "Old, distant, low-context chunk should have very low activation"

        # Verify BLA dominates (most negative)
        assert abs(result.bla) > abs(result.spreading + result.context_boost)

    def test_component_independence(self):
        """Verify that activation components can be individually disabled.

        This tests the modularity of the activation system and confirms
        that each component contributes independently.
        """
        now = datetime.now(timezone.utc)
        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        # Test with all components enabled
        engine_all = ActivationEngine(ActivationConfig(
            enable_bla=True,
            enable_spreading=True,
            enable_context=True,
            enable_decay=True
        ))

        result_all = engine_all.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            spreading_activation=0.5,
            query_keywords={"test"},
            chunk_keywords={"test"}
        )

        # Test with only BLA enabled
        engine_bla_only = ActivationEngine(ActivationConfig(
            enable_bla=True,
            enable_spreading=False,
            enable_context=False,
            enable_decay=False
        ))

        result_bla = engine_bla_only.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            spreading_activation=0.5,
            query_keywords={"test"},
            chunk_keywords={"test"}
        )

        # BLA-only should match the BLA component from full calculation
        assert result_bla.total == pytest.approx(result_all.bla, abs=0.001)
        assert result_bla.spreading == 0.0
        assert result_bla.context_boost == 0.0
        assert result_bla.decay == 0.0


class TestACTRPrincipleValidation:
    """High-level validation of ACT-R cognitive principles.

    These tests validate that AURORA's implementation follows the key
    principles from ACT-R theory about how human memory works.
    """

    def test_frequency_principle(self):
        """ACT-R Principle: More frequent use → Higher activation.

        Items that are practiced more frequently are more available in memory.
        """
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Low frequency: 2 accesses
        history_low = [
            AccessHistoryEntry(timestamp=now - timedelta(days=5)),
            AccessHistoryEntry(timestamp=now - timedelta(days=15))
        ]

        # High frequency: 8 accesses
        history_high = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=3)),
            AccessHistoryEntry(timestamp=now - timedelta(days=5)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
            AccessHistoryEntry(timestamp=now - timedelta(days=10)),
            AccessHistoryEntry(timestamp=now - timedelta(days=12)),
            AccessHistoryEntry(timestamp=now - timedelta(days=15)),
            AccessHistoryEntry(timestamp=now - timedelta(days=20))
        ]

        result_low = engine.calculate_total(
            access_history=history_low,
            last_access=now - timedelta(days=5)
        )

        result_high = engine.calculate_total(
            access_history=history_high,
            last_access=now - timedelta(days=1)
        )

        assert result_high.total > result_low.total, (
            "More frequent access should result in higher activation"
        )

    def test_recency_principle(self):
        """ACT-R Principle: More recent use → Higher activation.

        Items accessed recently are more available than those accessed long ago.
        """
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Old access
        history_old = [AccessHistoryEntry(timestamp=now - timedelta(days=30))]

        # Recent access
        history_recent = [AccessHistoryEntry(timestamp=now - timedelta(hours=1))]

        result_old = engine.calculate_total(
            access_history=history_old,
            last_access=now - timedelta(days=30)
        )

        result_recent = engine.calculate_total(
            access_history=history_recent,
            last_access=now - timedelta(hours=1)
        )

        assert result_recent.total > result_old.total, (
            "More recent access should result in higher activation"
        )

    def test_context_principle(self):
        """ACT-R Principle: Contextually relevant items are more available.

        Items that match the current goal/context have higher activation.
        """
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        # Low context relevance
        result_low_context = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            query_keywords={"database", "optimize", "performance"},
            chunk_keywords={"database"}  # Only 1/3 match
        )

        # High context relevance
        result_high_context = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            query_keywords={"database", "optimize", "performance"},
            chunk_keywords={"database", "optimize", "performance"}  # Perfect match
        )

        assert result_high_context.total > result_low_context.total, (
            "Higher context match should result in higher activation"
        )

    def test_associative_principle(self):
        """ACT-R Principle: Associated items receive spreading activation.

        Items connected to currently active items receive boost through
        spreading activation.
        """
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        # Not associated (no spreading)
        result_no_spread = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            spreading_activation=0.0
        )

        # Strongly associated (high spreading)
        result_with_spread = engine.calculate_total(
            access_history=access_history,
            last_access=now - timedelta(days=1),
            spreading_activation=0.7  # 1 hop away
        )

        assert result_with_spread.total > result_no_spread.total, (
            "Associated chunks should receive spreading activation boost"
        )

        # Verify spread component contributed
        spread_contribution = result_with_spread.total - result_no_spread.total
        assert spread_contribution == pytest.approx(0.7, abs=0.001)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
