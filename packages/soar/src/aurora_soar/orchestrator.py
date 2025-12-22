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

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from aurora_core.budget import CostTracker
from aurora_core.exceptions import BudgetExceededError
from aurora_core.logging import ConversationLogger, VerbosityLevel
from aurora_reasoning.decompose import DecompositionResult
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
            if phase4_result["final_verdict"] == "FAIL":
                logger.error("Decomposition verification failed")
                return self._handle_verification_failure(
                    query, phase4_result, verbosity
                )

            # Phase 5: Route to agents
            # Extract the decomposition dict from the phase wrapper
            decomposition_dict = phase3_result.get("decomposition", phase3_result)
            phase5_result_obj = self._phase5_route(decomposition_dict)
            # Store dict version in metadata, keep object for phase 6
            phase5_dict = phase5_result_obj.to_dict()
            phase5_dict["_timing_ms"] = 0  # Timing handled internally
            phase5_dict["_error"] = None
            self._phase_metadata["phase5_route"] = phase5_dict

            # Phase 6: Execute agents (needs RouteResult object)
            phase6_result_obj = self._phase6_collect(
                phase5_result_obj, phase2_result
            )
            # Store dict version in metadata, keep object for phase 7
            phase6_dict = phase6_result_obj.to_dict()
            phase6_dict["_timing_ms"] = 0  # Timing handled internally
            phase6_dict["_error"] = None
            phase6_dict["agents_executed"] = len(phase6_result_obj.agent_outputs)
            self._phase_metadata["phase6_collect"] = phase6_dict

            # Phase 7: Synthesize results (needs CollectResult object)
            decomposition_dict = phase3_result.get("decomposition", phase3_result)
            phase7_result_obj = self._phase7_synthesize(
                phase6_result_obj, query, decomposition_dict
            )
            # Store dict version in metadata
            phase7_dict = phase7_result_obj.to_dict()
            phase7_dict["_timing_ms"] = 0
            phase7_dict["_error"] = None
            self._phase_metadata["phase7_synthesize"] = phase7_dict

            # Phase 8: Record pattern (needs object versions)
            phase8_result = self._phase8_record(
                query, phase1_result["complexity"], decomposition_dict, phase6_result_obj, phase7_result_obj
            )
            phase8_dict = phase8_result.to_dict()
            phase8_dict["_timing_ms"] = 0
            phase8_dict["_error"] = None
            self._phase_metadata["phase8_record"] = phase8_dict

            # Phase 9: Format response (needs object versions)
            return self._phase9_respond(phase7_result_obj, phase8_result, verbosity)

        except BudgetExceededError:
            # Re-raise budget errors without handling - caller should handle budget limits
            raise
        except Exception as e:
            logger.exception(f"SOAR execution failed: {e}")
            return self._handle_execution_error(e, verbosity)

    def _phase1_assess(self, query: str) -> dict[str, Any]:
        """Execute Phase 1: Complexity Assessment."""
        logger.info("Phase 1: Assessing complexity")
        start_time = time.time()
        try:
            result = assess.assess_complexity(query, llm_client=self.reasoning_llm)
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            return result
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            return {
                "complexity": "MEDIUM",
                "confidence": 0.0,
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }

    def _phase2_retrieve(self, query: str, complexity: str) -> dict[str, Any]:
        """Execute Phase 2: Context Retrieval."""
        logger.info("Phase 2: Retrieving context")
        start_time = time.time()
        try:
            result = retrieve.retrieve_context(query, complexity, self.store)
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            return result
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            return {
                "code_chunks": [],
                "reasoning_chunks": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }

    def _phase3_decompose(
        self, query: str, context: dict, complexity: str
    ) -> dict[str, Any]:
        """Execute Phase 3: Query Decomposition."""
        logger.info("Phase 3: Decomposing query")
        start_time = time.time()
        try:
            # Get available agents from registry
            agents = self.agent_registry.list_all()
            available_agents = [agent.id for agent in agents]

            phase_result = decompose.decompose_query(
                query=query,
                context=context,
                complexity=complexity,
                llm_client=self.reasoning_llm,
                available_agents=available_agents,
            )
            result = phase_result.to_dict()
            # Add convenience fields for E2E tests
            result["subgoals_total"] = len(result["decomposition"]["subgoals"])
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            return result
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            return {
                "goal": query,
                "subgoals": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }

    def _phase4_verify(
        self, decomposition_dict: dict, query: str, complexity: str
    ) -> dict[str, Any]:
        """Execute Phase 4: Decomposition Verification."""
        logger.info("Phase 4: Verifying decomposition")
        start_time = time.time()
        try:
            # Get available agents from registry
            agents = self.agent_registry.list_all()
            available_agents = [agent.id for agent in agents]

            # Convert decomposition dict to DecompositionResult object
            # The dict contains a nested "decomposition" key from phase 3
            decomposition_data = decomposition_dict.get("decomposition", decomposition_dict)
            decomposition = DecompositionResult.from_dict(decomposition_data)

            phase_result = verify.verify_decomposition(
                decomposition=decomposition,
                complexity=complexity,
                llm_client=self.reasoning_llm,
                query=query,
                available_agents=available_agents,
            )
            result = phase_result.to_dict()
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            return result
        except Exception as e:
            logger.error(f"Phase 4 failed: {e}")
            return {
                "final_verdict": "FAIL",
                "overall_score": 0.0,
                "verification": {
                    "completeness": 0.0,
                    "consistency": 0.0,
                    "groundedness": 0.0,
                    "routability": 0.0,
                    "overall_score": 0.0,
                    "verdict": "FAIL",
                    "issues": [str(e)],
                    "suggestions": [],
                },
                "retry_count": 0,
                "all_attempts": [],
                "method": "error",
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }

    def _phase5_route(self, decomposition: dict) -> route.RouteResult:
        """Execute Phase 5: Agent Routing.

        Returns RouteResult object (not dict) for use by phase 6.
        """
        logger.info("Phase 5: Routing to agents")
        start_time = time.time()
        try:
            result = route.route_subgoals(decomposition, self.agent_registry)
            return result
        except Exception as e:
            logger.error(f"Phase 5 failed: {e}")
            # Return empty RouteResult on failure
            from aurora_soar.phases.route import RouteResult
            return RouteResult(
                agent_assignments=[],
                execution_plan=[],
                routing_metadata={"error": str(e)}
            )

    def _phase6_collect(
        self, routing: route.RouteResult, context: dict
    ) -> collect.CollectResult:
        """Execute Phase 6: Agent Execution.

        Returns CollectResult object (not dict) for use by phase 7.
        """
        logger.info("Phase 6: Executing agents")
        start_time = time.time()
        try:
            # Execute agents asynchronously
            result = asyncio.run(collect.execute_agents(routing, context))
            return result
        except Exception as e:
            logger.error(f"Phase 6 failed: {e}")
            # Return empty CollectResult on failure
            from aurora_soar.phases.collect import CollectResult
            return CollectResult(
                agent_outputs=[],
                execution_metadata={"error": str(e)},
                user_interactions=[]
            )

    def _phase7_synthesize(
        self, collect_result: collect.CollectResult, query: str, decomposition: dict
    ) -> synthesize.SynthesisResult:
        """Execute Phase 7: Result Synthesis."""
        logger.info("Phase 7: Synthesizing results")
        start_time = time.time()
        try:
            result = synthesize.synthesize_results(
                llm_client=self.solving_llm,
                query=query,
                collect_result=collect_result,
                decomposition=decomposition,
            )
            # Track timing
            self._track_llm_cost(
                self.solving_llm.default_model,
                result.timing.get("input_tokens", 0),
                result.timing.get("output_tokens", 0),
                "synthesize",
            )
            return result
        except Exception as e:
            logger.error(f"Phase 7 failed: {e}")
            # Return error synthesis result
            return synthesize.SynthesisResult(
                answer=f"Synthesis failed: {str(e)}",
                confidence=0.0,
                traceability=[],
                metadata={"error": str(e)},
                timing={"synthesis_ms": (time.time() - start_time) * 1000},
            )

    def _phase8_record(
        self,
        query: str,
        complexity: str,
        decomposition: dict,
        collect_result: collect.CollectResult,
        synthesis_result: synthesize.SynthesisResult,
    ) -> record.RecordResult:
        """Execute Phase 8: Pattern Recording."""
        logger.info("Phase 8: Recording pattern")
        start_time = time.time()
        try:
            result = record.record_pattern(
                store=self.store,
                query=query,
                complexity=complexity,
                decomposition=decomposition,
                collect_result=collect_result,
                synthesis_result=synthesis_result,
            )
            return result
        except Exception as e:
            logger.error(f"Phase 8 failed: {e}")
            return record.RecordResult(
                cached=False,
                reasoning_chunk_id=None,
                pattern_marked=False,
                activation_update=0.0,
                timing={"record_ms": (time.time() - start_time) * 1000, "error": str(e)},
            )

    def _phase9_respond(
        self, synthesis_result: synthesize.SynthesisResult, record_result: record.RecordResult, verbosity: str
    ) -> dict[str, Any]:
        """Execute Phase 9: Response Formatting."""
        logger.info("Phase 9: Formatting response")

        # Add phase 9 metadata
        self._phase_metadata["phase9_respond"] = {
            "verbosity": verbosity,
            "formatted": True,
        }

        metadata = self._build_metadata()
        response = respond.format_response(synthesis_result, record_result, metadata, verbosity)

        # Log conversation (async, non-blocking)
        execution_summary = {
            "duration_ms": metadata.get("total_duration_ms", 0),
            "overall_score": synthesis_result.confidence,
            "cached": record_result.cached,
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

        return response.to_dict()

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
        start_time = time.time()

        # For SIMPLE queries, we skip decomposition and call solving LLM directly
        from aurora_soar.phases.synthesize import SynthesisResult
        from aurora_soar.phases.record import RecordResult

        try:
            # Build prompt with context
            prompt_parts = [f"Query: {query}"]

            # Add retrieved context if available
            code_chunks = context.get("code_chunks", [])
            reasoning_chunks = context.get("reasoning_chunks", [])

            if code_chunks:
                prompt_parts.append("\nRelevant Code:")
                for chunk in code_chunks[:5]:  # Limit to top 5
                    content = chunk.content if hasattr(chunk, 'content') else chunk.get('content', '')
                    prompt_parts.append(f"- {content[:200]}...")  # Truncate long chunks

            if reasoning_chunks:
                prompt_parts.append("\nRelevant Context:")
                for chunk in reasoning_chunks[:3]:  # Limit to top 3
                    pattern = chunk.pattern if hasattr(chunk, 'pattern') else chunk.get('pattern', '')
                    prompt_parts.append(f"- {pattern}")

            prompt_parts.append("\nPlease provide a clear, concise answer:")
            prompt = "\n".join(prompt_parts)

            # Call solving LLM
            logger.info("Calling solving LLM for SIMPLE query")
            response = self.solving_llm.generate(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.7,
            )

            # Track cost
            self._track_llm_cost(
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                operation="simple_query_solving",
            )

            # Create synthesis result
            synthesis = SynthesisResult(
                answer=response.content,
                confidence=0.9,  # High confidence for direct LLM response
                traceability=[],
                metadata={
                    "simple_path": True,
                    "context_used": {
                        "code_chunks": len(code_chunks),
                        "reasoning_chunks": len(reasoning_chunks),
                    }
                },
                timing={
                    "synthesis_ms": (time.time() - start_time) * 1000,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                },
            )

        except Exception as e:
            logger.error(f"SIMPLE query path failed: {e}")
            synthesis = SynthesisResult(
                answer=f"Error processing query: {str(e)}",
                confidence=0.0,
                traceability=[],
                metadata={"error": str(e)},
                timing={"synthesis_ms": (time.time() - start_time) * 1000},
            )

        # Record pattern (lightweight for simple queries)
        record = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=0.0,
            timing={"record_ms": 0},
        )

        # Add simple path metadata to phase tracking
        self._phase_metadata["phase7_synthesize"] = synthesis.to_dict()
        self._phase_metadata["phase8_record"] = record.to_dict()

        # Use phase 9 to format response properly
        return self._phase9_respond(synthesis, record, verbosity)

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
        from aurora_soar.phases.synthesize import SynthesisResult
        from aurora_soar.phases.record import RecordResult

        synthesis = SynthesisResult(
            answer="Unable to decompose query successfully. Please rephrase or simplify.",
            confidence=0.0,
            traceability=[],
            metadata={
                "error": "verification_failed",
                "feedback": verification.get("feedback", ""),
            },
            timing={"synthesis_ms": 0},
        )

        record = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=0.0,
            timing={"record_ms": 0},
        )

        # Add verification failure to phase metadata before response formatting
        self._phase_metadata["verification_failure"] = verification

        return self._phase9_respond(synthesis, record, verbosity)

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
        from aurora_soar.phases.synthesize import SynthesisResult
        from aurora_soar.phases.record import RecordResult

        synthesis = SynthesisResult(
            answer=f"An error occurred during query processing: {str(error)}",
            confidence=0.0,
            traceability=[],
            metadata={"error": error.__class__.__name__},
            timing={"synthesis_ms": 0},
        )

        record = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=0.0,
            timing={"record_ms": 0},
        )

        # Add error details to phase metadata
        self._phase_metadata["error_details"] = str(error)

        return self._phase9_respond(synthesis, record, verbosity)

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
            "query_id": self._query_id,
            "query": self._query,
            "total_duration_ms": elapsed_time * 1000,
            "total_cost_usd": self._total_cost,
            "tokens_used": self._token_usage,
            "budget_status": self.cost_tracker.get_status(),
            "phases": self._phase_metadata,
            "timestamp": time.time(),
        }
