"""Base-Level Activation (BLA) Formula Implementation

This module implements the ACT-R Base-Level Activation formula, which calculates
activation based on the frequency and recency of chunk access patterns.

ACT-R BLA Formula:
    BLA = ln(Σ t_j^(-d))

Where:
    - t_j: time since j-th access (in seconds)
    - d: decay rate (default 0.5, standard ACT-R value)
    - Σ: sum over all past accesses

The formula captures two key insights from human memory research:
1. Recency: More recent accesses contribute more to activation
2. Frequency: More accesses lead to higher activation
3. Power law decay: Activation decays following a power law (t^-d)

Reference:
    Anderson, J. R., & Lebiere, C. (1998). The Atomic Components of Thought.
    Lawrence Erlbaum Associates. Chapter 3: Base-Level Learning.
"""

import math
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


class AccessHistoryEntry(BaseModel):
    """Represents a single access to a chunk in memory.

    Attributes:
        timestamp: UTC timestamp when the chunk was accessed
        context: Optional context information (e.g., query terms)

    """

    timestamp: datetime = Field(description="UTC timestamp of the access")
    context: str | None = Field(
        default=None,
        description="Optional context information for this access",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class BLAConfig(BaseModel):
    """Configuration for Base-Level Activation calculation.

    Attributes:
        decay_rate: The decay rate (d) in the power law formula (default 0.5)
        min_activation: Minimum activation value to return (prevents log(0))
        default_activation: Activation for chunks with no access history

    """

    decay_rate: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Decay rate in the power law (standard ACT-R value is 0.5)",
    )
    min_activation: float = Field(default=-10.0, description="Minimum activation value (log space)")
    default_activation: float = Field(
        default=-5.0,
        description="Default activation for never-accessed chunks",
    )


class BaseLevelActivation:
    """Calculates Base-Level Activation using the ACT-R formula.

    The BLA component reflects the frequency and recency of chunk access.
    It implements the power law of practice and the power law of forgetting,
    both fundamental patterns in human memory.

    Examples:
        >>> bla = BaseLevelActivation()
        >>> history = [
        ...     AccessHistoryEntry(timestamp=datetime.now(timezone.utc)),
        ...     AccessHistoryEntry(timestamp=datetime.now(timezone.utc) - timedelta(hours=1)),
        ...     AccessHistoryEntry(timestamp=datetime.now(timezone.utc) - timedelta(days=1))
        ... ]
        >>> activation = bla.calculate(history)
        >>> print(f"BLA: {activation:.3f}")

    """

    def __init__(self, config: BLAConfig | None = None):
        """Initialize the Base-Level Activation calculator.

        Args:
            config: Configuration for BLA calculation (uses defaults if None)

        """
        self.config = config or BLAConfig()

    def calculate(
        self,
        access_history: list[AccessHistoryEntry],
        current_time: datetime | None = None,
    ) -> float:
        """Calculate Base-Level Activation for a chunk.

        Args:
            access_history: List of past accesses to this chunk
            current_time: Current time for calculating recency (defaults to now)

        Returns:
            BLA value (log space, typically in range [-10, 5])

        Notes:
            - Returns default_activation if no access history
            - Clamps result to min_activation to prevent extreme negative values
            - Uses power law: BLA = ln(Σ t_j^(-d))

        """
        if not access_history:
            return self.config.default_activation

        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        # Calculate power law sum: Σ t_j^(-d)
        power_law_sum = 0.0
        decay_rate = self.config.decay_rate

        for entry in access_history:
            # Calculate time since access in seconds
            time_delta = (current_time - entry.timestamp).total_seconds()

            # Prevent division by zero or negative time
            if time_delta <= 0:
                time_delta = 1.0  # Treat as just accessed (1 second ago)

            # Add power law term: t^(-d)
            power_law_sum += math.pow(time_delta, -decay_rate)

        # Calculate BLA as natural log of sum
        bla = math.log(power_law_sum) if power_law_sum > 0 else self.config.default_activation

        # Clamp to minimum activation
        return max(bla, self.config.min_activation)

    def calculate_from_timestamps(
        self,
        timestamps: list[datetime],
        current_time: datetime | None = None,
    ) -> float:
        """Convenience method to calculate BLA from a list of timestamps.

        Args:
            timestamps: List of access timestamps
            current_time: Current time for calculating recency (defaults to now)

        Returns:
            BLA value (log space)

        """
        history = [AccessHistoryEntry(timestamp=ts) for ts in timestamps]
        return self.calculate(history, current_time)

    def calculate_from_access_counts(
        self,
        access_count: int,
        last_access: datetime,
        creation_time: datetime | None = None,
        current_time: datetime | None = None,
    ) -> float:
        """Approximate BLA when only access count and last access are known.

        This is a simplified approximation that assumes accesses were evenly
        distributed between creation and last access. Use full history when available.

        Args:
            access_count: Total number of times chunk was accessed
            last_access: Timestamp of most recent access
            creation_time: When chunk was created (defaults to 7 days before last_access)
            current_time: Current time for calculating recency (defaults to now)

        Returns:
            Approximate BLA value

        """
        if access_count == 0:
            return self.config.default_activation

        if current_time is None:
            current_time = datetime.now(timezone.utc)
        elif current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        if creation_time is None:
            # Assume chunk was created 7 days before last access
            from datetime import timedelta

            creation_time = last_access - timedelta(days=7)

        # Generate synthetic access history with exponential spacing
        # (more recent accesses weighted more heavily)
        history: list[AccessHistoryEntry] = []

        if access_count == 1:
            history = [AccessHistoryEntry(timestamp=last_access)]
        else:
            time_span = (last_access - creation_time).total_seconds()

            # Create exponentially spaced accesses
            for i in range(access_count):
                # Exponential spacing: more accesses near last_access
                fraction = math.pow(i / (access_count - 1), 2.0)
                offset_seconds = time_span * fraction

                timestamp = creation_time + timedelta(seconds=offset_seconds)
                history.append(AccessHistoryEntry(timestamp=timestamp))

        return self.calculate(history, current_time)


def calculate_bla(
    access_history: list[AccessHistoryEntry],
    decay_rate: float = 0.5,
    current_time: datetime | None = None,
) -> float:
    """Convenience function for calculating BLA with default configuration.

    Args:
        access_history: List of past accesses
        decay_rate: Decay rate parameter (default 0.5)
        current_time: Current time for recency calculation

    Returns:
        BLA value (log space)

    """
    config = BLAConfig(decay_rate=decay_rate)
    calculator = BaseLevelActivation(config)
    return calculator.calculate(access_history, current_time)
