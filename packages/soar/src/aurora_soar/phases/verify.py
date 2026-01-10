"""Phase 4: Decomposition Verification.

This module implements the Verify phase of the SOAR pipeline, which validates
decompositions with self-verification or adversarial approaches.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from aurora_reasoning.verify import VerificationOption

if TYPE_CHECKING:
    from aurora_reasoning import LLMClient
    from aurora_reasoning.decompose import DecompositionResult
    from aurora_reasoning.verify import VerificationResult

__all__ = [
    "verify_decomposition",
    "verify_lite",
    "VerifyPhaseResult",
    "RetrievalQuality",
    "assess_retrieval_quality",
]


class RetrievalQuality(Enum):
    """Quality assessment of retrieved context."""

    GOOD = "good"  # High groundedness (≥0.7) AND sufficient high-quality chunks (≥3)
    WEAK = "weak"  # Low groundedness (<0.7) OR insufficient high-quality chunks (<3)
    NONE = "none"  # No chunks retrieved (0 total chunks)


class VerifyPhaseResult:
    """Result of verify phase execution.

    Attributes:
        verification: The verification result
        retry_count: Number of retries attempted
        all_attempts: List of all verification attempts
        final_verdict: Final verdict (PASS or FAIL)
        timing_ms: Time taken in milliseconds
        method: Verification method used (self or adversarial)
        retrieval_quality: Quality assessment of retrieved context (optional)
    """

    def __init__(
        self,
        verification: VerificationResult,
        retry_count: int = 0,
        all_attempts: list[VerificationResult] | None = None,
        final_verdict: str = "PASS",
        timing_ms: float = 0.0,
        method: str = "self",
        retrieval_quality: RetrievalQuality | None = None,
    ):
        self.verification = verification
        self.retry_count = retry_count
        self.all_attempts = all_attempts or [verification]
        self.final_verdict = final_verdict
        self.timing_ms = timing_ms
        self.method = method
        self.retrieval_quality = retrieval_quality

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "verification": self.verification.to_dict(),
            "retry_count": self.retry_count,
            "all_attempts": [v.to_dict() for v in self.all_attempts],
            "final_verdict": self.final_verdict,
            "timing_ms": self.timing_ms,
            "method": self.method,
        }
        if self.retrieval_quality is not None:
            result["retrieval_quality"] = self.retrieval_quality.value
        return result


def assess_retrieval_quality(
    verification: VerificationResult,
    high_quality_chunks: int,
    total_chunks: int,
) -> RetrievalQuality:
    """Assess quality of retrieved context based on verification and chunk counts.

    Decision matrix:
    - NONE: total_chunks == 0
    - WEAK: verification.groundedness < 0.7 OR high_quality_chunks < 3
    - GOOD: verification.groundedness >= 0.7 AND high_quality_chunks >= 3

    Args:
        verification: Verification result with groundedness score
        high_quality_chunks: Count of chunks with activation >= ACTIVATION_THRESHOLD (0.3)
        total_chunks: Total number of chunks retrieved

    Returns:
        RetrievalQuality enum value
    """
    # No match scenario
    if total_chunks == 0:
        return RetrievalQuality.NONE

    # Weak match scenarios
    if verification.groundedness < 0.7 or high_quality_chunks < 3:
        return RetrievalQuality.WEAK

    # Good match scenario
    return RetrievalQuality.GOOD


def verify_lite(
    decomposition: dict[str, Any],
    available_agents: list[Any],
) -> tuple[bool, list[tuple[int, Any]], list[str]]:
    """Lightweight verification that checks decomposition validity and assigns agents.

    This function replaces the heavy verify_decomposition + route_subgoals workflow.
    It performs basic structural validation and agent assignment in one pass.

    Checks performed:
    1. Decomposition has "subgoals" key
    2. At least one subgoal exists
    3. Each subgoal has required fields (description, suggested_agent)
    4. All suggested agents exist in available_agents
    5. No circular dependencies in subgoal dependency graph

    Args:
        decomposition: Decomposition dict with subgoals and execution strategy
        available_agents: List of AgentInfo objects from registry

    Returns:
        Tuple of (passed, agent_assignments, issues):
        - passed: True if all checks pass, False otherwise
        - agent_assignments: List of (subgoal_index, AgentInfo) tuples for valid subgoals
        - issues: List of issue strings describing validation failures
    """
    issues: list[str] = []
    agent_assignments: list[tuple[int, Any]] = []

    # Check 1: Validate decomposition has "subgoals" key
    if "subgoals" not in decomposition:
        issues.append("Decomposition missing 'subgoals' key")
        return (False, [], issues)

    subgoals = decomposition["subgoals"]

    # Check 2: At least one subgoal required
    if not subgoals or len(subgoals) == 0:
        issues.append("Decomposition must have at least one subgoal")
        return (False, [], issues)

    # Build agent lookup map
    agent_map = {agent.id: agent for agent in available_agents}

    # Check 3 & 4: Validate subgoal structure and agent existence
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")

        # Validate required fields
        if "description" not in subgoal:
            issues.append(f"Subgoal {subgoal_index} missing 'description' field")
            continue

        if "suggested_agent" not in subgoal:
            issues.append(f"Subgoal {subgoal_index} missing 'suggested_agent' field")
            continue

        suggested_agent = subgoal["suggested_agent"]

        # Check if agent exists
        if suggested_agent not in agent_map:
            issues.append(f"Agent '{suggested_agent}' not found in registry")
            continue

        # Valid subgoal - create assignment
        agent_info = agent_map[suggested_agent]
        agent_assignments.append((subgoal_index, agent_info))

    # Check 5: Detect circular dependencies
    circular_issues = _check_circular_deps(subgoals)
    issues.extend(circular_issues)

    # Determine if passed
    passed = len(issues) == 0

    return (passed, agent_assignments, issues)


def _check_circular_deps(subgoals: list[dict[str, Any]]) -> list[str]:
    """Check for circular dependencies in subgoal dependency graph.

    Uses depth-first search to detect cycles in the dependency graph.

    Args:
        subgoals: List of subgoal dicts with 'subgoal_index' and 'depends_on'

    Returns:
        List of issue strings describing circular dependencies found
    """
    issues: list[str] = []

    # Build adjacency list for dependency graph
    graph: dict[int, list[int]] = {}
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")
        depends_on = subgoal.get("depends_on", [])
        graph[subgoal_index] = depends_on

    # DFS to detect cycles
    visited: set[int] = set()
    rec_stack: set[int] = set()

    def has_cycle(node: int) -> bool:
        """DFS helper to detect cycle from given node."""
        visited.add(node)
        rec_stack.add(node)

        # Visit all dependencies
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a back edge - cycle detected
                return True

        rec_stack.remove(node)
        return False

    # Check each subgoal for cycles
    for subgoal in subgoals:
        subgoal_index = subgoal.get("subgoal_index")
        if subgoal_index not in visited:
            if has_cycle(subgoal_index):
                issues.append(
                    f"Circular dependency detected in subgoal dependency graph involving subgoal {subgoal_index}"
                )
                break  # One cycle detection is enough

    return issues


def verify_decomposition(
    decomposition: DecompositionResult,
    complexity: str,
    llm_client: LLMClient,
    query: str,
    context_summary: str | None = None,
    available_agents: list[str] | None = None,
    max_retries: int = 2,
    interactive_mode: bool = False,
    retrieval_context: dict[str, Any] | None = None,
) -> VerifyPhaseResult:
    """Verify decomposition quality with retry loop.

    # DEPRECATED: This function will be removed in Phase 6.
    # Use verify_lite() instead for lightweight verification + agent assignment.

    This phase:
    1. Selects verification option based on complexity (MEDIUM→Self, COMPLEX→Adversarial)
    2. Calls reasoning.verify_decomposition with selected option
    3. If verdict is RETRY and retry_count < max_retries:
       a. Generate retry feedback from verification issues/suggestions
       b. Re-decompose with retry feedback
       c. Verify again
    4. If verdict is FAIL or max retries exhausted, return FAIL
    5. If verdict is PASS, return PASS
    6. (Optional) Assess retrieval quality and prompt user if weak match in interactive mode

    Args:
        decomposition: Decomposition result from Phase 3
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        llm_client: LLM client for verification
        query: Original user query
        context_summary: Optional summary of available context
        available_agents: Optional list of available agent names
        max_retries: Maximum number of retry attempts (default: 2)
        interactive_mode: Whether to prompt user for weak matches (default: False, CLI only)
        retrieval_context: Optional retrieval context with high_quality_count and total_retrieved

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

    # Assess retrieval quality if retrieval_context provided
    retrieval_quality = None
    if retrieval_context is not None:
        high_quality_count = retrieval_context.get("high_quality_count", 0)
        total_retrieved = retrieval_context.get("total_retrieved", 0)
        retrieval_quality = assess_retrieval_quality(
            verification=verification,
            high_quality_chunks=high_quality_count,
            total_chunks=total_retrieved,
        )

        # If weak match and interactive mode, prompt user
        if retrieval_quality == RetrievalQuality.WEAK and interactive_mode:
            user_choice = _prompt_user_for_weak_match(
                groundedness=verification.groundedness,
                high_quality_chunks=high_quality_count,
            )

            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"User selected option: {user_choice}")

    timing_ms = (time.perf_counter() - start_time) * 1000

    return VerifyPhaseResult(
        verification=verification,
        retry_count=retry_count,
        all_attempts=all_attempts,
        final_verdict=final_verdict,
        timing_ms=timing_ms,
        method=verification_method,
        retrieval_quality=retrieval_quality,
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


def _prompt_user_for_weak_match(groundedness: float, high_quality_chunks: int) -> int:
    """Prompt user when retrieval quality is weak.

    Displays a warning message with quality metrics and presents 3 options:
    1. Start anew (clear weak chunks, use general knowledge)
    2. Start over (rephrase query)
    3. Continue (proceed with weak chunks)

    Args:
        groundedness: Groundedness score from verification (0-1)
        high_quality_chunks: Count of chunks with activation >= 0.3

    Returns:
        User's choice (1, 2, or 3)
    """
    import click
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # Display warning message
    warning_text = f"""[bold yellow]⚠ Weak Retrieval Match Detected[/]

[bold]Quality Metrics:[/]
  • Groundedness Score: {groundedness:.2f} (threshold: 0.70)
  • High-Quality Chunks: {high_quality_chunks}/3 (activation ≥ 0.3)

The retrieved context may not be sufficient to answer your query accurately.

[bold]What would you like to do?[/]
  [cyan]1.[/] Start anew - Clear weak chunks and use LLM general knowledge
  [cyan]2.[/] Start over - Rephrase your query for better matches
  [cyan]3.[/] Continue - Proceed with the weak chunks anyway
"""

    console.print()
    console.print(Panel(warning_text, border_style="yellow", title="Retrieval Quality"))

    # Prompt user for choice
    while True:
        choice = int(
            click.prompt(
                "\nSelect an option",
                type=click.IntRange(1, 3),
                default=3,
                show_default=True,
            )
        )

        # Confirm choice
        console.print()
        if choice == 1:
            console.print("[green]✓[/] Starting anew with general knowledge...")
        elif choice == 2:
            console.print("[yellow]↻[/] Please rephrase your query and try again.")
        elif choice == 3:
            console.print("[blue]→[/] Continuing with weak chunks...")

        return choice
