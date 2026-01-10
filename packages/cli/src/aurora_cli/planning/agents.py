"""Agent capability matching for planning.

Wraps AgentManifest to recommend agents for subgoals based on capability matching.
"""

import logging
import re
from pathlib import Path
from typing import Optional

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


class AgentRecommender:
    """Recommends agents for subgoals based on capability matching.

    Wraps AgentManifest and ManifestManager to provide intelligent agent
    recommendations with gap detection and fallback handling.

    Attributes:
        manifest: Optional AgentManifest to use for recommendations
        config: Optional configuration object
        score_threshold: Minimum score for agent match (default 0.5)
        default_fallback: Default fallback agent (default "@full-stack-dev")
    """

    def __init__(
        self,
        manifest: Optional["AgentManifest"] = None,
        config: Optional[any] = None,
        score_threshold: float = 0.5,
        default_fallback: str = "@full-stack-dev",
        llm_client: Optional[any] = None,  # CLIPipeLLMClient
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
            return "- @full-stack-dev: General development tasks"

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
                # Extract keywords for suggested capabilities
                keywords = self._extract_keywords(subgoal)

                # Check if recommended agent exists
                agent_exists = self.verify_agent_exists(agent_id)

                gap = AgentGap(
                    subgoal_id=subgoal.id,
                    recommended_agent=agent_id,
                    agent_exists=agent_exists,
                    fallback=self.default_fallback,
                    suggested_capabilities=list(keywords)[:10],  # Limit to 10
                )
                gaps.append(gap)

        return gaps

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
            Default fallback agent ID (e.g., "@full-stack-dev")
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
        """Score an agent based on keyword overlap.

        Compares keywords against agent's capabilities and when_to_use text.
        Uses weighted scoring with when_to_use getting higher weight.

        Args:
            agent: Agent object from manifest
            keywords: Set of keywords from subgoal

        Returns:
            Score from 0.0 to 1.0 based on keyword overlap
        """
        if not keywords:
            return 0.0

        # Extract when_to_use keywords (higher weight)
        when_to_use_text = ""
        if hasattr(agent, "when_to_use") and agent.when_to_use:
            when_to_use_text = agent.when_to_use.lower()

        when_to_use_tokens = re.split(r"[^a-z0-9]+", when_to_use_text)
        when_to_use_keywords = {token for token in when_to_use_tokens if token and len(token) > 2}

        # Extract capabilities keywords (lower weight)
        capabilities_text = ""
        if hasattr(agent, "capabilities") and agent.capabilities:
            capabilities_text = " ".join(agent.capabilities).lower()

        capabilities_tokens = re.split(r"[^a-z0-9]+", capabilities_text)
        capabilities_keywords = {token for token in capabilities_tokens if token and len(token) > 2}

        # Calculate weighted overlap
        # when_to_use matches count as 2x, capabilities as 1x
        when_to_use_overlap = len(keywords & when_to_use_keywords)
        capabilities_overlap = len(keywords & capabilities_keywords)

        weighted_overlap = (when_to_use_overlap * 2.0) + capabilities_overlap
        max_possible = len(keywords) * 2.0  # Maximum if all matched in when_to_use

        if max_possible == 0:
            return 0.0

        score = weighted_overlap / max_possible

        return min(score, 1.0)  # Cap at 1.0

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
