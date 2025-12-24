"""Query execution module for AURORA CLI.

This module provides the QueryExecutor class that handles execution of queries
through either direct LLM calls or the full AURORA SOAR pipeline.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

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
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize QueryExecutor.

        Args:
            config: Optional configuration dictionary with settings like:
                - api_key: Anthropic API key
                - model: LLM model to use
                - temperature: Sampling temperature
                - max_tokens: Maximum tokens for generation
        """
        self.config = config or {}
        logger.info("QueryExecutor initialized")

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

            # Execute LLM call
            model = self.config.get("model", "claude-sonnet-4-20250514")
            temperature = self.config.get("temperature", 0.7)
            max_tokens = self.config.get("max_tokens", 500)

            if verbose:
                logger.info(f"Calling LLM: model={model}, temp={temperature}, max_tokens={max_tokens}")

            response = llm.generate(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            duration = time.time() - start_time

            if verbose:
                logger.info(
                    f"LLM response: {response.output_tokens} tokens, "
                    f"{duration:.2f}s, "
                    f"~${self._estimate_cost(response.input_tokens, response.output_tokens):.4f}"
                )

            return response.content

        except Exception as e:
            logger.error(f"Direct LLM execution failed: {e}", exc_info=True)
            raise RuntimeError(f"LLM execution failed: {e}") from e

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
                logger.info(f"AURORA execution complete: {duration:.2f}s, cost=${result.get('cost_usd', 0):.4f}")
                return final_response, phase_trace

            return final_response

        except Exception as e:
            logger.error(f"AURORA execution failed: {e}", exc_info=True)
            raise RuntimeError(f"AURORA execution failed: {e}") from e

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
        from aurora_core.config.loader import Config
        from aurora_soar.agent_registry import AgentRegistry
        from aurora_soar.orchestrator import SOAROrchestrator

        # Initialize LLM clients (use same model for both for now)
        reasoning_llm = self._initialize_llm_client(api_key)
        solving_llm = self._initialize_llm_client(api_key)

        # Create minimal config
        config_dict = {
            "budget": {"monthly_limit_usd": 100.0},
            "logging": {"conversation_logging_enabled": True},
        }
        config = Config(config_dict)

        # Initialize agent registry
        agent_registry = AgentRegistry()

        # Create orchestrator
        orchestrator = SOAROrchestrator(
            store=memory_store,
            agent_registry=agent_registry,
            config=config,
            reasoning_llm=reasoning_llm,
            solving_llm=solving_llm,
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
            # Search memory store (keyword-based for simplicity)
            results = memory_store.search_keyword(query, limit=limit)

            if not results:
                return ""

            # Format results as context
            context_parts = []
            for i, chunk in enumerate(results, 1):
                metadata = chunk.get("metadata", {})
                file_path = metadata.get("file_path", "unknown")
                content = chunk.get("content", "")
                context_parts.append(f"[{i}] {file_path}:\n{content}\n")

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
                    }
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
            "respond": lambda d: "Formatted response",
        }

        summary_fn = summaries.get(phase_name)
        if summary_fn:
            try:
                return summary_fn(phase_data)
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
