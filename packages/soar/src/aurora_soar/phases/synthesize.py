"""Phase 7: Result Synthesis.

This module implements the Synthesize phase of the SOAR pipeline, which combines
agent outputs into a coherent answer with traceability.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from aurora_reasoning import synthesize_results as reasoning_synthesize


if TYPE_CHECKING:
    from aurora_reasoning import LLMClient
    from aurora_soar.phases.collect import CollectResult

logger = logging.getLogger(__name__)

__all__ = ["synthesize_results", "SynthesisResult"]


class SynthesisResult:
    """Result of the Synthesize phase.

    Attributes:
        answer: Natural language synthesized answer
        confidence: Overall confidence score (0.0-1.0)
        traceability: List of claim-to-source mappings
        metadata: Synthesis metadata (retry count, verification scores, etc.)
        timing: Timing information

    """

    def __init__(
        self,
        answer: str,
        confidence: float,
        traceability: list[dict[str, Any]],
        metadata: dict[str, Any],
        timing: dict[str, Any],
    ):
        self.answer = answer
        self.confidence = confidence
        self.traceability = traceability
        self.metadata = metadata
        self.timing = timing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "traceability": self.traceability,
            "metadata": self.metadata,
            "timing": self.timing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SynthesisResult:
        """Create from dictionary representation."""
        return cls(
            answer=data["answer"],
            confidence=data["confidence"],
            traceability=data.get("traceability", []),
            metadata=data.get("metadata", {}),
            timing=data.get("timing", {}),
        )


def synthesize_results(
    llm_client: LLMClient,
    query: str,
    collect_result: CollectResult,
    decomposition: dict[str, Any],
) -> SynthesisResult:
    """Synthesize agent outputs into final answer.

    This function:
    1. Aggregates metadata from all agent executions
    2. Prepares agent outputs for synthesis
    3. Calls reasoning.synthesize_results for LLM-based synthesis
    4. Returns SynthesisResult with timing information

    Args:
        llm_client: LLM client to use for synthesis
        query: Original user query
        collect_result: Agent execution results from Phase 6
        decomposition: Decomposition from Phase 3

    Returns:
        SynthesisResult with answer, confidence, and traceability

    Raises:
        RuntimeError: If synthesis fails after retries

    """
    start_time = time.time()

    logger.info(f"Starting synthesis for {len(collect_result.agent_outputs)} agent outputs")

    # Prepare agent outputs for synthesis
    agent_outputs = []
    for output in collect_result.agent_outputs:
        agent_outputs.append(
            {
                "subgoal_index": output.subgoal_index,
                "agent_name": output.agent_id,
                "summary": output.summary,
                "confidence": output.confidence,
                "success": output.success,
                "data": output.data or {},
            },
        )

    # Aggregate metadata
    total_files_modified = 0
    user_interactions_count = 0
    subgoals_completed = 0
    subgoals_partial = 0
    subgoals_failed = 0

    for output in collect_result.agent_outputs:
        if output.success:
            subgoals_completed += 1
        elif output.execution_metadata and output.execution_metadata.get("partial_success"):
            subgoals_partial += 1
        else:
            subgoals_failed += 1

        # Count files modified
        if output.data and "files_modified" in output.data:
            total_files_modified += len(output.data["files_modified"])

        # Count user interactions
        if output.execution_metadata and "user_interactions" in output.execution_metadata:
            user_interactions_count += len(output.execution_metadata["user_interactions"])

    # Call reasoning synthesis
    try:
        synthesis_result = reasoning_synthesize(
            llm_client=llm_client,
            query=query,
            agent_outputs=agent_outputs,
            decomposition=decomposition,
            max_retries=2,
        )
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise RuntimeError(f"Failed to synthesize agent outputs: {e}") from e

    end_time = time.time()
    duration_ms = int((end_time - start_time) * 1000)

    logger.info(
        f"Synthesis complete: confidence={synthesis_result.confidence:.2f}, "
        f"duration={duration_ms}ms, "
        f"retry_count={synthesis_result.metadata.get('retry_count', 0)}",
    )

    # Add aggregated metadata
    synthesis_result.metadata.update(
        {
            "subgoals_completed": subgoals_completed,
            "subgoals_partial": subgoals_partial,
            "subgoals_failed": subgoals_failed,
            "total_files_modified": total_files_modified,
            "user_interactions_count": user_interactions_count,
        },
    )

    # Estimate token counts for cost tracking
    # Use rough approximation: 1 token ≈ 4 characters for English text
    prompt_text = f"{query} {decomposition.get('goal', '')} {len(agent_outputs)} outputs"
    input_tokens = len(prompt_text) // 4
    output_tokens = len(synthesis_result.answer) // 4

    return SynthesisResult(
        answer=synthesis_result.answer,
        confidence=synthesis_result.confidence,
        traceability=synthesis_result.traceability,
        metadata=synthesis_result.metadata,
        timing={
            "duration_ms": duration_ms,
            "started_at": start_time,
            "completed_at": end_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )
