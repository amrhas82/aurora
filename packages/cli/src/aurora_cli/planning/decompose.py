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
from pathlib import Path
from typing import Any

from aurora_cli.planning.agents import AgentRecommender
from aurora_cli.planning.cache import PlanDecompositionCache
from aurora_cli.planning.memory import FilePathResolver
from aurora_cli.planning.models import AgentGap, Complexity, FileResolution, Subgoal

# Try to import MemoryRetriever for context loading
try:
    from aurora_cli.memory.retrieval import MemoryRetriever

    MEMORY_RETRIEVER_AVAILABLE = True
except ImportError:
    MEMORY_RETRIEVER_AVAILABLE = False
    MemoryRetriever = None  # type: ignore

# Try to import SOAR - graceful fallback if not available
try:
    from aurora_reasoning.llm_client import LLMClient
    from aurora_soar.phases.decompose import decompose_query

    SOAR_AVAILABLE = True
except ImportError:
    SOAR_AVAILABLE = False
    decompose_query = None  # type: ignore
    LLMClient = None  # type: ignore

# Try to import ManifestManager for agent discovery
try:
    from aurora_cli.agent_discovery.manifest import ManifestManager

    MANIFEST_AVAILABLE = True
except ImportError:
    MANIFEST_AVAILABLE = False
    ManifestManager = None  # type: ignore

logger = logging.getLogger(__name__)


class PlanDecomposer:
    """Orchestrates SOAR decomposition for planning workflow.

    This class integrates SOAR's sophisticated decomposition capabilities
    into the planning system, with graceful fallback to heuristics when
    SOAR is unavailable or fails.

    Attributes:
        config: Optional configuration object for LLM settings
        cache: Specialized cache for decomposition results with LRU+TTL
    """

    def __init__(
        self,
        config: Any | None = None,
        store: Any | None = None,
        cache_capacity: int = 100,
        cache_ttl_hours: int = 24,
        enable_persistent_cache: bool = True,
    ):
        """Initialize PlanDecomposer.

        Args:
            config: Optional configuration object with LLM settings
            store: Optional SQLiteStore for memory retrieval
            cache_capacity: Maximum number of decompositions to cache (default: 100)
            cache_ttl_hours: Cache entry TTL in hours (default: 24)
            enable_persistent_cache: Enable persistent cache storage (default: True)
        """
        self.config = config
        self.store = store

        # Initialize specialized decomposition cache
        persistent_path = None
        if enable_persistent_cache:
            # Use .aurora/cache for persistent storage
            cache_dir = Path.cwd() / ".aurora" / "cache"
            persistent_path = cache_dir / "decomposition_cache.db"

        self.cache = PlanDecompositionCache(
            capacity=cache_capacity,
            ttl_hours=cache_ttl_hours,
            persistent_path=persistent_path,
        )

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

        # Check cache first (handles both in-memory and persistent)
        cached_result = self.cache.get(goal, complexity, context_files)
        if cached_result:
            logger.debug(f"Cache hit for goal: {goal[:50]}...")
            return cached_result

        # Try SOAR first
        if SOAR_AVAILABLE and decompose_query:
            try:
                context = self._build_context(context_files, goal=goal)
                subgoals = self._call_soar(goal, context, complexity)
                result = (subgoals, "soar")
                # Cache the result
                self.cache.set(goal, complexity, subgoals, "soar", context_files)
                return result
            except (ImportError, RuntimeError, TimeoutError) as e:
                logger.warning(f"SOAR decomposition failed: {e}, falling back to heuristics")

        # Fallback to heuristics
        subgoals = self._fallback_to_heuristics(goal, complexity)
        result = (subgoals, "heuristic")
        # Cache the heuristic result
        self.cache.set(goal, complexity, subgoals, "heuristic", context_files)
        return result

    def decompose_with_files(
        self,
        goal: str,
        complexity: Complexity | None = None,
        context_files: list[str] | None = None,
        store: Any = None,
    ) -> tuple[list[Subgoal], dict[str, list[FileResolution]], str]:
        """Decompose goal and resolve file paths for each subgoal.

        This method extends decompose() by also resolving file paths from
        indexed memory for each subgoal using FilePathResolver.

        Args:
            goal: The goal to decompose
            complexity: Optional complexity level (auto-assessed if None)
            context_files: Optional list of relevant file paths
            store: Optional SQLiteStore for file resolver

        Returns:
            Tuple of (subgoals, file_resolutions, decomposition_source)
            - subgoals: List of Subgoal objects
            - file_resolutions: Dict mapping subgoal IDs to list of FileResolution
            - decomposition_source: "soar" or "heuristic"
        """
        # First decompose to get subgoals
        subgoals, source = self.decompose(goal, complexity, context_files)

        # Create file path resolver
        resolver = FilePathResolver(store=store, config=self.config)

        # Resolve file paths for each subgoal
        file_resolutions: dict[str, list[FileResolution]] = {}

        for subgoal in subgoals:
            try:
                resolutions = resolver.resolve_for_subgoal(subgoal, limit=5)
                file_resolutions[subgoal.id] = resolutions
            except Exception as e:
                logger.warning(f"Failed to resolve files for subgoal {subgoal.id}: {e}")
                file_resolutions[subgoal.id] = []

        return subgoals, file_resolutions, source

    def decompose_with_agents(
        self,
        goal: str,
        complexity: Complexity | None = None,
        context_files: list[str] | None = None,
        config: Any = None,
    ) -> tuple[list[Subgoal], dict[str, tuple[str, float]], list[AgentGap], str]:
        """Decompose goal and recommend agents for each subgoal.

        This method extends decompose() by also recommending agents based
        on capability matching using AgentRecommender.

        Args:
            goal: The goal to decompose
            complexity: Optional complexity level (auto-assessed if None)
            context_files: Optional list of relevant file paths
            config: Optional configuration object

        Returns:
            Tuple of (subgoals, agent_recommendations, agent_gaps, decomposition_source)
            - subgoals: List of Subgoal objects
            - agent_recommendations: Dict mapping subgoal IDs to (agent_id, score)
            - agent_gaps: List of AgentGap objects for low-scoring matches
            - decomposition_source: "soar" or "heuristic"
        """
        # First decompose to get subgoals
        subgoals, source = self.decompose(goal, complexity, context_files)

        # Create agent recommender
        recommender = AgentRecommender(config=config)

        # Recommend agents for each subgoal
        agent_recommendations: dict[str, tuple[str, float]] = {}

        for subgoal in subgoals:
            try:
                agent_id, score = recommender.recommend_for_subgoal(subgoal)
                agent_recommendations[subgoal.id] = (agent_id, score)

                # Update subgoal with assigned agent
                subgoal.assigned_agent = agent_id
            except Exception as e:
                logger.warning(f"Failed to recommend agent for subgoal {subgoal.id}: {e}")
                # Use fallback
                fallback = recommender.get_fallback_agent()
                agent_recommendations[subgoal.id] = (fallback, 0.0)
                subgoal.assigned_agent = fallback

        # Detect gaps for low-scoring recommendations
        agent_gaps = recommender.detect_gaps(subgoals, agent_recommendations)

        return subgoals, agent_recommendations, agent_gaps, source

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics including size, hits, misses, hit_rate
        """
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear all cache entries (both in-memory and persistent)."""
        self.cache.clear()

    def _build_context(
        self,
        context_files: list[str] | None = None,
        goal: str | None = None,
    ) -> dict[str, Any]:
        """Build context dictionary for SOAR decomposition.

        Loads context from:
        1. Explicit context files (--context flag) - highest priority
        2. Memory retrieval based on goal query - if no explicit files

        Args:
            context_files: Optional list of relevant file paths
            goal: Optional goal string for memory retrieval

        Returns:
            Context dictionary with code_chunks and reasoning_chunks
        """
        code_chunks: list[Any] = []
        reasoning_chunks: list[Any] = []

        if not MEMORY_RETRIEVER_AVAILABLE or not MemoryRetriever:
            logger.debug("MemoryRetriever not available, returning empty context")
            return {"code_chunks": code_chunks, "reasoning_chunks": reasoning_chunks}

        try:
            retriever = MemoryRetriever(store=self.store, config=self.config)

            # Priority 1: Load explicit context files (highest priority)
            if context_files:
                paths = [Path(f) for f in context_files]
                loaded_chunks = retriever.load_context_files(paths)
                if loaded_chunks:
                    code_chunks.extend(loaded_chunks)
                    logger.info(
                        "Loaded %d explicit context files for decomposition",
                        len(loaded_chunks),
                    )

            # Priority 2: Always query memory to augment context (not just fallback)
            if goal and self.store:
                retrieved = retriever.retrieve(goal, limit=10)
                if retrieved:
                    code_chunks.extend(retrieved)
                    logger.info(
                        "Retrieved %d chunks from memory for decomposition",
                        len(retrieved),
                    )

        except Exception as e:
            logger.warning("Failed to build context: %s", e)

        return {"code_chunks": code_chunks, "reasoning_chunks": reasoning_chunks}

    def _read_file_lines(
        self, file_path: str, line_start: int, line_end: int, max_lines: int = 50
    ) -> str:
        """Read specific lines from a file."""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            start_idx = max(0, line_start - 1)
            end_idx = min(len(lines), line_end)
            if end_idx - start_idx > max_lines:
                end_idx = start_idx + max_lines
            return "".join(lines[start_idx:end_idx])
        except Exception:
            return ""

    def _build_context_summary(self, context: dict[str, Any]) -> str:
        """Build actionable context summary with actual code content.

        For top chunks, reads actual file content so the LLM can see real code.
        For remaining chunks, includes docstrings as fallback.

        Args:
            context: Context dict with code_chunks and reasoning_chunks

        Returns:
            Summary string with actual code the LLM can use for decomposition.
        """
        code_chunks = context.get("code_chunks", [])
        reasoning_chunks = context.get("reasoning_chunks", [])

        summary_parts = []

        if code_chunks:
            TOP_N_WITH_CODE = 7
            MAX_CHUNKS = 12

            summary_parts.append(f"## Relevant Code ({len(code_chunks)} elements)\n")

            for i, chunk in enumerate(code_chunks[:MAX_CHUNKS]):
                # Extract chunk info (handle both objects and dicts)
                if hasattr(chunk, "file_path"):
                    file_path = chunk.file_path
                    name = getattr(chunk, "name", "unknown")
                    element_type = getattr(chunk, "element_type", "")
                    line_start = getattr(chunk, "line_start", 0)
                    line_end = getattr(chunk, "line_end", 0)
                    docstring = getattr(chunk, "docstring", "") or ""
                elif isinstance(chunk, dict):
                    metadata = chunk.get("metadata", {})
                    if metadata:
                        file_path = metadata.get("file_path", "unknown")
                        name = metadata.get("name", "unknown")
                        element_type = metadata.get("type", "")
                        line_start = metadata.get("line_start", 0)
                        line_end = metadata.get("line_end", 0)
                    else:
                        file_path = chunk.get("file_path", "unknown")
                        name = chunk.get("name", "unknown")
                        element_type = chunk.get("element_type", "")
                        line_start = chunk.get("line_start", 0)
                        line_end = chunk.get("line_end", 0)
                    docstring = chunk.get("content", "")
                else:
                    continue

                short_path = "/".join(file_path.split("/")[-2:]) if "/" in file_path else file_path
                entry_parts = [f"### {element_type}: {name}", f"File: {short_path}"]

                # For top N chunks, read actual code
                if i < TOP_N_WITH_CODE and line_start and line_end:
                    code_content = self._read_file_lines(file_path, line_start, line_end)
                    if code_content:
                        entry_parts.append(f"```python\n{code_content.rstrip()}\n```")
                    elif docstring:
                        entry_parts.append(f"Description: {docstring[:300]}...")
                elif docstring:
                    doc_preview = docstring[:200] + "..." if len(docstring) > 200 else docstring
                    entry_parts.append(f"Description: {doc_preview}")

                summary_parts.append("\n".join(entry_parts))

            if len(code_chunks) > MAX_CHUNKS:
                summary_parts.append(f"\n... and {len(code_chunks) - MAX_CHUNKS} more elements")

        if reasoning_chunks:
            summary_parts.append(
                f"\n## Previous Solutions: {len(reasoning_chunks)} relevant patterns"
            )

        if not summary_parts:
            return "No indexed context available. Using LLM general knowledge."

        return "\n\n".join(summary_parts)

    def _load_available_agents(self) -> list[str] | None:
        """Load available agents from manifest.

        Loads the agent manifest and extracts agent IDs with @ prefix for
        use in SOAR decomposition.

        Returns:
            List of agent IDs with @ prefix (e.g., ["@full-stack-dev", "@qa-test-architect"])
            Returns None if manifest cannot be loaded.
            Returns empty list if manifest is empty.
        """
        if not MANIFEST_AVAILABLE or not ManifestManager:
            logger.debug("ManifestManager not available, agent discovery disabled")
            return None

        try:
            # Get or create default manifest path
            manifest_path = Path.cwd() / ".aurora" / "cache" / "agent_manifest.json"

            # Create manifest manager and load/refresh manifest
            manager = ManifestManager()
            manifest = manager.get_or_refresh(
                path=manifest_path,
                auto_refresh=True,
                refresh_interval_hours=24,
            )

            # Extract agent IDs with @ prefix
            agent_ids = [f"@{agent.id}" for agent in manifest.agents]
            logger.debug(f"Loaded {len(agent_ids)} agents from manifest")
            return agent_ids

        except Exception as e:
            logger.warning(f"Failed to load agent manifest: {e}")
            return None

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

        # Load available agents from manifest
        available_agents = self._load_available_agents()

        # Call SOAR decompose_query
        try:
            result = decompose_query(
                query=goal,
                context=context,
                complexity=complexity.value,
                llm_client=llm_client,
                available_agents=available_agents,
                use_cache=True,
            )

            # Convert SOAR result to Subgoal objects
            # Note: LLM returns: description, suggested_agent, is_critical, depends_on
            subgoals = []
            for idx, sg_dict in enumerate(result.decomposition.subgoals, 1):
                # Extract description and create a short title from it
                description = sg_dict.get("description", "No description")
                # Create title from first ~50 chars of description or use explicit title if present
                title = sg_dict.get("title")
                if not title:
                    # Generate title: Take first sentence or first 50 chars
                    title = description.split(".")[0][:60]
                    if len(description.split(".")[0]) > 60:
                        title = title.rsplit(" ", 1)[0] + "..."

                # Get agent - support both new schema (ideal_agent, assigned_agent) and legacy (suggested_agent)
                # New schema: ideal_agent = what SHOULD handle, assigned_agent = best available
                # Legacy: suggested_agent = both ideal and assigned
                ideal_agent = sg_dict.get("ideal_agent", "")
                ideal_agent_desc = sg_dict.get("ideal_agent_desc", "")
                assigned_agent = sg_dict.get("assigned_agent", "")

                # Fallback to legacy suggested_agent if new schema not present
                if not assigned_agent:
                    assigned_agent = sg_dict.get(
                        "suggested_agent", sg_dict.get("agent", "full-stack-dev")
                    )
                if not ideal_agent:
                    ideal_agent = assigned_agent  # Assume ideal == assigned for legacy

                # Ensure @ prefix
                agent = assigned_agent
                if not agent.startswith("@"):
                    agent = f"@{agent}"
                if ideal_agent and not ideal_agent.startswith("@"):
                    ideal_agent = f"@{ideal_agent}"

                # Get dependencies and normalize to sg-N format
                raw_deps = sg_dict.get("depends_on", sg_dict.get("dependencies", []))
                dependencies = []
                for dep in raw_deps:
                    dep_str = str(dep)
                    # Normalize: "1" -> "sg-1", "sg-1" stays "sg-1"
                    if not dep_str.startswith("sg-"):
                        # LLM often returns 0-indexed, convert to 1-indexed
                        try:
                            dep_num = int(dep_str)
                            # If it's 0-indexed (0, 1, 2...), convert to 1-indexed
                            if dep_num >= 0:
                                dep_str = f"sg-{dep_num + 1}"
                        except ValueError:
                            dep_str = f"sg-{dep_str}"
                    dependencies.append(dep_str)

                subgoal = Subgoal(
                    id=sg_dict.get("id", f"sg-{idx}"),
                    title=title,
                    description=description,
                    ideal_agent=ideal_agent,
                    ideal_agent_desc=ideal_agent_desc,
                    assigned_agent=agent,
                    dependencies=dependencies,
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

        # Create default client using CLIPipeLLMClient
        try:
            from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient

            return CLIPipeLLMClient(tool="claude", model="sonnet")
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
                ideal_agent="@holistic-architect",
                ideal_agent_desc="System design and architecture specialist",
                assigned_agent="@holistic-architect",
            )
        )

        # Always: Implementation
        subgoals.append(
            Subgoal(
                id="sg-2",
                title="Implement solution",
                description=f"Implement the planned solution for: {goal}",
                ideal_agent="@full-stack-dev",
                ideal_agent_desc="Full-stack development and implementation",
                assigned_agent="@full-stack-dev",
            )
        )

        # Always: Testing
        subgoals.append(
            Subgoal(
                id="sg-3",
                title="Test and verify",
                description=f"Write tests and verify solution for: {goal}",
                ideal_agent="@qa-test-architect",
                ideal_agent_desc="Quality assurance and testing specialist",
                assigned_agent="@qa-test-architect",
            )
        )

        # If complex, add documentation
        if complexity == Complexity.COMPLEX:
            subgoals.append(
                Subgoal(
                    id="sg-4",
                    title="Document changes",
                    description=f"Document implementation and update relevant docs for: {goal}",
                    ideal_agent="@full-stack-dev",
                    ideal_agent_desc="Full-stack development and documentation",
                    assigned_agent="@full-stack-dev",
                )
            )

        return subgoals
