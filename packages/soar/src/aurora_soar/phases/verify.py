"""Phase 4: Decomposition Verification.

This module implements the Verify phase of the SOAR pipeline, which validates
decompositions with self-verification or adversarial approaches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aurora_reasoning.verify import VerificationOption


if TYPE_CHECKING:
    from aurora_reasoning import LLMClient
    from aurora_reasoning.decompose import DecompositionResult
    from aurora_reasoning.verify import VerificationResult

__all__ = ["verify_decomposition", "VerifyPhaseResult"]


class VerifyPhaseResult:
    """Result of verify phase execution.

    Attributes:
        verification: The verification result
        retry_count: Number of retries attempted
        all_attempts: List of all verification attempts
        final_verdict: Final verdict (PASS or FAIL)
        timing_ms: Time taken in milliseconds
        method: Verification method used (self or adversarial)
    """

    def __init__(
        self,
        verification: VerificationResult,
        retry_count: int = 0,
        all_attempts: list[VerificationResult] | None = None,
        final_verdict: str = "PASS",
        timing_ms: float = 0.0,
        method: str = "self",
    ):
        self.verification = verification
        self.retry_count = retry_count
        self.all_attempts = all_attempts or [verification]
        self.final_verdict = final_verdict
        self.timing_ms = timing_ms
        self.method = method

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "verification": self.verification.to_dict(),
            "retry_count": self.retry_count,
            "all_attempts": [v.to_dict() for v in self.all_attempts],
            "final_verdict": self.final_verdict,
            "timing_ms": self.timing_ms,
            "method": self.method,
        }


def verify_decomposition(
    decomposition: DecompositionResult,
    complexity: str,
    llm_client: LLMClient,
    query: str,
    context_summary: str | None = None,
    available_agents: list[str] | None = None,
    max_retries: int = 2,
) -> VerifyPhaseResult:
    """Verify decomposition quality with retry loop.

    This phase:
    1. Selects verification option based on complexity (MEDIUM→Self, COMPLEX→Adversarial)
    2. Calls reasoning.verify_decomposition with selected option
    3. If verdict is RETRY and retry_count < max_retries:
       a. Generate retry feedback from verification issues/suggestions
       b. Re-decompose with retry feedback
       c. Verify again
    4. If verdict is FAIL or max retries exhausted, return FAIL
    5. If verdict is PASS, return PASS

    Args:
        decomposition: Decomposition result from Phase 3
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        llm_client: LLM client for verification
        query: Original user query
        context_summary: Optional summary of available context
        available_agents: Optional list of available agent names
        max_retries: Maximum number of retry attempts (default: 2)

    Returns:
        VerifyPhaseResult with verification results and retry history

    Raises:
        ValueError: If complexity is invalid
        RuntimeError: If LLM call fails
    """
    import time

    from aurora_reasoning.verify import VerificationOption, VerificationVerdict
    from aurora_reasoning.verify import verify_decomposition as reasoning_verify

    start_time = time.perf_counter()

    # Select verification option based on complexity
    verification_option = _select_verification_option(complexity)

    # Track verification method for metadata
    verification_method = (
        "adversarial" if verification_option == VerificationOption.ADVERSARIAL else "self"
    )

    # Track all attempts
    all_attempts: list[VerificationResult] = []
    retry_count = 0

    # Initial verification
    verification = reasoning_verify(
        llm_client=llm_client,
        query=query,
        decomposition=decomposition.to_dict(),
        option=verification_option,
        context_summary=context_summary,
        available_agents=available_agents,
    )
    all_attempts.append(verification)

    # Retry loop if needed
    while verification.verdict == VerificationVerdict.RETRY and retry_count < max_retries:
        retry_count += 1

        # Generate retry feedback
        retry_feedback = _generate_retry_feedback(
            llm_client=llm_client,
            verification=verification,
            attempt_number=retry_count,
        )

        # Re-decompose with retry feedback
        from aurora_soar.phases.decompose import decompose_query as phase_decompose

        # Import here to avoid circular import
        decompose_result = phase_decompose(
            query=query,
            context={"code_chunks": [], "reasoning_chunks": []},  # Context already available
            complexity=complexity,
            llm_client=llm_client,
            available_agents=available_agents,
            retry_feedback=retry_feedback,
            use_cache=False,  # Don't use cache for retries
        )

        # Update decomposition for next verification
        decomposition = decompose_result.decomposition

        # Verify again
        verification = reasoning_verify(
            llm_client=llm_client,
            query=query,
            decomposition=decomposition.to_dict(),
            option=verification_option,
            context_summary=context_summary,
            available_agents=available_agents,
        )
        all_attempts.append(verification)

    # Determine final verdict
    if verification.verdict == VerificationVerdict.PASS:
        final_verdict = "PASS"
    elif verification.verdict == VerificationVerdict.RETRY and retry_count >= max_retries:
        # Max retries exhausted, treat as FAIL
        final_verdict = "FAIL"
    else:  # FAIL verdict
        final_verdict = "FAIL"

    timing_ms = (time.perf_counter() - start_time) * 1000

    return VerifyPhaseResult(
        verification=verification,
        retry_count=retry_count,
        all_attempts=all_attempts,
        final_verdict=final_verdict,
        timing_ms=timing_ms,
        method=verification_method,
    )


def _select_verification_option(complexity: str) -> VerificationOption:
    """Select verification option based on complexity.

    Selection logic:
    - SIMPLE: No verification needed (should not reach this phase)
    - MEDIUM: Self-verification (Option A)
    - COMPLEX: Adversarial verification (Option B)
    - CRITICAL: Adversarial verification (Option B)

    Args:
        complexity: Complexity level string

    Returns:
        VerificationOption enum value

    Raises:
        ValueError: If complexity is invalid
    """
    complexity_upper = complexity.upper()

    if complexity_upper == "SIMPLE":
        # SIMPLE queries should bypass verification, but use SELF if called
        return VerificationOption.SELF

    if complexity_upper == "MEDIUM":
        return VerificationOption.SELF

    if complexity_upper in ["COMPLEX", "CRITICAL"]:
        return VerificationOption.ADVERSARIAL

    raise ValueError(f"Invalid complexity level: {complexity}")


def _generate_retry_feedback(
    llm_client: LLMClient,
    verification: VerificationResult,
    attempt_number: int,
) -> str:
    """Generate actionable retry feedback from verification results.

    Args:
        llm_client: LLM client for feedback generation
        verification: Verification result with issues and suggestions
        attempt_number: Current retry attempt number (1-based)

    Returns:
        Feedback string for next retry attempt
    """
    from aurora_reasoning.prompts.retry_feedback import RetryFeedbackPromptTemplate

    # Build feedback prompt
    prompt_template = RetryFeedbackPromptTemplate()
    system_prompt = prompt_template.build_system_prompt()
    user_prompt = prompt_template.build_user_prompt(
        verification_result=verification.to_dict(),
        attempt_number=attempt_number,
    )

    # Generate feedback (plain text response, not JSON)
    response = llm_client.generate(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.3,  # Some creativity for feedback generation
    )

    return response.content.strip()
