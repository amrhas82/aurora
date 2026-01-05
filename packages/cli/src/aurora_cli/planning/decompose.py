"""Plan decomposition using SOAR orchestration.

This module provides the PlanDecomposer class which integrates SOAR's
decompose_query functionality into the planning workflow. It handles:

- Building context from indexed code chunks
- Calling SOAR decomposition with proper parameters
- Graceful fallback to heuristic decomposition
- Caching of decomposition results
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from aurora_cli.planning.models import Complexity, Subgoal

# Try to import SOAR - graceful fallback if not available
try:
    from aurora_soar.phases.decompose import decompose_query
    from aurora_reasoning.llm_client import LLMClient
    SOAR_AVAILABLE = True
except ImportError:
    SOAR_AVAILABLE = False
    decompose_query = None  # type: ignore
    LLMClient = None  # type: ignore

logger = logging.getLogger(__name__)


class PlanDecomposer:
    """Orchestrates SOAR decomposition for planning workflow.

    This class integrates SOAR's sophisticated decomposition capabilities
    into the planning system, with graceful fallback to heuristics when
    SOAR is unavailable or fails.

    Attributes:
        config: Optional configuration object for LLM settings
        _cache: Cache for decomposition results (goal+complexity -> result)
    """

    def __init__(self, config: Any | None = None):
        """Initialize PlanDecomposer.

        Args:
            config: Optional configuration object with LLM settings
        """
        self.config = config
        self._cache: dict[str, tuple[list[Subgoal], str]] = {}

    def decompose(
        self,
        goal: str,
        complexity: Complexity | None = None,
        context_files: list[str] | None = None,
    ) -> tuple[list[Subgoal], str]:
        """Decompose a goal into subgoals using SOAR or heuristics.

        Args:
            goal: The goal to decompose
            complexity: Optional complexity level (auto-assessed if None)
            context_files: Optional list of relevant file paths

        Returns:
            Tuple of (subgoals list, decomposition_source)
            decomposition_source is "soar" or "heuristic"
        """
        # Use MODERATE as default complexity if not specified
        if complexity is None:
            complexity = Complexity.MODERATE

        # Check cache first
        cache_key = self._get_cache_key(goal, complexity)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for goal: {goal[:50]}...")
            return self._cache[cache_key]

        # Try SOAR first
        if SOAR_AVAILABLE and decompose_query:
            try:
                context = self._build_context(context_files)
                subgoals = self._call_soar(goal, context, complexity)
                result = (subgoals, "soar")
                self._cache[cache_key] = result
                return result
            except (ImportError, RuntimeError, TimeoutError) as e:
                logger.warning(f"SOAR decomposition failed: {e}, falling back to heuristics")

        # Fallback to heuristics
        subgoals = self._fallback_to_heuristics(goal, complexity)
        result = (subgoals, "heuristic")
        self._cache[cache_key] = result
        return result

    def _get_cache_key(self, goal: str, complexity: Complexity) -> str:
        """Generate cache key from goal and complexity.

        Args:
            goal: The goal string
            complexity: Complexity level

        Returns:
            Hash-based cache key
        """
        content = f"{goal}::{complexity.value}"
        return hashlib.md5(content.encode()).hexdigest()

    def _build_context(
        self, context_files: list[str] | None = None
    ) -> dict[str, Any]:
        """Build context dictionary for SOAR decomposition.

        Args:
            context_files: Optional list of relevant file paths

        Returns:
            Context dictionary with code_chunks and reasoning_chunks
        """
        # For now, return empty context
        # In future, integrate with memory retrieval system
        return {
            "code_chunks": [],
            "reasoning_chunks": [],
        }

    def _call_soar(
        self, goal: str, context: dict[str, Any], complexity: Complexity
    ) -> list[Subgoal]:
        """Call SOAR decompose_query and convert result to Subgoals.

        Args:
            goal: The goal to decompose
            context: Context dictionary with chunks
            complexity: Complexity level

        Returns:
            List of Subgoal objects

        Raises:
            ImportError: If SOAR is not available
            RuntimeError: If SOAR call fails
            TimeoutError: If SOAR call times out (30s)
        """
        if not SOAR_AVAILABLE or not decompose_query:
            raise ImportError("SOAR not available")

        # Create LLM client if not provided
        llm_client = self._get_llm_client()

        # Call SOAR decompose_query
        try:
            result = decompose_query(
                query=goal,
                context=context,
                complexity=complexity.value,
                llm_client=llm_client,
                available_agents=None,  # Will add agent discovery in task 2.4
                use_cache=True,
            )

            # Convert SOAR result to Subgoal objects
            subgoals = []
            for idx, sg_dict in enumerate(result.decomposition.subgoals, 1):
                subgoal = Subgoal(
                    id=sg_dict.get("id", f"sg-{idx}"),
                    title=sg_dict.get("title", f"Subgoal {idx}"),
                    description=sg_dict.get("description", "No description"),
                    recommended_agent=sg_dict.get("agent", "@full-stack-dev"),
                    agent_exists=True,  # Will validate in task 2.4
                    dependencies=sg_dict.get("dependencies", []),
                )
                subgoals.append(subgoal)

            return subgoals

        except Exception as e:
            logger.error(f"SOAR call failed: {e}")
            raise RuntimeError(f"SOAR decomposition failed: {e}")

    def _get_llm_client(self) -> Any:
        """Get or create LLM client for SOAR calls.

        Returns:
            LLMClient instance

        Raises:
            RuntimeError: If LLM client cannot be created
        """
        if not LLMClient:
            raise RuntimeError("LLMClient not available")

        # Use config if provided, otherwise use defaults
        if self.config and hasattr(self.config, "llm_client"):
            return self.config.llm_client

        # Create default client
        # This will use environment variables for API keys
        try:
            return LLMClient()
        except Exception as e:
            raise RuntimeError(f"Failed to create LLM client: {e}")

    def _fallback_to_heuristics(
        self, goal: str, complexity: Complexity | None = None
    ) -> list[Subgoal]:
        """Fallback to rule-based decomposition when SOAR unavailable.

        Args:
            goal: The goal to decompose
            complexity: Optional complexity level

        Returns:
            List of Subgoal objects from heuristic decomposition
        """
        logger.info("Using heuristic decomposition (SOAR unavailable)")

        # Simple heuristic: create 2-4 subgoals based on common patterns
        subgoals = []

        # Always: Plan and design
        subgoals.append(
            Subgoal(
                id="sg-1",
                title="Plan and design approach",
                description=f"Analyze requirements and design approach for: {goal}",
                recommended_agent="@holistic-architect",
                agent_exists=False,
            )
        )

        # Always: Implementation
        subgoals.append(
            Subgoal(
                id="sg-2",
                title="Implement solution",
                description=f"Implement the planned solution for: {goal}",
                recommended_agent="@full-stack-dev",
                agent_exists=False,
            )
        )

        # Always: Testing
        subgoals.append(
            Subgoal(
                id="sg-3",
                title="Test and verify",
                description=f"Write tests and verify solution for: {goal}",
                recommended_agent="@qa-test-architect",
                agent_exists=False,
            )
        )

        # If complex, add documentation
        if complexity == Complexity.COMPLEX:
            subgoals.append(
                Subgoal(
                    id="sg-4",
                    title="Document changes",
                    description=f"Document implementation and update relevant docs for: {goal}",
                    recommended_agent="@full-stack-dev",
                    agent_exists=False,
                )
            )

        return subgoals
