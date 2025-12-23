"""Phase 8: ACT-R Pattern Caching.

This module implements the Record phase of the SOAR pipeline, which caches
successful reasoning patterns to ACT-R memory for future retrieval.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from aurora_core.chunks import ReasoningChunk
from aurora_core.types import ChunkID

if TYPE_CHECKING:
    from aurora_core.store.base import Store
    from aurora_soar.phases.collect import CollectResult
    from aurora_soar.phases.synthesize import SynthesisResult

logger = logging.getLogger(__name__)

__all__ = ["record_pattern", "RecordResult"]


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


def record_pattern(
    store: Store,
    query: str,
    complexity: str,
    decomposition: dict[str, Any],
    collect_result: CollectResult,
    synthesis_result: SynthesisResult,
) -> RecordResult:
    """Record reasoning pattern to ACT-R memory.

    This function implements the caching policy:
    - success_score ≥ 0.8: Cache and mark as pattern (high activation boost +0.2)
    - success_score ≥ 0.5: Cache for learning (small activation boost +0.05)
    - success_score < 0.5: Skip caching (but apply activation penalty -0.1 if exists)

    Args:
        store: Store instance for caching
        query: Original user query
        complexity: Query complexity level
        decomposition: Decomposition from Phase 3
        collect_result: Agent execution results from Phase 6
        synthesis_result: Synthesis result from Phase 7

    Returns:
        RecordResult with caching status and chunk ID

    Raises:
        RuntimeError: If caching fails
    """
    start_time = time.time()

    success_score = synthesis_result.confidence

    logger.info(
        f"Recording pattern: query='{query[:50]}...', "
        f"complexity={complexity}, success_score={success_score:.2f}"
    )

    # Apply caching policy
    if success_score < 0.5:
        # Don't cache low-quality patterns
        logger.info("Skipping cache (score < 0.5)")

        # TODO: If pattern already exists, apply negative activation update
        # This would require retrieving existing patterns first

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

    # Extract tool information
    tools_used = set()
    tool_sequence = []

    for output in collect_result.agent_outputs:
        if output.execution_metadata and "tools_used" in output.execution_metadata:
            for tool in output.execution_metadata["tools_used"]:
                tools_used.add(tool)

        if output.execution_metadata and "tool_sequence" in output.execution_metadata:
            tool_sequence.extend(output.execution_metadata["tool_sequence"])

    # Create ReasoningChunk
    chunk_id = f"reasoning_{uuid.uuid4().hex[:16]}"

    reasoning_chunk = ReasoningChunk(
        chunk_id=chunk_id,
        pattern=query,
        complexity=complexity,
        subgoals=decomposition.get("subgoals", []),
        execution_order=decomposition.get("execution_order", []),
        tools_used=list(tools_used),
        tool_sequence=tool_sequence,
        success_score=success_score,
        metadata={
            "decomposition_goal": decomposition.get("goal", ""),
            "synthesis_confidence": synthesis_result.confidence,
            "subgoals_completed": synthesis_result.metadata.get("subgoals_completed", 0),
            "subgoals_partial": synthesis_result.metadata.get("subgoals_partial", 0),
            "subgoals_failed": synthesis_result.metadata.get("subgoals_failed", 0),
            "total_files_modified": synthesis_result.metadata.get("total_files_modified", 0),
        },
    )

    # Save to store
    try:
        store.save_chunk(reasoning_chunk)
        logger.info(f"Cached ReasoningChunk: {chunk_id}")
    except Exception as e:
        logger.error(f"Failed to cache ReasoningChunk: {e}")
        raise RuntimeError(f"Failed to cache reasoning pattern: {e}") from e

    # Determine if this should be marked as a reusable pattern
    pattern_marked = success_score >= 0.8
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
        f"Pattern cached: chunk_id={chunk_id}, "
        f"marked_as_pattern={pattern_marked}, "
        f"activation_update=+{activation_update}"
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
