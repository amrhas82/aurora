"""Pydantic models for Agent Discovery system.

This module defines the data models for agent information and manifest schema
used by the AURORA CLI agent discovery system.

Models:
    - AgentCategory: Enum for agent categories (eng, qa, product, general)
    - AgentInfo: Core agent metadata from frontmatter
    - AgentManifest: Manifest schema with version, sources, and agent list
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentCategory(str, Enum):
    """Agent category classification.

    Categories help organize agents by their primary function:
    - eng: Engineering/development agents
    - qa: Quality assurance/testing agents
    - product: Product management agents
    - general: General-purpose agents
    """

    ENG = "eng"
    QA = "qa"
    PRODUCT = "product"
    GENERAL = "general"


class AgentInfo(BaseModel):
    """Agent metadata extracted from markdown frontmatter.

    Required fields:
        id: Unique kebab-case identifier (e.g., 'quality-assurance')
        role: Agent's primary role/title
        goal: Brief description of agent's purpose

    Optional fields:
        category: Classification (eng/qa/product/general), defaults to 'general'
        skills: List of agent capabilities
        examples: Example use cases or prompts
        when_to_use: Guidance on when to invoke this agent
        dependencies: Other agents this agent may invoke
        source_file: Path to the original markdown file

    Example frontmatter:
        ---
        id: quality-assurance
        role: Test Architect & Quality Advisor
        goal: Ensure comprehensive test coverage and quality standards
        category: qa
        skills:
          - test strategy design
          - coverage analysis
          - quality gate decisions
        when_to_use: Use for test architecture review and quality decisions
        ---
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",  # Ignore unknown frontmatter fields
    )

    # Required fields
    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique kebab-case identifier for the agent",
    )
    role: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Agent's primary role or title",
    )
    goal: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Brief description of agent's purpose",
    )

    # Optional fields
    category: AgentCategory = Field(
        default=AgentCategory.GENERAL,
        description="Agent category classification",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="List of agent capabilities/skills",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example use cases or prompts",
    )
    when_to_use: str | None = Field(
        default=None,
        max_length=1000,
        description="Guidance on when to invoke this agent",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="IDs of other agents this agent may invoke",
    )
    source_file: str | None = Field(
        default=None,
        description="Path to the original markdown file",
    )

    @field_validator("id")
    @classmethod
    def validate_kebab_case_id(cls, v: str) -> str:
        """Validate that agent ID is in kebab-case format.

        Valid examples: 'quality-assurance', 'code-developer', 'orchestrator'
        Invalid examples: 'QA_Test', 'fullStackDev', 'test architect'

        Args:
            v: The agent ID to validate

        Returns:
            The validated ID (lowercased)

        Raises:
            ValueError: If ID is not valid kebab-case

        """
        # Normalize to lowercase
        v = v.lower().strip()

        # Kebab-case pattern: lowercase letters, numbers, hyphens
        # Can start with letter or number, no consecutive hyphens
        pattern = r"^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$"

        if not re.match(pattern, v):
            raise ValueError(
                f"Agent ID must be kebab-case (lowercase letters, numbers, hyphens). "
                f"Got: '{v}'. Examples: 'quality-assurance', '1-create-prd'",
            )

        return v

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: str | AgentCategory | None) -> AgentCategory:
        """Normalize category string to AgentCategory enum.

        Args:
            v: Category value (string or enum)

        Returns:
            AgentCategory enum value

        Raises:
            ValueError: If category is not recognized

        """
        if v is None:
            return AgentCategory.GENERAL

        if isinstance(v, AgentCategory):
            return v

        v_lower = str(v).lower().strip()

        # Map common variations
        category_map = {
            "eng": AgentCategory.ENG,
            "engineering": AgentCategory.ENG,
            "dev": AgentCategory.ENG,
            "development": AgentCategory.ENG,
            "qa": AgentCategory.QA,
            "quality": AgentCategory.QA,
            "test": AgentCategory.QA,
            "testing": AgentCategory.QA,
            "product": AgentCategory.PRODUCT,
            "pm": AgentCategory.PRODUCT,
            "general": AgentCategory.GENERAL,
            "other": AgentCategory.GENERAL,
        }

        if v_lower in category_map:
            return category_map[v_lower]

        # Try direct enum lookup
        try:
            return AgentCategory(v_lower)
        except ValueError:
            raise ValueError(f"Invalid category '{v}'. Must be one of: eng, qa, product, general")

    @field_validator("skills", "examples", "dependencies", mode="before")
    @classmethod
    def ensure_list(cls, v: Any) -> list[str]:
        """Ensure field is a list of strings.

        Handles cases where YAML might parse a single item as a string
        instead of a list.

        Args:
            v: Value to normalize

        Returns:
            List of strings

        """
        if v is None:
            return []
        if isinstance(v, str):
            # Single item provided as string
            return [v.strip()] if v.strip() else []
        if isinstance(v, list):
            return [str(item).strip() for item in v if item]
        return []


class ManifestStats(BaseModel):
    """Statistics about the agent manifest.

    Attributes:
        total: Total number of agents in manifest
        by_category: Count of agents per category
        malformed_files: Number of files that failed to parse

    """

    model_config = ConfigDict(str_strip_whitespace=True)

    total: int = Field(default=0, ge=0, description="Total number of agents")
    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Agent count per category",
    )
    malformed_files: int = Field(
        default=0,
        ge=0,
        description="Number of files that failed to parse",
    )


class AgentManifest(BaseModel):
    """Agent manifest schema with version control and caching metadata.

    The manifest aggregates all discovered agents from various sources
    and provides indexing for efficient lookup.

    Attributes:
        version: Manifest schema version
        generated_at: UTC timestamp when manifest was generated
        sources: List of discovery paths that were scanned
        agents: List of discovered agents
        stats: Aggregated statistics
        agents_by_id: Index for O(1) lookup by agent ID
        agents_by_category: Index for category-based filtering

    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    version: str = Field(
        default="1.0.0",
        description="Manifest schema version",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now().astimezone(),
        description="UTC timestamp when manifest was generated",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Discovery paths that were scanned",
    )
    agents: list[AgentInfo] = Field(
        default_factory=list,
        description="List of discovered agents",
    )
    stats: ManifestStats = Field(
        default_factory=ManifestStats,
        description="Aggregated statistics",
    )

    # Computed indexes (not serialized)
    _agents_by_id: dict[str, AgentInfo] = {}
    _agents_by_category: dict[AgentCategory, list[AgentInfo]] = {}

    def model_post_init(self, __context: Any) -> None:
        """Build indexes after model initialization."""
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        """Rebuild internal indexes for efficient lookup."""
        self._agents_by_id = {agent.id: agent for agent in self.agents}

        self._agents_by_category = {cat: [] for cat in AgentCategory}
        for agent in self.agents:
            self._agents_by_category[agent.category].append(agent)

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get agent by ID with O(1) lookup.

        Args:
            agent_id: Agent identifier to look up

        Returns:
            AgentInfo if found, None otherwise

        """
        return self._agents_by_id.get(agent_id.lower())

    def get_agents_by_category(self, category: AgentCategory) -> list[AgentInfo]:
        """Get all agents in a category.

        Args:
            category: Category to filter by

        Returns:
            List of agents in the category

        """
        return self._agents_by_category.get(category, [])

    def add_agent(self, agent: AgentInfo) -> bool:
        """Add an agent to the manifest.

        If an agent with the same ID exists, logs a warning and returns False.

        Args:
            agent: Agent to add

        Returns:
            True if added, False if duplicate

        """
        if agent.id in self._agents_by_id:
            return False

        self.agents.append(agent)
        self._agents_by_id[agent.id] = agent
        self._agents_by_category[agent.category].append(agent)
        return True

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize manifest to JSON-compatible dictionary.

        Returns:
            Dictionary suitable for JSON serialization

        """
        return {
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "sources": self.sources,
            "agents": [agent.model_dump(mode="json") for agent in self.agents],
            "stats": self.stats.model_dump(mode="json"),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> AgentManifest:
        """Deserialize manifest from JSON dictionary.

        Args:
            data: JSON dictionary

        Returns:
            AgentManifest instance

        """
        agents = [AgentInfo.model_validate(a) for a in data.get("agents", [])]
        stats = ManifestStats.model_validate(data.get("stats", {}))

        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        return cls(
            version=data.get("version", "1.0.0"),
            generated_at=generated_at or datetime.now().astimezone(),
            sources=data.get("sources", []),
            agents=agents,
            stats=stats,
        )
