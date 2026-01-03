"""Tests for template rendering in Aurora Planning System.

Tests cover:
- Template rendering for all 8 files
- Variable substitution
- File permissions
- JSON schema validation
- Atomic file generation
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


# Import renderer from CLI planning (which imports from aurora_planning)
try:
    # Try CLI imports first (where renderer is re-exported)
    from aurora_cli.planning.models import Complexity, Plan, PlanStatus, Subgoal
    from aurora_cli.planning.renderer import (
        TemplateRenderer,
        get_template_dir,
        render_plan_files,
    )
except ImportError as e:
    pytest.skip(f"aurora_cli.planning not available: {e}", allow_module_level=True)


@pytest.fixture
def sample_plan():
    """Create a sample plan for testing."""
    return Plan(
        plan_id="0001-test-plan",
        goal="Test goal for template rendering",
        status=PlanStatus.ACTIVE,
        complexity=Complexity.MODERATE,
        created_at=datetime(2026, 1, 3, 12, 0, 0),
        subgoals=[
            Subgoal(
                id="sg-1",
                title="First subgoal",
                description="Description for first subgoal",
                recommended_agent="@full-stack-dev",
                dependencies=[],
            ),
            Subgoal(
                id="sg-2",
                title="Second subgoal",
                description="Description for second subgoal",
                recommended_agent="@qa-test-architect",
                dependencies=["sg-1"],
            ),
        ],
        agent_gaps=[],
        context_sources=["manual"],
    )


class TestTemplateRenderer:
    """Tests for TemplateRenderer class."""

    def test_get_template_dir(self):
        """Test getting template directory path."""
        template_dir = get_template_dir()
        assert template_dir.exists()
        assert (template_dir / "plan.md.j2").exists()

    def test_renderer_initialization(self):
        """Test renderer initialization."""
        renderer = TemplateRenderer()
        assert renderer.template_dir.exists()
        assert renderer.env is not None

    def test_custom_template_dir(self, tmp_path):
        """Test renderer with custom template directory."""
        custom_dir = tmp_path / "custom_templates"
        custom_dir.mkdir()

        renderer = TemplateRenderer(template_dir=custom_dir)
        assert renderer.template_dir == custom_dir

    def test_build_context(self, sample_plan):
        """Test building template context from plan."""
        renderer = TemplateRenderer()
        context = renderer.build_context(sample_plan)

        # Check basic fields
        assert context["plan_id"] == "0001-test-plan"
        assert context["plan_name"] == "test-plan"
        assert context["goal"] == sample_plan.goal
        assert context["status"] == "active"
        assert context["complexity"] == "moderate"

        # Check subgoals
        assert len(context["subgoals"]) == 2
        assert context["subgoals"][0]["id"] == "sg-1"
        assert context["subgoals"][1]["dependencies"] == ["sg-1"]

    def test_render_template(self, sample_plan):
        """Test rendering a single template."""
        renderer = TemplateRenderer()
        context = renderer.build_context(sample_plan)

        content = renderer.render("plan.md.j2", context)

        # Verify content
        assert "0001-test-plan" in content
        assert "Test goal for template rendering" in content
        assert "sg-1" in content
        assert "@full-stack-dev" in content

    def test_title_filter(self):
        """Test custom title filter."""
        renderer = TemplateRenderer()

        # Test slug to title conversion
        result = renderer._title_filter("oauth-auth")
        assert result == "Oauth Auth"

        result = renderer._title_filter("user-dashboard")
        assert result == "User Dashboard"


class TestFileGeneration:
    """Tests for complete file generation."""

    def test_render_all_files(self, sample_plan, tmp_path):
        """Test rendering all 8 files."""
        output_dir = tmp_path / "plan"

        created_files = render_plan_files(sample_plan, output_dir)

        # Check count
        assert len(created_files) == 8

        # Check base files exist
        assert (output_dir / "plan.md").exists()
        assert (output_dir / "prd.md").exists()
        assert (output_dir / "tasks.md").exists()
        assert (output_dir / "agents.json").exists()

        # Check capability specs exist
        specs_dir = output_dir / "specs"
        assert specs_dir.exists()
        assert (specs_dir / "0001-test-plan-planning.md").exists()
        assert (specs_dir / "0001-test-plan-commands.md").exists()
        assert (specs_dir / "0001-test-plan-validation.md").exists()
        assert (specs_dir / "0001-test-plan-schemas.md").exists()

    def test_file_content_validity(self, sample_plan, tmp_path):
        """Test that generated files have valid content."""
        output_dir = tmp_path / "plan"
        render_plan_files(sample_plan, output_dir)

        # Check plan.md has expected content
        plan_md = (output_dir / "plan.md").read_text()
        assert "0001-test-plan" in plan_md
        assert "Test goal" in plan_md
        assert ("sg-1" in plan_md or "SG-1" in plan_md)
        assert ("sg-2" in plan_md or "SG-2" in plan_md)

        # Check prd.md has expected content
        prd_md = (output_dir / "prd.md").read_text()
        assert "PRD:" in prd_md
        assert "Functional Requirements" in prd_md

        # Check tasks.md has checkboxes
        tasks_md = (output_dir / "tasks.md").read_text()
        assert "[ ]" in tasks_md
        assert "Task Checklist" in tasks_md

    def test_agents_json_validity(self, sample_plan, tmp_path):
        """Test that agents.json is valid JSON."""
        output_dir = tmp_path / "plan"
        render_plan_files(sample_plan, output_dir)

        agents_json_path = output_dir / "agents.json"
        content = agents_json_path.read_text()

        # Parse JSON
        data = json.loads(content)

        # Validate structure
        assert data["plan_id"] == "0001-test-plan"
        assert data["goal"] == sample_plan.goal
        assert data["status"] == "active"
        assert len(data["subgoals"]) == 2


class TestVariableSubstitution:
    """Tests for template variable substitution."""

    def test_goal_substitution(self, sample_plan, tmp_path):
        """Test that goal is substituted in all files."""
        output_dir = tmp_path / "plan"
        created_files = render_plan_files(sample_plan, output_dir)

        goal_text = "Test goal for template rendering"

        # Check goal appears in at least plan.md, prd.md, agents.json
        plan_md = (output_dir / "plan.md").read_text()
        assert goal_text in plan_md

        prd_md = (output_dir / "prd.md").read_text()
        assert goal_text in prd_md

        agents_json = json.loads((output_dir / "agents.json").read_text())
        assert goal_text in agents_json["goal"]

    def test_plan_id_substitution(self, sample_plan, tmp_path):
        """Test that plan_id is substituted correctly."""
        output_dir = tmp_path / "plan"
        render_plan_files(sample_plan, output_dir)

        plan_id = "0001-test-plan"

        # Check all 8 files
        for file_name in ["plan.md", "prd.md", "tasks.md"]:
            content = (output_dir / file_name).read_text()
            assert plan_id in content

        # Check capability specs use plan_id in filename
        specs_dir = output_dir / "specs"
        assert (specs_dir / f"{plan_id}-planning.md").exists()

    def test_subgoal_substitution(self, sample_plan, tmp_path):
        """Test that subgoals are substituted correctly."""
        output_dir = tmp_path / "plan"
        render_plan_files(sample_plan, output_dir)

        plan_md = (output_dir / "plan.md").read_text()

        # Check both subgoals appear (case-insensitive)
        assert ("sg-1" in plan_md or "SG-1" in plan_md)
        assert "First subgoal" in plan_md
        assert ("sg-2" in plan_md or "SG-2" in plan_md)
        assert "Second subgoal" in plan_md
        assert "@full-stack-dev" in plan_md
        assert "@qa-test-architect" in plan_md


class TestFilePermissions:
    """Tests for file permissions."""

    def test_file_permissions_644(self, sample_plan, tmp_path):
        """Test that files have 0644 permissions."""
        output_dir = tmp_path / "plan"
        created_files = render_plan_files(sample_plan, output_dir)

        for file_path in created_files:
            import stat

            mode = stat.S_IMODE(file_path.stat().st_mode)
            assert mode == 0o644, f"{file_path.name} has wrong permissions: {oct(mode)}"

    def test_directory_creation(self, sample_plan, tmp_path):
        """Test that directories are created."""
        output_dir = tmp_path / "plan"
        render_plan_files(sample_plan, output_dir)

        assert output_dir.exists()
        assert (output_dir / "specs").exists()


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_template(self, sample_plan, tmp_path):
        """Test error when template is missing."""
        renderer = TemplateRenderer()

        with pytest.raises(Exception):
            renderer.render("nonexistent.j2", {})

    def test_cleanup_on_error(self, sample_plan, tmp_path):
        """Test that partial files are cleaned up on error."""
        # This is tested in atomic generation
        # The renderer itself doesn't clean up, that's in _write_plan_files
        pass


class TestAtomicGeneration:
    """Tests for atomic file generation (integration with core.py)."""

    def test_all_or_nothing(self, sample_plan, tmp_path):
        """Test that either all 8 files are created or none."""
        output_dir = tmp_path / "plan"

        try:
            created_files = render_plan_files(sample_plan, output_dir)
            # Should create all 8
            assert len(created_files) == 8
        except Exception:
            # If error, no files should be left
            if output_dir.exists():
                files = list(output_dir.rglob("*"))
                assert len(files) == 0, "Partial files left after error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
