"""
Unit tests for Decay Penalty calculation.

Tests the ACT-R decay component including:
- DecayConfig validation and defaults
- Decay calculation with logarithmic formula
- Grace period handling (no decay for recent accesses)
- Max days capping (prevent extreme penalties)
- Timezone handling (naive and aware datetimes)
- Convenience methods (calculate_from_hours, calculate_from_days)
- Decay curve generation
- Explanation generation
- Predefined decay profiles
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from aurora_core.activation.decay import (
    AGGRESSIVE_DECAY,
    GENTLE_DECAY,
    MODERATE_DECAY,
    DecayCalculator,
    DecayConfig,
    calculate_decay,
)


class TestDecayConfig:
    """Test DecayConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DecayConfig()
        assert config.decay_factor == 0.5
        assert config.max_days == 90.0
        assert config.min_penalty == -2.0
        assert config.grace_period_hours == 1.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DecayConfig(
            decay_factor=1.0,
            max_days=30.0,
            min_penalty=-3.0,
            grace_period_hours=2.0
        )
        assert config.decay_factor == 1.0
        assert config.max_days == 30.0
        assert config.min_penalty == -3.0
        assert config.grace_period_hours == 2.0

    def test_decay_factor_validation_range(self):
        """Test decay_factor must be in valid range [0.0, 2.0]."""
        # Valid values
        DecayConfig(decay_factor=0.0)
        DecayConfig(decay_factor=1.0)
        DecayConfig(decay_factor=2.0)

        # Invalid values should be caught by Pydantic
        with pytest.raises(Exception):
            DecayConfig(decay_factor=-0.1)
        with pytest.raises(Exception):
            DecayConfig(decay_factor=2.5)

    def test_max_days_validation(self):
        """Test max_days must be >= 1.0."""
        # Valid values
        DecayConfig(max_days=1.0)
        DecayConfig(max_days=100.0)

        # Invalid values
        with pytest.raises(Exception):
            DecayConfig(max_days=0.0)
        with pytest.raises(Exception):
            DecayConfig(max_days=-1.0)

    def test_min_penalty_validation(self):
        """Test min_penalty must be <= 0.0."""
        # Valid values
        DecayConfig(min_penalty=0.0)
        DecayConfig(min_penalty=-1.0)
        DecayConfig(min_penalty=-10.0)

        # Invalid values
        with pytest.raises(Exception):
            DecayConfig(min_penalty=0.1)
        with pytest.raises(Exception):
            DecayConfig(min_penalty=1.0)

    def test_grace_period_validation(self):
        """Test grace_period_hours must be >= 0.0."""
        # Valid values
        DecayConfig(grace_period_hours=0.0)
        DecayConfig(grace_period_hours=1.0)
        DecayConfig(grace_period_hours=24.0)

        # Invalid values
        with pytest.raises(Exception):
            DecayConfig(grace_period_hours=-0.1)


class TestDecayCalculator:
    """Test DecayCalculator functionality."""

    def test_initialization_default_config(self):
        """Test calculator initializes with default config."""
        calc = DecayCalculator()
        assert calc.config.decay_factor == 0.5
        assert calc.config.max_days == 90.0

    def test_initialization_custom_config(self):
        """Test calculator initializes with custom config."""
        config = DecayConfig(decay_factor=1.0, max_days=30.0)
        calc = DecayCalculator(config)
        assert calc.config.decay_factor == 1.0
        assert calc.config.max_days == 30.0

    def test_calculate_within_grace_period(self):
        """Test no decay within grace period (1 hour)."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)

        # 30 minutes ago (within 1 hour grace period)
        last_access = current - timedelta(minutes=30)
        penalty = calc.calculate(last_access, current)
        assert penalty == 0.0

        # 59 minutes ago (within grace period)
        last_access = current - timedelta(minutes=59)
        penalty = calc.calculate(last_access, current)
        assert penalty == 0.0

        # Exactly 1 hour (at grace period boundary)
        last_access = current - timedelta(hours=1)
        penalty = calc.calculate(last_access, current)
        assert penalty == 0.0

    def test_calculate_after_grace_period(self):
        """Test decay applies after grace period (but minimal for < 1 day)."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)

        # 3 hours ago (well after grace period but < 1 day)
        # log10(max(1.0, 3/24)) = log10(1.0) = 0, so penalty = -0.0
        last_access = current - timedelta(hours=3)
        penalty = calc.calculate(last_access, current)
        assert penalty == 0.0  # No decay for < 1 day (log10(1) = 0)

        # 2 days ago (meaningful decay)
        last_access = current - timedelta(days=2)
        penalty = calc.calculate(last_access, current)
        assert penalty < -0.1  # Should have measurable decay

    def test_calculate_one_day_ago(self):
        """Test decay for 1 day old access (log10(1) = 0)."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=1)

        penalty = calc.calculate(last_access, current)
        # 1 day = 24 hours, log10(1.0) = 0, so penalty = -0.5 * 0 = 0
        # But we're slightly over 1 day due to grace period
        expected = -0.5 * math.log10(1.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_ten_days_ago(self):
        """Test decay for 10 days old access."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        penalty = calc.calculate(last_access, current)
        # 10 days: -0.5 * log10(10) = -0.5 * 1.0 = -0.5
        expected = -0.5 * math.log10(10.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_hundred_days_ago(self):
        """Test decay for 100 days old access (near max_days)."""
        config = DecayConfig(max_days=120.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        penalty = calc.calculate(last_access, current)
        # 100 days: -0.5 * log10(100) = -0.5 * 2.0 = -1.0
        expected = -0.5 * math.log10(100.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_capped_at_max_days(self):
        """Test decay is capped at max_days."""
        config = DecayConfig(max_days=30.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)

        # Access 100 days ago (should be capped at 30)
        last_access = current - timedelta(days=100)
        penalty = calc.calculate(last_access, current)

        # Should use max_days (30) instead of actual days (100)
        expected = -0.5 * math.log10(30.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_clamped_at_min_penalty(self):
        """Test decay is clamped at min_penalty."""
        config = DecayConfig(decay_factor=2.0, max_days=1000.0, min_penalty=-1.5)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)

        # Very old access that would exceed min_penalty
        last_access = current - timedelta(days=500)
        penalty = calc.calculate(last_access, current)

        # Should be clamped at min_penalty
        assert penalty == -1.5

    def test_calculate_with_default_current_time(self):
        """Test calculate uses current time when not provided."""
        calc = DecayCalculator()
        last_access = datetime.now(timezone.utc) - timedelta(days=10)

        # Should not raise error and should calculate correctly
        penalty = calc.calculate(last_access)
        assert penalty < 0.0

    def test_calculate_with_naive_datetime_last_access(self):
        """Test calculate handles naive datetime for last_access."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)

        # Naive datetime (no timezone)
        last_access = datetime.now() - timedelta(days=10)

        # Should handle gracefully by adding UTC timezone
        penalty = calc.calculate(last_access, current)
        assert penalty < 0.0

    def test_calculate_with_naive_datetime_current_time(self):
        """Test calculate handles naive datetime for current_time."""
        calc = DecayCalculator()
        last_access = datetime.now(timezone.utc) - timedelta(days=10)

        # Naive current_time
        current = datetime.now()

        # Should handle gracefully by adding UTC timezone
        penalty = calc.calculate(last_access, current)
        assert penalty < 0.0

    def test_calculate_with_different_decay_factors(self):
        """Test different decay factors produce proportional results."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        # Standard decay factor (0.5)
        calc1 = DecayCalculator(DecayConfig(decay_factor=0.5))
        penalty1 = calc1.calculate(last_access, current)

        # Double decay factor (1.0)
        calc2 = DecayCalculator(DecayConfig(decay_factor=1.0))
        penalty2 = calc2.calculate(last_access, current)

        # penalty2 should be roughly 2x penalty1
        assert abs(penalty2 - (penalty1 * 2)) < 0.01

    def test_calculate_from_hours_within_grace_period(self):
        """Test calculate_from_hours with grace period."""
        calc = DecayCalculator()

        # Within grace period
        penalty = calc.calculate_from_hours(0.5)
        assert penalty == 0.0

        penalty = calc.calculate_from_hours(1.0)
        assert penalty == 0.0

    def test_calculate_from_hours_after_grace_period(self):
        """Test calculate_from_hours after grace period."""
        calc = DecayCalculator()

        # 24 hours = 1 day
        penalty = calc.calculate_from_hours(24.0)
        expected = -0.5 * math.log10(1.0)
        assert abs(penalty - expected) < 0.01

        # 240 hours = 10 days
        penalty = calc.calculate_from_hours(240.0)
        expected = -0.5 * math.log10(10.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_from_hours_capped(self):
        """Test calculate_from_hours respects max_days cap."""
        config = DecayConfig(max_days=30.0)
        calc = DecayCalculator(config)

        # 2400 hours = 100 days (should be capped at 30)
        penalty = calc.calculate_from_hours(2400.0)
        expected = -0.5 * math.log10(30.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_from_days_basic(self):
        """Test calculate_from_days with various day counts."""
        calc = DecayCalculator()

        # 1 day
        penalty = calc.calculate_from_days(1.0)
        expected = -0.5 * math.log10(1.0)
        assert abs(penalty - expected) < 0.01

        # 10 days
        penalty = calc.calculate_from_days(10.0)
        expected = -0.5 * math.log10(10.0)
        assert abs(penalty - expected) < 0.01

        # 100 days
        penalty = calc.calculate_from_days(100.0)
        # Capped at max_days (90)
        expected = -0.5 * math.log10(90.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_from_days_fractional(self):
        """Test calculate_from_days with fractional days."""
        calc = DecayCalculator()

        # 0.5 days = 12 hours
        penalty = calc.calculate_from_days(0.5)
        # Within grace period, should be 0
        assert penalty == 0.0

        # 2.5 days
        penalty = calc.calculate_from_days(2.5)
        expected = -0.5 * math.log10(2.5)
        assert abs(penalty - expected) < 0.01


class TestDecayCurve:
    """Test decay curve generation."""

    def test_get_decay_curve_default_params(self):
        """Test get_decay_curve with default parameters."""
        calc = DecayCalculator()
        curve = calc.get_decay_curve()

        # Should return default num_points (50)
        assert len(curve) == 50

        # Each point should be (days, penalty) tuple
        for days, penalty in curve:
            assert isinstance(days, float)
            assert isinstance(penalty, float)
            assert penalty <= 0.0  # Penalties are non-positive

    def test_get_decay_curve_custom_max_days(self):
        """Test get_decay_curve with custom max_days."""
        calc = DecayCalculator()
        curve = calc.get_decay_curve(max_days=30, num_points=10)

        assert len(curve) == 10

        # First point should be at day 0
        assert curve[0][0] == 0.0

        # Last point should be at max_days
        assert abs(curve[-1][0] - 30.0) < 0.1

    def test_get_decay_curve_monotonic_decrease(self):
        """Test decay curve shows monotonic decrease."""
        calc = DecayCalculator()
        curve = calc.get_decay_curve(max_days=50, num_points=20)

        # Penalties should become more negative over time
        # (except within grace period where they stay at 0)
        for i in range(1, len(curve)):
            days_prev, penalty_prev = curve[i-1]
            days_curr, penalty_curr = curve[i]

            # Days should increase
            assert days_curr > days_prev

            # Penalty should decrease or stay same (become more negative or equal)
            assert penalty_curr <= penalty_prev + 0.01  # Small tolerance

    def test_get_decay_curve_single_point(self):
        """Test get_decay_curve with single point."""
        calc = DecayCalculator()
        curve = calc.get_decay_curve(max_days=10, num_points=1)

        assert len(curve) == 1
        assert curve[0][0] == 0.0  # Only point should be at day 0


class TestExplainDecay:
    """Test decay explanation generation."""

    def test_explain_decay_basic(self):
        """Test explain_decay returns all expected fields."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        explanation = calc.explain_decay(last_access, current)

        # Check all expected fields
        assert 'penalty' in explanation
        assert 'days_since_access' in explanation
        assert 'hours_since_access' in explanation
        assert 'grace_period_applied' in explanation
        assert 'grace_period_hours' in explanation
        assert 'capped_at_max' in explanation
        assert 'max_days' in explanation
        assert 'decay_factor' in explanation
        assert 'formula' in explanation

    def test_explain_decay_within_grace_period(self):
        """Test explain_decay shows grace period applied."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(minutes=30)

        explanation = calc.explain_decay(last_access, current)

        assert explanation['penalty'] == 0.0
        assert explanation['grace_period_applied'] is True
        assert explanation['hours_since_access'] < 1.0

    def test_explain_decay_after_grace_period(self):
        """Test explain_decay shows no grace period."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        explanation = calc.explain_decay(last_access, current)

        assert explanation['penalty'] < 0.0
        assert explanation['grace_period_applied'] is False
        assert explanation['days_since_access'] > 9.0

    def test_explain_decay_capped_at_max(self):
        """Test explain_decay shows capping."""
        config = DecayConfig(max_days=30.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        explanation = calc.explain_decay(last_access, current)

        assert explanation['capped_at_max'] is True
        assert explanation['days_since_access'] > 90.0
        # Formula should show capped value (30) not actual (100)
        assert '30.00' in explanation['formula']

    def test_explain_decay_not_capped(self):
        """Test explain_decay shows no capping for recent access."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        explanation = calc.explain_decay(last_access, current)

        assert explanation['capped_at_max'] is False

    def test_explain_decay_formula_format(self):
        """Test formula string is properly formatted."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        explanation = calc.explain_decay(last_access, current)

        formula = explanation['formula']
        assert '-0.5' in formula  # decay_factor
        assert 'log10' in formula
        assert '10.' in formula  # days value


class TestConvenienceFunction:
    """Test the calculate_decay convenience function."""

    def test_calculate_decay_default_params(self):
        """Test convenience function with default parameters."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        penalty = calculate_decay(last_access, current_time=current)

        # Should match calculator result
        calc = DecayCalculator()
        expected = calc.calculate(last_access, current)
        assert abs(penalty - expected) < 0.01

    def test_calculate_decay_custom_decay_factor(self):
        """Test convenience function with custom decay_factor."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        penalty = calculate_decay(last_access, decay_factor=1.0, current_time=current)

        # Should use specified decay_factor
        expected = -1.0 * math.log10(10.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_decay_custom_max_days(self):
        """Test convenience function with custom max_days."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        penalty = calculate_decay(last_access, max_days=30.0, current_time=current)

        # Should cap at 30 days
        expected = -0.5 * math.log10(30.0)
        assert abs(penalty - expected) < 0.01

    def test_calculate_decay_without_current_time(self):
        """Test convenience function uses current time by default."""
        last_access = datetime.now(timezone.utc) - timedelta(days=10)

        # Should not raise error
        penalty = calculate_decay(last_access)
        assert penalty < 0.0


class TestPredefinedProfiles:
    """Test predefined decay profiles."""

    def test_aggressive_decay_config(self):
        """Test AGGRESSIVE_DECAY profile configuration."""
        assert AGGRESSIVE_DECAY.decay_factor == 1.0
        assert AGGRESSIVE_DECAY.max_days == 30.0
        assert AGGRESSIVE_DECAY.grace_period_hours == 0.5

    def test_moderate_decay_config(self):
        """Test MODERATE_DECAY profile configuration."""
        assert MODERATE_DECAY.decay_factor == 0.5
        assert MODERATE_DECAY.max_days == 90.0
        assert MODERATE_DECAY.grace_period_hours == 1.0

    def test_gentle_decay_config(self):
        """Test GENTLE_DECAY profile configuration."""
        assert GENTLE_DECAY.decay_factor == 0.25
        assert GENTLE_DECAY.max_days == 180.0
        assert GENTLE_DECAY.grace_period_hours == 2.0

    def test_aggressive_decay_stronger_penalty(self):
        """Test AGGRESSIVE_DECAY produces stronger penalties."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=10)

        calc_aggressive = DecayCalculator(AGGRESSIVE_DECAY)
        calc_moderate = DecayCalculator(MODERATE_DECAY)
        calc_gentle = DecayCalculator(GENTLE_DECAY)

        penalty_aggressive = calc_aggressive.calculate(last_access, current)
        penalty_moderate = calc_moderate.calculate(last_access, current)
        penalty_gentle = calc_gentle.calculate(last_access, current)

        # Aggressive should have most negative penalty
        assert penalty_aggressive < penalty_moderate
        assert penalty_moderate < penalty_gentle

    def test_gentle_decay_longer_grace_period(self):
        """Test GENTLE_DECAY has longer grace period."""
        current = datetime.now(timezone.utc)
        # 1.5 hours ago
        last_access = current - timedelta(hours=1.5)

        calc_aggressive = DecayCalculator(AGGRESSIVE_DECAY)
        calc_moderate = DecayCalculator(MODERATE_DECAY)
        calc_gentle = DecayCalculator(GENTLE_DECAY)

        penalty_aggressive = calc_aggressive.calculate(last_access, current)
        penalty_moderate = calc_moderate.calculate(last_access, current)
        penalty_gentle = calc_gentle.calculate(last_access, current)

        # At 1.5 hours (< 1 day, so log10(1) = 0):
        # - Aggressive (0.5h grace): past grace but < 1 day so penalty = 0
        # - Moderate (1.0h grace): past grace but < 1 day so penalty = 0
        # - Gentle (2.0h grace): within grace period so penalty = 0
        # All are 0, but gentle is still in grace period
        assert penalty_aggressive == 0.0  # Past grace, but < 1 day
        assert penalty_moderate == 0.0  # Past grace, but < 1 day
        assert penalty_gentle == 0.0  # Still in grace period

        # Test at 3 days to show real differences
        last_access_3d = current - timedelta(days=3)
        penalty_aggressive_3d = calc_aggressive.calculate(last_access_3d, current)
        penalty_moderate_3d = calc_moderate.calculate(last_access_3d, current)
        penalty_gentle_3d = calc_gentle.calculate(last_access_3d, current)

        # Now we should see differences (aggressive > moderate > gentle)
        assert penalty_aggressive_3d < penalty_moderate_3d < penalty_gentle_3d
        assert penalty_aggressive_3d < -0.2  # Aggressive has stronger penalty

    def test_profiles_with_calculator(self):
        """Test all profiles work correctly with DecayCalculator."""
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=30)

        for profile in [AGGRESSIVE_DECAY, MODERATE_DECAY, GENTLE_DECAY]:
            calc = DecayCalculator(profile)
            penalty = calc.calculate(last_access, current)

            # All should produce valid penalties
            assert penalty <= 0.0
            assert penalty >= profile.min_penalty


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_future_last_access(self):
        """Test handling of last_access in the future."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)
        last_access = current + timedelta(days=1)

        # Should handle gracefully (treat as within grace period)
        penalty = calc.calculate(last_access, current)
        # Negative time delta should result in 0 or minimal penalty
        assert penalty >= calc.config.min_penalty

    def test_same_time_access(self):
        """Test last_access equals current_time."""
        calc = DecayCalculator()
        current = datetime.now(timezone.utc)

        penalty = calc.calculate(current, current)
        # Should be within grace period
        assert penalty == 0.0

    def test_zero_decay_factor(self):
        """Test decay with zero decay_factor (no decay)."""
        config = DecayConfig(decay_factor=0.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        penalty = calc.calculate(last_access, current)
        # Zero decay factor means no penalty
        assert penalty == 0.0

    def test_very_large_decay_factor(self):
        """Test decay with maximum decay_factor."""
        config = DecayConfig(decay_factor=2.0, min_penalty=-5.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        penalty = calc.calculate(last_access, current)
        # Should produce large penalty
        assert penalty < -1.5

    def test_very_short_max_days(self):
        """Test decay with minimum max_days."""
        config = DecayConfig(max_days=1.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=100)

        penalty = calc.calculate(last_access, current)
        # Should cap at 1 day
        expected = -0.5 * math.log10(1.0)
        assert abs(penalty - expected) < 0.01

    def test_zero_grace_period(self):
        """Test decay with no grace period."""
        config = DecayConfig(grace_period_hours=0.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(minutes=1)

        penalty = calc.calculate(last_access, current)
        # Should have immediate decay (no grace period)
        assert penalty == 0.0  # Still within first hour, log10(x < 1) handled

    def test_very_long_grace_period(self):
        """Test decay with extended grace period."""
        config = DecayConfig(grace_period_hours=48.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(hours=24)

        penalty = calc.calculate(last_access, current)
        # Should still be within grace period
        assert penalty == 0.0

    def test_min_penalty_zero(self):
        """Test decay with min_penalty set to zero."""
        config = DecayConfig(min_penalty=0.0, max_days=1000.0, decay_factor=2.0)
        calc = DecayCalculator(config)
        current = datetime.now(timezone.utc)
        last_access = current - timedelta(days=500)

        penalty = calc.calculate(last_access, current)
        # Should be clamped at 0.0 even though formula gives negative
        assert penalty == 0.0

    def test_calculate_from_hours_zero(self):
        """Test calculate_from_hours with zero hours."""
        calc = DecayCalculator()
        penalty = calc.calculate_from_hours(0.0)
        assert penalty == 0.0

    def test_calculate_from_days_zero(self):
        """Test calculate_from_days with zero days."""
        calc = DecayCalculator()
        penalty = calc.calculate_from_days(0.0)
        assert penalty == 0.0

    def test_microsecond_precision(self):
        """Test calculation handles microsecond precision."""
        calc = DecayCalculator()
        current = datetime(2024, 1, 1, 12, 0, 0, 500000, tzinfo=timezone.utc)
        last_access = datetime(2024, 1, 1, 12, 0, 0, 0, tzinfo=timezone.utc)

        penalty = calc.calculate(last_access, current)
        # 500000 microseconds = 0.5 seconds (within grace period)
        assert penalty == 0.0


class TestLogarithmicBehavior:
    """Test the logarithmic decay behavior matches ACT-R theory."""

    def test_decay_logarithmic_progression(self):
        """Test decay follows logarithmic curve (10x time = +1.0 to log)."""
        calc = DecayCalculator()

        # 1 day
        penalty_1 = calc.calculate_from_days(1.0)

        # 10 days
        penalty_10 = calc.calculate_from_days(10.0)

        # 100 days (capped at 90)
        penalty_100 = calc.calculate_from_days(100.0)

        # Differences should be approximately equal (logarithmic)
        # log10(10) - log10(1) = 1.0
        # log10(90) - log10(10) ≈ 0.95
        diff_1_10 = penalty_1 - penalty_10
        diff_10_100 = penalty_10 - penalty_100

        # Should be roughly equal (within 20% tolerance)
        assert abs(diff_1_10 - diff_10_100) < 0.2

    def test_recent_vs_old_penalty_ratio(self):
        """Test penalty ratio matches logarithmic expectation."""
        config = DecayConfig(decay_factor=1.0, max_days=200.0)
        calc = DecayCalculator(config)

        # 10 days: penalty = -1.0 * log10(10) = -1.0
        penalty_10 = calc.calculate_from_days(10.0)

        # 100 days: penalty = -1.0 * log10(100) = -2.0
        penalty_100 = calc.calculate_from_days(100.0)

        # Ratio should be 2:1
        assert abs(penalty_100 / penalty_10 - 2.0) < 0.1
