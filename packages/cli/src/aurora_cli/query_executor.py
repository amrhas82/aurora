"""Query execution module for AURORA CLI.

This module provides the QueryExecutor class that handles execution of queries
through either direct LLM calls or the full AURORA SOAR pipeline.
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aurora_cli.errors import APIError, ErrorHandler
from aurora_core.budget.tracker import BudgetExceededError, CostTracker
from aurora_reasoning.llm_client import AnthropicClient, LLMClient

if TYPE_CHECKING:
    from aurora_core.store.base import Store
    from aurora_soar.orchestrator import SOAROrchestrator


logger = logging.getLogger(__name__)


class QueryExecutor:
    """Executor for query processing with direct LLM or AURORA pipeline.

    This class abstracts the execution logic for queries, providing methods
    for both direct LLM calls (fast mode) and full AURORA orchestration
    (complex queries).

    Attributes:
        config: Configuration dictionary with execution settings
        interactive_mode: Whether to prompt user for weak retrieval matches

    """

    def __init__(self, config: dict[str, Any] | None = None, interactive_mode: bool = False):
        """Initialize QueryExecutor.

        Args:
            config: Optional configuration dictionary with settings like:
                - api_key: Anthropic API key
                - model: LLM model to use
                - temperature: Sampling temperature
                - max_tokens: Maximum tokens for generation
            interactive_mode: If True, prompt user when retrieval quality is weak.
                Only applicable to CLI usage (not MCP tools). Default: False.

        """
        self.config = config or {}
        self.interactive_mode = interactive_mode
        self.error_handler = ErrorHandler()
        logger.info(f"QueryExecutor initialized (interactive_mode={interactive_mode})")

    def execute_direct_llm(
        self,
        query: str,
        api_key: str,
        memory_store: Store | None = None,
        verbose: bool = False,
    ) -> str:
        """Execute query using direct LLM call (fast mode).

        This method bypasses the full AURORA pipeline and sends the query
        directly to the LLM. Optionally includes memory context if a memory
        store is provided and contains relevant chunks.

        Args:
            query: The user query string
            api_key: Anthropic API key for authentication
            memory_store: Optional memory store for context retrieval
            verbose: If True, log detailed execution information

        Returns:
            The LLM's response as a string

        Raises:
            ValueError: If query is empty or API key is invalid
            RuntimeError: If API call fails after retries

        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not api_key or not api_key.strip():
            raise ValueError("API key is required for LLM execution")

        start_time = time.time()

        try:
            # Initialize budget tracker with config overrides
            budget_path_str = self.config.get("budget_tracker_path")
            if budget_path_str:
                budget_path = Path(budget_path_str)
            else:
                budget_path = Path.home() / ".aurora" / "budget_tracker.json"

            budget_limit = self.config.get("budget_limit", 10.0)

            tracker = CostTracker(monthly_limit_usd=budget_limit, tracker_path=budget_path)

            # Check budget BEFORE making LLM call
            model = self.config.get("model", "claude-sonnet-4-20250514")
            max_tokens = self.config.get("max_tokens", 500)

            # Estimate cost (conservative: assume full prompt + expected response)
            estimated_cost = tracker.estimate_cost(model, len(query), max_tokens)

            if verbose:
                logger.info(f"Estimated cost: ${estimated_cost:.4f}")

            # This will raise BudgetExceededError if budget exceeded
            tracker.check_budget(estimated_cost, raise_on_exceeded=True)

            # Initialize LLM client
            llm = self._initialize_llm_client(api_key)

            # Build prompt with optional memory context
            prompt = query
            if memory_store is not None:
                context = self._get_memory_context(memory_store, query, limit=3)
                if context:
                    prompt = f"Context:\n{context}\n\nQuery: {query}"
                    if verbose:
                        logger.info(f"Added memory context ({len(context)} chars)")

            # Execute LLM call with retry logic
            temperature = self.config.get("temperature", 0.7)

            if verbose:
                logger.info(
                    f"Calling LLM: model={model}, temp={temperature}, max_tokens={max_tokens}",
                )

            response = self._call_llm_with_retry(
                llm=llm,
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                verbose=verbose,
            )

            duration = time.time() - start_time

            # Record actual cost after successful LLM call
            actual_cost = tracker.calculate_cost(
                model,
                response.input_tokens,
                response.output_tokens,
            )
            tracker.record_cost(
                model=model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                operation="direct_llm",
                query_id=None,
            )

            if verbose:
                logger.info(
                    f"LLM response: {response.output_tokens} tokens, "
                    f"{duration:.2f}s, "
                    f"~${actual_cost:.4f}",
                )

            # Type assertion: we know response.content is a string from LLM client
            return str(response.content)

        except BudgetExceededError:
            # Re-raise budget errors without wrapping
            raise

        except APIError:
            # Re-raise API errors with formatted messages
            raise
        except Exception as e:
            logger.error(f"Direct LLM execution failed: {e}", exc_info=True)
            error_msg = self.error_handler.handle_api_error(e, "Direct LLM query")
            raise APIError(error_msg) from e

    def execute_with_auto_escalation(
        self,
        query: str,
        api_key: str,
        memory_store: Store,
        verbose: bool = False,
        confidence_threshold: float = 0.6,
    ) -> str | tuple[str, dict[str, Any]]:
        """Execute query with automatic escalation based on confidence.

        This method assesses query complexity first, then decides whether to
        use direct LLM or SOAR pipeline based on confidence score. In non-interactive
        mode, low-confidence queries automatically escalate to SOAR. In interactive
        mode, user is prompted to confirm escalation.

        Args:
            query: The user query string
            api_key: Anthropic API key for authentication
            memory_store: Memory store for context retrieval (required)
            verbose: If True, return phase trace data (SOAR) or detailed logs
            confidence_threshold: Confidence below this triggers escalation (default: 0.6)

        Returns:
            If verbose=False: The final response string
            If verbose=True: Tuple of (response, metadata_dict)

        Raises:
            ValueError: If query is empty or memory store is None
            RuntimeError: If execution fails

        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if memory_store is None:
            raise ValueError("Memory store is required for auto-escalation")

        try:
            # Assess query complexity
            from aurora_soar.phases.assess import assess_complexity

            llm = self._initialize_llm_client(api_key)
            assessment = assess_complexity(query, llm_client=llm)

            complexity = assessment.get("complexity", "SIMPLE")
            confidence = assessment.get("confidence", 1.0)

            logger.info(
                f"Complexity assessment: {complexity} "
                f"(confidence={confidence:.3f}, method={assessment.get('method')})",
            )

            # Determine if escalation is needed
            should_escalate = False
            if confidence < confidence_threshold:
                logger.info(
                    f"Low confidence ({confidence:.3f} < {confidence_threshold}), "
                    "considering escalation to SOAR",
                )

                if self.interactive_mode:
                    # Prompt user for escalation decision
                    import click

                    should_escalate = click.confirm(
                        f"Query has low confidence ({confidence:.2f}). "
                        "Use SOAR 9-phase pipeline for better accuracy?",
                        default=False,
                    )

                    if should_escalate:
                        logger.info("User confirmed escalation to SOAR")
                    else:
                        logger.info("User declined escalation, using direct LLM")
                else:
                    # Non-interactive: auto-escalate
                    should_escalate = True
                    logger.info("Non-interactive mode: auto-escalating to SOAR")

            # Execute based on escalation decision
            if should_escalate or complexity in ["COMPLEX", "CRITICAL"]:
                logger.info("Executing with SOAR pipeline")
                return self.execute_aurora(
                    query=query,
                    api_key=api_key,
                    memory_store=memory_store,
                    verbose=verbose,
                )
            logger.info("Executing with direct LLM")
            response = self.execute_direct_llm(
                query=query,
                api_key=api_key,
                memory_store=memory_store,
                verbose=verbose,
            )

            if verbose:
                # Return response with assessment metadata
                metadata = {
                    "method": "direct_llm",
                    "assessment": assessment,
                    "escalated": False,
                }
                return response, metadata

            return response

        except Exception as e:
            logger.error(f"Auto-escalation execution failed: {e}", exc_info=True)
            raise

    def execute_aurora(
        self,
        query: str,
        api_key: str,
        memory_store: Store,
        verbose: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        """Execute query using full AURORA SOAR pipeline.

        This method uses the complete 9-phase SOAR orchestration for complex
        queries that require decomposition, multi-agent execution, and synthesis.

        Args:
            query: The user query string
            api_key: Anthropic API key for authentication
            memory_store: Memory store for context retrieval (required)
            verbose: If True, return phase trace data

        Returns:
            If verbose=False: The final response string
            If verbose=True: Tuple of (response, phase_trace_dict)

        Raises:
            ValueError: If query is empty or memory store is None
            RuntimeError: If orchestrator execution fails

        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if memory_store is None:
            raise ValueError("Memory store is required for AURORA execution")

        start_time = time.time()

        try:
            # Initialize orchestrator
            orchestrator = self._initialize_orchestrator(api_key, memory_store)

            if verbose:
                logger.info("Executing AURORA orchestrator with full pipeline")

            # Execute SOAR pipeline
            verbosity = "VERBOSE" if verbose else "NORMAL"
            result = orchestrator.execute(query=query, verbosity=verbosity)

            duration = time.time() - start_time

            # Extract response
            final_response = result.get("answer", "")

            if verbose:
                # Build phase trace
                phase_trace = self._build_phase_trace(result, duration)
                logger.info(
                    f"AURORA execution complete: {duration:.2f}s, cost=${result.get('cost_usd', 0):.4f}",
                )
                return str(final_response), phase_trace

            return str(final_response)

        except APIError:
            # Re-raise API errors with formatted messages
            raise
        except Exception as e:
            logger.error(f"AURORA execution failed: {e}", exc_info=True)
            error_msg = self.error_handler.handle_api_error(e, "AURORA orchestrator")
            raise APIError(error_msg) from e

    def _initialize_llm_client(self, api_key: str) -> LLMClient:
        """Initialize LLM client with API key.

        Args:
            api_key: Anthropic API key

        Returns:
            Configured LLMClient instance

        """
        model = self.config.get("model", "claude-sonnet-4-20250514")
        return AnthropicClient(api_key=api_key, default_model=model)

    def _initialize_orchestrator(
        self,
        api_key: str,
        memory_store: Store,
    ) -> SOAROrchestrator:
        """Initialize SOAR orchestrator with dependencies.

        Args:
            api_key: Anthropic API key
            memory_store: Memory store instance

        Returns:
            Configured SOAROrchestrator instance

        """
        from aurora_cli.config import Config
        from aurora_soar.agent_registry import AgentRegistry
        from aurora_soar.orchestrator import SOAROrchestrator

        # Initialize LLM clients (use same model for both for now)
        reasoning_llm = self._initialize_llm_client(api_key)
        solving_llm = self._initialize_llm_client(api_key)

        # Create config with overrides for execution context
        config = Config()
        # Add execution-specific settings
        config._data.setdefault("budget", {})["monthly_limit_usd"] = 100.0
        config._data.setdefault("logging", {})["conversation_logging_enabled"] = True

        # Initialize agent registry
        agent_registry = AgentRegistry()

        # Create orchestrator with interactive mode setting
        orchestrator = SOAROrchestrator(
            store=memory_store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=reasoning_llm,
            solving_llm=solving_llm,
            interactive_mode=self.interactive_mode,
        )

        return orchestrator

    def _get_memory_context(
        self,
        memory_store: Store,
        query: str,
        limit: int = 3,
    ) -> str:
        """Retrieve relevant context from memory store.

        Args:
            memory_store: Memory store to query
            query: Query string for context retrieval
            limit: Maximum number of chunks to retrieve

        Returns:
            Formatted context string (empty if no results)

        """
        try:
            # Use MemoryManager to perform hybrid search with activation scoring
            from aurora_cli.memory_manager import MemoryManager

            # Create a temporary MemoryManager with the memory store
            # This allows us to use the proper search functionality
            manager = MemoryManager(memory_store=memory_store)

            # Perform search using hybrid retrieval
            results = manager.search(query, limit=limit)

            if not results:
                return ""

            # Format results as context with file paths and line ranges
            context_parts = []
            for i, result in enumerate(results, 1):
                file_path = result.file_path or "unknown"
                line_range = f"{result.line_range[0]}-{result.line_range[1]}"
                content = result.content
                context_parts.append(f"[{i}] {file_path} (lines {line_range}):\n{content}\n")

            logger.debug(f"Retrieved {len(results)} chunks for context")
            return "\n".join(context_parts)

        except Exception as e:
            logger.warning(f"Failed to retrieve memory context: {e}")
            return ""

    def _build_phase_trace(self, result: dict[str, Any], total_duration: float) -> dict[str, Any]:
        """Build phase trace from orchestrator result.

        Args:
            result: Orchestrator execution result
            total_duration: Total execution duration in seconds

        Returns:
            Dictionary with phase trace information

        """
        reasoning_trace = result.get("reasoning_trace", {})
        metadata = result.get("metadata", {})

        # Extract phase information
        phases = []
        for phase_name in [
            "assess",
            "retrieve",
            "decompose",
            "verify",
            "route",
            "collect",
            "synthesize",
            "record",
            "respond",
        ]:
            phase_data = reasoning_trace.get(phase_name, {})
            if phase_data:
                phases.append(
                    {
                        "name": phase_name.capitalize(),
                        "duration": phase_data.get("duration_ms", 0) / 1000.0,
                        "summary": self._get_phase_summary(phase_name, phase_data),
                    },
                )

        return {
            "phases": phases,
            "total_duration": total_duration,
            "total_cost": result.get("cost_usd", 0.0),
            "confidence": result.get("confidence", 0.0),
            "overall_score": result.get("overall_score", 0.0),
            "metadata": metadata,
        }

    def _get_phase_summary(self, phase_name: str, phase_data: dict[str, Any]) -> str:
        """Generate human-readable summary for a phase.

        Args:
            phase_name: Name of the phase
            phase_data: Phase execution data

        Returns:
            Brief summary string

        """
        summaries = {
            "assess": lambda d: f"Complexity: {d.get('complexity', 'unknown')}",
            "retrieve": lambda d: f"Retrieved {d.get('chunks_retrieved', 0)} chunks",
            "decompose": lambda d: f"Created {len(d.get('subgoals', []))} subgoals",
            "verify": lambda d: f"Quality score: {d.get('quality_score', 0):.2f}",
            "route": lambda d: f"Assigned {len(d.get('agent_assignments', []))} agents",
            "collect": lambda d: f"Executed {d.get('executions', 0)} agents",
            "synthesize": lambda d: f"Synthesized from {d.get('sources', 0)} sources",
            "record": lambda d: f"Cached {d.get('patterns_cached', 0)} patterns",
            "respond": lambda _: "Formatted response",
        }

        summary_fn = summaries.get(phase_name)
        if summary_fn:
            try:
                return summary_fn(phase_data)  # type: ignore[no-untyped-call]
            except Exception:
                return "Completed"
        return "Completed"

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate API cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD

        """
        # Claude Sonnet 4 pricing (approximate)
        INPUT_COST_PER_1K = 0.003
        OUTPUT_COST_PER_1K = 0.015

        input_cost = (input_tokens / 1000.0) * INPUT_COST_PER_1K
        output_cost = (output_tokens / 1000.0) * OUTPUT_COST_PER_1K

        return input_cost + output_cost

    def _call_llm_with_retry(
        self,
        llm: LLMClient,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        verbose: bool = False,
        max_retries: int = 3,
    ) -> Any:
        """Call LLM with exponential backoff retry logic.

        Implements retry logic for transient failures like rate limits and server errors.
        Uses exponential backoff with jitter to avoid thundering herd.

        Args:
            llm: LLM client instance
            prompt: Prompt to send to LLM
            model: Model name to use
            max_tokens: Maximum tokens for generation
            temperature: Sampling temperature
            verbose: If True, log retry attempts
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            LLM response object

        Raises:
            APIError: If all retries are exhausted or non-retryable error occurs

        """
        base_delay = 0.1  # Start with 100ms
        last_error = None

        for attempt in range(max_retries):
            try:
                response = llm.generate(
                    prompt=prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if error is retryable
                is_rate_limit = "429" in error_str or "rate limit" in error_str
                is_server_error = any(
                    code in error_str for code in ["500", "502", "503", "504", "server error"]
                )
                is_network_error = any(
                    term in error_str
                    for term in ["connection", "timeout", "network", "temporarily unavailable"]
                )

                is_retryable = is_rate_limit or is_server_error or is_network_error

                # Non-retryable errors: raise immediately
                if not is_retryable or attempt == max_retries - 1:
                    logger.error(f"LLM API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                    error_msg = self.error_handler.handle_api_error(e, "LLM API call")
                    raise APIError(error_msg) from e

                # Calculate delay with exponential backoff and jitter
                delay = base_delay * (2**attempt)
                jitter = random.uniform(0, delay * 0.1)  # Add 0-10% jitter
                total_delay = delay + jitter

                if verbose or is_rate_limit:
                    logger.info(
                        f"Retrying LLM call in {total_delay:.2f}s... "
                        f"(attempt {attempt + 1}/{max_retries})",
                    )

                time.sleep(total_delay)

        # Should never reach here, but just in case
        error_msg = self.error_handler.handle_api_error(
            last_error or Exception("Unknown error"),
            "LLM API call",
        )
        raise APIError(error_msg)
