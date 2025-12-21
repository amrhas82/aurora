"""SOAR Orchestrator - Main Pipeline Coordination.

This module implements the 9-phase SOAR (Sense-Orient-Adapt-Respond) orchestrator
that coordinates the entire reasoning pipeline from query assessment to response
formatting.

The 9 phases are:
1. Assess - Determine query complexity
2. Retrieve - Get relevant context from memory
3. Decompose - Break query into subgoals
4. Verify - Validate decomposition quality
5. Route - Assign agents to subgoals
6. Collect - Execute agents and gather results
7. Synthesize - Combine results into answer
8. Record - Cache reasoning patterns
9. Respond - Format final response

The orchestrator manages:
- Phase execution and coordination
- Error handling and graceful degradation
- Budget tracking and enforcement
- Metadata aggregation
- Conversation logging
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from aurora_core.budget import CostTracker
from aurora_core.exceptions import BudgetExceededError
from aurora_core.logging import ConversationLogger, VerbosityLevel
from aurora_soar.phases import (
    assess,
    collect,
    decompose,
    record,
    respond,
    retrieve,
    route,
    synthesize,
    verify,
)


if TYPE_CHECKING:
    from aurora_core.config.loader import Config
    from aurora_core.store.base import Store
    from aurora_reasoning.llm_client import LLMClient
    from aurora_soar.agent_registry import AgentRegistry


logger = logging.getLogger(__name__)


class SOAROrchestrator:
    """SOAR Pipeline Orchestrator.

    Coordinates the 9-phase reasoning pipeline with budget tracking,
    error handling, and conversation logging.

    Attributes:
        store: ACT-R memory store for context retrieval and pattern caching
        agent_registry: Registry for agent discovery and routing
        config: System configuration
        reasoning_llm: LLM client for reasoning tasks (assessment, decomposition, verification)
        solving_llm: LLM client for solving tasks (agent execution, synthesis)
    """

    def __init__(
        self,
        store: Store,
        agent_registry: AgentRegistry,
        config: Config,
        reasoning_llm: LLMClient,
        solving_llm: LLMClient,
        cost_tracker: CostTracker | None = None,
        conversation_logger: ConversationLogger | None = None,
    ):
        """Initialize SOAR orchestrator.

        Args:
            store: ACT-R memory store instance
            agent_registry: Agent registry instance
            config: System configuration
            reasoning_llm: LLM client for reasoning tasks (Tier 2 model: Sonnet/GPT-4)
            solving_llm: LLM client for solving tasks (Tier 1 model: Haiku/GPT-3.5)
            cost_tracker: Optional cost tracker (creates default if not provided)
            conversation_logger: Optional conversation logger (creates default if not provided)
        """
        self.store = store
        self.agent_registry = agent_registry
        self.config = config
        self.reasoning_llm = reasoning_llm
        self.solving_llm = solving_llm

        # Initialize cost tracker
        if cost_tracker is None:
            monthly_limit = config.get("budget", {}).get("monthly_limit_usd", 100.0)
            cost_tracker = CostTracker(monthly_limit_usd=monthly_limit)
        self.cost_tracker = cost_tracker

        # Initialize conversation logger
        if conversation_logger is None:
            logging_enabled = config.get("logging", {}).get("conversation_logging_enabled", True)
            conversation_logger = ConversationLogger(enabled=logging_enabled)
        self.conversation_logger = conversation_logger

        # Initialize phase-level metadata tracking
        self._phase_metadata: dict[str, Any] = {}
        self._total_cost: float = 0.0
        self._token_usage: dict[str, int] = {"input": 0, "output": 0}
        self._start_time: float = 0.0
        self._query_id: str = ""
        self._query: str = ""

        logger.info("SOAR orchestrator initialized")

    def execute(
        self,
        query: str,
        verbosity: str = "NORMAL",
        max_cost_usd: float | None = None,
    ) -> dict[str, Any]:
        """Execute the full 9-phase SOAR pipeline.

        This is the main entry point for query processing. It coordinates all
        phases and handles errors gracefully.

        Args:
            query: User query string
            verbosity: Output verbosity level (QUIET, NORMAL, VERBOSE, JSON)
            max_cost_usd: Optional budget limit for this query (overrides config)

        Returns:
            Dict with keys:
                - answer: str (synthesized answer)
                - confidence: float (0-1)
                - overall_score: float (0-1)
                - reasoning_trace: dict (phase outputs)
                - metadata: dict (execution metadata)
                - cost_usd: float (actual cost)

        Raises:
            BudgetExceededError: If query would exceed budget limits
            ValidationError: If query is invalid or malformed
            StorageError: If memory operations fail critically
        """
        self._start_time = time.time()
        self._phase_metadata = {}
        self._total_cost = 0.0
        self._token_usage = {"input": 0, "output": 0}
        self._query = query
        self._query_id = f"soar-{int(time.time() * 1000)}"

        logger.info(f"Starting SOAR execution for query: {query[:100]}...")

        try:
            # Budget check before execution
            estimated_cost = self.cost_tracker.estimate_cost(
                model=self.reasoning_llm.default_model,
                prompt_length=len(query),
                max_output_tokens=4096,
            )

            can_proceed, budget_message = self.cost_tracker.check_budget(estimated_cost)

            if not can_proceed:
                # Hard limit exceeded - reject query
                status = self.cost_tracker.get_status()
                raise BudgetExceededError(
                    message=budget_message,
                    consumed_usd=status["consumed_usd"],
                    limit_usd=status["limit_usd"],
                    estimated_cost=estimated_cost,
                )

            if budget_message:
                # Soft limit warning
                logger.warning(budget_message)

            # Phase 1: Assess complexity
            phase1_result = self._phase1_assess(query)
            self._phase_metadata["phase1_assess"] = phase1_result

            # Phase 2: Retrieve context
            phase2_result = self._phase2_retrieve(
                query, phase1_result["complexity"]
            )
            self._phase_metadata["phase2_retrieve"] = phase2_result

            # Check for SIMPLE query early exit
            if phase1_result["complexity"] == "SIMPLE":
                # Skip decomposition, go directly to solving
                logger.info("SIMPLE query detected, bypassing decomposition")
                return self._execute_simple_path(query, phase2_result, verbosity)

            # Phase 3: Decompose query
            phase3_result = self._phase3_decompose(
                query, phase2_result, phase1_result["complexity"]
            )
            self._phase_metadata["phase3_decompose"] = phase3_result

            # Phase 4: Verify decomposition
            phase4_result = self._phase4_verify(
                phase3_result, query, phase1_result["complexity"]
            )
            self._phase_metadata["phase4_verify"] = phase4_result

            # Check verification verdict
            if phase4_result["verdict"] == "FAIL":
                logger.error("Decomposition verification failed")
                return self._handle_verification_failure(
                    query, phase4_result, verbosity
                )

            # Phase 5: Route to agents
            phase5_result = self._phase5_route(phase3_result)
            self._phase_metadata["phase5_route"] = phase5_result

            # Phase 6: Execute agents
            phase6_result = self._phase6_collect(
                phase5_result, phase2_result
            )
            self._phase_metadata["phase6_collect"] = phase6_result

            # Phase 7: Synthesize results
            phase7_result = self._phase7_synthesize(
                phase6_result, query, phase3_result
            )
            self._phase_metadata["phase7_synthesize"] = phase7_result

            # Phase 8: Record pattern
            phase8_result = self._phase8_record(
                query, phase3_result, phase6_result, phase7_result
            )
            self._phase_metadata["phase8_record"] = phase8_result

            # Phase 9: Format response
            return self._phase9_respond(phase7_result, verbosity)

        except Exception as e:
            logger.exception(f"SOAR execution failed: {e}")
            return self._handle_execution_error(e, verbosity)

    def _phase1_assess(self, query: str) -> dict[str, Any]:
        """Execute Phase 1: Complexity Assessment."""
        logger.info("Phase 1: Assessing complexity")
        return assess.assess_complexity(query, llm_client=self.reasoning_llm)

    def _phase2_retrieve(self, query: str, complexity: str) -> dict[str, Any]:
        """Execute Phase 2: Context Retrieval."""
        logger.info("Phase 2: Retrieving context")
        return retrieve.retrieve_context(query, complexity, self.store)

    def _phase3_decompose(
        self, query: str, context: dict, complexity: str
    ) -> dict[str, Any]:
        """Execute Phase 3: Query Decomposition."""
        logger.info("Phase 3: Decomposing query")
        return decompose.decompose_query(query, context, complexity)

    def _phase4_verify(
        self, decomposition: dict, query: str, complexity: str
    ) -> dict[str, Any]:
        """Execute Phase 4: Decomposition Verification."""
        logger.info("Phase 4: Verifying decomposition")
        # Select verification option based on complexity
        option = "A" if complexity == "MEDIUM" else "B"
        return verify.verify_decomposition(decomposition, query, option)

    def _phase5_route(self, decomposition: dict) -> dict[str, Any]:
        """Execute Phase 5: Agent Routing."""
        logger.info("Phase 5: Routing to agents")
        return route.route_subgoals(decomposition, self.agent_registry)

    def _phase6_collect(
        self, routing: dict, context: dict
    ) -> dict[str, Any]:
        """Execute Phase 6: Agent Execution."""
        logger.info("Phase 6: Executing agents")
        return collect.execute_agents(routing, context)

    def _phase7_synthesize(
        self, execution: dict, query: str, decomposition: dict
    ) -> dict[str, Any]:
        """Execute Phase 7: Result Synthesis."""
        logger.info("Phase 7: Synthesizing results")
        agent_outputs = execution.get("agent_outputs", [])
        return synthesize.synthesize_results(agent_outputs, query, decomposition)

    def _phase8_record(
        self,
        query: str,
        decomposition: dict,
        execution: dict,
        synthesis: dict,
    ) -> dict[str, Any]:
        """Execute Phase 8: Pattern Recording."""
        logger.info("Phase 8: Recording pattern")
        return record.record_pattern(
            query, decomposition, execution, synthesis, self.store
        )

    def _phase9_respond(
        self, synthesis: dict, verbosity: str
    ) -> dict[str, Any]:
        """Execute Phase 9: Response Formatting."""
        logger.info("Phase 9: Formatting response")
        metadata = self._build_metadata()
        response = respond.format_response(synthesis, metadata, verbosity)

        # Log conversation (async, non-blocking)
        execution_summary = {
            "duration_ms": metadata.get("total_duration_ms", 0),
            "overall_score": synthesis.get("confidence", 0.0),
            "cached": metadata.get("phases", {}).get("phase8_record", {}).get("cached", False),
            "cost_usd": metadata.get("total_cost_usd", 0.0),
            "tokens_used": metadata.get("tokens_used", {}),
        }

        self.conversation_logger.log_interaction(
            query=self._query,
            query_id=self._query_id,
            phase_data=metadata.get("phases", {}),
            execution_summary=execution_summary,
            metadata=metadata,
        )

        return response

    def _execute_simple_path(
        self, query: str, context: dict, verbosity: str
    ) -> dict[str, Any]:
        """Execute simplified path for SIMPLE queries (bypass decomposition).

        Args:
            query: User query
            context: Retrieved context
            verbosity: Output verbosity

        Returns:
            Formatted response
        """
        logger.info("Executing SIMPLE query path")

        # For SIMPLE queries, we skip decomposition and call solving LLM directly
        # This will be implemented in Phase 3-4
        # For now, return a placeholder

        synthesis = {
            "answer": "SIMPLE query placeholder - direct LLM call will be implemented",
            "confidence": 0.9,
            "traceability": [],
        }

        metadata = self._build_metadata()
        return respond.format_response(synthesis, metadata, verbosity)

    def _handle_verification_failure(
        self, query: str, verification: dict, verbosity: str
    ) -> dict[str, Any]:
        """Handle decomposition verification failure.

        Args:
            query: Original query
            verification: Verification result
            verbosity: Output verbosity

        Returns:
            Error response with partial results
        """
        logger.error("Returning partial results due to verification failure")

        synthesis = {
            "answer": "Unable to decompose query successfully. Please rephrase or simplify.",
            "confidence": 0.0,
            "traceability": [],
            "error": "verification_failed",
            "feedback": verification.get("feedback", ""),
        }

        metadata = self._build_metadata()
        metadata["verification_failure"] = verification

        return respond.format_response(synthesis, metadata, verbosity)

    def _handle_execution_error(
        self, error: Exception, verbosity: str
    ) -> dict[str, Any]:
        """Handle execution errors with graceful degradation.

        Args:
            error: Exception that occurred
            verbosity: Output verbosity

        Returns:
            Error response
        """
        logger.error(f"Handling execution error: {error}")

        synthesis = {
            "answer": f"An error occurred during query processing: {str(error)}",
            "confidence": 0.0,
            "traceability": [],
            "error": error.__class__.__name__,
        }

        metadata = self._build_metadata()
        metadata["error_details"] = str(error)

        return respond.format_response(synthesis, metadata, verbosity)

    def _track_llm_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        operation: str,
    ) -> float:
        """Track cost of an LLM call.

        Args:
            model: Model identifier
            input_tokens: Input tokens used
            output_tokens: Output tokens generated
            operation: Operation name (e.g., "assess", "decompose")

        Returns:
            Cost in USD
        """
        cost = self.cost_tracker.record_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            operation=operation,
        )

        # Accumulate totals
        self._total_cost += cost
        self._token_usage["input"] += input_tokens
        self._token_usage["output"] += output_tokens

        logger.debug(
            f"LLM cost tracked: ${cost:.6f} for {operation} "
            f"({input_tokens} in, {output_tokens} out)"
        )

        return cost

    def _build_metadata(self) -> dict[str, Any]:
        """Build aggregated metadata from all phases.

        Returns:
            Dict with execution metadata
        """
        elapsed_time = time.time() - self._start_time

        return {
            "total_duration_ms": elapsed_time * 1000,
            "total_cost_usd": self._total_cost,
            "tokens_used": self._token_usage,
            "budget_status": self.cost_tracker.get_status(),
            "phases": self._phase_metadata,
            "timestamp": time.time(),
        }
