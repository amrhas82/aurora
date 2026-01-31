"""SOAR Orchestrator - Main Pipeline Coordination.

This module implements the simplified 7-phase SOAR (Sense-Orient-Adapt-Respond)
orchestrator that coordinates the entire reasoning pipeline from query assessment
to response formatting.

The 7 phases are (Task 5.7 - simplified from 9 phases):
1. Assess - Determine query complexity
2. Retrieve - Get relevant context from memory
3. Decompose - Break query into subgoals
4. Verify - Validate decomposition + assign agents (combined with routing)
5. Collect - Execute agents and gather results
6. Synthesize - Combine results into answer
7. Record - Cache reasoning patterns (lightweight)
8. Respond - Format final response

Key simplifications:
- Phase 4 (Verify) now uses verify_lite which combines validation + agent assignment
- Removed separate Route phase (agent assignment now part of verify_lite)
- Phase 7 (Record) uses record_pattern_lightweight for minimal overhead
- Total phases reduced from 9 to 7 for improved performance

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
from typing import TYPE_CHECKING, Any, Callable, cast

from aurora_core.budget import CostTracker
from aurora_core.exceptions import BudgetExceededError
from aurora_core.logging import ConversationLogger
from aurora_core.metrics.query_metrics import QueryMetrics
from aurora_soar import discovery_adapter
from aurora_soar.phases import (
    assess,
    collect,
    decompose,
    record,
    respond,
    retrieve,
    synthesize,
    verify,
)
from aurora_soar.phases.respond import Verbosity

if TYPE_CHECKING:
    from aurora_core.store.base import Store
    from aurora_reasoning.llm_client import LLMClient
    from aurora_soar.agent_registry import AgentInfo, AgentRegistry

    # Config can be a dict or Config wrapper class - both support .get() method
    Config = dict[str, Any]


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
        config: Config,
        reasoning_llm: LLMClient,
        solving_llm: LLMClient,
        agent_registry: AgentRegistry | None = None,
        cost_tracker: CostTracker | None = None,
        conversation_logger: ConversationLogger | None = None,
        interactive_mode: bool = False,
        phase_callback: Callable[[str, str, dict[str, Any]], None] | None = None,
    ):
        """Initialize SOAR orchestrator.

        Args:
            store: ACT-R memory store instance
            config: System configuration
            reasoning_llm: LLM client for reasoning tasks (Tier 2 model: Sonnet/GPT-4)
            solving_llm: LLM client for solving tasks (Tier 1 model: Haiku/GPT-3.5)
            agent_registry: Optional agent registry instance. If None, uses discovery_adapter.
            cost_tracker: Optional cost tracker (creates default if not provided)
            conversation_logger: Optional conversation logger (creates default if not provided)
            interactive_mode: If True, prompt user for weak retrieval matches (CLI only, default: False)
            phase_callback: Optional callback invoked before/after each phase.
                Signature: callback(phase_name, status, result_summary)
                - phase_name: str - Name of the phase (e.g., "assess", "decompose")
                - status: str - Either "before" or "after"
                - result_summary: dict - Summary of phase result (empty for "before")

        """
        self.store = store
        self.agent_registry = agent_registry
        self.config = config
        self.interactive_mode = interactive_mode
        self.reasoning_llm = reasoning_llm
        self.solving_llm = solving_llm
        self.phase_callback = phase_callback

        # Initialize ManifestManager if agent_registry not provided
        self._use_discovery = agent_registry is None
        if self._use_discovery:
            self._manifest_manager = discovery_adapter.get_manifest_manager()

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

        # Initialize query metrics tracker (Task 4.5.3)
        self.query_metrics = QueryMetrics()

        # Initialize LLM circuit breaker for decompose phase
        from aurora_spawner.circuit_breaker import get_circuit_breaker

        self._llm_circuit_breaker = get_circuit_breaker()

        # Configure health monitoring (combined proactive + early detection)
        self._configure_health_monitoring()

        # Initialize phase-level metadata tracking
        self._phase_metadata: dict[str, Any] = {}
        self._total_cost: float = 0.0
        self._token_usage: dict[str, int] = {"input": 0, "output": 0}
        self._start_time: float = 0.0
        self._query_id: str = ""
        self._query: str = ""

        logger.info("SOAR orchestrator initialized")

    def _configure_health_monitoring(self) -> None:
        """Configure health monitoring (proactive + early detection) from config.

        Combines configuration of both systems in a single pass for startup performance.
        """
        from aurora_spawner.early_detection import (
            EarlyDetectionConfig,
            reset_early_detection_monitor,
        )
        from aurora_spawner.observability import ProactiveHealthConfig, get_health_monitor

        # Get config dicts (single lookup each)
        health_config_dict = self.config.get("proactive_health_checks", {})
        early_config_dict = self.config.get("early_detection", {})

        health_enabled = health_config_dict.get("enabled", True)
        early_enabled = early_config_dict.get("enabled", True)

        # Configure proactive health checking
        if health_enabled:
            proactive_config = ProactiveHealthConfig(
                enabled=True,
                check_interval=health_config_dict.get("check_interval", 5.0),
                no_output_threshold=health_config_dict.get("no_output_threshold", 15.0),
                failure_threshold=health_config_dict.get("failure_threshold", 3),
            )

            health_monitor = get_health_monitor()
            health_monitor._proactive_config = proactive_config
            logger.debug(
                f"Proactive health: interval={proactive_config.check_interval}s, "
                f"threshold={proactive_config.no_output_threshold}s",
            )
        else:
            logger.debug("Proactive health checking disabled")

        # Configure early detection
        if early_enabled:
            early_config = EarlyDetectionConfig(
                enabled=True,
                check_interval=early_config_dict.get("check_interval", 2.0),
                stall_threshold=early_config_dict.get("stall_threshold", 15.0),
                min_output_bytes=early_config_dict.get("min_output_bytes", 100),
                stderr_pattern_check=early_config_dict.get("stderr_pattern_check", True),
                memory_limit_mb=early_config_dict.get("memory_limit_mb"),
            )

            reset_early_detection_monitor(early_config)
            logger.debug(
                f"Early detection: interval={early_config.check_interval}s, "
                f"stall={early_config.stall_threshold}s",
            )
        else:
            logger.debug("Early detection disabled")

    def _list_agents(self) -> list[AgentInfo]:
        """List all available agents using registry or discovery adapter.

        Returns:
            List of AgentInfo objects (from either registry or discovery)

        """
        if self._use_discovery:
            return discovery_adapter.list_agents()
        if self.agent_registry is None:
            return []
        return self.agent_registry.list_all()

    def _get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID using registry or discovery adapter.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentInfo object if found, None otherwise

        """
        if self._use_discovery:
            return discovery_adapter.get_agent(agent_id)
        if self.agent_registry is None:
            return None
        return self.agent_registry.get(agent_id)

    def _get_or_create_fallback_agent(self) -> AgentInfo:
        """Get or create a fallback agent when no suitable agent is found.

        Returns:
            AgentInfo object for fallback agent

        """
        if self._use_discovery:
            return discovery_adapter.create_fallback_agent()
        if self.agent_registry is None:
            raise RuntimeError("No agent registry available to create fallback agent")
        return self.agent_registry.create_fallback_agent()

    def _invoke_callback(
        self,
        phase_name: str,
        status: str,
        result_summary: dict[str, Any] | None = None,
    ) -> None:
        """Invoke phase callback if configured.

        Exceptions from the callback are caught and logged, not propagated.

        Args:
            phase_name: Name of the phase (e.g., "assess", "decompose")
            status: Either "before" or "after"
            result_summary: Summary of phase result (empty dict for "before")

        """
        if self.phase_callback is None:
            return

        try:
            self.phase_callback(phase_name, status, result_summary or {})
        except Exception as e:
            logger.warning(f"Phase callback failed for {phase_name}/{status}: {e}")

    def execute(
        self,
        query: str,
        verbosity: str = "NORMAL",
        _max_cost_usd: float | None = None,
        context_files: list[str] | None = None,
        stop_after_verify: bool = False,
    ) -> dict[str, Any]:
        """Execute the full 8-phase SOAR pipeline.

        This is the main entry point for query processing. It coordinates all
        phases and handles errors gracefully.

        Args:
            query: User query string
            verbosity: Output verbosity level (QUIET, NORMAL, VERBOSE, JSON)
            max_cost_usd: Optional budget limit for this query (overrides config)
            context_files: Optional list of context files to inject
            stop_after_verify: If True, stop after phase 4 (verify) and return
                decomposition + agent assignments. Used by `aur goals` to get
                mature decomposition without executing agents.

        Returns:
            Dict with keys (full execution):
                - answer: str (synthesized answer)
                - confidence: float (0-1)
                - overall_score: float (0-1)
                - reasoning_trace: dict (phase outputs)
                - metadata: dict (execution metadata)
                - cost_usd: float (actual cost)

            Dict with keys (stop_after_verify=True):
                - decomposition: dict (subgoals with agent assignments)
                - agent_assignments: list[dict] (index, agent_id, match_quality)
                - subgoals_detailed: list[dict] (full subgoal info)
                - complexity: str (SIMPLE, MEDIUM, COMPLEX)
                - context: dict (retrieved context)
                - metadata: dict (execution metadata)

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

            # Check budget with raise_on_exceeded=False to get tuple return
            # We'll raise manually with proper error attributes
            can_proceed, budget_message = self.cost_tracker.check_budget(
                estimated_cost,
                raise_on_exceeded=False,
            )

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
            phase2_result = self._phase2_retrieve(query, phase1_result["complexity"])

            # Inject context files if provided (--context flag)
            if context_files:
                phase2_result = self._inject_context_files(phase2_result, context_files)

            self._phase_metadata["phase2_retrieve"] = phase2_result

            # Check for SIMPLE query early exit
            if phase1_result["complexity"] == "SIMPLE":
                if stop_after_verify:
                    # For goals-only mode, return single-subgoal decomposition
                    logger.info("SIMPLE query with stop_after_verify, returning single subgoal")
                    return self._build_simple_verify_result(query, phase2_result)
                # Skip decomposition, go directly to solving
                logger.info("SIMPLE query detected, bypassing decomposition")
                return self._execute_simple_path(query, phase2_result, verbosity)

            # Check SOAR cache for a previous successful decomposition
            cache_hit = self._check_soar_cache_hit(phase2_result)
            if cache_hit is not None:
                logger.info("SOAR cache hit: reusing previous decomposition")
                self._phase_metadata["cache_hit"] = True
                phase3_result = cache_hit
                self._phase_metadata["phase3_decompose"] = phase3_result

                # Trigger phase callback to show cached decomposition in UX
                decomposition = phase3_result.get("decomposition", phase3_result)
                subgoal_count = len(decomposition.get("subgoals", []))
                if self.phase_callback:
                    self.phase_callback(
                        "decompose",
                        "before",
                        {"query": query, "cached": True},
                    )
                    self.phase_callback(
                        "decompose",
                        "after",
                        {
                            "subgoal_count": subgoal_count,
                            "cached": True,
                            "cache_source": phase3_result.get("_cache_source", "unknown"),
                        },
                    )

                # For goals-only mode with cache hit, return directly without re-verifying
                # (cached decomposition was already verified when first saved)
                if stop_after_verify and cache_hit.get("_cache_source"):
                    return self._build_cached_verify_result(
                        query=query,
                        complexity=phase1_result["complexity"],
                        context=phase2_result,
                        cache_hit=cache_hit,
                    )
            else:
                # Phase 3: Decompose query
                phase3_result = self._phase3_decompose(
                    query,
                    phase2_result,
                    phase1_result["complexity"],
                )
                self._phase_metadata["phase3_decompose"] = phase3_result

            # Check if Phase 3 failed before proceeding
            if phase3_result.get("_error") is not None:
                logger.error(f"Phase 3 decomposition failed: {phase3_result['_error']}")
                # Return partial results with error indication
                return self._handle_decomposition_failure(query, phase3_result, verbosity)

            # Phase 4: Verify decomposition with verify_lite (Task 5.3)
            logger.info("Phase 4: Verifying decomposition")
            self._invoke_callback("verify", "before", {})

            # Extract decomposition dict and get available agents
            decomposition_dict = phase3_result.get("decomposition", phase3_result)
            available_agents = self._get_available_agents()

            # Call verify_lite which combines validation + agent assignment
            passed, agent_assignments, issues = verify.verify_lite(
                decomposition_dict,
                available_agents,
                complexity=phase1_result["complexity"],
            )

            # Build subgoal summary for display and output formatting
            subgoals = decomposition_dict.get("subgoals", [])
            subgoal_details = []
            for idx, agent in agent_assignments:
                sg = subgoals[idx] if idx < len(subgoals) else {}
                # Check if agent is a spawn (gap) - marked by verify_lite
                agent_config = getattr(agent, "config", {}) or {}
                is_spawn = agent_config.get("is_spawn", False)
                match_quality = agent_config.get("match_quality", "acceptable")
                ideal_agent = agent_config.get("ideal_agent", "")
                ideal_agent_desc = agent_config.get("ideal_agent_desc", "")
                subgoal_details.append(
                    {
                        "index": idx + 1,
                        "description": sg.get("description", ""),
                        "agent": agent.id,
                        "is_critical": sg.get("is_critical", False),
                        "depends_on": sg.get("depends_on", []),
                        "is_spawn": is_spawn,
                        "match_quality": match_quality,
                        "ideal_agent": ideal_agent,
                        "ideal_agent_desc": ideal_agent_desc,
                    },
                )

            # Invoke callback with result (including subgoal details for table display)
            self._invoke_callback(
                "verify",
                "after",
                {
                    "verdict": "PASS" if passed else "FAIL",
                    "overall_score": 1.0 if passed else 0.5,
                    "issues": issues,
                    "agents_assigned": len(agent_assignments),
                    "subgoals": subgoal_details,  # For table display
                },
            )

            phase4_result = {
                "final_verdict": "PASS" if passed else "FAIL",
                "agent_assignments": [
                    {"index": idx, "agent_id": agent.id} for idx, agent in agent_assignments
                ],
                "issues": issues,
                "subgoals_detailed": subgoal_details,  # Add detailed subgoal data
                "_timing_ms": 0,
                "_error": None,
            }
            self._phase_metadata["phase4_verify"] = phase4_result

            # Check verification verdict with auto-retry (Task 5.3)
            if not passed:
                logger.warning(f"Verification failed: {issues}. Retrying decomposition...")
                # Generate retry feedback from issues
                retry_feedback = "Please fix the following issues:\n" + "\n".join(
                    f"- {issue}" for issue in issues
                )

                # Retry decomposition with feedback
                phase3_result = self._phase3_decompose(
                    query,
                    phase2_result,
                    phase1_result["complexity"],
                    _retry_feedback=retry_feedback,
                )
                self._phase_metadata["phase3_decompose_retry"] = phase3_result

                # Retry verification
                decomposition_dict = phase3_result.get("decomposition", phase3_result)
                passed, agent_assignments, issues = verify.verify_lite(
                    decomposition_dict,
                    available_agents,
                    complexity=phase1_result["complexity"],
                )

                # Rebuild subgoal details for retry
                subgoal_details = []
                for idx, agent in agent_assignments:
                    sg = subgoals[idx] if idx < len(subgoals) else {}
                    agent_config = getattr(agent, "config", {}) or {}
                    is_spawn = agent_config.get("is_spawn", False)
                    match_quality = agent_config.get("match_quality", "acceptable")
                    ideal_agent = agent_config.get("ideal_agent", "")
                    ideal_agent_desc = agent_config.get("ideal_agent_desc", "")
                    subgoal_details.append(
                        {
                            "index": idx + 1,
                            "description": sg.get("description", ""),
                            "agent": agent.id,
                            "is_critical": sg.get("is_critical", False),
                            "depends_on": sg.get("depends_on", []),
                            "is_spawn": is_spawn,
                            "match_quality": match_quality,
                            "ideal_agent": ideal_agent,
                            "ideal_agent_desc": ideal_agent_desc,
                        },
                    )

                phase4_result = {
                    "final_verdict": "PASS" if passed else "FAIL",
                    "agent_assignments": [
                        {"index": idx, "agent_id": agent.id} for idx, agent in agent_assignments
                    ],
                    "issues": issues,
                    "subgoals_detailed": subgoal_details,  # Add detailed subgoal data
                    "_timing_ms": 0,
                    "_error": None,
                }
                self._phase_metadata["phase4_verify_retry"] = phase4_result

                if not passed:
                    logger.error("Decomposition verification failed after retry")
                    return self._handle_verification_failure(query, phase4_result, verbosity)

            # Early exit for goals-only mode (aur goals uses stop_after_verify=True)
            if stop_after_verify:
                # Get detailed subgoals from phase4 result or default to empty
                raw_detailed = phase4_result.get("subgoals_detailed", [])
                # Cast to the expected type - the verify phase returns list[dict]
                detailed_subgoals = cast(list[dict[str, Any]], raw_detailed)
                return self._build_verify_only_result(
                    query=query,
                    complexity=phase1_result["complexity"],
                    context=phase2_result,
                    decomposition=decomposition_dict,
                    agent_assignments=agent_assignments,
                    subgoal_details=detailed_subgoals,
                    issues=issues,
                )

            # Phase 5: Execute agents (Task 5.4 - removed route phase, pass agent_assignments directly)
            subgoals = decomposition_dict.get("subgoals", [])
            progress_callback = self._get_progress_callback()  # Task 5.5

            # Build context with original query for agent prompts
            collect_context = dict(phase2_result)
            collect_context["query"] = query  # Add original query for agent context

            try:
                phase5_result_obj = self._phase5_collect(
                    agent_assignments,
                    subgoals,
                    collect_context,
                    progress_callback,
                )
                # Store dict version in metadata with recovery info
                phase5_dict = phase5_result_obj.to_dict()
                phase5_dict["_timing_ms"] = 0  # Timing handled internally
                phase5_dict["_error"] = None
                phase5_dict["agents_executed"] = len(phase5_result_obj.agent_outputs)

                # Extract early termination data
                early_terminations = phase5_dict.get("execution_metadata", {}).get(
                    "early_terminations",
                    [],
                )

                # Extract circuit breaker data
                circuit_blocked = phase5_dict.get("execution_metadata", {}).get(
                    "circuit_blocked",
                    [],
                )
                circuit_blocked_agents = [cb["agent_id"] for cb in circuit_blocked]

                # Add recovery metrics with detailed categorization
                phase5_dict["recovery_metrics"] = {
                    "total_failures": 0,
                    "early_terminations": len(early_terminations),
                    "early_termination_details": early_terminations,
                    "circuit_breaker_blocks": len(circuit_blocked),
                    "circuit_blocked_agents": circuit_blocked_agents,
                    "circuit_blocked_details": circuit_blocked,
                    "timeout_count": 0,
                    "timeout_agents": [],
                    "rate_limit_count": 0,
                    "rate_limit_agents": [],
                    "auth_failure_count": 0,
                    "auth_failed_agents": [],
                    "fallback_used_count": len(phase5_result_obj.fallback_agents),
                    "fallback_agents": phase5_result_obj.fallback_agents,
                }

                self._phase_metadata["phase5_collect"] = phase5_dict

                # Track spawned agents count for metrics (Task 4.5.1)
                spawned_agents_count = len(agent_assignments)

                # Track fallback to LLM count for metrics (Task 4.5.2)
                fallback_to_llm_count = len(phase5_result_obj.fallback_agents)

            except RuntimeError as e:
                # Critical subgoal failure - attempt recovery
                logger.error(f"Critical failure in agent execution: {e}")
                return self._handle_critical_failure(query, str(e), verbosity)

            # Phase 6: Synthesize results
            phase6_result_obj = self._phase6_synthesize(
                phase5_result_obj,
                query,
                decomposition_dict,
            )
            # Store dict version in metadata
            phase6_dict = phase6_result_obj.to_dict()
            phase6_dict["_timing_ms"] = 0
            phase6_dict["_error"] = None
            self._phase_metadata["phase6_synthesize"] = phase6_dict

            # Phase 7: Record pattern with lightweight record (Task 5.6)
            import tempfile

            log_path = (
                self.conversation_logger.get_current_log_path()
                if hasattr(self.conversation_logger, "get_current_log_path")
                else tempfile.gettempdir() + "/soar.log"
            )
            phase7_result = self._phase7_record(
                query,
                phase6_result_obj,
                log_path,
            )
            phase7_dict = phase7_result.to_dict()
            phase7_dict["_timing_ms"] = 0
            phase7_dict["_error"] = None
            self._phase_metadata["phase7_record"] = phase7_dict

            # Record query metrics (Task 4.5.3)
            execution_duration_ms = (time.time() - self._start_time) * 1000
            self.query_metrics.record_query(
                query_id=self._query_id,
                query_type="soar",
                duration_ms=execution_duration_ms,
                query_text=query,
                complexity=phase1_result["complexity"],
                success=True,
                phase_count=7,  # Updated from 9 to 7 phases (Task 5.7)
                metadata={
                    "spawned_agents_count": spawned_agents_count,
                    "fallback_to_llm_count": fallback_to_llm_count,
                },
            )

            # Phase 8: Format response
            return self._phase8_respond(phase6_result_obj, phase7_result, verbosity)

        except BudgetExceededError:
            # Re-raise budget errors without handling - caller should handle budget limits
            raise
        except Exception as e:
            logger.exception(f"SOAR execution failed: {e}")
            return self._handle_execution_error(e, verbosity)

    def _get_available_agents(self) -> list[Any]:
        """Get list of available agents from registry or discovery system.

        Returns:
            List of available AgentInfo objects

        """
        if self._use_discovery:
            # Use discovery adapter to get agents from manifest (already handles conversion)
            return discovery_adapter.list_agents()
        # Use agent registry
        if not self.agent_registry:
            return []
        return self.agent_registry.list_all()

    def _get_progress_callback(self) -> Callable[[str], None]:
        """Create progress callback for streaming agent execution updates (Task 5.5).

        Returns:
            Callback function that prints progress messages

        """

        def progress_callback(message: str) -> None:
            """Print progress message to stdout."""
            print(message, flush=True)

        return progress_callback

    def _phase1_assess(self, query: str) -> dict[str, Any]:
        """Execute Phase 1: Complexity Assessment."""
        logger.info("Phase 1: Assessing complexity")
        self._invoke_callback("assess", "before", {})
        start_time = time.time()
        try:
            result = assess.assess_complexity(query, _llm_client=self.reasoning_llm)
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            self._invoke_callback(
                "assess",
                "after",
                {"complexity": result.get("complexity", "UNKNOWN")},
            )
            return result
        except Exception as e:
            logger.error(f"Phase 1 failed: {e}")
            result = {
                "complexity": "MEDIUM",
                "confidence": 0.0,
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }
            self._invoke_callback("assess", "after", {"complexity": "MEDIUM", "error": str(e)})
            return result

    def _inject_context_files(
        self,
        phase2_result: dict[str, Any],
        context_files: list[str],
    ) -> dict[str, Any]:
        """Inject explicit context files into phase 2 results.

        Loads context files directly and merges them with retrieved context.
        Used for --context flag support.

        Args:
            phase2_result: Result from phase 2 (retrieve)
            context_files: List of file paths to load

        Returns:
            Modified phase2_result with injected context

        """
        from pathlib import Path

        try:
            from aurora_cli.memory.retrieval import MemoryRetriever

            retriever = MemoryRetriever()
            paths = [Path(f) for f in context_files]
            loaded_chunks = retriever.load_context_files(paths)

            if loaded_chunks:
                # Prepend to code_chunks (explicit context has priority)
                existing_chunks = phase2_result.get("code_chunks", [])
                phase2_result["code_chunks"] = loaded_chunks + existing_chunks
                logger.info(f"Injected {len(loaded_chunks)} context files into retrieval results")

        except Exception as e:
            logger.warning(f"Failed to inject context files: {e}")

        return phase2_result

    def _phase2_retrieve(self, query: str, complexity: str) -> dict[str, Any]:
        """Execute Phase 2: Context Retrieval."""
        logger.info("Phase 2: Retrieving context")
        self._invoke_callback("retrieve", "before", {})
        start_time = time.time()
        try:
            result = retrieve.retrieve_context(query, complexity, self.store)
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            chunks_count = len(result.get("code_chunks", [])) + len(
                result.get("reasoning_chunks", []),
            )
            self._invoke_callback("retrieve", "after", {"chunks_retrieved": chunks_count})
            return result
        except Exception as e:
            logger.error(f"Phase 2 failed: {e}")
            result = {
                "code_chunks": [],
                "reasoning_chunks": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }
            self._invoke_callback("retrieve", "after", {"chunks_retrieved": 0, "error": str(e)})
            return result

    def _phase3_decompose(
        self,
        query: str,
        context: dict[str, Any],
        complexity: str,
        _retry_feedback: str | None = None,
    ) -> dict[str, Any]:
        """Execute Phase 3: Query Decomposition.

        Args:
            query: The user query to decompose
            context: Context from phase 2 (memory retrieval)
            complexity: Complexity level (simple/medium/complex)
            retry_feedback: Optional feedback from failed verification to guide retry

        """
        logger.info("Phase 3: Decomposing query")
        self._invoke_callback("decompose", "before", {})
        start_time = time.time()

        # Check circuit breaker before making LLM call
        agent_key = f"decompose:{getattr(self.reasoning_llm, '_tool', 'unknown')}"
        skip, reason = self._llm_circuit_breaker.should_skip(agent_key)
        if skip:
            logger.warning(f"Phase 3 skipped by circuit breaker: {reason}")
            result = {
                "goal": query,
                "subgoals": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": f"Circuit breaker: {reason}",
            }
            self._invoke_callback("decompose", "after", {"subgoal_count": 0, "error": reason})
            return result

        try:
            # Get available agents from registry or discovery
            agents = self._list_agents()
            available_agents = [agent.id for agent in agents]

            phase_result = decompose.decompose_query(
                query=query,
                context=context,
                complexity=complexity,
                llm_client=self.reasoning_llm,
                available_agents=available_agents,
                retry_feedback=_retry_feedback,
            )
            result = phase_result.to_dict()
            # Add convenience fields for E2E tests
            result["subgoals_total"] = len(result["decomposition"]["subgoals"])
            result["_timing_ms"] = (time.time() - start_time) * 1000
            result["_error"] = None
            self._invoke_callback("decompose", "after", {"subgoal_count": result["subgoals_total"]})

            # Record success to close circuit if it was half-open
            self._llm_circuit_breaker.record_success(agent_key)

            return result
        except RuntimeError as e:
            # Classify error and record in circuit breaker
            failure_type = self._classify_api_error(str(e))
            self._llm_circuit_breaker.record_failure(agent_key, failure_type=failure_type)
            logger.error(f"Phase 3 failed (type={failure_type}): {e}")
            result = {
                "goal": query,
                "subgoals": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }
            self._invoke_callback("decompose", "after", {"subgoal_count": 0, "error": str(e)})
            return result
        except Exception as e:
            logger.error(f"Phase 3 failed: {e}")
            result = {
                "goal": query,
                "subgoals": [],
                "_timing_ms": (time.time() - start_time) * 1000,
                "_error": str(e),
            }
            self._invoke_callback("decompose", "after", {"subgoal_count": 0, "error": str(e)})
            return result

    # NOTE: Old _phase4_verify and _phase5_route removed (Tasks 5.2, 6.3)
    # - Verification now uses verify_lite directly in execute() method
    # - Routing functionality integrated into verify_lite

    def _phase5_collect(
        self,
        agent_assignments: list[tuple[int, Any]],
        subgoals: list[dict[str, Any]],
        context: dict[str, Any],
        on_progress: Callable[[str], None] | None = None,
    ) -> collect.CollectResult:
        """Execute Phase 5: Agent Execution (Task 5.4 - updated signature).

        Args:
            agent_assignments: List of (subgoal_index, AgentInfo) tuples
            subgoals: List of subgoal dictionaries
            context: Retrieved context from phase 2
            on_progress: Optional progress callback for streaming updates

        Returns:
            CollectResult object for use by phase 6

        """
        logger.info("Phase 5: Executing agents")

        # Reset health monitors to ensure fresh state with correct config
        from aurora_spawner.early_detection import reset_early_detection_monitor
        from aurora_spawner.observability import reset_health_monitor

        reset_health_monitor()
        reset_early_detection_monitor()

        self._invoke_callback("collect", "before", {})
        try:
            # Load recovery config from policies
            from aurora_cli.policies import PoliciesEngine

            try:
                policies = PoliciesEngine()
                recovery_config = policies.get_recovery_config()
                max_retries = recovery_config.max_retries
                fallback_to_llm = recovery_config.fallback_to_llm
                agent_timeout = recovery_config.timeout_seconds
            except Exception as e:
                logger.warning(f"Failed to load policies, using defaults: {e}")
                max_retries = 2
                fallback_to_llm = True
                agent_timeout = 300  # 5 minutes - matches collect.DEFAULT_AGENT_TIMEOUT

            # Execute agents asynchronously with recovery config
            result = asyncio.run(
                collect.execute_agents(
                    agent_assignments=agent_assignments,
                    subgoals=subgoals,
                    _context=context,
                    on_progress=on_progress,
                    _agent_timeout=agent_timeout,
                    max_retries=max_retries,
                    fallback_to_llm=fallback_to_llm,
                ),
            )

            # Analyze failure patterns and trigger recovery
            recovery_metrics = self._analyze_execution_failures(result)
            failed_count = recovery_metrics["failed_count"]
            early_term_count = recovery_metrics["early_term_count"]
            circuit_failures = recovery_metrics["circuit_failures"]
            timeout_failures = recovery_metrics["timeout_failures"]

            # Log recovery summary with early termination breakdown
            if failed_count > 0:
                early_term_details = [
                    f"{d['agent_id']} ({d['reason']}, {d['detection_time']}ms)"
                    for d in recovery_metrics.get("early_term_details", [])
                ]
                logger.info(
                    f"Agent execution completed with {failed_count} failures. "
                    f"Fallback used: {len(result.fallback_agents)}, "
                    f"Early terminations: {early_term_count}, "
                    f"Circuit breaker: {len(circuit_failures)}, "
                    f"Timeouts: {len(timeout_failures)}",
                )
                if early_term_details:
                    logger.info(f"Early termination details: {', '.join(early_term_details)}")

                # Trigger recovery procedures if needed
                if circuit_failures:
                    self._trigger_circuit_recovery(circuit_failures)

                if early_term_count > 0:
                    logger.info(
                        f"Early termination system detected {early_term_count} problematic agents in real-time. "
                        "Circuit breaker and retry policies active for future attempts.",
                    )

            findings_count = len(result.agent_outputs) if result.agent_outputs else 0
            self._invoke_callback(
                "collect",
                "after",
                {
                    "findings_count": findings_count,
                    "failed_count": failed_count,
                    "fallback_count": len(result.fallback_agents),
                    "early_terminations": early_term_count,
                    "circuit_failures": len(circuit_failures),
                    "timeout_failures": len(timeout_failures),
                },
            )
            return result
        except RuntimeError as e:
            # Critical subgoal failure - propagate to trigger recovery
            logger.error(f"Critical failure in Phase 5: {e}")
            self._invoke_callback(
                "collect",
                "after",
                {
                    "findings_count": 0,
                    "error": str(e),
                    "critical_failure": True,
                },
            )
            raise
        except Exception as e:
            logger.error(f"Phase 5 collect failed: {e}")
            # Return empty CollectResult on failure
            from aurora_soar.phases.collect import CollectResult

            self._invoke_callback("collect", "after", {"findings_count": 0, "error": str(e)})
            return CollectResult(
                agent_outputs=[],
                execution_metadata={"error": str(e)},
                user_interactions=[],
            )

    def _phase6_synthesize(
        self,
        collect_result: collect.CollectResult,
        query: str,
        decomposition: dict[str, Any],
    ) -> synthesize.SynthesisResult:
        """Execute Phase 6: Result Synthesis (Task 5.7 - renumbered from phase 7)."""
        logger.info("Phase 6: Synthesizing results")
        self._invoke_callback("synthesize", "before", {})
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
            self._invoke_callback("synthesize", "after", {"confidence": result.confidence})
            return result
        except Exception as e:
            logger.error(f"Phase 7 failed: {e}")
            # Return error synthesis result
            self._invoke_callback("synthesize", "after", {"confidence": 0.0, "error": str(e)})
            return synthesize.SynthesisResult(
                answer=f"Synthesis failed: {str(e)}",
                confidence=0.0,
                traceability=[],
                metadata={"error": str(e)},
                timing={"synthesis_ms": (time.time() - start_time) * 1000},
            )

    def _phase7_record(
        self,
        query: str,
        synthesis_result: synthesize.SynthesisResult,
        log_path: str,
    ) -> record.RecordResult:
        """Execute Phase 7: Pattern Recording with lightweight record (Task 5.6).

        Args:
            query: Original user query
            synthesis_result: Synthesis result from phase 6
            log_path: Path to conversation log file

        Returns:
            RecordResult with caching status

        """
        logger.info("Phase 7: Recording pattern (lightweight)")
        self._invoke_callback("record", "before", {})
        start_time = time.time()
        try:
            result = record.record_pattern_lightweight(
                store=self.store,
                query=query,
                synthesis_result=synthesis_result,
                log_path=log_path,
            )
            self._invoke_callback("record", "after", {"cached": result.cached})
            return result
        except Exception as e:
            logger.error(f"Phase 7 record failed: {e}")
            self._invoke_callback("record", "after", {"cached": False, "error": str(e)})
            return record.RecordResult(
                cached=False,
                reasoning_chunk_id=None,
                pattern_marked=False,
                activation_update=0.0,
                timing={"record_ms": (time.time() - start_time) * 1000, "error": str(e)},
            )

    def _phase8_respond(
        self,
        synthesis_result: synthesize.SynthesisResult,
        record_result: record.RecordResult,
        verbosity: str,
    ) -> dict[str, Any]:
        """Execute Phase 8: Response Formatting (Task 5.7 - renumbered from phase 9)."""
        logger.info("Phase 8: Formatting response")
        self._invoke_callback("respond", "before", {})

        # Add phase 8 metadata (Task 5.7 - updated phase number)
        self._phase_metadata["phase8_respond"] = {
            "verbosity": verbosity,
            "formatted": True,
        }

        metadata = self._build_metadata()
        response = respond.format_response(
            synthesis_result,
            record_result,
            metadata,
            Verbosity(verbosity.lower()),
        )

        # Only log+index successful runs (confidence >= 0.5)
        # Failed runs pollute retrieval with error logs
        log_path = None
        if synthesis_result.confidence >= 0.5:
            execution_summary = {
                "duration_ms": metadata.get("total_duration_ms", 0),
                "overall_score": synthesis_result.confidence,
                "cached": record_result.cached,
                "cost_usd": metadata.get("total_cost_usd", 0.0),
                "tokens_used": metadata.get("tokens_used", {}),
            }

            log_path = self.conversation_logger.log_interaction(
                query=self._query,
                query_id=self._query_id,
                phase_data=metadata.get("phases", {}),
                execution_summary=execution_summary,
                metadata=metadata,
            )

            # Auto-index the conversation log as knowledge chunk
            if log_path and self.store:
                self._index_conversation_log(log_path)
        else:
            logger.info(
                "Skipping conversation log (confidence=%.2f < 0.5)",
                synthesis_result.confidence,
            )

        self._invoke_callback("respond", "after", {"formatted": True})

        # Build result with log path in metadata
        result = response.to_dict()
        if "metadata" not in result:
            result["metadata"] = {}
        if log_path:
            result["metadata"]["log_path"] = str(log_path)
        return result

    def _execute_simple_path(
        self,
        query: str,
        context: dict[str, Any],
        verbosity: str,
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
        from aurora_soar.phases.record import RecordResult
        from aurora_soar.phases.synthesize import SynthesisResult

        try:
            # Build prompt with context
            prompt_parts = [f"Query: {query}"]

            # Add retrieved context if available
            code_chunks = context.get("code_chunks", [])
            reasoning_chunks = context.get("reasoning_chunks", [])

            if code_chunks:
                prompt_parts.append("\nRelevant Code:")
                for chunk in code_chunks[:5]:  # Limit to top 5
                    # Handle both CodeChunk objects and dict representations
                    if hasattr(chunk, "file_path"):
                        # CodeChunk object - build display from attributes
                        file_path = chunk.file_path
                        name = getattr(chunk, "name", "")
                        docstring = getattr(chunk, "docstring", "") or ""
                        signature = getattr(chunk, "signature", "") or ""
                        display = f"{file_path}: {name}"
                        if signature:
                            display += f" - {signature[:100]}"
                        if docstring:
                            display += f"\n  {docstring[:150]}"
                        prompt_parts.append(f"- {display}")
                    elif isinstance(chunk, dict):
                        # Dict representation
                        content = chunk.get("content", "")
                        if isinstance(content, dict):
                            # Nested content dict (from to_json format)
                            file_path = content.get("file", "")
                            name = content.get("function", "")
                            display = f"{file_path}: {name}"
                        else:
                            display = str(content)[:200]
                        prompt_parts.append(f"- {display}")
                    else:
                        # Fallback
                        prompt_parts.append(f"- {str(chunk)[:200]}")

            if reasoning_chunks:
                prompt_parts.append("\nRelevant Context:")
                for chunk in reasoning_chunks[:3]:  # Limit to top 3
                    # Handle both objects and dict representations
                    if hasattr(chunk, "pattern"):
                        pattern = chunk.pattern
                    elif isinstance(chunk, dict):
                        pattern = chunk.get("pattern", str(chunk)[:200])
                    else:
                        pattern = str(chunk)[:200]
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
                    },
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

        # Record query metrics for simple path (Task 4.5.3)
        execution_duration_ms = (time.time() - self._start_time) * 1000
        self.query_metrics.record_query(
            query_id=self._query_id,
            query_type="simple",
            duration_ms=execution_duration_ms,
            query_text=query,
            complexity="SIMPLE",
            success=True,
            phase_count=2,  # Only assess + retrieve for simple queries
            metadata={
                "spawned_agents_count": 0,  # No agents spawned for simple queries
                "fallback_to_llm_count": 0,  # No fallback needed
            },
        )

        # Use phase 9 to format response properly
        return self._phase8_respond(synthesis, record, verbosity)

    def _handle_verification_failure(
        self,
        _query: str,
        verification: dict[str, Any],
        verbosity: str,
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
        from aurora_soar.phases.record import RecordResult
        from aurora_soar.phases.synthesize import SynthesisResult

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

        return self._phase8_respond(synthesis, record, verbosity)

    def _handle_decomposition_failure(
        self,
        _query: str,
        decomposition_result: dict[str, Any],
        verbosity: str,
    ) -> dict[str, Any]:
        """Handle decomposition failure (Phase 3 error).

        Args:
            query: Original query
            decomposition_result: Decomposition result with error
            verbosity: Output verbosity

        Returns:
            Error response with partial results

        """
        error_msg = decomposition_result.get("_error", "Unknown decomposition error")
        logger.error(f"Returning partial results due to decomposition failure: {error_msg}")
        from aurora_soar.phases.record import RecordResult
        from aurora_soar.phases.synthesize import SynthesisResult

        synthesis = SynthesisResult(
            answer="Unable to decompose query successfully. Please rephrase or simplify.",
            confidence=0.0,
            traceability=[],
            metadata={
                "error": "decomposition_failed",
                "details": error_msg,
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

        # Add decomposition failure to phase metadata before response formatting
        self._phase_metadata["decomposition_failure"] = decomposition_result

        return self._phase8_respond(synthesis, record, verbosity)

    def _handle_critical_failure(
        self,
        _query: str,
        error_msg: str,
        verbosity: str,
    ) -> dict[str, Any]:
        """Handle critical subgoal failure with recovery attempt.

        Args:
            query: Original query
            error_msg: Error message from critical failure
            verbosity: Output verbosity

        Returns:
            Error response with recovery information

        """
        logger.error(f"Handling critical failure: {error_msg}")
        from aurora_soar.phases.record import RecordResult
        from aurora_soar.phases.synthesize import SynthesisResult

        # Build recovery context
        recovery_info = {
            "critical_failure": True,
            "error": error_msg,
            "recovery_attempted": False,
            "recovery_strategy": "Circuit breaker and retry policies active",
        }

        synthesis = SynthesisResult(
            answer=(
                f"Unable to complete the query due to a critical failure: {error_msg}\n\n"
                "Recovery mechanisms have been activated for future attempts:\n"
                "- Circuit breaker tracking failing agents\n"
                "- Retry policies with exponential backoff\n"
                "- Fallback to direct LLM for failed agents\n\n"
                "Please try rephrasing the query or breaking it into smaller parts."
            ),
            confidence=0.0,
            traceability=[],
            metadata=recovery_info,
            timing={"synthesis_ms": 0},
        )

        record = RecordResult(
            cached=False,
            reasoning_chunk_id=None,
            pattern_marked=False,
            activation_update=0.0,
            timing={"record_ms": 0},
        )

        # Add critical failure to phase metadata
        self._phase_metadata["critical_failure"] = recovery_info

        return self._phase8_respond(synthesis, record, verbosity)

    def _handle_execution_error(self, error: Exception, verbosity: str) -> dict[str, Any]:
        """Handle execution errors with graceful degradation.

        Args:
            error: Exception that occurred
            verbosity: Output verbosity

        Returns:
            Error response

        """
        logger.error(f"Handling execution error: {error}")
        from aurora_soar.phases.record import RecordResult
        from aurora_soar.phases.synthesize import SynthesisResult

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

        return self._phase8_respond(synthesis, record, verbosity)

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
            f"({input_tokens} in, {output_tokens} out)",
        )

        return cost

    def _build_simple_verify_result(
        self,
        query: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build result for SIMPLE query in goals-only mode.

        For SIMPLE queries, we create a single-subgoal decomposition
        pointing to a generic development agent.

        Args:
            query: Original user query
            context: Retrieved context from phase 2

        Returns:
            Dict with single-subgoal decomposition

        """
        elapsed_time = time.time() - self._start_time

        # Create single subgoal for simple query
        single_subgoal = {
            "id": "sg-1",
            "description": query,
            "depends_on": [],
            "is_critical": True,
        }

        decomposition = {
            "goal": query,
            "subgoals": [single_subgoal],
        }

        # Assign to code-developer as default
        subgoal_details = [
            {
                "index": 1,
                "description": query,
                "agent": "@code-developer",
                "is_critical": True,
                "depends_on": [],
                "is_spawn": False,
                "match_quality": "excellent",
                "ideal_agent": "@code-developer",
                "ideal_agent_desc": "General development tasks",
            },
        ]

        # Extract memory context
        memory_context = []
        code_chunks = context.get("code_chunks", [])
        for chunk in code_chunks[:10]:
            if hasattr(chunk, "file_path"):
                file_path = chunk.file_path
                score = getattr(chunk, "activation", 0.5)
            elif isinstance(chunk, dict):
                # Check top-level first, then metadata dict (hybrid retriever returns file_path in metadata)
                file_path = chunk.get("file_path") or chunk.get("file", "")
                if not file_path:
                    metadata = chunk.get("metadata", {})
                    if isinstance(metadata, dict):
                        file_path = metadata.get("file_path", "")
                # Score: prefer hybrid_score, then activation_score, then activation
                score = (
                    chunk.get("hybrid_score")
                    or chunk.get("activation_score")
                    or chunk.get("activation", 0.5)
                )
            else:
                continue
            if file_path:
                memory_context.append((file_path, score))

        return {
            "decomposition": decomposition,
            "agent_assignments": [
                {
                    "index": 0,
                    "agent_id": "@code-developer",
                    "match_quality": "excellent",
                    "is_spawn": False,
                    "ideal_agent": "@code-developer",
                    "ideal_agent_desc": "General development tasks",
                },
            ],
            "subgoals_detailed": subgoal_details,
            "complexity": "SIMPLE",
            "context": context,
            "memory_context": memory_context,
            "issues": [],
            "metadata": {
                "query_id": self._query_id,
                "query": query,
                "total_duration_ms": elapsed_time * 1000,
                "total_cost_usd": self._total_cost,
                "tokens_used": self._token_usage,
                "phases": self._phase_metadata,
                "stop_after_verify": True,
                "simple_path": True,
            },
        }

    def _build_verify_only_result(
        self,
        query: str,
        complexity: str,
        context: dict[str, Any],
        decomposition: dict[str, Any],
        agent_assignments: list[tuple[int, Any]],
        subgoal_details: list[dict[str, Any]],
        issues: list[str],
    ) -> dict[str, Any]:
        """Build result for goals-only mode (stop_after_verify=True).

        This method builds a result structure suitable for `aur goals` when
        SOAROrchestrator is used with stop_after_verify=True. It contains
        all the decomposition and agent matching information without executing
        the agents.

        Args:
            query: Original user query
            complexity: Assessed complexity (SIMPLE, MEDIUM, COMPLEX)
            context: Retrieved context from phase 2
            decomposition: Decomposition dict from phase 3
            agent_assignments: List of (subgoal_index, AgentInfo) tuples
            subgoal_details: Detailed subgoal info including match_quality
            issues: Any verification issues (should be empty if passed)

        Returns:
            Dict with decomposition results for goals.json generation

        """
        elapsed_time = time.time() - self._start_time

        # Build agent assignments with full details
        assignments_detailed = []
        for idx, agent in agent_assignments:
            agent_config = getattr(agent, "config", {}) or {}
            assignments_detailed.append(
                {
                    "index": idx,
                    "agent_id": agent.id,
                    "match_quality": agent_config.get("match_quality", "acceptable"),
                    "is_spawn": agent_config.get("is_spawn", False),
                    "ideal_agent": agent_config.get("ideal_agent", ""),
                    "ideal_agent_desc": agent_config.get("ideal_agent_desc", ""),
                },
            )

        # Extract memory context for goals.json
        memory_context = []
        code_chunks = context.get("code_chunks", [])
        for chunk in code_chunks[:10]:  # Top 10
            if hasattr(chunk, "file_path"):
                file_path = chunk.file_path
                score = getattr(chunk, "activation", 0.5)
            elif isinstance(chunk, dict):
                # Check top-level first, then metadata dict (hybrid retriever returns file_path in metadata)
                file_path = chunk.get("file_path") or chunk.get("file", "")
                if not file_path:
                    metadata = chunk.get("metadata", {})
                    if isinstance(metadata, dict):
                        file_path = metadata.get("file_path", "")
                # Score: prefer hybrid_score, then activation_score, then activation
                score = (
                    chunk.get("hybrid_score")
                    or chunk.get("activation_score")
                    or chunk.get("activation", 0.5)
                )
            else:
                continue
            if file_path:
                memory_context.append((file_path, score))

        return {
            "decomposition": decomposition,
            "agent_assignments": assignments_detailed,
            "subgoals_detailed": subgoal_details,
            "complexity": complexity,
            "context": context,
            "memory_context": memory_context,
            "issues": issues,
            "metadata": {
                "query_id": self._query_id,
                "query": query,
                "total_duration_ms": elapsed_time * 1000,
                "total_cost_usd": self._total_cost,
                "tokens_used": self._token_usage,
                "phases": self._phase_metadata,
                "stop_after_verify": True,
            },
        }

    def _build_cached_verify_result(
        self,
        query: str,
        complexity: str,
        context: dict[str, Any],
        cache_hit: dict[str, Any],
    ) -> dict[str, Any]:
        """Build result for goals-only mode from a cache hit (goals.json).

        This skips re-verification since the cached decomposition was already
        verified when first saved to goals.json.

        Args:
            query: Original user query
            complexity: Assessed complexity (SIMPLE, MEDIUM, COMPLEX)
            context: Retrieved context from phase 2
            cache_hit: Cached phase3 result from goals.json

        Returns:
            Dict with decomposition results ready for goals.json output

        """
        elapsed_time = time.time() - self._start_time
        decomposition = cache_hit.get("decomposition", {})
        subgoals = decomposition.get("subgoals", [])

        # Build subgoal details from cached data
        subgoal_details = []
        agent_assignments = []
        for idx, sg in enumerate(subgoals):
            agent_id = sg.get("assigned_agent") or sg.get("agent") or "@code-developer"
            # Use `or ""` pattern to handle None values (`.get()` returns None if key exists with None value)
            ideal_agent = sg.get("ideal_agent") or ""
            ideal_agent_desc = sg.get("ideal_agent_desc") or ""
            match_quality = sg.get("match_quality") or "excellent"
            subgoal_details.append(
                {
                    "index": idx + 1,
                    "description": sg.get("description") or "",
                    "agent": agent_id,
                    "is_critical": sg.get("is_critical", True),
                    "depends_on": sg.get("depends_on") or [],
                    "is_spawn": False,
                    "match_quality": match_quality,
                    "ideal_agent": ideal_agent,
                    "ideal_agent_desc": ideal_agent_desc,
                }
            )
            agent_assignments.append(
                {
                    "index": idx,
                    "agent_id": agent_id,
                    "match_quality": match_quality,
                    "is_spawn": False,
                    "ideal_agent": ideal_agent,
                    "ideal_agent_desc": ideal_agent_desc,
                }
            )

        # Extract memory context from phase 2
        memory_context = []
        code_chunks = context.get("code_chunks", [])
        for chunk in code_chunks[:10]:
            if hasattr(chunk, "file_path"):
                file_path = chunk.file_path
                score = getattr(chunk, "activation", 0.5)
            elif isinstance(chunk, dict):
                file_path = chunk.get("file_path") or chunk.get("metadata", {}).get("file_path", "")
                score = (
                    chunk.get("hybrid_score")
                    or chunk.get("activation_score")
                    or chunk.get("activation", 0.5)
                )
            else:
                continue
            if file_path:
                memory_context.append((file_path, score))

        return {
            "decomposition": decomposition,
            "agent_assignments": agent_assignments,
            "subgoals_detailed": subgoal_details,
            "complexity": complexity,
            "context": context,
            "memory_context": memory_context,
            "issues": [],
            "metadata": {
                "query_id": self._query_id,
                "query": query,
                "total_duration_ms": elapsed_time * 1000,
                "total_cost_usd": self._total_cost,
                "tokens_used": self._token_usage,
                "phases": self._phase_metadata,
                "stop_after_verify": True,
                "cache_source": cache_hit.get("_cache_source", ""),
            },
        }

    def _build_metadata(self) -> dict[str, Any]:
        """Build aggregated metadata from all phases.

        Returns:
            Dict with execution metadata including recovery information

        """
        elapsed_time = time.time() - self._start_time

        metadata = {
            "query_id": self._query_id,
            "query": self._query,
            "total_duration_ms": elapsed_time * 1000,
            "total_cost_usd": self._total_cost,
            "tokens_used": self._token_usage,
            "budget_status": self.cost_tracker.get_status(),
            "phases": self._phase_metadata,
            "timestamp": time.time(),
        }

        # Add recovery metrics if any failures occurred
        if hasattr(self, "_circuit_failures") and self._circuit_failures:
            metadata["recovery"] = {
                "circuit_breaker_triggered": True,
                "circuit_failures": self._circuit_failures,
                "total_circuit_failures": len(self._circuit_failures),
            }

        return metadata

    def _split_large_chunk_by_sections(self, chunk: Any, max_chars: int = 2048) -> list[Any]:
        """Split a large chunk by H2 markdown sections.

        Args:
            chunk: CodeChunk to split
            max_chars: Maximum characters per chunk

        Returns:
            List of smaller chunks split by sections

        """
        from aurora_core.chunks import CodeChunk

        text = chunk.docstring or ""
        if len(text) <= max_chars:
            return [chunk]

        # Split by H2 headers (##)
        sections: list[tuple[str | None, str]] = []
        current_section: list[str] = []
        current_header: str | None = None

        for line in text.split("\n"):
            if line.strip().startswith("## "):
                # Save previous section
                if current_section:
                    sections.append((current_header, "\n".join(current_section)))
                # Start new section
                current_header = line.strip()[3:]
                current_section = [line]
            else:
                current_section.append(line)

        # Save last section
        if current_section:
            sections.append((current_header, "\n".join(current_section)))

        # Create chunks from sections
        split_chunks = []
        truncation_suffix = "\n\n[... content truncated ...]"
        for i, (header, content) in enumerate(sections, 1):
            if len(content) > max_chars:
                # Section still too large, truncate (debug level - this is expected behavior)
                original_len = len(content)
                content = content[: max_chars - len(truncation_suffix)] + truncation_suffix
                logger.debug(
                    f"Section '{header}' truncated from {original_len} to {len(content)} chars",
                )

            # Create new chunk with section suffix
            section_chunk = CodeChunk(
                chunk_id=f"{chunk.id}_section_{i}",
                file_path=chunk.file_path,
                element_type=chunk.element_type,
                name=f"{chunk.name} - {header or 'Section ' + str(i)}",
                line_start=chunk.line_start,
                line_end=chunk.line_end,
                signature=chunk.signature,
                docstring=content,
                language=chunk.language,
                metadata={
                    **(chunk.metadata if chunk.metadata else {}),
                    "section_index": i,
                    "section_header": header,
                    "is_split_section": True,
                    "parent_chunk_id": chunk.id,
                },
            )
            split_chunks.append(section_chunk)

        logger.info(f"Split chunk {chunk.id} into {len(split_chunks)} sections")
        return split_chunks

    def _analyze_execution_failures(self, result: collect.CollectResult) -> dict[str, Any]:
        """Analyze agent execution failures and categorize them for recovery.

        Args:
            result: CollectResult from agent execution phase

        Returns:
            Dict with failure analysis:
                - failed_count: Total failed agents
                - early_term_count: Agents with early termination
                - early_term_details: List of early termination details
                - circuit_failures: List of agent IDs blocked by circuit breaker
                - timeout_failures: List of agent IDs that timed out
                - rate_limit_failures: List of agent IDs that hit rate limits
                - auth_failures: List of agent IDs with authentication issues

        """
        failed_count = 0
        early_term_count = 0
        early_term_details = []
        circuit_failures = []
        timeout_failures = []
        rate_limit_failures = []
        auth_failures = []

        for output in result.agent_outputs:
            if not output.success:
                failed_count += 1
                error_msg = (output.error or "").lower()
                metadata = output.execution_metadata

                # Track early termination patterns with details
                term_reason = metadata.get("termination_reason")
                if term_reason:
                    early_term_count += 1
                    early_term_details.append(
                        {
                            "agent_id": output.agent_id,
                            "reason": term_reason,
                            "detection_time": metadata.get("duration_ms", 0),
                        },
                    )
                    logger.debug(
                        f"Agent {output.agent_id} early termination: {term_reason} "
                        f"(detected in {metadata.get('duration_ms', 0)}ms)",
                    )

                # Track circuit breaker failures
                if "circuit open" in error_msg or "circuit" in error_msg:
                    circuit_failures.append(output.agent_id)
                    logger.warning(f"Agent {output.agent_id} blocked by circuit breaker")

                # Track timeout failures
                if any(pattern in error_msg for pattern in ["timeout", "timed out"]):
                    timeout_failures.append(output.agent_id)
                    logger.debug(f"Agent {output.agent_id} timed out")

                # Track rate limit failures
                if any(
                    pattern in error_msg
                    for pattern in ["rate limit", "429", "quota exceeded", "too many requests"]
                ):
                    rate_limit_failures.append(output.agent_id)
                    logger.warning(f"Agent {output.agent_id} hit rate limit")

                # Track authentication failures
                if any(pattern in error_msg for pattern in ["auth", "401", "403", "unauthorized"]):
                    auth_failures.append(output.agent_id)
                    logger.error(f"Agent {output.agent_id} authentication failed")

        return {
            "failed_count": failed_count,
            "early_term_count": early_term_count,
            "early_term_details": early_term_details,
            "circuit_failures": circuit_failures,
            "timeout_failures": timeout_failures,
            "rate_limit_failures": rate_limit_failures,
            "auth_failures": auth_failures,
        }

    def _trigger_circuit_recovery(self, failed_agents: list[str]) -> None:
        """Trigger recovery procedures for circuit-broken agents.

        This method is called when agents fail due to circuit breaker activation.
        It logs the failures for future analysis and can trigger additional
        recovery actions.

        Args:
            failed_agents: List of agent IDs that were blocked by circuit breaker

        """
        logger.warning(
            f"Circuit breaker recovery triggered for {len(failed_agents)} agents: "
            f"{', '.join(failed_agents)}",
        )

        # Store circuit failure metadata for analysis
        if not hasattr(self, "_circuit_failures"):
            self._circuit_failures = []

        for agent_id in failed_agents:
            self._circuit_failures.append(
                {
                    "agent_id": agent_id,
                    "timestamp": time.time(),
                    "query_id": self._query_id,
                },
            )

        # Add circuit failure context to phase metadata
        if "circuit_breaker_failures" not in self._phase_metadata:
            self._phase_metadata["circuit_breaker_failures"] = []

        self._phase_metadata["circuit_breaker_failures"].extend(
            [{"agent_id": aid, "timestamp": time.time()} for aid in failed_agents],
        )

        logger.info(
            "Circuit breaker failures recorded. "
            "Agents will be retried after reset timeout (typically 120s).",
        )

    def _check_soar_cache_hit(self, phase2_result: dict[str, Any]) -> dict[str, Any] | None:
        """Check for cached decomposition from conversation logs or existing goals.json.

        Checks two sources:
        1. Active goals.json files in .aurora/plans/active/ with matching title
        2. Conversation log chunks with hybrid_score >= 0.90

        Args:
            phase2_result: Result from phase 2 (retrieve)

        Returns:
            A phase3-compatible dict if cache hit found, None otherwise

        """
        # First, check active goals.json files for exact/near-exact title match
        goals_hit = self._check_goals_json_cache(self._query)
        if goals_hit is not None:
            return goals_hit

        # Then check conversation logs from phase 2 retrieval
        code_chunks = phase2_result.get("code_chunks", [])

        for chunk in code_chunks:
            # Get file path from chunk
            if hasattr(chunk, "file_path"):
                file_path = chunk.file_path or ""
                score = getattr(chunk, "activation", 0.0)
            elif isinstance(chunk, dict):
                file_path = chunk.get("file_path") or chunk.get("metadata", {}).get("file_path", "")
                score = (
                    chunk.get("hybrid_score")
                    or chunk.get("activation_score")
                    or chunk.get("activation", 0.0)
                )
            else:
                continue

            # Only consider conversation logs with high relevance
            if "/logs/conversations/" not in file_path:
                continue
            if score < 0.90:
                continue

            # Try to parse the log for cached decomposition
            parsed = self._parse_soar_log(file_path)
            if parsed is None:
                continue

            # Validate: must have non-empty subgoals and no error
            decomposition = parsed.get("decomposition", {})
            subgoals = decomposition.get("subgoals", [])
            if not subgoals:
                continue
            if parsed.get("_error") is not None:
                continue

            logger.info(
                "Cache hit from %s (score=%.3f, %d subgoals)",
                file_path,
                score,
                len(subgoals),
            )
            # Add cache source for display
            parsed["_cache_source"] = str(file_path)
            return parsed

        return None

    def _check_goals_json_cache(self, query: str) -> dict[str, Any] | None:
        """Check active goals.json files for a matching title.

        Scans .aurora/plans/active/*/goals.json for a title that matches
        the current query (case-insensitive, normalized whitespace).

        Uses fuzzy matching with similarity threshold to avoid false matches.

        Args:
            query: Current query string

        Returns:
            A phase3-compatible dict if matching goals found, None otherwise

        """
        import hashlib
        import json
        from pathlib import Path

        try:
            # Normalize query for comparison (preserve more structure)
            query_normalized = " ".join(query.lower().strip().split())
            query_hash = hashlib.sha256(query_normalized.encode("utf-8")).hexdigest()[:16]
            logger.debug(f"Cache check: normalized query = '{query_normalized}' (hash={query_hash})")

            # Find .aurora directory relative to current working directory
            aurora_dir = Path.cwd() / ".aurora" / "plans" / "active"
            if not aurora_dir.exists():
                logger.debug(f"Cache check: aurora_dir does not exist: {aurora_dir}")
                return None

            logger.debug(f"Cache check: scanning {aurora_dir}")

            for plan_dir in aurora_dir.iterdir():
                if not plan_dir.is_dir():
                    continue

                goals_file = plan_dir / "goals.json"
                if not goals_file.exists():
                    continue

                try:
                    goals_data = json.loads(goals_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                # Check title match (exact normalized match required)
                title = goals_data.get("title", "")
                title_normalized = " ".join(title.lower().strip().split())

                # Require exact match to avoid false cache hits
                if title_normalized != query_normalized:
                    # Log for debugging cache misses
                    if logger.isEnabledFor(10):  # DEBUG level
                        similarity = sum(1 for a, b in zip(title_normalized, query_normalized) if a == b)
                        logger.debug(
                            f"Cache check: no match for {plan_dir.name} "
                            f"(similarity={similarity}/{max(len(title_normalized), len(query_normalized))})"
                        )
                    continue

                logger.info(f"Cache check: found matching goals.json in {plan_dir.name}")

                # Found matching goals - convert to phase3 format
                subgoals = goals_data.get("subgoals", [])
                if not subgoals:
                    continue

                # Convert goals.json subgoals to phase3 decomposition format
                phase3_subgoals = []
                for sg in subgoals:
                    # Map goals.json fields to verify_lite expected fields
                    # goals.json: agent → assigned_agent, ideal_agent → suggested_agent
                    # Use `or ""` pattern to handle None values
                    phase3_subgoals.append(
                        {
                            "id": sg.get("id") or "",
                            "description": sg.get("description") or sg.get("title") or "",
                            "depends_on": sg.get("dependencies") or [],
                            "is_critical": sg.get("is_critical", True),
                            # verify_lite checks for these fields
                            "assigned_agent": sg.get("agent") or "",
                            "suggested_agent": sg.get("ideal_agent") or "",
                            # Additional context
                            "ideal_agent": sg.get("ideal_agent") or "",
                            "ideal_agent_desc": sg.get("ideal_agent_desc") or "",
                            "source_file": sg.get("source_file") or "",
                            "match_quality": sg.get("match_quality") or "excellent",
                        }
                    )

                logger.info(
                    "Cache hit from goals.json: %s (%d subgoals)",
                    goals_file,
                    len(phase3_subgoals),
                )

                return {
                    "goal": title,
                    "decomposition": {
                        "goal": title,
                        "subgoals": phase3_subgoals,
                    },
                    "subgoals_total": len(phase3_subgoals),
                    "_timing_ms": 0,
                    "_error": None,
                    "_cache_source": str(goals_file),
                }

        except Exception as e:
            logger.debug(f"Failed to check goals.json cache: {e}")

        return None

    @staticmethod
    def _parse_soar_log(log_path: str) -> dict[str, Any] | None:
        """Parse a SOAR conversation log and extract the decomposition result.

        Reads the markdown log file and looks for a JSON metadata block
        containing the phase 3 decomposition.

        Args:
            log_path: Path to the conversation log markdown file

        Returns:
            A phase3-compatible dict if decomposition found, None otherwise

        """
        import json
        from pathlib import Path

        try:
            path = Path(log_path)
            if not path.exists():
                return None

            content = path.read_text(encoding="utf-8", errors="ignore")

            # Look for ## Metadata section with JSON code block
            in_metadata = False
            json_lines: list[str] = []
            in_json_block = False

            for line in content.split("\n"):
                if line.strip().startswith("## Metadata"):
                    in_metadata = True
                    continue
                if in_metadata:
                    if line.strip().startswith("```json"):
                        in_json_block = True
                        continue
                    if in_json_block:
                        if line.strip() == "```":
                            break
                        json_lines.append(line)
                    # Stop if we hit another H2
                    if line.strip().startswith("## ") and not line.strip().startswith(
                        "## Metadata"
                    ):
                        break

            if not json_lines:
                return None

            metadata = json.loads("\n".join(json_lines))

            # Extract phase3 decomposition from metadata
            phases = metadata.get("phases", {})
            phase3 = phases.get("phase3_decompose")
            if phase3 is None:
                return None

            return phase3

        except Exception as e:
            logger.debug(f"Failed to parse SOAR log {log_path}: {e}")
            return None

    @staticmethod
    def _classify_api_error(error_msg: str) -> str:
        """Classify an API error message into a circuit breaker failure type.

        Args:
            error_msg: Error message string from the API call

        Returns:
            Failure type string for the circuit breaker

        """
        msg = error_msg.lower()

        # Permanent errors (will trigger fast-fail in circuit breaker)
        if "api error: model:" in msg or "invalid model" in msg or "model not found" in msg:
            return "invalid_model"
        if "unauthorized" in msg or "api key" in msg or "401" in msg:
            return "auth_error"
        if "forbidden" in msg or "403" in msg:
            return "forbidden"
        if "invalid request" in msg or "400" in msg or "bad request" in msg:
            return "invalid_request"

        # Transient errors (allow retries)
        # Includes quota exhaustion (e.g., "You're out of extra usage")
        if (
            "rate limit" in msg
            or "429" in msg
            or "too many requests" in msg
            or "out of" in msg
            and "usage" in msg
            or "quota" in msg
        ):
            return "rate_limit"
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "500" in msg or "internal server error" in msg or "server error" in msg:
            return "server_error"

        return "unknown"

    def _index_conversation_log(self, log_path: Any) -> None:
        """Index conversation log as knowledge chunk for future retrieval.

        Args:
            log_path: Path to the conversation log markdown file

        """
        try:
            from pathlib import Path

            from aurora_context_code.languages.markdown import MarkdownParser
            from aurora_context_code.semantic import EmbeddingProvider

            # Parse markdown log into chunks (ensure absolute path)
            parser = MarkdownParser()
            chunks = parser.parse(Path(log_path).resolve())

            if not chunks:
                logger.debug(f"No chunks extracted from {log_path}")
                return

            # Generate embeddings and store chunks
            embedding_provider = EmbeddingProvider()
            indexed_count = 0
            split_count = 0

            for chunk in chunks:
                try:
                    # Check if chunk is too large and needs splitting
                    if len(chunk.docstring or "") > 2048:
                        # Split by H2 sections
                        section_chunks = self._split_large_chunk_by_sections(chunk)
                        split_count += len(section_chunks) - 1

                        # Index each section
                        for section_chunk in section_chunks:
                            try:
                                # Final safety check: ensure docstring is under limit
                                docstring = section_chunk.docstring or ""
                                if len(docstring) > 2048:
                                    logger.warning(
                                        f"Section {section_chunk.id} still too large after splitting "
                                        f"({len(docstring)} chars), truncating to 2048",
                                    )
                                    docstring = docstring[:2019] + "\n\n[... truncated ...]"
                                    section_chunk.docstring = docstring

                                embedding = embedding_provider.embed_chunk(docstring)
                                section_chunk.embeddings = embedding
                                self.store.save_chunk(section_chunk)
                                indexed_count += 1
                                logger.debug(f"Indexed section chunk: {section_chunk.id}")
                            except Exception as e:
                                logger.warning(f"Failed to index section {section_chunk.id}: {e}")
                                continue
                    else:
                        # Chunk is small enough, index directly
                        docstring = chunk.docstring or ""
                        # Safety check (should never trigger since we check > 2048 above)
                        if len(docstring) > 2048:
                            logger.warning(
                                f"Chunk {chunk.id} unexpectedly too large ({len(docstring)} chars), truncating",
                            )
                            docstring = docstring[:2019] + "\n\n[... truncated ...]"
                            chunk.docstring = docstring

                        embedding = embedding_provider.embed_chunk(docstring)
                        chunk.embeddings = embedding  # type: ignore[assignment]
                        self.store.save_chunk(chunk)
                        indexed_count += 1
                        logger.debug(f"Indexed conversation chunk: {chunk.id}")

                except Exception as e:
                    logger.warning(f"Failed to index chunk {chunk.id}: {e}")
                    continue

            logger.info(
                f"Indexed conversation log: {log_path} "
                f"({indexed_count} chunks, {split_count} sections created from large chunks)",
            )

        except Exception as e:
            logger.warning(f"Failed to auto-index conversation log: {e}")
            # Don't fail the query if indexing fails
