"""Template rendering for Aurora Planning System.

This module provides Jinja2-based template rendering for generating
all 8 plan files from templates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

# Import from the correct location - Plan model is in aurora_cli.planning.models
try:
    from aurora_cli.planning.models import Plan
except ImportError:
    # Fallback for type checking
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from aurora_cli.planning.models import Plan  # type: ignore

__all__ = ["TemplateRenderer", "get_template_dir", "render_plan_files"]

logger = logging.getLogger(__name__)


def get_template_dir() -> Path:
    """Get the templates directory path.

    Returns:
        Path to templates directory

    """
    # Templates are in the package
    package_dir = Path(__file__).parent
    return package_dir / "templates"


class TemplateRenderer:
    """Template renderer using Jinja2."""

    def __init__(self, template_dir: Path | None = None):
        """Initialize renderer with template directory.

        Args:
            template_dir: Optional custom template directory (default: package templates)

        """
        self.template_dir = template_dir or get_template_dir()
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,  # Security: Enable autoescape for XSS protection
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        # Add custom filters
        self.env.filters["title"] = self._title_filter

    def _title_filter(self, value: str) -> str:
        """Custom title filter for plan names."""
        # Convert slug to title: "oauth-auth" -> "OAuth Auth"
        return value.replace("-", " ").title()

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with context.

        Args:
            template_name: Name of template file (e.g., "plan.md.j2")
            context: Template context dictionary

        Returns:
            Rendered template content

        Raises:
            FileNotFoundError: If template not found

        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error("Failed to render template %s: %s", template_name, e)
            raise

    def build_context(self, plan: Plan) -> dict[str, Any]:
        """Build template context from Plan object.

        Args:
            plan: Plan to build context from

        Returns:
            Template context dictionary

        """
        # Extract plan name from ID (e.g., "0001-oauth-auth" -> "oauth-auth")
        plan_name = plan.plan_id.split("-", 1)[1] if "-" in plan.plan_id else plan.plan_id

        # Build ISO 8601 timestamps for JSON
        created_iso = (
            plan.created_at.isoformat()
            if plan.created_at
            else datetime.now(timezone.utc).isoformat()
        )

        # Build subgoals with enhanced agent capability context
        subgoals_context = []
        for sg in plan.subgoals:
            # Detect gap: ideal_agent differs from assigned_agent
            ideal = getattr(sg, "ideal_agent", None) or sg.assigned_agent
            is_gap = ideal != sg.assigned_agent

            # Determine match quality based on gap detection
            # match_quality may be set by SOAR decomposition, default to "excellent"/"acceptable"
            match_quality = getattr(sg, "match_quality", None)
            if match_quality is None:
                match_quality = "acceptable" if is_gap else "excellent"

            subgoals_context.append(
                {
                    "id": sg.id,
                    "title": sg.title,
                    "description": sg.description,
                    "ideal_agent": ideal,
                    "ideal_agent_desc": getattr(sg, "ideal_agent_desc", "") or "",
                    "assigned_agent": sg.assigned_agent,
                    "match_quality": match_quality,
                    "is_gap": is_gap,
                    "dependencies": sg.dependencies,
                },
            )

        # Calculate agent statistics
        excellent_count = sum(1 for sg in subgoals_context if sg["match_quality"] == "excellent")
        acceptable_count = sum(1 for sg in subgoals_context if sg["match_quality"] == "acceptable")
        insufficient_count = sum(
            1 for sg in subgoals_context if sg["match_quality"] == "insufficient"
        )
        gap_count = sum(1 for sg in subgoals_context if sg["is_gap"])

        context = {
            # Basic plan info
            "plan_id": plan.plan_id,
            "plan_name": plan_name,
            "goal": plan.goal,
            "status": plan.status.value,
            "complexity": plan.complexity.value,
            "created_at": plan.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": created_iso,  # For agents.json template
            "tags": [],  # Empty tags list for now
            # Subgoals with enhanced context
            "subgoals": subgoals_context,
            # Agent capability statistics
            "agent_stats": {
                "excellent_count": excellent_count,
                "acceptable_count": acceptable_count,
                "insufficient_count": insufficient_count,
                "gap_count": gap_count,
                "total_subgoals": len(subgoals_context),
            },
            # Metadata
            "agent_gaps": plan.agent_gaps,
            "context_sources": plan.context_sources,
            "file_resolutions": plan.file_resolutions,
            # Optional fields
            "archived_at": (
                plan.archived_at.strftime("%Y-%m-%d %H:%M:%S") if plan.archived_at else None
            ),
            "duration_days": plan.duration_days,
            # Enhanced fields from decomposition (Task 6.0+)
            "decomposition_source": plan.decomposition_source,
            "context_summary": plan.context_summary,
            # Computed fields for templates
            "subgoal_count": len(plan.subgoals),
            "has_dependencies": any(sg.dependencies for sg in plan.subgoals),
            "has_agent_gaps": gap_count > 0,
            "has_insufficient_agents": insufficient_count > 0,
            "cross_team_dependencies": 0,  # Placeholder for future enhancement
        }

        return context


def render_plan_files(
    plan: Plan,
    output_dir: Path,
    template_dir: Path | None = None,
) -> list[Path]:
    """Render all plan files from templates.

    Generates 4 base files:
    - plan.md: Overview and subgoal breakdown
    - prd.md: Product requirements document
    - tasks.md: Implementation task list
    - agents.json: Machine-readable plan data

    Args:
        plan: Plan to render
        output_dir: Directory to write files to
        template_dir: Optional custom template directory

    Returns:
        List of created file paths

    Raises:
        OSError: If file write fails

    """
    renderer = TemplateRenderer(template_dir)
    context = renderer.build_context(plan)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define base files to generate
    file_templates = [
        ("plan.md.j2", "plan.md"),
        ("prd.md.j2", "prd.md"),
        ("tasks.md.j2", "tasks.md"),
        ("agents.json.j2", "agents.json"),
    ]

    created_files = []

    for template_name, output_name in file_templates:
        try:
            # Render template
            content = renderer.render(template_name, context)

            # Write file
            output_path = output_dir / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent exists
            output_path.write_text(content, encoding="utf-8")

            # Set permissions
            output_path.chmod(0o644)

            created_files.append(output_path)
            logger.debug("Created file: %s", output_path)

        except Exception as e:
            logger.error("Failed to render %s: %s", template_name, e)
            # Clean up partial files on error
            for created in created_files:
                if created.exists():
                    created.unlink()
            raise

    return created_files
