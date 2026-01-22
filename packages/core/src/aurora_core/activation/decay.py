"""Decay Penalty Calculation

This module implements decay penalty for ACT-R activation, which reduces
activation for chunks that haven't been accessed recently. The decay
reflects the natural forgetting curve observed in human memory.

Decay Formula:
    Decay = -decay_factor × log10(days_since_access)

Where:
    - decay_factor: Decay rate (default 0.5)
    - days_since_access: Time since last access in days
    - Capped at max_days (default 90) to prevent extreme penalties

The log10 relationship means:
    - 1 day ago: -0.5 × 0 = 0.0 (no decay)
    - 10 days ago: -0.5 × 1 = -0.5
    - 100 days ago: -0.5 × 2 = -1.0
    - 1000 days ago: capped at 90 days

Reference:
    Anderson, J. R., & Schooler, L. J. (1991). Reflections of the environment
    in memory. Psychological Science, 2(6), 396-408.
"""

import math
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DecayConfig(BaseModel):
    """Configuration for decay calculation.

    Attributes:
        decay_factor: Decay rate multiplier (default 0.5, ACT-R standard)
        max_days: Maximum days for decay calculation (default 90)
        min_penalty: Minimum penalty value (most negative)
        grace_period_hours: Hours with no decay after creation (default 1)

    """

    decay_factor: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Decay rate multiplier (standard ACT-R value is 0.5)",
    )
    max_days: float = Field(
        default=90.0,
        ge=1.0,
        description="Maximum days for decay calculation (caps extreme values)",
    )
    min_penalty: float = Field(
        default=-2.0,
        le=0.0,
        description="Minimum penalty value (most negative)",
    )
    grace_period_hours: float = Field(
        default=1.0,
        ge=0.0,
        description="Hours with no decay after creation (recently created chunks)",
    )

    @field_validator("decay_factor")
    @classmethod
    def validate_decay_factor(cls, v: float) -> float:
        """Ensure decay factor is non-negative."""
        if v < 0:
            raise ValueError("Decay factor must be non-negative")
        return v

    @field_validator("min_penalty")
    @classmethod
    def validate_min_penalty(cls, v: float) -> float:
        """Ensure minimum penalty is non-positive."""
        if v > 0:
            raise ValueError("Minimum penalty must be non-positive")
        return v


class DecayCalculator:
    """Calculates decay penalty based on time since last access.

    The decay penalty reflects forgetting over time, following a logarithmic
    curve that matches empirical human memory data. Recent accesses have
    minimal decay, while old accesses have significant penalties.

    Examples:
        >>> from datetime import datetime, timedelta, timezone
        >>> decay = DecayCalculator()
        >>>
        >>> # Recent access (1 day ago)
        >>> last_access = datetime.now(timezone.utc) - timedelta(days=1)
        >>> penalty = decay.calculate(last_access)
        >>> print(f"1 day: {penalty:.3f}")
        1 day: -0.000
        >>>
        >>> # Old access (30 days ago)
        >>> last_access = datetime.now(timezone.utc) - timedelta(days=30)
        >>> penalty = decay.calculate(last_access)
        >>> print(f"30 days: {penalty:.3f}")
        30 days: -0.737

    """

    def __init__(self, config: DecayConfig | None = None):
        """Initialize the decay calculator.

        Args:
            config: Configuration for decay calculation (uses defaults if None)

        """
        self.config = config or DecayConfig()

    def calculate(self, last_access: datetime, current_time: datetime | None = None) -> float:
        """Calculate decay penalty for a chunk.

        Args:
            last_access: Timestamp of last access
            current_time: Current time for calculation (defaults to now)

        Returns:
            Decay penalty (non-positive value, 0.0 to min_penalty)

        Notes:
            - Returns 0.0 for very recent accesses (within grace period)
            - Returns min_penalty for very old accesses (beyond max_days)
            - Uses log10 for realistic forgetting curve

        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Ensure last_access is timezone-aware
        if last_access.tzinfo is None:
            last_access = last_access.replace(tzinfo=timezone.utc)

        # Calculate time since access
        time_delta = current_time - last_access
        hours_since_access = time_delta.total_seconds() / 3600.0

        # Apply grace period (no decay for very recent accesses)
        if hours_since_access <= self.config.grace_period_hours:
            return 0.0

        # Convert to days
        days_since_access = hours_since_access / 24.0

        # Cap at maximum days
        days_since_access = min(days_since_access, self.config.max_days)

        # Calculate decay penalty: -decay_factor × log10(days)
        # For days < 1, we get log10(x) < 0, so we use max(1, days)
        # to ensure we're always taking log of values >= 1
        penalty = -self.config.decay_factor * math.log10(max(1.0, days_since_access))

        # Clamp to minimum penalty
        return max(penalty, self.config.min_penalty)

    def calculate_from_hours(self, hours_since_access: float) -> float:
        """Calculate decay penalty from hours since access.

        Convenience method that doesn't require datetime objects.

        Args:
            hours_since_access: Hours since last access

        Returns:
            Decay penalty (non-positive value)

        """
        # Apply grace period
        if hours_since_access <= self.config.grace_period_hours:
            return 0.0

        days_since_access = hours_since_access / 24.0

        # Cap at maximum days
        days_since_access = min(days_since_access, self.config.max_days)

        # Calculate penalty
        penalty = -self.config.decay_factor * math.log10(max(1.0, days_since_access))

        # Clamp to minimum penalty
        return max(penalty, self.config.min_penalty)

    def calculate_from_days(self, days_since_access: float) -> float:
        """Calculate decay penalty from days since access.

        Convenience method for direct day-based calculations.

        Args:
            days_since_access: Days since last access

        Returns:
            Decay penalty (non-positive value)

        """
        # Convert to hours and use standard calculation
        return self.calculate_from_hours(days_since_access * 24.0)

    def get_decay_curve(
        self,
        max_days: int | None = None,
        num_points: int = 50,
    ) -> list[tuple[float, float]]:
        """Get decay curve data points for visualization.

        Args:
            max_days: Maximum days to plot (defaults to config.max_days)
            num_points: Number of data points to generate

        Returns:
            List of (days, penalty) tuples for plotting

        Example:
            >>> decay = DecayCalculator()
            >>> curve = decay.get_decay_curve(max_days=30, num_points=10)
            >>> for days, penalty in curve:
            ...     print(f"Day {days:.1f}: {penalty:.3f}")

        """
        if max_days is None:
            max_days = int(self.config.max_days)

        points = []
        for i in range(num_points):
            days = (max_days / (num_points - 1)) * i if num_points > 1 else 0
            penalty = self.calculate_from_days(days)
            points.append((days, penalty))

        return points

    def explain_decay(
        self,
        last_access: datetime,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Explain how decay was calculated.

        Args:
            last_access: Timestamp of last access
            current_time: Current time for calculation (defaults to now)

        Returns:
            Dictionary with explanation:
                - penalty: Final decay penalty value
                - days_since_access: Days since last access
                - hours_since_access: Hours since last access
                - grace_period_applied: Whether grace period was applied
                - capped_at_max: Whether capped at max_days
                - formula: Formula used for calculation

        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if last_access.tzinfo is None:
            last_access = last_access.replace(tzinfo=timezone.utc)

        time_delta = current_time - last_access
        hours_since_access = time_delta.total_seconds() / 3600.0
        days_since_access = hours_since_access / 24.0

        grace_period_applied = hours_since_access <= self.config.grace_period_hours
        capped_at_max = days_since_access > self.config.max_days

        penalty = self.calculate(last_access, current_time)

        return {
            "penalty": penalty,
            "days_since_access": days_since_access,
            "hours_since_access": hours_since_access,
            "grace_period_applied": grace_period_applied,
            "grace_period_hours": self.config.grace_period_hours,
            "capped_at_max": capped_at_max,
            "max_days": self.config.max_days,
            "decay_factor": self.config.decay_factor,
            "formula": f"-{self.config.decay_factor} × log10({min(days_since_access, self.config.max_days):.2f})",
        }


def calculate_decay(
    last_access: datetime,
    decay_factor: float = 0.5,
    max_days: float = 90.0,
    current_time: datetime | None = None,
) -> float:
    """Convenience function for calculating decay penalty.

    Args:
        last_access: Timestamp of last access
        decay_factor: Decay rate multiplier (default 0.5)
        max_days: Maximum days for calculation (default 90)
        current_time: Current time for calculation (defaults to now)

    Returns:
        Decay penalty (non-positive value)

    """
    config = DecayConfig(decay_factor=decay_factor, max_days=max_days)
    calculator = DecayCalculator(config)
    return calculator.calculate(last_access, current_time)


# Common decay profiles for different use cases
AGGRESSIVE_DECAY = DecayConfig(decay_factor=1.0, max_days=30.0, grace_period_hours=0.5)

MODERATE_DECAY = DecayConfig(decay_factor=0.5, max_days=90.0, grace_period_hours=1.0)

GENTLE_DECAY = DecayConfig(decay_factor=0.25, max_days=180.0, grace_period_hours=2.0)


__all__ = [
    "DecayConfig",
    "DecayCalculator",
    "calculate_decay",
    "AGGRESSIVE_DECAY",
    "MODERATE_DECAY",
    "GENTLE_DECAY",
]
