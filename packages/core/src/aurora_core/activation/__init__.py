"""ACT-R Activation Engine Module

This module implements the ACT-R (Adaptive Control of Thought-Rational) activation
framework for memory retrieval in AURORA. The activation system determines which
code chunks are most relevant based on usage patterns, recency, and contextual relevance.

ACT-R Activation Formula:
    Total Activation = BLA + Spreading + Context Boost - Decay

Where:
    - BLA (Base-Level Activation): ln(Σ t_j^(-d)) where d=0.5 (decay rate)
    - Spreading: 0.7^(hop_count) per hop, max 3 hops
    - Context Boost: keyword_overlap × 0.5 (max)
    - Decay: -0.5 × log10(days_since_access), capped at 90 days

Components:
    - base_level: Base-level activation calculation (BLA)
    - spreading: Spreading activation via relationships
    - context_boost: Context boost from keyword overlap
    - decay: Decay penalty calculation
    - engine: Main ActivationEngine integrating all formulas
    - retrieval: Activation-based retrieval with thresholds

Usage:
    from aurora_core.activation import ActivationEngine, ActivationRetriever

    engine = ActivationEngine()
    retriever = ActivationRetriever(engine)

    # Calculate activation for a chunk
    activation_score = engine.calculate_activation(
        chunk_id="func_123",
        query_context=["database", "query", "optimization"]
    )

    # Retrieve chunks by activation
    results = retriever.retrieve(
        query="optimize database queries",
        max_results=10,
        threshold=0.3
    )
"""

# Version information
__version__ = "1.0.0"
__author__ = "AURORA Development Team"

# Module exports - will be populated as components are implemented
__all__ = [
    # Core activation components
    "ActivationEngine",
    "ActivationConfig",
    "ActivationComponents",
    "DEFAULT_CONFIG",
    "AGGRESSIVE_CONFIG",
    "CONSERVATIVE_CONFIG",
    "BLA_FOCUSED_CONFIG",
    "CONTEXT_FOCUSED_CONFIG",
    "ActivationRetriever",
    "RetrievalConfig",
    "RetrievalResult",
    "BatchRetriever",
    "ChunkData",
    # Formula components
    "BaseLevelActivation",
    "BLAConfig",
    "AccessHistoryEntry",
    "calculate_bla",
    "SpreadingActivation",
    "SpreadingConfig",
    "Relationship",
    "RelationshipGraph",
    "calculate_spreading",
    "ContextBoost",
    "ContextBoostConfig",
    "KeywordExtractor",
    "calculate_context_boost",
    "DecayCalculator",
    "DecayConfig",
    "calculate_decay",
    "AGGRESSIVE_DECAY",
    "MODERATE_DECAY",
    "GENTLE_DECAY",
    # Graph caching
    "RelationshipProvider",
    "GraphCacheConfig",
    "RelationshipGraphCache",
    "CachedSpreadingActivation",
    # Configuration
    "ActivationConfig",
]

# Import implemented components
from .base_level import AccessHistoryEntry, BaseLevelActivation, BLAConfig, calculate_bla
from .context_boost import (
    ContextBoost,
    ContextBoostConfig,
    KeywordExtractor,
    calculate_context_boost,
)
from .decay import (
    AGGRESSIVE_DECAY,
    GENTLE_DECAY,
    MODERATE_DECAY,
    DecayCalculator,
    DecayConfig,
    calculate_decay,
)
from .engine import (
    AGGRESSIVE_CONFIG,
    BLA_FOCUSED_CONFIG,
    CONSERVATIVE_CONFIG,
    CONTEXT_FOCUSED_CONFIG,
    DEFAULT_CONFIG,
    ActivationComponents,
    ActivationConfig,
    ActivationEngine,
)
from .graph_cache import (
    CachedSpreadingActivation,
    GraphCacheConfig,
    RelationshipGraphCache,
    RelationshipProvider,
)
from .retrieval import (
    ActivationRetriever,
    BatchRetriever,
    ChunkData,
    RetrievalConfig,
    RetrievalResult,
)
from .spreading import (
    Relationship,
    RelationshipGraph,
    SpreadingActivation,
    SpreadingConfig,
    calculate_spreading,
)
