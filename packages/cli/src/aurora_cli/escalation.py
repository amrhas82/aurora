"""Auto-escalation handler for AURORA CLI.

This module implements automatic escalation between simple and complex query handling:
- Simple queries (< 0.6 complexity) → Direct LLM call (fast, low cost)
- Complex queries (>= 0.6 complexity) → Full AURORA pipeline (SOAR, agents, memory)

The escalation is transparent to the user - they just ask questions and the system
automatically chooses the appropriate execution path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from aurora_soar.phases.assess import assess_complexity

__all__ = ["AutoEscalationHandler", "EscalationConfig", "EscalationResult"]

logger = logging.getLogger(__name__)


@dataclass
class EscalationConfig:
    """Configuration for auto-escalation behavior.

    Attributes:
        threshold: Complexity threshold for escalation (0.0-1.0).
                  Queries below this use direct LLM, above use AURORA.
        enable_keyword_only: If True, use keyword-only classification (no LLM cost).
                           If False, use LLM verification for borderline cases.
        force_aurora: If True, always use AURORA (bypass escalation logic).
        force_direct: If True, always use direct LLM (bypass escalation logic).

    Example:
        >>> config = EscalationConfig(threshold=0.6, enable_keyword_only=True)
        >>> handler = AutoEscalationHandler(config=config)

    """

    threshold: float = 0.6
    enable_keyword_only: bool = True
    force_aurora: bool = False
    force_direct: bool = False

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not (0.0 <= self.threshold <= 1.0):
            raise ValueError(f"threshold must be in [0, 1], got {self.threshold}")
        if self.force_aurora and self.force_direct:
            raise ValueError("Cannot force both AURORA and direct modes simultaneously")


@dataclass
class EscalationResult:
    """Result of escalation decision.

    Attributes:
        use_aurora: Whether to use AURORA (True) or direct LLM (False)
        complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
        confidence: Confidence in classification (0.0-1.0)
        method: Classification method used ("keyword" or "llm")
        reasoning: Explanation of decision
        score: Complexity score (0.0-1.0)

    Example:
        >>> result = handler.assess_query("How to calculate totals?")
        >>> if result.use_aurora:
        ...     # Use full AURORA pipeline
        ...     response = aurora_orchestrator.execute(query)
        ... else:
        ...     # Use direct LLM call
        ...     response = llm_client.generate(query)

    """

    use_aurora: bool
    complexity: str
    confidence: float
    method: str
    reasoning: str
    score: float


class AutoEscalationHandler:
    """Automatic escalation between direct LLM and full AURORA pipeline.

    This class analyzes query complexity using the Phase 2 keyword classifier
    and decides whether to route to:
    - Direct LLM: Fast, low-cost, suitable for simple queries (< threshold)
    - AURORA: Full SOAR pipeline, agents, memory (>= threshold)

    The escalation is transparent - users don't need to choose the mode explicitly.

    Attributes:
        config: Escalation configuration
        llm_client: Optional LLM client for Tier 2 classification

    Example:
        >>> handler = AutoEscalationHandler()
        >>> result = handler.assess_query("What is a function?")
        >>> print(f"Use AURORA: {result.use_aurora}")
        >>> print(f"Complexity: {result.complexity}")

    """

    def __init__(
        self,
        config: EscalationConfig | None = None,
        llm_client: Any | None = None,
    ):
        """Initialize auto-escalation handler.

        Args:
            config: Escalation configuration (uses defaults if None)
            llm_client: Optional LLM client for Tier 2 verification

        """
        self.config = config or EscalationConfig()
        self.llm_client = llm_client

    def assess_query(self, query: str) -> EscalationResult:
        """Assess query and determine whether to use AURORA or direct LLM.

        Args:
            query: User query string

        Returns:
            EscalationResult with routing decision and analysis

        Example:
            >>> handler = AutoEscalationHandler()
            >>> result = handler.assess_query("Explain authentication")
            >>> if result.use_aurora:
            ...     print("Using full AURORA pipeline")
            ... else:
            ...     print("Using direct LLM")

        """
        # Check for forced modes
        if self.config.force_aurora:
            return EscalationResult(
                use_aurora=True,
                complexity="FORCED",
                confidence=1.0,
                method="forced",
                reasoning="Forced to use AURORA (force_aurora=True)",
                score=1.0,
            )

        if self.config.force_direct:
            return EscalationResult(
                use_aurora=False,
                complexity="FORCED",
                confidence=1.0,
                method="forced",
                reasoning="Forced to use direct LLM (force_direct=True)",
                score=0.0,
            )

        # Assess complexity using Phase 2 keyword classifier
        llm_for_assessment = None if self.config.enable_keyword_only else self.llm_client

        assessment = assess_complexity(query, llm_client=llm_for_assessment)

        complexity = assessment["complexity"]
        confidence = assessment["confidence"]
        method = assessment["method"]
        reasoning = assessment["reasoning"]
        score = assessment.get("score", self._complexity_to_score(complexity))

        # Make escalation decision based on threshold (score ranges 0.0-1.0)
        use_aurora = score >= self.config.threshold

        # Log decision
        logger.info(
            f"Escalation decision: {'AURORA' if use_aurora else 'Direct LLM'} "
            f"(complexity={complexity}, score={score:.3f}, "
            f"threshold={self.config.threshold:.3f}, confidence={confidence:.3f})",
        )

        return EscalationResult(
            use_aurora=use_aurora,
            complexity=complexity,
            confidence=confidence,
            method=method,
            reasoning=reasoning,
            score=score,
        )

    def _complexity_to_score(self, complexity: str) -> float:
        """Convert complexity level to numeric score.

        Args:
            complexity: Complexity level (SIMPLE, MEDIUM, COMPLEX, CRITICAL)

        Returns:
            Numeric score (0.0-1.0)

        """
        mapping = {
            "SIMPLE": 0.2,
            "MEDIUM": 0.5,
            "COMPLEX": 0.75,
            "CRITICAL": 0.95,
        }
        return mapping.get(complexity.upper(), 0.5)

    def should_use_aurora(self, query: str) -> bool:
        """Simple convenience method to check if AURORA should be used.

        Args:
            query: User query string

        Returns:
            True if AURORA should be used, False for direct LLM

        Example:
            >>> handler = AutoEscalationHandler()
            >>> if handler.should_use_aurora("complex refactoring task"):
            ...     # Use AURORA
            ...     pass
            ... else:
            ...     # Use direct LLM
            ...     pass

        """
        result = self.assess_query(query)
        return result.use_aurora

    def get_execution_mode(self, query: str) -> str:
        """Get execution mode name for logging/display.

        Args:
            query: User query string

        Returns:
            "aurora" or "direct" depending on escalation decision

        Example:
            >>> handler = AutoEscalationHandler()
            >>> mode = handler.get_execution_mode("What is a class?")
            >>> print(f"Execution mode: {mode}")

        """
        result = self.assess_query(query)
        return "aurora" if result.use_aurora else "direct"
