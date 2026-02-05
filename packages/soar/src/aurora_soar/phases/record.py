"""Phase 8: ACT-R Pattern Caching.

This module implements the Record phase of the SOAR pipeline, which caches
successful reasoning patterns to ACT-R memory for future retrieval.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aurora_core.chunks import ReasoningChunk
from aurora_core.types import ChunkID


if TYPE_CHECKING:
    from aurora_core.store.base import Store
    from aurora_soar.phases.synthesize import SynthesisResult

logger = logging.getLogger(__name__)

__all__ = ["RecordResult", "SummaryRecord", "record_pattern_lightweight"]


@dataclass
class SummaryRecord:
    """Lightweight record for caching query summaries.

    A minimal record format for caching successful query results.
    Stores only essential information for future retrieval.

    Attributes:
        id: Unique identifier for the record
        query: Original query (max 200 chars)
        summary: Brief summary of result (max 500 chars)
        confidence: Confidence score (0-1) from synthesis
        log_file: Path to full session log
        keywords: Extracted keywords for retrieval
        timestamp: Unix timestamp of record creation

    """

    id: str
    query: str
    summary: str
    confidence: float
    log_file: str
    keywords: list[str]
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "query": self.query,
            "summary": self.summary,
            "confidence": self.confidence,
            "log_file": self.log_file,
            "keywords": self.keywords,
            "timestamp": self.timestamp,
        }


class RecordResult:
    """Result of the Record phase.

    Attributes:
        cached: Whether pattern was cached
        reasoning_chunk_id: ID of cached ReasoningChunk (if cached)
        pattern_marked: Whether pattern was marked as reusable
        activation_update: Activation adjustment applied
        timing: Timing information

    """

    def __init__(
        self,
        cached: bool,
        reasoning_chunk_id: str | None,
        pattern_marked: bool,
        activation_update: float,
        timing: dict[str, Any],
    ):
        self.cached = cached
        self.reasoning_chunk_id = reasoning_chunk_id
        self.pattern_marked = pattern_marked
        self.activation_update = activation_update
        self.timing = timing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "cached": self.cached,
            "reasoning_chunk_id": self.reasoning_chunk_id,
            "pattern_marked": self.pattern_marked,
            "activation_update": self.activation_update,
            "timing": self.timing,
        }


def _extract_keywords(query: str, summary: str) -> list[str]:
    """Extract keywords from query and summary for retrieval.

    Simple keyword extraction:
    1. Take first 200 chars of query + first 100 chars of summary
    2. Split on whitespace
    3. Filter common stop words
    4. Keep unique words
    5. Return top 10 by frequency

    Args:
        query: Original query text
        summary: Summary text from synthesis

    Returns:
        List of up to 10 keyword strings

    """
    # Common stop words to filter
    stop_words = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "and",
        "or",
        "but",
        "not",
        "this",
        "that",
        "it",
    }

    # Combine query (first 200 chars) and summary (first 100 chars)
    text = query[:200] + " " + summary[:100]

    # Split on whitespace and lowercase
    words = text.lower().split()

    # Filter stop words and short words
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Count frequency and take top 10 unique
    from collections import Counter

    word_counts = Counter(keywords)
    top_keywords = [word for word, _ in word_counts.most_common(10)]

    return top_keywords


def record_pattern_lightweight(
    store: Store,
    query: str,
    synthesis_result: SynthesisResult,
    log_path: str,
) -> RecordResult:
    """Lightweight pattern recording with minimal overhead.

    Simplified caching that stores only essential information:
    - Query (truncated to 200 chars)
    - Summary (truncated to 500 chars)
    - Confidence score
    - Log file path
    - Keywords for retrieval

    Caching policy based on confidence:
    - confidence >= 0.8: Cache as reusable pattern (+0.2 activation)
    - confidence >= 0.5: Cache for learning (+0.05 activation)
    - confidence < 0.5: Skip caching

    Args:
        store: Store instance for caching
        query: Original user query
        synthesis_result: Synthesis result with confidence and summary
        log_path: Path to full session log file

    Returns:
        RecordResult with caching status and metadata

    Raises:
        RuntimeError: If caching fails

    """
    start_time = time.time()

    confidence = synthesis_result.confidence
    summary = synthesis_result.summary if hasattr(synthesis_result, "summary") else ""

    logger.info(
        f"Recording pattern (lightweight): query='{query[:50]}...', confidence={confidence:.2f}",
    )

    # Apply caching policy
    if confidence < 0.5:
        # Don't cache low-quality patterns
        logger.info("Skipping cache (confidence < 0.5)")

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        return RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=-0.1,
            timing={
                "duration_ms": duration_ms,
                "started_at": start_time,
                "completed_at": end_time,
            },
        )

    # Truncate query and summary
    query_truncated = query[:200]
    summary_truncated = summary[:500]

    # Extract keywords
    keywords = _extract_keywords(query, summary)

    # Create unique ID
    chunk_id = f"summary_{uuid.uuid4().hex[:16]}"

    # Create ReasoningChunk with minimal data
    reasoning_chunk = ReasoningChunk(
        chunk_id=chunk_id,
        pattern=query_truncated,
        complexity="SIMPLE",  # Default for lightweight mode
        subgoals=[],  # Not stored in lightweight mode
        execution_order=[],  # Not stored in lightweight mode
        tools_used=[],  # Not stored in lightweight mode
        tool_sequence=[],  # Not stored in lightweight mode
        success_score=confidence,
        metadata={
            "summary": summary_truncated,
            "log_file": log_path,
            "keywords": keywords,
            "lightweight": True,
        },
    )

    # Save to store
    try:
        store.save_chunk(reasoning_chunk)
        logger.info(f"Cached SummaryRecord: {chunk_id}")
    except Exception as e:
        logger.error(f"Failed to cache SummaryRecord: {e}")
        raise RuntimeError(f"Failed to cache pattern: {e}") from e

    # Determine activation boost
    pattern_marked = confidence >= 0.8
    activation_update = 0.2 if pattern_marked else 0.05

    # Update activation
    try:
        store.update_activation(ChunkID(chunk_id), activation_update)
        logger.debug(f"Updated activation for {chunk_id}: +{activation_update}")
    except Exception as e:
        logger.warning(f"Failed to update activation: {e}")

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    logger.info(
        f"Pattern cached (lightweight): chunk_id={chunk_id}, "
        f"marked_as_pattern={pattern_marked}, "
        f"activation_update=+{activation_update}",
    )

    return RecordResult(
        cached=True,
        reasoning_chunk_id=chunk_id,
        pattern_marked=pattern_marked,
        activation_update=activation_update,
        timing={
            "duration_ms": duration_ms,
            "started_at": start_time,
            "completed_at": end_time,
        },
    )
