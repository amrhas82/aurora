"""Phase 9: Response Formatting.

This module implements the Respond phase of the SOAR pipeline, which formats
the final response with appropriate verbosity level (QUIET, NORMAL, VERBOSE, JSON).
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from aurora_soar.phases.record import RecordResult
    from aurora_soar.phases.synthesize import SynthesisResult

__all__ = ["format_response", "Verbosity", "ResponseResult"]


def _make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format.

    Recursively converts dataclasses, lists, and dicts to JSON-compatible types.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    if isinstance(obj, Enum):
        return obj.value
    # For other types, try to convert to string
    return str(obj)


class Verbosity(str, Enum):
    """Output verbosity levels."""

    QUIET = "quiet"  # Single line with score
    NORMAL = "normal"  # Phase progress with key metrics
    VERBOSE = "verbose"  # Full trace with detailed metadata
    JSON = "json"  # Structured JSON logs for each phase


class ResponseResult:
    """Result of the Respond phase.

    Attributes:
        formatted_output: Formatted response string
        raw_data: Complete structured data (for JSON mode or programmatic access)

    """

    def __init__(
        self,
        formatted_output: str,
        raw_data: dict[str, Any],
    ):
        self.formatted_output = formatted_output
        self.raw_data = raw_data

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return self.raw_data


def format_response(
    synthesis_result: SynthesisResult,
    record_result: RecordResult,
    phase_metadata: dict[str, Any],
    verbosity: Verbosity = Verbosity.NORMAL,
) -> ResponseResult:
    """Format final response with appropriate verbosity.

    Args:
        synthesis_result: Synthesis result from Phase 7
        record_result: Recording result from Phase 8
        phase_metadata: Aggregated metadata from all phases (timing, costs, etc.)
        verbosity: Output verbosity level

    Returns:
        ResponseResult with formatted output and raw data

    """
    # Build complete response data structure
    raw_data = {
        "answer": synthesis_result.answer,
        "confidence": synthesis_result.confidence,
        "overall_score": synthesis_result.confidence,
        "reasoning_trace": {
            "traceability": synthesis_result.traceability,
            "synthesis_metadata": synthesis_result.metadata,
        },
        "metadata": {
            "cached": record_result.cached,
            "reasoning_chunk_id": record_result.reasoning_chunk_id,
            "pattern_marked": record_result.pattern_marked,
            **phase_metadata,
        },
    }

    # Format based on verbosity level
    if verbosity == Verbosity.QUIET:
        formatted_output = _format_quiet(synthesis_result)
    elif verbosity == Verbosity.NORMAL:
        formatted_output = _format_normal(synthesis_result, record_result, phase_metadata)
    elif verbosity == Verbosity.VERBOSE:
        formatted_output = _format_verbose(synthesis_result, record_result, phase_metadata)
    else:  # JSON
        # Convert any non-serializable objects (like dataclasses) to dicts
        serializable_data = _make_json_serializable(raw_data)
        formatted_output = json.dumps(serializable_data, indent=2)

    return ResponseResult(
        formatted_output=formatted_output,
        raw_data=raw_data,
    )


def _format_quiet(synthesis_result: SynthesisResult) -> str:
    """Format QUIET output: single line with score.

    Args:
        synthesis_result: Synthesis result

    Returns:
        Single line formatted string

    """
    score = synthesis_result.confidence
    status = "✓" if score >= 0.7 else "⚠" if score >= 0.5 else "✗"

    return f"{status} Score: {score:.2f} | {synthesis_result.answer[:100]}..."


def _format_normal(
    synthesis_result: SynthesisResult,
    record_result: RecordResult,
    phase_metadata: dict[str, Any],
) -> str:
    """Format NORMAL output: phase progress with key metrics.

    Args:
        synthesis_result: Synthesis result
        record_result: Recording result
        phase_metadata: Aggregated phase metadata

    Returns:
        Multi-line formatted string

    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("SOAR PIPELINE RESULT")
    lines.append("=" * 80)

    # Answer
    lines.append("\nANSWER:")
    lines.append(synthesis_result.answer)

    # Key Metrics
    lines.append("\n" + "-" * 80)
    lines.append("KEY METRICS:")
    lines.append(f"  Confidence: {synthesis_result.confidence:.2f}")
    lines.append(
        f"  Subgoals: {synthesis_result.metadata.get('subgoals_completed', 0)} completed, "
        f"{synthesis_result.metadata.get('subgoals_partial', 0)} partial, "
        f"{synthesis_result.metadata.get('subgoals_failed', 0)} failed",
    )
    lines.append(f"  Files Modified: {synthesis_result.metadata.get('total_files_modified', 0)}")

    # Subgoal Breakdown (if available)
    subgoal_breakdown = _extract_subgoal_breakdown(phase_metadata)
    if subgoal_breakdown:
        lines.append("\n" + "-" * 80)
        lines.append("SUBGOAL BREAKDOWN:")
        for sg in subgoal_breakdown:
            critical_marker = " [CRITICAL]" if sg.get("is_critical") else ""
            # Handle both int (0-indexed) and string ("sg-1") dependency formats
            deps_list = sg.get("depends_on", [])
            if deps_list:
                formatted_deps = []
                for d in deps_list:
                    if isinstance(d, int):
                        formatted_deps.append(str(d + 1))  # Convert 0-indexed to 1-indexed
                    elif isinstance(d, str):
                        # Extract number from "sg-N" format or use as-is
                        if d.startswith("sg-"):
                            formatted_deps.append(d[3:])  # Extract N from "sg-N"
                        else:
                            formatted_deps.append(d)
                    else:
                        formatted_deps.append(str(d))
                deps = f" (depends on: {', '.join(formatted_deps)})"
            else:
                deps = ""
            lines.append(f"  {sg['index']}. {sg['description'][:70]}{critical_marker}")
            lines.append(f"     Agent: {sg['agent']}{deps}")

    # Phase Summary
    if "phases" in phase_metadata:
        lines.append("\nPHASE SUMMARY:")
        for phase_name, phase_data in phase_metadata["phases"].items():
            # Skip non-dict phase data (e.g., error_details string)
            if not isinstance(phase_data, dict):
                continue
            duration = phase_data.get("duration_ms", 0)
            lines.append(f"  {phase_name}: {duration}ms")

    # Caching Status
    lines.append("\nCACHING:")
    if record_result.cached:
        status = "Marked as pattern" if record_result.pattern_marked else "Cached for learning"
        lines.append(f"  Status: {status}")
        lines.append(f"  Chunk ID: {record_result.reasoning_chunk_id}")
    else:
        lines.append("  Status: Not cached (low quality)")

    lines.append("=" * 80)

    return "\n".join(lines)


def _format_verbose(
    synthesis_result: SynthesisResult,
    record_result: RecordResult,
    phase_metadata: dict[str, Any],
) -> str:
    """Format VERBOSE output: full trace with detailed metadata.

    Args:
        synthesis_result: Synthesis result
        record_result: Recording result
        phase_metadata: Aggregated phase metadata

    Returns:
        Multi-line formatted string with full details

    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("SOAR PIPELINE VERBOSE TRACE")
    lines.append("=" * 80)

    # Answer Section
    lines.append("\n" + "=" * 80)
    lines.append("ANSWER")
    lines.append("=" * 80)
    lines.append(synthesis_result.answer)

    # Confidence & Scores
    lines.append("\n" + "=" * 80)
    lines.append("CONFIDENCE & QUALITY SCORES")
    lines.append("=" * 80)
    lines.append(f"Overall Confidence: {synthesis_result.confidence:.2f}")
    if "verification_score" in synthesis_result.metadata:
        lines.append(f"Verification Score: {synthesis_result.metadata['verification_score']:.2f}")
    if "coherence" in synthesis_result.metadata:
        lines.append(f"  Coherence: {synthesis_result.metadata['coherence']:.2f}")
    if "completeness" in synthesis_result.metadata:
        lines.append(f"  Completeness: {synthesis_result.metadata['completeness']:.2f}")
    if "factuality" in synthesis_result.metadata:
        lines.append(f"  Factuality: {synthesis_result.metadata['factuality']:.2f}")

    # Subgoal Breakdown
    subgoal_breakdown = _extract_subgoal_breakdown(phase_metadata)
    if subgoal_breakdown:
        lines.append("\n" + "=" * 80)
        lines.append("SUBGOAL DECOMPOSITION")
        lines.append("=" * 80)
        for sg in subgoal_breakdown:
            critical_marker = " [CRITICAL]" if sg.get("is_critical") else ""
            lines.append(f"\n{sg['index']}. {sg['description']}{critical_marker}")
            lines.append(f"   Assigned Agent: {sg['agent']}")
            if sg.get("depends_on"):
                deps_str = ", ".join(str(d + 1) for d in sg["depends_on"])
                lines.append(f"   Dependencies: Subgoals {deps_str}")

    # Traceability
    lines.append("\n" + "=" * 80)
    lines.append("TRACEABILITY")
    lines.append("=" * 80)
    if synthesis_result.traceability:
        for i, trace in enumerate(synthesis_result.traceability, 1):
            lines.append(
                f"{i}. Agent: {trace['agent']} | "
                f"Subgoal {trace['subgoal_id']}: {trace['subgoal_description']}",
            )
    else:
        lines.append("  No traceability information available")

    # Synthesis Metadata
    lines.append("\n" + "=" * 80)
    lines.append("EXECUTION SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Subgoals Completed: {synthesis_result.metadata.get('subgoals_completed', 0)}")
    lines.append(f"Subgoals Partial: {synthesis_result.metadata.get('subgoals_partial', 0)}")
    lines.append(f"Subgoals Failed: {synthesis_result.metadata.get('subgoals_failed', 0)}")
    lines.append(f"Files Modified: {synthesis_result.metadata.get('total_files_modified', 0)}")
    lines.append(
        f"User Interactions: {synthesis_result.metadata.get('user_interactions_count', 0)}",
    )

    # Phase Timing
    if "phases" in phase_metadata:
        lines.append("\n" + "=" * 80)
        lines.append("PHASE TIMING")
        lines.append("=" * 80)
        total_duration = 0
        for phase_name, phase_data in phase_metadata["phases"].items():
            # Skip non-dict phase data (e.g., error_details string)
            if not isinstance(phase_data, dict):
                continue
            duration = phase_data.get("duration_ms", 0)
            total_duration += duration
            lines.append(f"  {phase_name}: {duration}ms")
        lines.append(f"\nTotal Duration: {total_duration}ms")

    # Caching Details
    lines.append("\n" + "=" * 80)
    lines.append("PATTERN CACHING")
    lines.append("=" * 80)
    if record_result.cached:
        lines.append(f"Status: {'Pattern' if record_result.pattern_marked else 'Cached'}")
        lines.append(f"Chunk ID: {record_result.reasoning_chunk_id}")
        lines.append(f"Activation Update: +{record_result.activation_update:.2f}")
    else:
        lines.append("Status: Not cached (score < 0.5)")
        lines.append(f"Activation Update: {record_result.activation_update:.2f}")

    # Cost Information (if available)
    if "cost" in phase_metadata:
        lines.append("\n" + "=" * 80)
        lines.append("COST TRACKING")
        lines.append("=" * 80)
        cost_data = phase_metadata["cost"]
        lines.append(f"Estimated Cost: ${cost_data.get('estimated_usd', 0.0):.4f}")
        lines.append(f"Actual Cost: ${cost_data.get('actual_usd', 0.0):.4f}")
        if "tokens_used" in cost_data:
            tokens = cost_data["tokens_used"]
            lines.append(
                f"Tokens: {tokens.get('input', 0)} input + "
                f"{tokens.get('output', 0)} output = "
                f"{tokens.get('total', 0)} total",
            )

    lines.append("\n" + "=" * 80)

    return "\n".join(lines)


def _extract_subgoal_breakdown(phase_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract subgoal breakdown from phase metadata.

    Args:
        phase_metadata: Aggregated phase metadata

    Returns:
        List of subgoal detail dicts, or empty list if not available

    """
    phases = phase_metadata.get("phases", {})

    # Try to get from phase4_verify (primary)
    phase4 = phases.get("phase4_verify", {})
    if isinstance(phase4, dict) and "subgoals_detailed" in phase4:
        return cast(list[dict[str, Any]], phase4["subgoals_detailed"])

    # Try to get from phase4_verify_retry (fallback)
    phase4_retry = phases.get("phase4_verify_retry", {})
    if isinstance(phase4_retry, dict) and "subgoals_detailed" in phase4_retry:
        return cast(list[dict[str, Any]], phase4_retry["subgoals_detailed"])

    return []
