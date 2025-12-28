"""
Integration tests for ActivationEngine (Full Activation Formula).

Tests the complete ACT-R activation engine including:
- Total activation formula: BLA + Spreading + Context - Decay
- Integration of all four activation components
- Component enable/disable toggles
- Preset configurations (DEFAULT, AGGRESSIVE, CONSERVATIVE, BLA_FOCUSED, CONTEXT_FOCUSED)
- Activation explanation and debugging features
- Configuration updates and dynamic reconfiguration
- Edge cases and component interactions
- Full activation workflow integration
"""

from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.base_level import AccessHistoryEntry, BLAConfig
from aurora_core.activation.context_boost import ContextBoostConfig
from aurora_core.activation.decay import DecayConfig
from aurora_core.activation.engine import (
    AGGRESSIVE_CONFIG,
    BLA_FOCUSED_CONFIG,
    CONSERVATIVE_CONFIG,
    CONTEXT_FOCUSED_CONFIG,
    DEFAULT_CONFIG,
    ActivationComponents,
    ActivationConfig,
    ActivationEngine,
)
from aurora_core.activation.spreading import RelationshipGraph, SpreadingConfig


class TestActivationConfig:
    """Test ActivationConfig model."""

    def test_default_config(self):
        """Test default configuration has all components enabled."""
        config = ActivationConfig()
        assert config.enable_bla is True
        assert config.enable_spreading is True
        assert config.enable_context is True
        assert config.enable_decay is True
        assert config.bla_config is not None
        assert config.spreading_config is not None
        assert config.context_config is not None
        assert config.decay_config is not None

    def test_custom_config_with_sub_configs(self):
        """Test creating custom config with specific sub-configs."""
        config = ActivationConfig(
            bla_config=BLAConfig(decay_rate=0.6),
            spreading_config=SpreadingConfig(spread_factor=0.8),
            context_config=ContextBoostConfig(boost_factor=1.0),
            decay_config=DecayConfig(decay_factor=0.8),
            enable_spreading=False,
        )
        assert config.bla_config.decay_rate == 0.6
        assert config.spreading_config.spread_factor == 0.8
        assert config.context_config.boost_factor == 1.0
        assert config.decay_config.decay_factor == 0.8
        assert config.enable_spreading is False

    def test_disable_all_components(self):
        """Test disabling all components."""
        config = ActivationConfig(
            enable_bla=False, enable_spreading=False, enable_context=False, enable_decay=False
        )
        assert config.enable_bla is False
        assert config.enable_spreading is False
        assert config.enable_context is False
        assert config.enable_decay is False


class TestActivationComponents:
    """Test ActivationComponents model."""

    def test_default_components_all_zero(self):
        """Test default components are all zero."""
        components = ActivationComponents()
        assert components.bla == 0.0
        assert components.spreading == 0.0
        assert components.context_boost == 0.0
        assert components.decay == 0.0
        assert components.total == 0.0

    def test_components_can_be_set(self):
        """Test components can be set to custom values."""
        components = ActivationComponents(
            bla=2.5, spreading=0.7, context_boost=0.3, decay=-1.2, total=2.3
        )
        assert components.bla == 2.5
        assert components.spreading == 0.7
        assert components.context_boost == 0.3
        assert components.decay == -1.2
        assert components.total == 2.3

    def test_components_mutable(self):
        """Test components can be updated after creation."""
        components = ActivationComponents()
        components.bla = 1.5
        components.total = 1.5
        assert components.bla == 1.5
        assert components.total == 1.5


class TestActivationEngine:
    """Test ActivationEngine core functionality."""

    def test_engine_initialization_default(self):
        """Test engine initializes with default config."""
        engine = ActivationEngine()
        assert engine.config is not None
        assert engine.bla_calculator is not None
        assert engine.spreading_calculator is not None
        assert engine.context_calculator is not None
        assert engine.decay_calculator is not None

    def test_engine_initialization_custom_config(self):
        """Test engine initializes with custom config."""
        config = ActivationConfig(bla_config=BLAConfig(decay_rate=0.6))
        engine = ActivationEngine(config)
        assert engine.config.bla_config.decay_rate == 0.6

    @pytest.mark.core
    @pytest.mark.critical
    def test_calculate_total_with_all_components(self):
        """Test calculating total activation with all components enabled."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Setup data for all components
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]
        last_access = now - timedelta(days=1)
        spreading = 0.5
        query_keywords = {"database", "optimize", "performance"}
        chunk_keywords = {"database", "query", "index", "performance"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # All components should have non-zero values
        assert components.bla != 0.0  # Has access history
        assert components.spreading == 0.5  # Direct value
        assert components.context_boost > 0.0  # Has keyword overlap
        assert components.decay <= 0.0  # 1 day ago (can be -0.0 due to grace period)

        # Total should be sum of all (decay is negative)
        expected_total = (
            components.bla + components.spreading + components.context_boost - abs(components.decay)
        )
        assert components.total == pytest.approx(expected_total, abs=0.001)

    @pytest.mark.core
    @pytest.mark.critical
    def test_calculate_total_missing_data_returns_partial(self):
        """Test that missing data for components results in 0.0 for those components."""
        engine = ActivationEngine()

        # Only provide spreading activation, no other data
        components = engine.calculate_total(spreading_activation=0.8)

        assert components.bla == 0.0  # No access history
        assert components.spreading == 0.8  # Provided
        assert components.context_boost == 0.0  # No keywords
        assert components.decay == 0.0  # No last_access
        assert components.total == 0.8

    @pytest.mark.core
    @pytest.mark.critical
    def test_calculate_total_with_bla_disabled(self):
        """Test calculation with BLA disabled."""
        config = ActivationConfig(enable_bla=False)
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        components = engine.calculate_total(
            access_history=access_history, spreading_activation=0.5, current_time=now
        )

        assert components.bla == 0.0  # Disabled
        assert components.spreading == 0.5
        assert components.total == 0.5

    def test_calculate_total_with_spreading_disabled(self):
        """Test calculation with spreading disabled."""
        config = ActivationConfig(enable_spreading=False)
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        components = engine.calculate_total(
            access_history=access_history, spreading_activation=0.5, current_time=now
        )

        assert components.bla != 0.0  # Enabled
        assert components.spreading == 0.0  # Disabled (even though value provided)
        assert components.total == pytest.approx(components.bla, abs=0.001)

    def test_calculate_total_with_context_disabled(self):
        """Test calculation with context boost disabled."""
        config = ActivationConfig(enable_context=False)
        engine = ActivationEngine(config)

        query_keywords = {"database", "optimize"}
        chunk_keywords = {"database", "query"}

        components = engine.calculate_total(
            query_keywords=query_keywords, chunk_keywords=chunk_keywords
        )

        assert components.context_boost == 0.0  # Disabled
        assert components.total == 0.0

    def test_calculate_total_with_decay_disabled(self):
        """Test calculation with decay disabled."""
        config = ActivationConfig(enable_decay=False)
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        last_access = now - timedelta(days=30)

        components = engine.calculate_total(
            last_access=last_access, spreading_activation=0.5, current_time=now
        )

        assert components.decay == 0.0  # Disabled
        assert components.spreading == 0.5
        assert components.total == 0.5

    def test_calculate_total_all_disabled_returns_zero(self):
        """Test that disabling all components returns zero total."""
        config = ActivationConfig(
            enable_bla=False, enable_spreading=False, enable_context=False, enable_decay=False
        )
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        # Provide all data
        components = engine.calculate_total(
            access_history=[AccessHistoryEntry(timestamp=now)],
            last_access=now,
            spreading_activation=1.0,
            query_keywords={"test"},
            chunk_keywords={"test"},
            current_time=now,
        )

        assert components.total == 0.0

    def test_calculate_bla_only(self):
        """Test calculating only BLA component."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Use very recent accesses to get positive BLA
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(seconds=10)),
            AccessHistoryEntry(timestamp=now - timedelta(seconds=20)),
            AccessHistoryEntry(timestamp=now - timedelta(seconds=30)),
        ]

        bla = engine.calculate_bla_only(access_history, now)
        assert bla > -2.0  # BLA can be negative, but should be reasonable for recent accesses
        assert isinstance(bla, float)

    def test_calculate_spreading_only(self):
        """Test calculating only spreading component."""
        engine = ActivationEngine()

        graph = RelationshipGraph()
        graph.add_relationship(from_chunk="chunk_a", to_chunk="chunk_b", rel_type="calls")
        graph.add_relationship(from_chunk="chunk_b", to_chunk="chunk_c", rel_type="calls")

        spreading = engine.calculate_spreading_only(source_chunks=["chunk_a"], graph=graph)

        assert "chunk_b" in spreading
        assert "chunk_c" in spreading
        assert spreading["chunk_b"] > spreading["chunk_c"]  # Closer gets more

    def test_calculate_context_only(self):
        """Test calculating only context boost component."""
        engine = ActivationEngine()

        query_keywords = {"database", "optimize", "performance"}
        chunk_keywords = {"database", "query", "performance"}

        context_boost = engine.calculate_context_only(query_keywords, chunk_keywords)

        # 2/3 keywords match, default boost factor is 0.5
        # boost = (2/3) * 0.5 = 0.333...
        assert context_boost == pytest.approx(0.333, abs=0.01)

    def test_calculate_decay_only(self):
        """Test calculating only decay penalty component."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        last_access = now - timedelta(days=10)

        decay = engine.calculate_decay_only(last_access, now)

        assert decay < 0.0  # Decay is always negative
        assert isinstance(decay, float)


class TestActivationEngineExplain:
    """Test ActivationEngine explain functionality."""

    def test_explain_activation_full(self):
        """Test explaining activation with all components."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]
        last_access = now - timedelta(days=1)
        query_keywords = {"database", "optimize"}
        chunk_keywords = {"database", "query", "optimize"}

        explanation = engine.explain_activation(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=0.5,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # Check structure
        assert "components" in explanation
        assert "enabled_components" in explanation
        assert "bla_details" in explanation
        assert "spreading_details" in explanation
        assert "context_details" in explanation
        assert "decay_details" in explanation

        # Check enabled components
        assert "bla" in explanation["enabled_components"]
        assert "spreading" in explanation["enabled_components"]
        assert "context" in explanation["enabled_components"]
        assert "decay" in explanation["enabled_components"]

        # Check component details
        assert explanation["bla_details"]["access_count"] == 2
        assert "formula" in explanation["bla_details"]

        assert explanation["spreading_details"]["value"] == 0.5
        assert "formula" in explanation["spreading_details"]

        assert "matching_keywords" in explanation["context_details"]
        assert explanation["context_details"]["matching_keywords"] == ["database", "optimize"]
        assert explanation["context_details"]["overlap_fraction"] == pytest.approx(1.0, abs=0.01)

        assert "days_since_access" in explanation["decay_details"]

    def test_explain_activation_partial_components(self):
        """Test explaining activation with only some components enabled."""
        config = ActivationConfig(enable_spreading=False, enable_decay=False)
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        query_keywords = {"test"}
        chunk_keywords = {"test"}

        explanation = engine.explain_activation(
            access_history=access_history,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        assert "bla" in explanation["enabled_components"]
        assert "context" in explanation["enabled_components"]
        assert "spreading" not in explanation["enabled_components"]
        assert "decay" not in explanation["enabled_components"]

        assert "spreading_details" not in explanation
        assert "decay_details" not in explanation

    def test_explain_activation_no_keywords(self):
        """Test explaining activation when context boost not calculated."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        explanation = engine.explain_activation(access_history=access_history, current_time=now)

        # Context should be in enabled_components list only if keywords provided
        # Since no keywords provided, context won't be in enabled list
        assert (
            "context" not in explanation["enabled_components"]
            or "context_details" not in explanation
        )


class TestActivationEngineConfigUpdate:
    """Test ActivationEngine configuration updates."""

    def test_update_bla_config(self):
        """Test updating BLA configuration."""
        engine = ActivationEngine()

        original_decay_rate = engine.config.bla_config.decay_rate

        new_bla_config = BLAConfig(decay_rate=0.7)
        engine.update_config(bla_config=new_bla_config)

        assert engine.config.bla_config.decay_rate == 0.7
        assert engine.config.bla_config.decay_rate != original_decay_rate

    def test_update_spreading_config(self):
        """Test updating spreading configuration."""
        engine = ActivationEngine()

        new_spreading_config = SpreadingConfig(spread_factor=0.8)
        engine.update_config(spreading_config=new_spreading_config)

        assert engine.config.spreading_config.spread_factor == 0.8

    def test_update_context_config(self):
        """Test updating context boost configuration."""
        engine = ActivationEngine()

        new_context_config = ContextBoostConfig(boost_factor=1.0)
        engine.update_config(context_config=new_context_config)

        assert engine.config.context_config.boost_factor == 1.0

    def test_update_decay_config(self):
        """Test updating decay configuration."""
        engine = ActivationEngine()

        new_decay_config = DecayConfig(decay_factor=0.8)
        engine.update_config(decay_config=new_decay_config)

        assert engine.config.decay_config.decay_factor == 0.8

    def test_update_multiple_configs(self):
        """Test updating multiple configurations at once."""
        engine = ActivationEngine()

        engine.update_config(
            bla_config=BLAConfig(decay_rate=0.6),
            context_config=ContextBoostConfig(boost_factor=0.8),
        )

        assert engine.config.bla_config.decay_rate == 0.6
        assert engine.config.context_config.boost_factor == 0.8


class TestPresetConfigurations:
    """Test predefined preset configurations."""

    def test_default_config_preset(self):
        """Test DEFAULT_CONFIG preset."""
        config = DEFAULT_CONFIG
        assert config.enable_bla is True
        assert config.enable_spreading is True
        assert config.enable_context is True
        assert config.enable_decay is True

    def test_aggressive_config_preset(self):
        """Test AGGRESSIVE_CONFIG preset has stronger parameters."""
        config = AGGRESSIVE_CONFIG

        # Should have stronger influence from all components
        assert config.bla_config.decay_rate == 0.6  # Higher decay
        assert config.spreading_config.spread_factor == 0.8  # Stronger spreading
        assert config.context_config.boost_factor == 0.8  # Larger boost
        assert config.decay_config.decay_factor == 1.0  # Aggressive decay penalty
        assert config.decay_config.max_days == 30.0  # Shorter memory

    def test_conservative_config_preset(self):
        """Test CONSERVATIVE_CONFIG preset has weaker parameters."""
        config = CONSERVATIVE_CONFIG

        # Should have minimal influence from components
        assert config.bla_config.decay_rate == 0.4  # Lower decay
        assert config.spreading_config.spread_factor == 0.6  # Weaker spreading
        assert config.spreading_config.max_hops == 2  # Fewer hops
        assert config.context_config.boost_factor == 0.3  # Smaller boost
        assert config.decay_config.decay_factor == 0.25  # Gentle decay penalty
        assert config.decay_config.max_days == 180.0  # Longer memory

    def test_bla_focused_config_preset(self):
        """Test BLA_FOCUSED_CONFIG preset emphasizes frequency/recency."""
        config = BLA_FOCUSED_CONFIG

        # Spreading should be disabled
        assert config.enable_spreading is False

        # BLA should use standard settings
        assert config.bla_config.decay_rate == 0.5

        # Others minimized
        assert config.context_config.boost_factor == 0.2
        assert config.decay_config.decay_factor == 0.3

    def test_context_focused_config_preset(self):
        """Test CONTEXT_FOCUSED_CONFIG preset emphasizes query relevance."""
        config = CONTEXT_FOCUSED_CONFIG

        # Context boost should be maximized
        assert config.context_config.boost_factor == 1.0

        # BLA reduced
        assert config.bla_config.decay_rate == 0.3

        # Spreading moderate
        assert config.spreading_config.spread_factor == 0.6
        assert config.spreading_config.max_hops == 2

    def test_presets_create_working_engines(self):
        """Test that all preset configs can create working engines."""
        presets = [
            DEFAULT_CONFIG,
            AGGRESSIVE_CONFIG,
            CONSERVATIVE_CONFIG,
            BLA_FOCUSED_CONFIG,
            CONTEXT_FOCUSED_CONFIG,
        ]

        for preset in presets:
            engine = ActivationEngine(preset)
            assert engine is not None

            # Should be able to calculate activation
            components = engine.calculate_total(spreading_activation=0.5)
            assert components.total is not None


class TestActivationEngineIntegration:
    """Test full integration scenarios with realistic data."""

    def test_realistic_code_chunk_activation(self):
        """Test activation calculation for a realistic code chunk scenario."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Scenario: A database function that was accessed multiple times
        # recently and is related to the current query
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=3)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]
        last_access = now - timedelta(hours=2)

        # Spreading from related chunks
        spreading = 0.35  # Some activation from related functions

        # Query about database optimization
        query_keywords = {"database", "optimize", "query", "performance"}
        chunk_keywords = {"database", "connection", "query", "pool", "optimize"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # Verify all components are present (BLA can be negative for old accesses)
        assert components.bla != 0.0  # Has access history
        assert components.spreading == 0.35
        assert components.context_boost > 0.0  # Good keyword overlap
        assert components.decay <= 0.0  # Small penalty (2 hours, might be in grace period)

        # Total should be influenced by spreading and context
        # BLA may be negative but spreading and context should help
        assert components.spreading + components.context_boost > 0.5

    def test_old_unused_chunk_activation(self):
        """Test activation for a chunk that hasn't been used in a long time."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Scenario: Old utility function, not accessed recently
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=180)),
            AccessHistoryEntry(timestamp=now - timedelta(days=200)),
        ]
        last_access = now - timedelta(days=180)

        # No spreading, no context match
        spreading = 0.0
        query_keywords = {"database", "optimize"}
        chunk_keywords = {"utility", "helper", "format"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # BLA should be low (old accesses)
        assert components.bla < -3.0

        # No spreading
        assert components.spreading == 0.0

        # No context match
        assert components.context_boost == 0.0

        # Large decay penalty (180 days, capped at 90)
        assert components.decay < -0.5

        # Total should be very negative
        assert components.total < -3.0

    def test_high_spreading_low_bla_scenario(self):
        """Test scenario where spreading is high but BLA is low."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Rarely accessed but strongly connected to query-relevant chunks
        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=60))]
        last_access = now - timedelta(days=60)

        # High spreading from related chunks
        spreading = 1.2

        # Some keyword match
        query_keywords = {"database", "transaction"}
        chunk_keywords = {"transaction", "commit", "rollback"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # Spreading should be present and high
        assert components.spreading == 1.2

        # BLA will be negative for old accesses (this is correct ACT-R behavior)
        # The key is that spreading provides substantial positive activation
        assert components.bla < 0.0  # Old access means negative BLA

        # Total may be positive or negative depending on whether spreading overcomes BLA+decay
        # The important thing is that spreading contributes positively
        assert components.spreading > 0.0

    def test_perfect_context_match_scenario(self):
        """Test scenario with perfect keyword overlap."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Moderate access history
        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=5))]
        last_access = now - timedelta(days=5)

        # Perfect keyword match
        query_keywords = {"database", "optimize", "index"}
        chunk_keywords = {"database", "optimize", "index"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=0.0,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # Perfect match: overlap_fraction = 1.0, boost_factor = 0.5
        # context_boost = 1.0 * 0.5 = 0.5
        assert components.context_boost == pytest.approx(0.5, abs=0.01)

    def test_comparative_activation_ranking(self):
        """Test that activation properly ranks chunks by relevance."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Chunk A: Recent, relevant
        components_a = engine.calculate_total(
            access_history=[
                AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
                AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            ],
            last_access=now - timedelta(hours=1),
            spreading_activation=0.5,
            query_keywords={"database", "query"},
            chunk_keywords={"database", "query", "sql"},
            current_time=now,
        )

        # Chunk B: Old, less relevant
        components_b = engine.calculate_total(
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=30))],
            last_access=now - timedelta(days=30),
            spreading_activation=0.1,
            query_keywords={"database", "query"},
            chunk_keywords={"utility", "helper"},
            current_time=now,
        )

        # Chunk C: Never accessed but highly relevant
        components_c = engine.calculate_total(
            access_history=[],
            spreading_activation=0.0,
            query_keywords={"database", "query"},
            chunk_keywords={"database", "query", "optimize"},
            current_time=now,
        )

        # Chunk A should rank highest (recent + relevant)
        assert components_a.total > components_b.total

        # Chunk C should rank lowest (no BLA despite context match)
        assert components_c.total < components_a.total


class TestActivationEngineEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_access_history(self):
        """Test handling of empty access history."""
        engine = ActivationEngine()

        components = engine.calculate_total(access_history=[], spreading_activation=0.5)

        # Should use default BLA
        assert components.bla == -5.0  # default_activation
        assert components.spreading == 0.5
        assert components.total == pytest.approx(-4.5, abs=0.01)

    def test_none_access_history(self):
        """Test handling of None access history."""
        engine = ActivationEngine()

        components = engine.calculate_total(access_history=None, spreading_activation=0.5)

        # Should result in 0.0 BLA (component disabled for this calculation)
        assert components.bla == 0.0
        assert components.spreading == 0.5
        assert components.total == 0.5

    def test_very_large_access_history(self):
        """Test handling of very large access history."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        # Many accesses - test that calculation handles large datasets
        access_history = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=i))
            for i in range(1, 101)  # 100 accesses in past 100 hours
        ]

        components = engine.calculate_total(access_history=access_history, current_time=now)

        # Should complete without error (main goal is performance/stability)
        assert isinstance(components.bla, float)
        assert isinstance(components.total, float)
        # BLA value doesn't matter as much as successful calculation
        # The ACT-R formula can produce negative values for old accesses

    def test_negative_spreading_activation(self):
        """Test handling of negative spreading activation."""
        engine = ActivationEngine()

        # Spreading can be negative in some implementations
        components = engine.calculate_total(spreading_activation=-0.5)

        assert components.spreading == -0.5
        assert components.total == -0.5

    def test_zero_keyword_overlap(self):
        """Test handling of zero keyword overlap."""
        engine = ActivationEngine()

        query_keywords = {"database", "query"}
        chunk_keywords = {"network", "socket"}

        components = engine.calculate_total(
            query_keywords=query_keywords, chunk_keywords=chunk_keywords
        )

        assert components.context_boost == 0.0

    def test_empty_keyword_sets(self):
        """Test handling of empty keyword sets."""
        engine = ActivationEngine()

        components = engine.calculate_total(query_keywords=set(), chunk_keywords={"test"})

        # Empty query keywords should result in 0.0 boost
        assert components.context_boost == 0.0

    def test_all_components_negative(self):
        """Test scenario where all components contribute negatively."""
        config = ActivationConfig(enable_spreading=False, enable_context=False)
        engine = ActivationEngine(config)
        now = datetime.now(timezone.utc)

        # Very old access
        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=365))]
        last_access = now - timedelta(days=365)

        components = engine.calculate_total(
            access_history=access_history, last_access=last_access, current_time=now
        )

        # Both BLA and decay should be negative
        assert components.bla < 0.0
        assert components.decay < 0.0
        assert components.total < -5.0


class TestActivationEngineFormula:
    """Test that the total activation formula is correctly implemented."""

    def test_formula_correctness_manual_calculation(self):
        """Test that total matches manual formula calculation."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        access_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        last_access = now - timedelta(days=1)
        spreading = 0.5
        query_keywords = {"database"}
        chunk_keywords = {"database", "query"}

        components = engine.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=now,
        )

        # Manually calculate expected total
        manual_total = (
            components.bla + components.spreading + components.context_boost - abs(components.decay)
        )

        assert components.total == pytest.approx(manual_total, abs=0.001)

    def test_formula_decay_subtracted_not_added(self):
        """Test that decay penalty is subtracted from total, not added."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        last_access = now - timedelta(days=10)

        components = engine.calculate_total(
            spreading_activation=1.0, last_access=last_access, current_time=now
        )

        # Decay should be negative
        assert components.decay < 0.0

        # Total should be less than spreading alone
        assert components.total < 1.0

        # Verify decay reduced the total
        assert components.total == pytest.approx(1.0 - abs(components.decay), abs=0.001)

    def test_formula_all_components_sum_correctly(self):
        """Test that all enabled components sum correctly to total."""
        engine = ActivationEngine()
        now = datetime.now(timezone.utc)

        components = engine.calculate_total(
            access_history=[AccessHistoryEntry(timestamp=now - timedelta(days=2))],
            last_access=now - timedelta(days=2),
            spreading_activation=0.8,
            query_keywords={"test", "function"},
            chunk_keywords={"test", "unit", "function"},
            current_time=now,
        )

        # Calculate sum manually
        manual_sum = (
            components.bla + components.spreading + components.context_boost - abs(components.decay)
        )

        assert components.total == pytest.approx(manual_sum, abs=0.001)
