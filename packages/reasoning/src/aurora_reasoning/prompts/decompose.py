"""Query decomposition prompt template with JSON schema."""

import json
from typing import Any

from . import PromptTemplate


class DecomposePromptTemplate(PromptTemplate):
    """Prompt template for query decomposition into subgoals.

    Decomposes complex queries into actionable subgoals with agent routing
    and execution order.
    """

    def __init__(self) -> None:
        super().__init__(name="decompose", version="1.0")

    # Agent capability mappings for better matching
    AGENT_CAPABILITIES = {
        # Core development agents
        "code-developer": {
            "specialties": [
                "code implementation",
                "debugging",
                "refactoring",
                "API development",
                "frontend development",
                "backend development",
                "bug fixes",
            ],
            "can_handle": [
                "documentation updates",
                "basic security review",
                "simple DevOps tasks",
            ],
        },
        "system-architect": {
            "specialties": [
                "system design",
                "architecture",
                "API design",
                "infrastructure planning",
                "technology selection",
                "scalability design",
            ],
            "can_handle": ["code review", "dependency analysis", "data modeling"],
        },
        "quality-assurance": {
            "specialties": [
                "test architecture",
                "test strategy",
                "quality assessment",
                "test design",
                "integration testing",
                "performance testing",
            ],
            "can_handle": ["code review for quality", "acceptance criteria validation"],
        },
        # Product/Business agents
        "feature-planner": {
            "specialties": [
                "PRD creation",
                "product strategy",
                "feature prioritization",
                "roadmap planning",
                "stakeholder communication",
            ],
            "can_handle": ["user research synthesis", "competitive analysis"],
        },
        "backlog-manager": {
            "specialties": [
                "backlog management",
                "story refinement",
                "acceptance criteria",
                "sprint planning",
                "prioritization",
            ],
            "can_handle": ["user story validation", "requirement clarification"],
        },
        "market-researcher": {
            "specialties": [
                "market research",
                "competitive analysis",
                "brainstorming",
                "project discovery",
                "requirement gathering",
            ],
            "can_handle": ["data analysis", "process documentation"],
        },
        # Design agents
        "ui-designer": {
            "specialties": [
                "UI/UX design",
                "wireframes",
                "prototypes",
                "user experience",
                "accessibility",
                "design systems",
            ],
            "can_handle": ["frontend specifications", "user flow design"],
        },
        "story-writer": {
            "specialties": [
                "story creation",
                "epic management",
                "retrospectives",
                "agile processes",
                "team facilitation",
            ],
            "can_handle": ["sprint planning support", "process improvement"],
        },
        # Fallback
        "master": {
            "specialties": ["general tasks", "multi-domain work"],
            "can_handle": ["any task as fallback"],
        },
    }

    def build_system_prompt(self, **kwargs: Any) -> str:
        """Build system prompt for query decomposition with agent capabilities."""
        available_agents = kwargs.get("available_agents", [])
        complexity = kwargs.get("complexity", "MEDIUM")

        if available_agents:
            # Build detailed agent capability text
            agent_details = []
            for agent in available_agents:
                if agent in self.AGENT_CAPABILITIES:
                    caps = self.AGENT_CAPABILITIES[agent]
                    specialties = ", ".join(caps["specialties"][:4])
                    agent_details.append(f"  - {agent}: {specialties}")
                else:
                    agent_details.append(f"  - {agent}: general capabilities")

            agents_text = f"""Available agents with capabilities:
{chr(10).join(agent_details)}

For each subgoal, specify TWO agents:
1. ideal_agent: The IDEAL agent for this task (any name, even if not available)
2. assigned_agent: The BEST AVAILABLE agent from the list above

MATCH QUALITY RULES:
- "excellent": Assign when task matches agent's SPECIALTIES
  Examples: @quality-assurance for testing, @system-architect for design
- "acceptable": Assign when agent CAN HANDLE the task but isn't specialized
  Examples: @code-developer for documentation, @market-researcher for basic research
- "insufficient": Assign when no agent is capable, using @master as fallback
  Examples: @master for creative writing, @master for video editing

Common ideal agents to consider (even if not available):
- creative-writer: story editing, narrative, creative writing
- data-analyst: data analysis, visualization, statistics, ML
- ux-designer: UI/UX design, wireframes, prototypes
- devops-engineer: CI/CD, infrastructure, deployment, monitoring
- security-expert: security audits, vulnerability analysis, compliance
- technical-writer: documentation, API docs, user guides"""
        else:
            agents_text = """No agents available.

For ideal_agent: specify the ideal agent name for the task (any domain)
For assigned_agent: use 'master' as fallback for all subgoals
For match_quality: use 'insufficient' when master is not ideal"""

        # Complexity-based subgoal limits and execution preferences
        # 2-4-6: progressive scaling, forces prioritization over sprawl
        SUBGOAL_LIMITS = {"MEDIUM": 2, "COMPLEX": 4, "CRITICAL": 6}
        EXEC_PREFERENCE = {
            "MEDIUM": "sequential - one subgoal builds on previous findings",
            "COMPLEX": "mixed - parallel for independent domains, sequential for dependent work",
            "CRITICAL": "parallel where possible - maximize agent utilization",
        }

        max_subgoals = SUBGOAL_LIMITS.get(complexity, 2)
        exec_pref = EXEC_PREFERENCE.get(complexity, "sequential")

        guidelines = f"""
COMPLEXITY: {complexity}
MAX SUBGOALS: {max_subgoals}
EXECUTION: Prefer {exec_pref}

RULES:
• Do not exceed {max_subgoals} subgoals
• Research queries (how/why/what): ONE comprehensive subgoal preferred
• Same-agent + no dependencies → merge into one subgoal
• Subgoals = independent work, not phases of same task
"""

        return f"""You are a query decomposition expert for a code reasoning system.

{guidelines}

Your task is to break down complex queries into concrete, actionable subgoals that can be
executed by specialized agents.

For each subgoal, specify:
1. A clear, specific goal statement (what needs to be done)
2. The IDEAL agent (unconstrained - what specialist SHOULD handle this)
3. A brief description of the ideal agent's capabilities
4. The ASSIGNED agent (from available list - best available match)
5. MATCH QUALITY - how well the assigned agent fits this task
6. Whether the subgoal is critical to the overall query
7. Dependencies on other subgoals (by index)
8. SOURCE FILE - match the subgoal to a relevant file path from the provided context

{agents_text}

You MUST respond with valid JSON only. Use this exact schema:
{{
  "goal": "High-level goal summarizing what we're trying to achieve",
  "subgoals": [
    {{
      "description": "Specific subgoal description",
      "ideal_agent": "agent-that-should-handle-this",
      "ideal_agent_desc": "Brief description of ideal agent capabilities",
      "assigned_agent": "best-available-agent",
      "match_quality": "excellent | acceptable | insufficient",
      "source_file": "path/to/relevant/file.py",  // REQUIRED: pick from "Available Source Files" section
      "is_critical": true/false,
      "depends_on": [0, 1]  // indices of prerequisite subgoals
    }}
  ],
  "execution_order": [
    {{
      "phase": 1,
      "parallelizable": [0, 1],  // subgoal indices that can run in parallel
      "sequential": [2]  // subgoals that must run after this phase
    }}
  ],
  "expected_tools": ["list", "of", "expected", "tool", "types"]
}}"""

    def build_user_prompt(self, **kwargs: Any) -> str:
        """Build user prompt for query decomposition.

        Args:
            query: The user query to decompose
            context_summary: Optional summary of retrieved context
            available_agents: Optional list of available agent names
            retry_feedback: Optional feedback from previous decomposition attempt

        Returns:
            User prompt string

        """
        query = kwargs.get("query", "")
        context_summary = kwargs.get("context_summary")
        available_agents = kwargs.get("available_agents", [])
        retry_feedback = kwargs.get("retry_feedback")

        prompt_parts = [f"Query: {query}"]

        if context_summary:
            prompt_parts.append(f"\nRelevant Context Summary:\n{context_summary}")

        if available_agents:
            prompt_parts.append(f"\nAvailable Agents: {', '.join(available_agents)}")

        if retry_feedback:
            prompt_parts.append(
                f"\n⚠️ Previous decomposition had issues. Feedback:\n{retry_feedback}\n"
                "Please revise your decomposition to address these concerns.",
            )

        prompt_parts.append("\nDecompose this query into actionable subgoals in JSON format.")

        return "\n".join(prompt_parts)

    def _format_single_example(self, example: dict[str, Any]) -> str:
        """Format a single example for query decomposition.

        Args:
            example: Dict with 'query' and 'decomposition' keys

        Returns:
            Formatted example string

        """
        decomposition = example.get("decomposition", {})
        return f"""Query: {example["query"]}

Decomposition: {json.dumps(decomposition, indent=2)}"""


__all__ = ["DecomposePromptTemplate"]
