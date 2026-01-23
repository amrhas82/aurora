"""ACT-R Activation Engine

This module integrates all ACT-R activation components into a unified
ActivationEngine that calculates total activation for memory chunks.

Total Activation Formula:
    Total = BLA + Spreading + Context Boost - Decay

Where:
    - BLA (Base-Level Activation): Frequency and recency of access
    - Spreading: Activation from related chunks
    - Context Boost: Relevance to current query
    - Decay: Penalty for time since last access

The engine provides a simple interface for calculating activation scores
that can be used for memory retrieval and ranking.

Reference:
    Anderson, J. R. (2007). How Can the Human Mind Occur in the Physical Universe?
    Oxford University Press.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aurora_core.activation.base_level import AccessHistoryEntry, BaseLevelActivation, BLAConfig
from aurora_core.activation.context_boost import ContextBoost, ContextBoostConfig
from aurora_core.activation.decay import DecayCalculator, DecayConfig
from aurora_core.activation.spreading import RelationshipGraph, SpreadingActivation, SpreadingConfig

logger = logging.getLogger(__name__)


# Module-level cache for ActivationEngine instances (singleton per db_path)
_engine_cache: dict[str, "ActivationEngine"] = {}
_engine_cache_lock = threading.Lock()


class ActivationConfig(BaseModel):
    """Configuration for the ActivationEngine.

    This consolidates all activation component configurations into a
    single config object with sensible defaults based on ACT-R research.

    Attributes:
        bla_config: Base-level activation configuration
        spreading_config: Spreading activation configuration
        context_config: Context boost configuration
        decay_config: Decay calculation configuration
        enable_bla: Whether to include BLA in total activation
        enable_spreading: Whether to include spreading in total activation
        enable_context: Whether to include context boost in total activation
        enable_decay: Whether to include decay in total activation

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bla_config: BLAConfig = Field(default_factory=BLAConfig)
    spreading_config: SpreadingConfig = Field(default_factory=SpreadingConfig)
    context_config: ContextBoostConfig = Field(default_factory=ContextBoostConfig)
    decay_config: DecayConfig = Field(default_factory=DecayConfig)

    enable_bla: bool = Field(default=True, description="Include base-level activation in total")
    enable_spreading: bool = Field(
        default=True,
        description="Include spreading activation in total",
    )
    enable_context: bool = Field(default=True, description="Include context boost in total")
    enable_decay: bool = Field(default=True, description="Include decay penalty in total")


class ActivationComponents(BaseModel):
    """Individual activation components for a chunk.

    This breaks down the total activation into its constituent parts,
    useful for debugging and understanding why a chunk was retrieved.

    Attributes:
        bla: Base-level activation component
        spreading: Spreading activation component
        context_boost: Context boost component
        decay: Decay penalty component
        total: Total activation (sum of all components)

    """

    bla: float = Field(default=0.0, description="Base-level activation")
    spreading: float = Field(default=0.0, description="Spreading activation")
    context_boost: float = Field(default=0.0, description="Context boost")
    decay: float = Field(default=0.0, description="Decay penalty")
    total: float = Field(default=0.0, description="Total activation")

    class Config:
        frozen = False  # Allow updates


class ActivationEngine:
    """Unified engine for calculating ACT-R activation.

    This engine integrates all activation components (BLA, spreading,
    context boost, decay) to compute total activation scores for chunks.

    Examples:
        >>> from datetime import datetime, timedelta, timezone
        >>> engine = ActivationEngine()
        >>>
        >>> # Calculate activation with all components
        >>> access_history = [
        ...     AccessHistoryEntry(timestamp=datetime.now(timezone.utc) - timedelta(days=1)),
        ...     AccessHistoryEntry(timestamp=datetime.now(timezone.utc) - timedelta(days=7))
        ... ]
        >>>
        >>> activation = engine.calculate_total(
        ...     access_history=access_history,
        ...     last_access=datetime.now(timezone.utc) - timedelta(days=1),
        ...     spreading_activation=0.5,
        ...     query_keywords={'database', 'optimize'},
        ...     chunk_keywords={'database', 'query', 'performance'}
        ... )
        >>> print(f"Total activation: {activation.total:.3f}")

    """

    def __init__(self, config: ActivationConfig | None = None):
        """Initialize the activation engine.

        Args:
            config: Configuration for all activation components

        """
        self.config = config or ActivationConfig()

        # Initialize component calculators
        self.bla_calculator = BaseLevelActivation(self.config.bla_config)
        self.spreading_calculator = SpreadingActivation(self.config.spreading_config)
        self.context_calculator = ContextBoost(self.config.context_config)
        self.decay_calculator = DecayCalculator(self.config.decay_config)

    def calculate_total(
        self,
        access_history: list[AccessHistoryEntry] | None = None,
        last_access: datetime | None = None,
        spreading_activation: float = 0.0,
        query_keywords: set[str] | None = None,
        chunk_keywords: set[str] | None = None,
        current_time: datetime | None = None,
    ) -> ActivationComponents:
        """Calculate total activation with all components.

        Args:
            access_history: List of past accesses for BLA calculation
            last_access: Most recent access timestamp for decay calculation
            spreading_activation: Pre-calculated spreading activation value
            query_keywords: Keywords from the query for context boost
            chunk_keywords: Keywords from the chunk for context boost
            current_time: Current time for calculations (defaults to now)

        Returns:
            ActivationComponents with all component values and total

        Notes:
            - Components can be disabled via config (enable_* flags)
            - Missing data for a component results in 0.0 for that component
            - Total = BLA + Spreading + Context - Decay

        """
        components = ActivationComponents()

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Calculate BLA
        if self.config.enable_bla and access_history is not None:
            components.bla = self.bla_calculator.calculate(
                access_history=access_history,
                current_time=current_time,
            )

        # Add spreading activation (pre-calculated)
        if self.config.enable_spreading:
            components.spreading = spreading_activation

        # Calculate context boost
        if self.config.enable_context and query_keywords and chunk_keywords:
            components.context_boost = self.context_calculator.calculate(
                query_keywords=query_keywords,
                chunk_keywords=chunk_keywords,
            )

        # Calculate decay penalty
        if self.config.enable_decay and last_access is not None:
            components.decay = self.decay_calculator.calculate(
                last_access=last_access,
                current_time=current_time,
            )

        # Calculate total activation
        components.total = (
            components.bla
            + components.spreading
            + components.context_boost
            - abs(components.decay)  # Decay is negative, so we subtract its absolute value
        )

        return components

    def calculate_bla_only(
        self,
        access_history: list[AccessHistoryEntry],
        current_time: datetime | None = None,
    ) -> float:
        """Calculate only base-level activation.

        Args:
            access_history: List of past accesses
            current_time: Current time (defaults to now)

        Returns:
            BLA value

        """
        return self.bla_calculator.calculate(access_history, current_time)

    def calculate_spreading_only(
        self,
        source_chunks: list[str],
        graph: RelationshipGraph,
        bidirectional: bool = True,
    ) -> dict[str, float]:
        """Calculate only spreading activation.

        Args:
            source_chunks: Starting chunks for spreading
            graph: Relationship graph to traverse
            bidirectional: Spread along both directions

        Returns:
            Dictionary mapping chunk_id -> spreading_activation

        """
        return self.spreading_calculator.calculate(
            source_chunks=source_chunks,
            graph=graph,
            bidirectional=bidirectional,
        )

    def calculate_context_only(self, query_keywords: set[str], chunk_keywords: set[str]) -> float:
        """Calculate only context boost.

        Args:
            query_keywords: Keywords from query
            chunk_keywords: Keywords from chunk

        Returns:
            Context boost value

        """
        return self.context_calculator.calculate(query_keywords, chunk_keywords)

    def calculate_decay_only(
        self,
        last_access: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Calculate only decay penalty.

        Args:
            last_access: Timestamp of last access
            current_time: Current time (defaults to now)

        Returns:
            Decay penalty (non-positive value)

        """
        return self.decay_calculator.calculate(last_access, current_time)

    def explain_activation(
        self,
        access_history: list[AccessHistoryEntry] | None = None,
        last_access: datetime | None = None,
        spreading_activation: float = 0.0,
        query_keywords: set[str] | None = None,
        chunk_keywords: set[str] | None = None,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Explain how activation was calculated.

        Provides detailed breakdown of each component for debugging
        and understanding retrieval behavior.

        Args:
            access_history: List of past accesses
            last_access: Most recent access timestamp
            spreading_activation: Pre-calculated spreading value
            query_keywords: Keywords from query
            chunk_keywords: Keywords from chunk
            current_time: Current time (defaults to now)

        Returns:
            Dictionary with detailed explanation:
                - components: ActivationComponents object
                - bla_details: BLA calculation details
                - context_details: Context boost details (if applicable)
                - decay_details: Decay calculation details (if applicable)
                - enabled_components: List of enabled component names

        """
        components = self.calculate_total(
            access_history=access_history,
            last_access=last_access,
            spreading_activation=spreading_activation,
            query_keywords=query_keywords,
            chunk_keywords=chunk_keywords,
            current_time=current_time,
        )

        enabled_components: list[str] = []
        explanation: dict[str, Any] = {
            "components": components.model_dump(),
            "enabled_components": enabled_components,
        }

        # Add component-specific details
        if self.config.enable_bla:
            enabled_components.append("bla")
            explanation["bla_details"] = {
                "access_count": len(access_history) if access_history else 0,
                "formula": "ln(Σ t_j^(-d)) where d=0.5",
            }

        if self.config.enable_spreading:
            enabled_components.append("spreading")
            explanation["spreading_details"] = {
                "value": spreading_activation,
                "formula": "weight × 0.7^(hop_count)",
            }

        if self.config.enable_context and query_keywords and chunk_keywords:
            enabled_components.append("context")
            matching = query_keywords & chunk_keywords
            explanation["context_details"] = {
                "query_keywords": sorted(query_keywords),
                "chunk_keywords": sorted(chunk_keywords),
                "matching_keywords": sorted(matching),
                "overlap_fraction": len(matching) / len(query_keywords) if query_keywords else 0.0,
                "formula": "overlap_fraction × 0.5",
            }

        if self.config.enable_decay and last_access:
            enabled_components.append("decay")
            decay_explanation = self.decay_calculator.explain_decay(last_access, current_time)
            explanation["decay_details"] = decay_explanation

        return explanation

    def update_config(
        self,
        bla_config: BLAConfig | None = None,
        spreading_config: SpreadingConfig | None = None,
        context_config: ContextBoostConfig | None = None,
        decay_config: DecayConfig | None = None,
    ) -> None:
        """Update component configurations.

        Args:
            bla_config: New BLA configuration
            spreading_config: New spreading configuration
            context_config: New context boost configuration
            decay_config: New decay configuration

        """
        if bla_config:
            self.config.bla_config = bla_config
            self.bla_calculator = BaseLevelActivation(bla_config)

        if spreading_config:
            self.config.spreading_config = spreading_config
            self.spreading_calculator = SpreadingActivation(spreading_config)

        if context_config:
            self.config.context_config = context_config
            self.context_calculator = ContextBoost(context_config)

        if decay_config:
            self.config.decay_config = decay_config
            self.decay_calculator = DecayCalculator(decay_config)


# Preset configurations for common use cases
DEFAULT_CONFIG = ActivationConfig()

# Aggressive configuration (strong influence from all components)
AGGRESSIVE_CONFIG = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.6),
    spreading_config=SpreadingConfig(spread_factor=0.8, max_hops=3),
    context_config=ContextBoostConfig(boost_factor=0.8),
    decay_config=DecayConfig(decay_factor=1.0, max_days=30.0),
)

# Conservative configuration (minimal influence from components)
CONSERVATIVE_CONFIG = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.4),
    spreading_config=SpreadingConfig(spread_factor=0.6, max_hops=2),
    context_config=ContextBoostConfig(boost_factor=0.3),
    decay_config=DecayConfig(decay_factor=0.25, max_days=180.0),
)

# BLA-focused configuration (emphasize frequency/recency, minimize others)
BLA_FOCUSED_CONFIG = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.5),
    spreading_config=SpreadingConfig(spread_factor=0.5, max_hops=2),
    context_config=ContextBoostConfig(boost_factor=0.2),
    decay_config=DecayConfig(decay_factor=0.3, max_days=90.0),
    enable_spreading=False,  # Disable spreading for pure BLA
)

# Context-focused configuration (emphasize relevance to query)
CONTEXT_FOCUSED_CONFIG = ActivationConfig(
    bla_config=BLAConfig(decay_rate=0.3),
    spreading_config=SpreadingConfig(spread_factor=0.6, max_hops=2),
    context_config=ContextBoostConfig(boost_factor=1.0),
    decay_config=DecayConfig(decay_factor=0.3, max_days=120.0),
)


def get_cached_engine(store: Any, config: ActivationConfig | None = None) -> ActivationEngine:
    """Get or create cached ActivationEngine instance.

    Returns cached engine if one exists for the given db_path (singleton pattern),
    otherwise creates a new one and caches it. Thread-safe.

    Args:
        store: Storage backend (must have db_path attribute)
        config: Activation configuration (optional, uses default if not provided)

    Returns:
        Cached or new ActivationEngine instance (singleton per db_path)

    """
    # Get db_path from store
    db_path = getattr(store, "db_path", ":memory:")

    with _engine_cache_lock:
        # Check cache
        if db_path in _engine_cache:
            logger.debug(f"Reusing cached ActivationEngine for db_path={db_path}")
            return _engine_cache[db_path]

        # Cache miss - create new engine
        logger.debug(f"Creating new ActivationEngine for db_path={db_path}")
        engine = ActivationEngine(config=config)

        # Cache it
        _engine_cache[db_path] = engine

        return engine


__all__ = [
    "ActivationConfig",
    "ActivationComponents",
    "ActivationEngine",
    "get_cached_engine",
    "DEFAULT_CONFIG",
    "AGGRESSIVE_CONFIG",
    "CONSERVATIVE_CONFIG",
    "BLA_FOCUSED_CONFIG",
    "CONTEXT_FOCUSED_CONFIG",
]
