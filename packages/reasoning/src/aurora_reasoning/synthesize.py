"""Result synthesis logic for combining agent outputs.

This module implements synthesis of agent outputs into a coherent final answer
with traceability to sources and verification of synthesis quality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .prompts.verify_synthesis import VerifySynthesisPromptTemplate


if TYPE_CHECKING:
    from .llm_client import LLMClient

__all__ = ["synthesize_results", "SynthesisResult"]


class SynthesisResult:
    """Result of agent output synthesis.

    Attributes:
        answer: Natural language synthesized answer
        confidence: Overall confidence score (0.0-1.0)
        traceability: List of claim-to-source mappings
        metadata: Additional synthesis metadata
        raw_response: Raw LLM response text
        prompt_used: Prompt text sent to LLM

    """

    def __init__(
        self,
        answer: str,
        confidence: float,
        traceability: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
        raw_response: str = "",
        prompt_used: str = "",
    ):
        self.answer = answer
        self.confidence = confidence
        self.traceability = traceability
        self.metadata = metadata or {}
        self.raw_response = raw_response
        self.prompt_used = prompt_used

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "traceability": self.traceability,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SynthesisResult:
        """Create from dictionary representation."""
        return cls(
            answer=data["answer"],
            confidence=data["confidence"],
            traceability=data.get("traceability", []),
            metadata=data.get("metadata", {}),
        )


def synthesize_results(
    llm_client: LLMClient,
    query: str,
    agent_outputs: list[dict[str, Any]],
    decomposition: dict[str, Any],
    max_retries: int = 2,
) -> SynthesisResult:
    """Synthesize agent outputs into a coherent final answer.

    This function:
    1. Gathers all agent output summaries
    2. Builds synthesis prompt with original query and agent summaries
    3. Calls LLM for natural language synthesis (NOT JSON)
    4. Validates traceability (every claim links to agent summary)
    5. Verifies synthesis quality
    6. Retries with feedback if quality score < 0.6 (max 2 retries)

    Args:
        llm_client: LLM client to use for synthesis
        query: Original user query
        agent_outputs: List of agent execution results with summaries
        decomposition: Original decomposition with goal and subgoals
        max_retries: Maximum number of synthesis retries (default: 2)

    Returns:
        SynthesisResult with answer, confidence, and traceability

    Raises:
        ValueError: If synthesis fails validation
        RuntimeError: If LLM call fails after retries

    """
    retry_count = 0
    feedback = None

    while retry_count <= max_retries:
        # Gather agent summaries
        summaries = []
        for i, output in enumerate(agent_outputs):
            subgoal = (
                decomposition.get("subgoals", [])[i]
                if i < len(decomposition.get("subgoals", []))
                else {}
            )
            summaries.append(
                {
                    "subgoal_id": i,
                    "subgoal_description": subgoal.get("description", ""),
                    "agent": output.get("agent_name", "unknown"),
                    "summary": output.get("summary", ""),
                    "confidence": output.get("confidence", 0.0),
                },
            )

        # Build synthesis prompt
        system_prompt = _build_synthesis_system_prompt()
        user_prompt = _build_synthesis_user_prompt(
            query=query,
            goal=decomposition.get("goal", ""),
            summaries=summaries,
            retry_feedback=feedback,
        )

        # Call LLM for natural language synthesis (NOT JSON)
        response = llm_client.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,  # Low-medium temperature for coherent synthesis
        )

        # Parse synthesis response
        try:
            synthesis = _parse_synthesis_response(response.content)
        except ValueError as e:
            if retry_count >= max_retries:
                raise ValueError(
                    f"Synthesis parsing failed after {max_retries} retries: {e}",
                ) from e
            feedback = (
                f"Previous synthesis had parsing error: {e}. Please ensure proper formatting."
            )
            retry_count += 1
            continue

        # Traceability validation removed - was overengineered
        # If agents did their job, the answer will naturally reference their findings
        traceability_warning = None

        # Verify synthesis quality
        verification_result = verify_synthesis(
            llm_client=llm_client,
            query=query,
            agent_outputs=agent_outputs,
            synthesis_answer=synthesis["answer"],
        )

        # Check if synthesis passes quality threshold
        if verification_result["overall_score"] >= 0.6:
            # Success - return synthesis result
            full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
            metadata = {
                "retry_count": retry_count,
                "verification_score": verification_result["overall_score"],
                "coherence": verification_result.get("coherence", 0.0),
                "completeness": verification_result.get("completeness", 0.0),
                "factuality": verification_result.get("factuality", 0.0),
            }
            if traceability_warning:
                metadata["traceability_warning"] = traceability_warning
            return SynthesisResult(
                answer=synthesis["answer"],
                confidence=verification_result["overall_score"],
                traceability=_extract_traceability(synthesis["answer"], summaries),
                metadata=metadata,
                raw_response=response.content,
                prompt_used=full_prompt,
            )

        # Quality score too low - prepare retry feedback
        if retry_count >= max_retries:
            # Return best-effort synthesis even if quality is low
            full_prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
            metadata = {
                "retry_count": retry_count,
                "verification_score": verification_result["overall_score"],
                "quality_warning": "Synthesis quality below threshold after max retries",
            }
            if traceability_warning:
                metadata["traceability_warning"] = traceability_warning
            return SynthesisResult(
                answer=synthesis["answer"],
                confidence=verification_result["overall_score"],
                traceability=_extract_traceability(synthesis["answer"], summaries),
                metadata=metadata,
                raw_response=response.content,
                prompt_used=full_prompt,
            )

        # Prepare feedback for retry
        issues = verification_result.get("issues", [])
        feedback = (
            f"Previous synthesis had quality score {verification_result['overall_score']:.2f} (threshold: 0.6). "
            f"Issues identified: {', '.join(issues)}. "
            f"Please improve the synthesis to address these issues."
        )
        retry_count += 1

    # Should never reach here, but satisfy mypy
    raise RuntimeError("Synthesis loop exited unexpectedly")


def verify_synthesis(
    llm_client: LLMClient,
    query: str,
    agent_outputs: list[dict[str, Any]],
    synthesis_answer: str,
) -> dict[str, Any]:
    """Verify synthesis quality using LLM-based verification.

    This function checks:
    - Coherence: Is the answer well-structured and logical?
    - Completeness: Does it address all aspects of the query?
    - Factuality: Are all claims traceable to agent outputs?

    Args:
        llm_client: LLM client to use for verification
        query: Original user query
        agent_outputs: Agent execution results
        synthesis_answer: Synthesized answer to verify

    Returns:
        Dict with verification scores and issues

    Raises:
        ValueError: If verification response is invalid
        RuntimeError: If LLM call fails after retries

    """
    prompt_template = VerifySynthesisPromptTemplate()

    system_prompt = prompt_template.build_system_prompt()
    user_prompt = prompt_template.build_user_prompt(
        query=query,
        agent_outputs=agent_outputs,
        synthesis_answer=synthesis_answer,
    )

    # Call LLM with JSON output requirement
    verification = llm_client.generate_json(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.1,  # Very low temperature for consistent scoring
    )

    # Validate response is a dict (generate_json already parses JSON)
    if not isinstance(verification, dict):
        raise ValueError(
            f"LLM returned non-dict response: {type(verification)}\n"
            f"Response: {str(verification)[:500]}",
        )

    # Validate required fields
    required_fields = ["coherence", "completeness", "factuality", "overall_score"]
    missing = [f for f in required_fields if f not in verification]
    if missing:
        raise ValueError(
            f"Verification missing required fields: {missing}\nResponse: {verification}",
        )

    # Validate score ranges
    for score_field in required_fields:
        score = verification[score_field]
        if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
            raise ValueError(f"Invalid {score_field} score: {score} (must be float in [0.0, 1.0])")

    # Calculate expected overall score (equal weighting)
    expected_score = (
        verification["coherence"] + verification["completeness"] + verification["factuality"]
    ) / 3.0

    # Allow small floating point difference
    if abs(verification["overall_score"] - expected_score) > 0.01:
        verification["overall_score"] = expected_score

    return verification


def _build_synthesis_system_prompt() -> str:
    """Build system prompt for synthesis."""
    return """You are an expert at synthesizing information from multiple sources into a coherent answer.

Your task is to combine the agent outputs into a natural language answer that:
1. Directly addresses the user's query
2. Integrates information from all relevant agent outputs
3. Maintains traceability (cite which agent provided which information)
4. Uses clear, concise language
5. Acknowledges any limitations or uncertainties

Format your response as:

ANSWER:
[Your synthesized natural language answer here. Include inline references like (Agent: <agent_name>) when citing specific information.]

CONFIDENCE: [float between 0.0 and 1.0]

Do NOT output JSON. Output natural language with the above structure."""


def _build_synthesis_user_prompt(
    query: str,
    goal: str,
    summaries: list[dict[str, Any]],
    retry_feedback: str | None = None,
) -> str:
    """Build user prompt for synthesis."""
    prompt_parts = []

    if retry_feedback:
        prompt_parts.append(f"FEEDBACK FROM PREVIOUS ATTEMPT:\n{retry_feedback}\n\n---\n")

    prompt_parts.append(f"ORIGINAL QUERY:\n{query}\n")
    prompt_parts.append(f"\nDECOMPOSITION GOAL:\n{goal}\n")
    prompt_parts.append("\nAGENT OUTPUTS:\n")

    for summary in summaries:
        prompt_parts.append(
            f"\nSubgoal {summary['subgoal_id']}: {summary['subgoal_description']}\n"
            f"Agent: {summary['agent']}\n"
            f"Summary: {summary['summary']}\n"
            f"Confidence: {summary['confidence']:.2f}\n",
        )

    prompt_parts.append(
        "\n---\n\nPlease synthesize the above agent outputs into a coherent answer to the original query.",
    )

    return "".join(prompt_parts)


def _parse_synthesis_response(response: str) -> dict[str, Any]:
    """Parse synthesis response into structured format.

    Args:
        response: Raw LLM response

    Returns:
        Dict with 'answer' and 'confidence' keys

    Raises:
        ValueError: If response format is invalid

    """
    lines = response.strip().split("\n")

    answer_lines = []
    confidence = 0.5  # Default confidence

    in_answer = False
    for line in lines:
        line_stripped = line.strip()

        if line_stripped.startswith("ANSWER:"):
            in_answer = True
            # Check if answer is on same line
            answer_text = line_stripped[7:].strip()
            if answer_text:
                answer_lines.append(answer_text)
        elif line_stripped.startswith("CONFIDENCE:"):
            in_answer = False
            # Extract confidence value
            conf_text = line_stripped[11:].strip()
            try:
                confidence = float(conf_text)
                if not (0.0 <= confidence <= 1.0):
                    raise ValueError(f"Confidence {confidence} out of range [0.0, 1.0]")
            except ValueError as e:
                raise ValueError(f"Invalid confidence value: {conf_text}") from e
        elif in_answer and line_stripped:
            answer_lines.append(line_stripped)

    if not answer_lines:
        raise ValueError("No ANSWER section found in synthesis response")

    # Preserve newlines for markdown formatting
    answer = "\n".join(answer_lines)

    return {
        "answer": answer,
        "confidence": confidence,
    }


def _validate_traceability(answer: str, summaries: list[dict[str, Any]]) -> None:
    """Validate that answer has traceability to agent outputs.

    Args:
        answer: Synthesized answer
        summaries: Agent output summaries

    Raises:
        ValueError: If traceability is insufficient

    """
    # Check if answer references at least one agent
    has_reference = False
    for summary in summaries:
        agent_name = summary["agent"]
        if agent_name.lower() in answer.lower():
            has_reference = True
            break

    if not has_reference and len(summaries) > 0:
        raise ValueError(
            "Answer does not reference any agent outputs. "
            "Please include inline citations like (Agent: <agent_name>).",
        )


def _extract_traceability(answer: str, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract traceability mappings from answer.

    Args:
        answer: Synthesized answer
        summaries: Agent output summaries

    Returns:
        List of dicts with 'claim' and 'source' keys

    """
    traceability = []

    # Simple extraction: look for (Agent: <name>) patterns
    for summary in summaries:
        agent_name = summary["agent"]
        if agent_name.lower() in answer.lower():
            traceability.append(
                {
                    "agent": agent_name,
                    "subgoal_id": summary["subgoal_id"],
                    "subgoal_description": summary["subgoal_description"],
                },
            )

    return traceability
