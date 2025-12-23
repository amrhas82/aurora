"""
Unit tests for Base-Level Activation (BLA) formula.

Tests the ACT-R BLA calculation including:
- Power law decay formula: BLA = ln(Σ t_j^(-d))
- Frequency effects (more accesses = higher activation)
- Recency effects (recent accesses = higher activation)
- Edge cases (no history, very old accesses, etc.)
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.base_level import (
    AccessHistoryEntry,
    BaseLevelActivation,
    BLAConfig,
    calculate_bla,
)


class TestAccessHistoryEntry:
    """Test AccessHistoryEntry model."""

    def test_create_entry_with_timezone(self):
        """Test creating entry with timezone-aware timestamp."""
        now = datetime.now(timezone.utc)
        entry = AccessHistoryEntry(timestamp=now)
        assert entry.timestamp.tzinfo is not None
        assert entry.context is None

    def test_create_entry_with_context(self):
        """Test creating entry with context information."""
        now = datetime.now(timezone.utc)
        entry = AccessHistoryEntry(timestamp=now, context="database query")
        assert entry.context == "database query"

    def test_naive_timestamp_converted_to_utc(self):
        """Test that naive timestamps are converted to UTC."""
        naive_time = datetime(2025, 1, 1, 12, 0, 0)
        entry = AccessHistoryEntry(timestamp=naive_time)
        assert entry.timestamp.tzinfo is not None


class TestBLAConfig:
    """Test BLA configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BLAConfig()
        assert config.decay_rate == 0.5
        assert config.min_activation == -10.0
        assert config.default_activation == -5.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BLAConfig(decay_rate=0.6, min_activation=-15.0, default_activation=-8.0)
        assert config.decay_rate == 0.6
        assert config.min_activation == -15.0
        assert config.default_activation == -8.0

    def test_decay_rate_validation(self):
        """Test decay rate must be in valid range."""
        # Valid values
        BLAConfig(decay_rate=0.0)
        BLAConfig(decay_rate=0.5)
        BLAConfig(decay_rate=1.0)

        # Invalid values should be caught by Pydantic
        with pytest.raises(Exception):
            BLAConfig(decay_rate=-0.1)
        with pytest.raises(Exception):
            BLAConfig(decay_rate=1.5)


class TestBaseLevelActivation:
    """Test BaseLevelActivation calculation."""

    def test_never_accessed_chunk(self):
        """Test that chunks with no access history get default activation."""
        bla = BaseLevelActivation()
        activation = bla.calculate([])
        assert activation == -5.0  # default_activation

    def test_single_recent_access(self):
        """Test chunk accessed once recently has high activation."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Access 1 second ago
        history = [AccessHistoryEntry(timestamp=now - timedelta(seconds=1))]
        activation = bla.calculate(history, now)

        # Should be close to 0 (ln(1^-0.5) = ln(1) = 0)
        assert activation == pytest.approx(0.0, abs=0.1)

    def test_multiple_accesses_increase_activation(self):
        """Test that more accesses lead to higher activation (frequency effect)."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Single access
        single_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        single_activation = bla.calculate(single_history, now)

        # Multiple accesses
        multiple_history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=2)),
            AccessHistoryEntry(timestamp=now - timedelta(days=3)),
        ]
        multiple_activation = bla.calculate(multiple_history, now)

        # Multiple accesses should have higher activation
        assert multiple_activation > single_activation

    def test_recent_access_higher_than_old(self):
        """Test that recent accesses contribute more than old ones (recency effect)."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Recent access
        recent_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        recent_activation = bla.calculate(recent_history, now)

        # Old access
        old_history = [AccessHistoryEntry(timestamp=now - timedelta(days=30))]
        old_activation = bla.calculate(old_history, now)

        # Recent access should have higher activation
        assert recent_activation > old_activation

    def test_power_law_decay(self):
        """Test that activation follows power law decay formula."""
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Test specific time points
        # BLA = ln(t^-0.5) = -0.5 * ln(t)

        # 1 day ago: ln(86400^-0.5)
        history_1day = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        activation_1day = bla.calculate(history_1day, now)
        expected_1day = math.log(math.pow(86400, -0.5))
        assert activation_1day == pytest.approx(expected_1day, abs=0.01)

        # 10 days ago: ln(864000^-0.5)
        history_10days = [AccessHistoryEntry(timestamp=now - timedelta(days=10))]
        activation_10days = bla.calculate(history_10days, now)
        expected_10days = math.log(math.pow(864000, -0.5))
        assert activation_10days == pytest.approx(expected_10days, abs=0.01)

    def test_activation_clamped_to_minimum(self):
        """Test that very old accesses are clamped to minimum activation."""
        config = BLAConfig(min_activation=-10.0)
        bla = BaseLevelActivation(config)
        now = datetime.now(timezone.utc)

        # Very old access (1000 days ago)
        history = [AccessHistoryEntry(timestamp=now - timedelta(days=1000))]
        activation = bla.calculate(history, now)

        # Should be clamped to minimum
        assert activation >= config.min_activation

    def test_calculate_from_timestamps(self):
        """Test convenience method that takes raw timestamps."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        timestamps = [now - timedelta(days=1), now - timedelta(days=7)]

        activation = bla.calculate_from_timestamps(timestamps, now)
        assert activation < 0  # Should be negative for past accesses

    def test_calculate_from_access_counts(self):
        """Test approximation method using only access count and last access."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)
        last_access = now - timedelta(days=1)

        # Approximate with 5 accesses
        activation = bla.calculate_from_access_counts(
            access_count=5, last_access=last_access, current_time=now
        )

        # Should produce a reasonable activation value
        assert -10.0 < activation < 5.0

    def test_zero_access_count_returns_default(self):
        """Test that zero access count returns default activation."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        activation = bla.calculate_from_access_counts(
            access_count=0, last_access=now, current_time=now
        )

        assert activation == -5.0  # default_activation

    def test_negative_time_delta_handled(self):
        """Test that negative time deltas are handled gracefully."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Future timestamp (should be treated as very recent)
        history = [AccessHistoryEntry(timestamp=now + timedelta(seconds=10))]
        activation = bla.calculate(history, now)

        # Should not crash and should return a valid value
        assert activation == pytest.approx(0.0, abs=0.1)

    def test_different_decay_rates(self):
        """Test that different decay rates produce different results."""
        now = datetime.now(timezone.utc)
        history = [AccessHistoryEntry(timestamp=now - timedelta(days=10))]

        # Lower decay rate (slower forgetting)
        bla_slow = BaseLevelActivation(BLAConfig(decay_rate=0.3))
        activation_slow = bla_slow.calculate(history, now)

        # Higher decay rate (faster forgetting)
        bla_fast = BaseLevelActivation(BLAConfig(decay_rate=0.7))
        activation_fast = bla_fast.calculate(history, now)

        # Slower decay should have higher activation
        assert activation_slow > activation_fast

    def test_custom_current_time(self):
        """Test that custom current_time parameter works correctly."""
        bla = BaseLevelActivation()

        # Create history at a specific time
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        history = [AccessHistoryEntry(timestamp=base_time)]

        # Calculate activation 1 day later
        current_time = base_time + timedelta(days=1)
        activation = bla.calculate(history, current_time)

        # Should be the same as if we used relative times
        now = datetime.now(timezone.utc)
        relative_history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        relative_activation = bla.calculate(relative_history, now)

        assert activation == pytest.approx(relative_activation, abs=0.1)


class TestCalculateBlaFunction:
    """Test standalone calculate_bla function."""

    def test_calculate_bla_with_defaults(self):
        """Test standalone function with default parameters."""
        now = datetime.now(timezone.utc)
        history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]

        activation = calculate_bla(history, current_time=now)
        assert activation < 0  # Should be negative for past accesses

    def test_calculate_bla_with_custom_decay(self):
        """Test standalone function with custom decay rate."""
        now = datetime.now(timezone.utc)
        history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]

        activation = calculate_bla(history, decay_rate=0.6, current_time=now)
        assert activation < 0


class TestACTRFormula:
    """Test that implementation matches ACT-R literature."""

    def test_actr_example_single_access(self):
        """Test against known ACT-R calculation for single access."""
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Single access 86400 seconds ago (1 day)
        history = [AccessHistoryEntry(timestamp=now - timedelta(days=1))]
        activation = bla.calculate(history, now)

        # Expected: ln(86400^-0.5) = -0.5 * ln(86400) ≈ -5.738
        expected = -0.5 * math.log(86400)
        assert activation == pytest.approx(expected, abs=0.01)

    def test_actr_example_multiple_accesses(self):
        """Test against known ACT-R calculation for multiple accesses."""
        bla = BaseLevelActivation(BLAConfig(decay_rate=0.5))
        now = datetime.now(timezone.utc)

        # Multiple accesses at different times
        history = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=10)),
        ]
        activation = bla.calculate(history, now)

        # Expected: ln(86400^-0.5 + 864000^-0.5)
        t1 = 86400  # 1 day in seconds
        t2 = 864000  # 10 days in seconds
        power_sum = math.pow(t1, -0.5) + math.pow(t2, -0.5)
        expected = math.log(power_sum)

        assert activation == pytest.approx(expected, abs=0.01)

    def test_frequency_principle(self):
        """Test ACT-R principle: practice strengthens activation."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Less practice (2 accesses)
        less_practice = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=7)),
        ]
        activation_less = bla.calculate(less_practice, now)

        # More practice (5 accesses)
        more_practice = [
            AccessHistoryEntry(timestamp=now - timedelta(days=1)),
            AccessHistoryEntry(timestamp=now - timedelta(days=2)),
            AccessHistoryEntry(timestamp=now - timedelta(days=3)),
            AccessHistoryEntry(timestamp=now - timedelta(days=4)),
            AccessHistoryEntry(timestamp=now - timedelta(days=5)),
        ]
        activation_more = bla.calculate(more_practice, now)

        # More practice should have higher activation
        assert activation_more > activation_less

    def test_recency_principle(self):
        """Test ACT-R principle: recent practice is more effective."""
        bla = BaseLevelActivation()
        now = datetime.now(timezone.utc)

        # Recent practice schedule
        recent = [
            AccessHistoryEntry(timestamp=now - timedelta(hours=1)),
            AccessHistoryEntry(timestamp=now - timedelta(hours=2)),
            AccessHistoryEntry(timestamp=now - timedelta(hours=3)),
        ]
        activation_recent = bla.calculate(recent, now)

        # Old practice schedule (same number, but older)
        old = [
            AccessHistoryEntry(timestamp=now - timedelta(days=10)),
            AccessHistoryEntry(timestamp=now - timedelta(days=11)),
            AccessHistoryEntry(timestamp=now - timedelta(days=12)),
        ]
        activation_old = bla.calculate(old, now)

        # Recent practice should have much higher activation
        assert activation_recent > activation_old


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
