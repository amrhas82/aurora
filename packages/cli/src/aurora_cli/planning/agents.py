"""Agent capability matching for planning.

Wraps AgentManifest to recommend agents for subgoals based on capability matching.
Provides AgentMatcher for ideal vs assigned agent comparison and gap detection.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from aurora_cli.planning.models import AgentGap, Subgoal


# Try to import ManifestManager - graceful fallback if not available
try:
    from aurora_cli.agent_discovery.manifest import AgentManifest, ManifestManager

    MANIFEST_AVAILABLE = True
except ImportError:
    MANIFEST_AVAILABLE = False
    ManifestManager = None  # type: ignore
    AgentManifest = None  # type: ignore

logger = logging.getLogger(__name__)

# Common stop words to filter out from keyword extraction
STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
}


# =============================================================================
# New AgentMatcher for ideal vs assigned comparison (used by aur soar/goals)
# =============================================================================


@dataclass
class GapInfo:
    """Information about a detected agent gap.

    Represents a subgoal where the ideal agent differs from the assigned agent,
    indicating a gap in the agent registry.

    Attributes:
        subgoal_id: ID of the subgoal with the gap (e.g., "sg-1")
        ideal_agent: Agent that SHOULD handle this task (unconstrained)
        ideal_agent_desc: Description of the ideal agent's capabilities
        assigned_agent: Best AVAILABLE agent from manifest

    """

    subgoal_id: str
    ideal_agent: str
    ideal_agent_desc: str
    assigned_agent: str


@dataclass
class MatchResult:
    """Result of matching a subgoal to an agent.

    Contains the matched agent, gap detection result, and optional spawn prompt.

    Attributes:
        subgoal_id: ID of the subgoal
        agent: Agent to use (ideal if spawning, assigned otherwise)
        is_gap: True if ideal != assigned
        gap_info: Gap details if is_gap is True
        spawn_prompt: Prompt for ad-hoc spawning (aur soar only)

    """

    subgoal_id: str
    agent: str
    is_gap: bool
    gap_info: GapInfo | None = None
    spawn_prompt: str | None = None


class AgentMatcher:
    """Matches subgoals to agents with gap detection and ad-hoc spawning.

    Compares ideal_agent (what SHOULD handle the task) with assigned_agent
    (best available from manifest) to detect gaps. Used by both aur soar
    and aur goals:

    - aur soar: Spawns ad-hoc agents when gaps detected
    - aur goals: Reports gaps with suggestions for agent creation

    Attributes:
        manifest: AgentManifest for checking agent existence
        available_agents_list: Formatted list of available agents for spawn prompts

    """

    def __init__(self, manifest: Optional["AgentManifest"] = None) -> None:
        """Initialize agent matcher.

        Args:
            manifest: Optional AgentManifest (loads from cache if None)

        """
        self.manifest = manifest
        self._available_agents_list: str | None = None

    def match_subgoal(
        self,
        subgoal: dict,
        for_spawn: bool = False,
    ) -> MatchResult:
        """Match a subgoal to an agent, detecting gaps.

        Compares ideal_agent vs assigned_agent from the subgoal dict.
        If they differ, a gap is detected.

        Args:
            subgoal: Dict with keys: id, ideal_agent, ideal_agent_desc, assigned_agent
            for_spawn: If True, generate spawn_prompt for gaps (aur soar mode)

        Returns:
            MatchResult with gap detection and optional spawn prompt

        """
        subgoal_id = subgoal.get("id", "unknown")
        ideal = subgoal.get("ideal_agent", "")
        ideal_desc = subgoal.get("ideal_agent_desc", "")
        assigned = subgoal.get("assigned_agent", "")
        description = subgoal.get("description", "")

        # Normalize agent IDs (ensure @ prefix)
        ideal = self._normalize_agent_id(ideal)
        assigned = self._normalize_agent_id(assigned)

        # Gap detection: ideal != assigned
        is_gap = ideal != assigned

        # Build gap info if gap detected
        gap_info = None
        if is_gap:
            gap_info = GapInfo(
                subgoal_id=subgoal_id,
                ideal_agent=ideal,
                ideal_agent_desc=ideal_desc,
                assigned_agent=assigned,
            )

        # Build spawn prompt if requested and gap detected
        spawn_prompt = None
        if is_gap and for_spawn:
            spawn_prompt = self._create_spawn_prompt(
                agent_name=ideal,
                agent_desc=ideal_desc,
                task_description=description,
            )

        # For spawning, use ideal agent; otherwise use assigned
        agent_to_use = ideal if for_spawn else assigned

        return MatchResult(
            subgoal_id=subgoal_id,
            agent=agent_to_use,
            is_gap=is_gap,
            gap_info=gap_info,
            spawn_prompt=spawn_prompt,
        )

    def detect_gaps(self, subgoals: list[dict]) -> list[GapInfo]:
        """Detect all gaps in a list of subgoals.

        Used by aur goals to report gaps with suggestions.

        Args:
            subgoals: List of subgoal dicts with ideal_agent, assigned_agent

        Returns:
            List of GapInfo for subgoals where ideal != assigned

        """
        gaps = []
        for subgoal in subgoals:
            result = self.match_subgoal(subgoal, for_spawn=False)
            if result.is_gap and result.gap_info:
                gaps.append(result.gap_info)
        return gaps

    def agent_exists(self, agent_id: str) -> bool:
        """Check if an agent exists in the manifest.

        Args:
            agent_id: Agent ID with or without @ prefix

        Returns:
            True if agent exists in manifest

        """
        if self.manifest is None:
            self._load_manifest()

        if self.manifest is None:
            return False

        agent_id_clean = agent_id.lstrip("@")
        try:
            agent = self.manifest.get_agent(agent_id_clean)
            return agent is not None
        except Exception:
            return False

    def _create_spawn_prompt(
        self,
        agent_name: str,
        agent_desc: str,
        task_description: str,
    ) -> str:
        """Create a prompt for ad-hoc agent spawning.

        Used by aur soar when no suitable agent exists. The prompt
        instructs the LLM to act as the ideal agent and complete the task.

        Args:
            agent_name: Name of the ideal agent (e.g., "@creative-writer")
            agent_desc: Description of the agent's capabilities
            task_description: The task to complete

        Returns:
            Formatted spawn prompt for LLM

        """
        # Get available agents list for context
        available_list = self._get_available_agents_list()

        return f"""For this specific request, act as a {agent_name} specialist ({agent_desc}).

Task: {task_description}

IMPORTANT: Emit brief progress updates (e.g., "Analyzing...", "Found X...") as you work.

Please complete this task directly without additional questions or preamble. Provide the complete deliverable.

---

After your deliverable, suggest a formal agent specification for this capability:
- Agent ID (kebab-case)
- Role/title
- Goal description
- Key capabilities (3-5 items)

Available agents for reference:
{available_list}
"""

    def _get_available_agents_list(self) -> str:
        """Get formatted list of available agents.

        Cached for efficiency across multiple spawn prompts.

        Returns:
            Formatted string with agent IDs and descriptions

        """
        if self._available_agents_list is not None:
            return self._available_agents_list

        if self.manifest is None:
            self._load_manifest()

        if self.manifest is None or not self.manifest.agents:
            self._available_agents_list = "- (no agents registered)"
            return self._available_agents_list

        lines = []
        for agent in self.manifest.agents:
            desc = ""
            if hasattr(agent, "goal") and agent.goal:
                desc = agent.goal[:60] + "..." if len(agent.goal) > 60 else agent.goal
            elif hasattr(agent, "when_to_use") and agent.when_to_use:
                desc = (
                    agent.when_to_use[:60] + "..."
                    if len(agent.when_to_use) > 60
                    else agent.when_to_use
                )

            lines.append(f"- @{agent.id}: {desc}")

        self._available_agents_list = "\n".join(lines)
        return self._available_agents_list

    def _normalize_agent_id(self, agent_id: str) -> str:
        """Normalize agent ID to include @ prefix.

        Args:
            agent_id: Agent ID with or without @ prefix

        Returns:
            Agent ID with @ prefix

        """
        if not agent_id:
            return "@unknown"
        return agent_id if agent_id.startswith("@") else f"@{agent_id}"

    def _load_manifest(self) -> None:
        """Load agent manifest from cache."""
        if not MANIFEST_AVAILABLE or not ManifestManager:
            logger.warning("ManifestManager not available")
            return

        try:
            manifest_path = Path.cwd() / ".aurora" / "cache" / "agent_manifest.json"
            manager = ManifestManager()
            self.manifest = manager.get_or_refresh(
                path=manifest_path,
                auto_refresh=True,
                refresh_interval_hours=24,
            )
            logger.debug(f"Loaded agent manifest with {len(self.manifest.agents)} agents")
        except Exception as e:
            logger.warning(f"Failed to load agent manifest: {e}")


# =============================================================================
# Legacy AgentRecommender (kept for backward compatibility)
# =============================================================================


class AgentRecommender:
    """Recommends agents for subgoals based on capability matching.

    Wraps AgentManifest and ManifestManager to provide intelligent agent
    recommendations with gap detection and fallback handling.

    Attributes:
        manifest: Optional AgentManifest to use for recommendations
        config: Optional configuration object
        score_threshold: Minimum score for agent match (default 0.5)
        default_fallback: Default fallback agent (default "@code-developer")

    """

    def __init__(
        self,
        manifest: Optional["AgentManifest"] = None,
        config: Any | None = None,
        score_threshold: float = 0.5,
        default_fallback: str = "@code-developer",
        llm_client: Any | None = None,  # CLIPipeLLMClient
    ) -> None:
        """Initialize agent recommender.

        Args:
            manifest: Optional AgentManifest to use (loads from cache if None)
            config: Optional configuration object
            score_threshold: Minimum score for agent match (default 0.5)
            default_fallback: Default fallback agent ID
            llm_client: Optional LLM client for fallback classification

        """
        self.manifest = manifest
        self.config = config
        self.score_threshold = score_threshold
        self.default_fallback = default_fallback
        self.llm_client = llm_client

    def recommend_for_subgoal(self, subgoal: Subgoal) -> tuple[str, float]:
        """Recommend best agent for a subgoal based on capability matching.

        Extracts keywords from subgoal and scores agents based on keyword
        overlap with their capabilities and when_to_use descriptions.

        Args:
            subgoal: Subgoal to recommend agent for

        Returns:
            Tuple of (agent_id, score)
            - agent_id: Recommended agent ID with @ prefix
            - score: Match score from 0.0 to 1.0

        """
        # Load manifest if not provided
        if self.manifest is None:
            try:
                self.manifest = self._load_manifest()
            except Exception as e:
                logger.warning(f"Failed to load agent manifest: {e}")
                return (self.default_fallback, 0.0)

        # Extract keywords from subgoal
        keywords = self._extract_keywords(subgoal)

        if not keywords:
            logger.debug(f"No keywords extracted from subgoal {subgoal.id}")
            return (self.default_fallback, 0.0)

        # Score each agent
        best_agent = None
        best_score = 0.0

        for agent in self.manifest.agents:
            score = self._score_agent(agent, keywords)
            if score > best_score:
                best_score = score
                best_agent = agent

        # Check if score meets threshold
        if best_agent and best_score >= self.score_threshold:
            return (f"@{best_agent.id}", best_score)

        # Return fallback if no good match
        return (self.default_fallback, best_score)

    async def recommend_for_subgoal_async(self, subgoal: Subgoal) -> tuple[str, float]:
        """Recommend best agent with LLM fallback for low-scoring matches.

        First tries keyword-based matching. If score < threshold and LLM client
        is available, uses LLM to classify the subgoal.

        Args:
            subgoal: Subgoal to recommend agent for

        Returns:
            Tuple of (agent_id, score)
            - agent_id: Recommended agent ID with @ prefix
            - score: Match score from 0.0 to 1.0

        """
        # Try keyword matching first
        agent_id, score = self.recommend_for_subgoal(subgoal)

        # If score meets threshold, return immediately
        if score >= self.score_threshold:
            return (agent_id, score)

        # Try LLM fallback if available
        if self.llm_client is not None:
            try:
                llm_agent_id, llm_score = await self._llm_classify(subgoal)

                # Use LLM result if it meets threshold
                if llm_score >= self.score_threshold:
                    return (llm_agent_id, llm_score)
            except Exception as e:
                logger.warning(f"LLM classification failed: {e}")
                # Fall through to return keyword result

        # Return keyword-based result (may be below threshold)
        return (agent_id, score)

    async def _llm_classify(self, subgoal: Subgoal) -> tuple[str, float]:
        """Use LLM to suggest agent when keyword matching fails.

        Args:
            subgoal: Subgoal to classify

        Returns:
            Tuple of (agent_id, confidence)

        Raises:
            ValueError: If LLM response is invalid

        """
        if self.llm_client is None:
            raise ValueError("LLM client not available")

        # Load manifest if needed
        if self.manifest is None:
            try:
                self.manifest = self._load_manifest()
            except Exception as e:
                logger.warning(f"Failed to load manifest for LLM classification: {e}")
                raise

        # Format agent list for prompt
        agent_list = self._format_agents()

        # Build classification prompt
        prompt = f"""Task: {subgoal.title}
Description: {subgoal.description}

Available agents:
{agent_list}

Which agent is best suited for this task?

Return JSON with this exact structure:
{{
    "agent_id": "@agent-id",
    "confidence": 0.85,
    "reasoning": "brief explanation"
}}

Important:
- agent_id must match one of the available agents (with @ prefix)
- confidence must be between 0.0 and 1.0
- reasoning should be 1-2 sentences"""

        # Call LLM
        response = await self.llm_client.generate(prompt, phase_name="agent_matching")

        # Parse JSON response
        import json

        try:
            # Clean up response
            text = response.content.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text)

            agent_id = data.get("agent_id", "")
            confidence = float(data.get("confidence", 0.0))

            # Validate
            if not agent_id.startswith("@"):
                raise ValueError(f"Invalid agent_id format: {agent_id}")
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(f"Invalid confidence: {confidence}")

            return (agent_id, confidence)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse LLM classification: {e}")
            raise ValueError(f"Invalid LLM response: {e}")

    def _format_agents(self) -> str:
        """Format agent list for LLM prompt.

        Returns:
            Formatted string with agent IDs and descriptions

        """
        if self.manifest is None or not self.manifest.agents:
            return "- @code-developer: General development tasks"

        lines = []
        for agent in self.manifest.agents:
            desc = ""
            if hasattr(agent, "when_to_use") and agent.when_to_use:
                desc = agent.when_to_use
            elif hasattr(agent, "capabilities") and agent.capabilities:
                desc = ", ".join(agent.capabilities[:3])

            lines.append(f"- @{agent.id}: {desc}")

        return "\n".join(lines)

    def detect_gaps(
        self,
        subgoals: list[Subgoal],
        recommendations: dict[str, tuple[str, float]],
    ) -> list[AgentGap]:
        """Detect agent gaps for subgoals with low-scoring recommendations.

        Args:
            subgoals: List of subgoals
            recommendations: Dict mapping subgoal ID to (agent_id, score)

        Returns:
            List of AgentGap objects for subgoals with score < threshold

        """
        gaps = []

        for subgoal in subgoals:
            if subgoal.id not in recommendations:
                continue

            agent_id, score = recommendations[subgoal.id]

            # Gap if score below threshold
            if score < self.score_threshold:
                # Create gap with new schema
                gap = AgentGap(
                    subgoal_id=subgoal.id,
                    ideal_agent=agent_id,
                    ideal_agent_desc=f"Agent for: {subgoal.description[:50]}",
                    assigned_agent=self.default_fallback,
                )
                gaps.append(gap)

        return gaps

    def score_agent_for_subgoal(self, agent_id: str, subgoal: Subgoal) -> float:
        """Score how well a specific agent matches a subgoal.

        Unlike recommend_for_subgoal which finds the best agent, this method
        scores a specific agent that's already been assigned (e.g., by SOAR).

        Args:
            agent_id: Agent ID with @ prefix (e.g., "@code-developer")
            subgoal: Subgoal to score against

        Returns:
            Match score from 0.0 to 1.0

        """
        # Load manifest if not provided
        if self.manifest is None:
            try:
                self.manifest = self._load_manifest()
            except Exception as e:
                logger.warning(f"Failed to load agent manifest: {e}")
                return 0.4  # Moderate confidence if can't verify

        # Strip @ prefix if present
        agent_id_clean = agent_id.lstrip("@")

        # Find the agent in manifest
        try:
            agent = self.manifest.get_agent(agent_id_clean)
            if agent is None:
                return 0.3  # Low score for unknown agents
        except Exception:
            return 0.3

        # Extract keywords from subgoal
        keywords = self._extract_keywords(subgoal)

        if not keywords:
            return 0.4  # Moderate confidence if no keywords to match

        # Score this specific agent
        score = self._score_agent(agent, keywords)

        # Boost score slightly since SOAR (LLM) assigned it - has semantic understanding
        # Keyword matching can underestimate due to paraphrasing
        # But don't give high confidence if there's no keyword overlap at all
        if score > 0.2:
            # Good keyword match - boost for semantic understanding
            boosted_score = min(score + 0.2, 1.0)
        elif score > 0:
            # Some match - modest boost
            boosted_score = min(score + 0.1, 0.6)
        else:
            # No keyword match - low confidence (can't verify LLM assignment)
            boosted_score = 0.3

        return boosted_score

    def verify_agent_exists(self, agent_id: str) -> bool:
        """Verify that an agent exists in the manifest.

        Args:
            agent_id: Agent ID with or without @ prefix

        Returns:
            True if agent exists, False otherwise

        """
        # Load manifest if not available
        if self.manifest is None:
            try:
                self.manifest = self._load_manifest()
            except Exception as e:
                logger.warning(f"Failed to load agent manifest: {e}")
                return False

        # Strip @ prefix if present
        agent_id_clean = agent_id.lstrip("@")

        # Check if agent exists
        try:
            agent = self.manifest.get_agent(agent_id_clean)
            return agent is not None
        except Exception:
            return False

    def get_fallback_agent(self) -> str:
        """Get default fallback agent ID.

        Returns:
            Default fallback agent ID (e.g., "@code-developer")

        """
        return self.default_fallback

    def _extract_keywords(self, subgoal: Subgoal) -> set[str]:
        """Extract keywords from subgoal title and description.

        Tokenizes, converts to lowercase, and removes stop words.

        Args:
            subgoal: Subgoal to extract keywords from

        Returns:
            Set of unique keywords

        """
        # Combine title and description
        text = f"{subgoal.title} {subgoal.description}"

        # Convert to lowercase
        text = text.lower()

        # Split on non-alphanumeric characters
        tokens = re.split(r"[^a-z0-9]+", text)

        # Filter out stop words and empty strings
        keywords = {
            token for token in tokens if token and len(token) > 2 and token not in STOP_WORDS
        }

        return keywords

    def _score_agent(self, agent: any, keywords: set[str]) -> float:
        """Score an agent based on keyword overlap and action word matching.

        Compares keywords against agent's goal, when_to_use, capabilities,
        and AGENT_ACTION_WORDS for semantic matching. Action words like
        "analyze", "implement", "debug" boost scores for matching agents.

        Args:
            agent: Agent object from manifest
            keywords: Set of keywords from subgoal

        Returns:
            Score from 0.0 to 1.0 based on keyword overlap

        """
        if not keywords:
            return 0.0

        # Extract goal keywords (high weight) - primary description of agent
        goal_text = ""
        if hasattr(agent, "goal") and agent.goal:
            goal_text = agent.goal.lower()

        goal_tokens = re.split(r"[^a-z0-9]+", goal_text)
        goal_keywords = {token for token in goal_tokens if token and len(token) > 2}

        # Extract when_to_use keywords (high weight) - may be null
        when_to_use_text = ""
        if hasattr(agent, "when_to_use") and agent.when_to_use:
            when_to_use_text = agent.when_to_use.lower()

        when_to_use_tokens = re.split(r"[^a-z0-9]+", when_to_use_text)
        when_to_use_keywords = {token for token in when_to_use_tokens if token and len(token) > 2}

        # Combine goal and when_to_use for primary matching
        primary_keywords = goal_keywords | when_to_use_keywords

        # Extract capabilities keywords (lower weight)
        capabilities_text = ""
        if hasattr(agent, "capabilities") and agent.capabilities:
            capabilities_text = " ".join(agent.capabilities).lower()

        capabilities_tokens = re.split(r"[^a-z0-9]+", capabilities_text)
        capabilities_keywords = {token for token in capabilities_tokens if token and len(token) > 2}

        # Calculate weighted overlap
        # primary (goal/when_to_use) matches count as 2x, capabilities as 1x
        primary_overlap = len(keywords & primary_keywords)
        capabilities_overlap = len(keywords & capabilities_keywords)

        weighted_overlap = (primary_overlap * 2.0) + capabilities_overlap
        max_possible = len(keywords) * 2.0  # Maximum if all matched in primary

        if max_possible == 0:
            return 0.0

        base_score = weighted_overlap / max_possible

        # Partial/stem matching - boost score if subgoal keywords partially match
        # agent's goal keywords (e.g., "implementation" matches "implement")
        # This works automatically for any agent without hardcoded word lists
        all_agent_keywords = primary_keywords | capabilities_keywords
        if all_agent_keywords:
            partial_matches = 0
            matched_keywords = set()  # Track to avoid double counting

            for keyword in keywords:
                if keyword in matched_keywords:
                    continue  # Already counted via exact match
                for agent_kw in all_agent_keywords:
                    # Skip if already exact match
                    if keyword == agent_kw:
                        matched_keywords.add(keyword)
                        break
                    # Partial match if one is prefix of other (handles verb forms)
                    # e.g., "implement" matches "implementation", "analyze" matches "analyzing"
                    if len(keyword) >= 4 and len(agent_kw) >= 4:
                        if keyword.startswith(agent_kw[:4]) or agent_kw.startswith(keyword[:4]):
                            partial_matches += 1
                            matched_keywords.add(keyword)
                            break

            # Boost score for partial matches (+0.1 per match, cap at 0.3)
            partial_boost = min(partial_matches * 0.1, 0.3)
            base_score += partial_boost

        return min(base_score, 1.0)  # Cap at 1.0

    def _load_manifest(self) -> "AgentManifest":
        """Load agent manifest from cache.

        Returns:
            AgentManifest instance

        Raises:
            RuntimeError: If ManifestManager not available
            Exception: If manifest cannot be loaded

        """
        if not MANIFEST_AVAILABLE or not ManifestManager:
            raise RuntimeError("ManifestManager not available")

        # Get or create default manifest path
        manifest_path = Path.cwd() / ".aurora" / "cache" / "agent_manifest.json"

        # Create manifest manager and load/refresh manifest
        manager = ManifestManager()
        manifest = manager.get_or_refresh(
            path=manifest_path,
            auto_refresh=True,
            refresh_interval_hours=24,
        )

        logger.debug(f"Loaded agent manifest with {len(manifest.agents)} agents")
        return manifest

    def recommend_for_description(self, description: str) -> tuple[str, float]:
        """Find best agent for a task description string.

        Used by verify.py to match ideal_agent_desc to available agents
        without needing a full Subgoal object. Reuses existing keyword
        extraction and scoring logic.

        Args:
            description: Task description (e.g., ideal_agent_desc from SOAR)

        Returns:
            Tuple of (agent_id, score)
            - agent_id: Best matching agent ID with @ prefix
            - score: Match score from 0.0 to 1.0

        """
        # Load manifest if not provided
        if self.manifest is None:
            try:
                self.manifest = self._load_manifest()
            except Exception as e:
                logger.warning(f"Failed to load agent manifest: {e}")
                return (self.default_fallback, 0.0)

        # Extract keywords from description text
        text = description.lower()
        tokens = re.split(r"[^a-z0-9]+", text)
        keywords = {t for t in tokens if t and len(t) > 2 and t not in STOP_WORDS}

        if not keywords:
            logger.debug("No keywords extracted from description")
            return (self.default_fallback, 0.0)

        # Score each agent using existing _score_agent method
        best_agent = None
        best_score = 0.0

        for agent in self.manifest.agents:
            score = self._score_agent(agent, keywords)
            if score > best_score:
                best_score = score
                best_agent = agent

        # Use lower threshold (0.15) for description matching
        # since we don't have structured Subgoal with title+description
        if best_agent and best_score >= 0.15:
            return (f"@{best_agent.id}", best_score)

        # Return fallback if no good match
        return (self.default_fallback, best_score)
