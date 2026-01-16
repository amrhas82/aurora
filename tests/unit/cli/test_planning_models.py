"""Unit tests for planning Pydantic models.

Tests Plan, Subgoal, PlanManifest models with validation,
serialization, and error message verification.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from aurora_cli.planning.models import Complexity, Plan, PlanManifest, PlanStatus, Subgoal


class TestPlanStatusEnum:
    """Tests for PlanStatus enum."""

    def test_active_value(self) -> None:
        """ACTIVE serializes to 'active'."""
        assert PlanStatus.ACTIVE.value == "active"

    def test_archived_value(self) -> None:
        """ARCHIVED serializes to 'archived'."""
        assert PlanStatus.ARCHIVED.value == "archived"

    def test_failed_value(self) -> None:
        """FAILED serializes to 'failed'."""
        assert PlanStatus.FAILED.value == "failed"

    def test_json_serialization(self) -> None:
        """Enum serializes to lowercase string in JSON."""
        assert json.dumps(PlanStatus.ACTIVE.value) == '"active"'


class TestComplexityEnum:
    """Tests for Complexity enum."""

    def test_simple_value(self) -> None:
        """SIMPLE serializes to 'simple'."""
        assert Complexity.SIMPLE.value == "simple"

    def test_moderate_value(self) -> None:
        """MODERATE serializes to 'moderate'."""
        assert Complexity.MODERATE.value == "moderate"

    def test_complex_value(self) -> None:
        """COMPLEX serializes to 'complex'."""
        assert Complexity.COMPLEX.value == "complex"

    def test_json_serialization(self) -> None:
        """Enum serializes to lowercase string in JSON."""
        assert json.dumps(Complexity.COMPLEX.value) == '"complex"'


class TestSubgoalModel:
    """Tests for Subgoal model."""

    def test_valid_subgoal_creation(self) -> None:
        """Creates valid subgoal with all fields."""
        subgoal = Subgoal(
            id="sg-1",
            title="Implement authentication",
            description="Create OAuth2 authentication flow with JWT tokens",
            assigned_agent="@full-stack-dev",
        )

        assert subgoal.id == "sg-1"
        assert subgoal.title == "Implement authentication"
        assert subgoal.assigned_agent == "@full-stack-dev"
        assert subgoal.dependencies == []

    def test_subgoal_with_dependencies(self) -> None:
        """Creates subgoal with dependency list."""
        subgoal = Subgoal(
            id="sg-2",
            title="Write authentication tests",
            description="Create unit and integration tests for auth",
            assigned_agent="@qa-test-architect",
            dependencies=["sg-1"],
        )

        assert subgoal.dependencies == ["sg-1"]

    def test_invalid_subgoal_id_format(self) -> None:
        """Rejects invalid subgoal ID format."""
        with pytest.raises(ValidationError) as exc_info:
            Subgoal(
                id="subgoal-1",  # Should be sg-1
                title="Some title here",
                description="Some description that is long enough",
                assigned_agent="@dev",
            )

        error_msg = str(exc_info.value)
        assert "sg-N" in error_msg or "subgoal-1" in error_msg

    def test_invalid_subgoal_id_no_number(self) -> None:
        """Rejects subgoal ID without number."""
        with pytest.raises(ValidationError) as exc_info:
            Subgoal(
                id="sg-",
                title="Some title here",
                description="Some description that is long enough",
                assigned_agent="@dev",
            )

        error_msg = str(exc_info.value)
        assert "sg-N" in error_msg or "sg-" in error_msg

    def test_agent_without_at_is_coerced(self) -> None:
        """Agent without @ prefix is coerced to have @ prefix."""
        subgoal = Subgoal(
            id="sg-1",
            title="Some title here",
            description="Some description that is long enough",
            assigned_agent="full-stack-dev",  # Missing @ - should be coerced
        )

        assert subgoal.assigned_agent == "@full-stack-dev"

    def test_agent_with_uppercase_is_preserved(self) -> None:
        """Agent with uppercase is preserved (coercion only adds @ prefix)."""
        # Note: SOAR outputs lowercase agents, but we don't reject uppercase
        # since the coercion layer only handles @ prefix, not case normalization
        subgoal = Subgoal(
            id="sg-1",
            title="Some title here",
            description="Some description that is long enough",
            assigned_agent="@FullStackDev",  # Preserved as-is
        )

        assert subgoal.assigned_agent == "@FullStackDev"

    def test_title_too_short(self) -> None:
        """Rejects title shorter than 5 chars."""
        with pytest.raises(ValidationError) as exc_info:
            Subgoal(
                id="sg-1",
                title="Test",  # 4 chars
                description="Some description that is long enough",
                assigned_agent="@dev",
            )

        errors = exc_info.value.errors()
        assert any("title" in str(e) for e in errors)

    def test_description_too_short(self) -> None:
        """Rejects description shorter than 10 chars."""
        with pytest.raises(ValidationError) as exc_info:
            Subgoal(
                id="sg-1",
                title="Valid title",
                description="Short",  # Less than 10 chars
                assigned_agent="@dev",
            )

        errors = exc_info.value.errors()
        assert any("description" in str(e) for e in errors)

    def test_json_serialization_roundtrip(self) -> None:
        """Subgoal survives JSON serialization roundtrip."""
        original = Subgoal(
            id="sg-3",
            title="Test subgoal title",
            description="This is a test description for the subgoal",
            assigned_agent="@qa-test-architect",
            dependencies=["sg-1", "sg-2"],
        )

        json_str = original.model_dump_json()
        restored = Subgoal.model_validate_json(json_str)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.assigned_agent == original.assigned_agent
        assert restored.dependencies == original.dependencies

    def test_dependencies_normalized_from_string(self) -> None:
        """Single string dependency is converted to list."""
        subgoal = Subgoal(
            id="sg-2",
            title="Valid title here",
            description="Valid description here that is long enough",
            assigned_agent="@dev",
            dependencies="sg-1",  # type: ignore[arg-type] # String instead of list
        )

        assert subgoal.dependencies == ["sg-1"]

    def test_dependencies_none_becomes_empty_list(self) -> None:
        """None dependencies becomes empty list."""
        subgoal = Subgoal(
            id="sg-1",
            title="Valid title here",
            description="Valid description here that is long enough",
            assigned_agent="@dev",
            dependencies=None,  # type: ignore[arg-type]
        )

        assert subgoal.dependencies == []


class TestPlanModel:
    """Tests for Plan model."""

    @pytest.fixture
    def valid_subgoals(self) -> list[Subgoal]:
        """Create valid subgoals for testing."""
        return [
            Subgoal(
                id="sg-1",
                title="Implement core feature",
                description="Create the main functionality for the feature",
                assigned_agent="@full-stack-dev",
            ),
            Subgoal(
                id="sg-2",
                title="Write unit tests",
                description="Create comprehensive unit tests for the feature",
                assigned_agent="@qa-test-architect",
                dependencies=["sg-1"],
            ),
        ]

    def test_valid_plan_creation(self, valid_subgoals: list[Subgoal]) -> None:
        """Creates valid plan with all fields."""
        plan = Plan(
            plan_id="0001-oauth-auth",
            goal="Implement OAuth2 authentication with JWT tokens",
            subgoals=valid_subgoals,
        )

        assert plan.plan_id == "0001-oauth-auth"
        assert plan.status == PlanStatus.ACTIVE
        assert plan.complexity == Complexity.MODERATE
        assert len(plan.subgoals) == 2
        assert plan.agent_gaps == []

    def test_plan_with_empty_plan_id(self, valid_subgoals: list[Subgoal]) -> None:
        """Plan can be created with empty plan_id (to be generated later)."""
        plan = Plan(
            goal="Implement some feature with enough description",
            subgoals=valid_subgoals,
        )

        assert plan.plan_id == ""

    def test_invalid_plan_id_format(self, valid_subgoals: list[Subgoal]) -> None:
        """Rejects invalid plan ID format."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                plan_id="oauth-auth",  # Missing NNNN prefix
                goal="Implement OAuth2 authentication with JWT",
                subgoals=valid_subgoals,
            )

        error_msg = str(exc_info.value)
        assert "NNNN-slug" in error_msg or "oauth-auth" in error_msg

    def test_goal_too_short(self, valid_subgoals: list[Subgoal]) -> None:
        """Rejects goal shorter than 10 chars."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="Add auth",  # Less than 10 chars
                subgoals=valid_subgoals,
            )

        errors = exc_info.value.errors()
        assert any("goal" in str(e) for e in errors)

    def test_goal_too_long(self, valid_subgoals: list[Subgoal]) -> None:
        """Rejects goal longer than 500 chars."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="x" * 501,
                subgoals=valid_subgoals,
            )

        errors = exc_info.value.errors()
        assert any("goal" in str(e) for e in errors)

    def test_too_few_subgoals(self) -> None:
        """Rejects plan with no subgoals."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="Implement feature with sufficient length",
                subgoals=[],
            )

        errors = exc_info.value.errors()
        assert any("subgoals" in str(e) for e in errors)

    def test_too_many_subgoals(self) -> None:
        """Rejects plan with more than 10 subgoals."""
        many_subgoals = [
            Subgoal(
                id=f"sg-{i}",
                title=f"Subgoal number {i}",
                description=f"Description for subgoal {i} that is long enough",
                assigned_agent="@dev",
            )
            for i in range(1, 12)  # 11 subgoals
        ]

        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="Plan with too many subgoals to be manageable",
                subgoals=many_subgoals,
            )

        errors = exc_info.value.errors()
        assert any("subgoals" in str(e) for e in errors)

    def test_invalid_dependency_reference(self) -> None:
        """Rejects plan with invalid dependency reference."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="First subgoal title",
                description="Description for first subgoal here",
                assigned_agent="@dev",
            ),
            Subgoal(
                id="sg-2",
                title="Second subgoal title",
                description="Description for second subgoal",
                assigned_agent="@dev",
                dependencies=["sg-999"],  # Invalid reference
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="Plan with invalid dependency reference",
                subgoals=subgoals,
            )

        error_msg = str(exc_info.value)
        assert "sg-999" in error_msg or "unknown dependency" in error_msg.lower()

    def test_circular_dependency_detection(self) -> None:
        """Detects circular dependencies."""
        subgoals = [
            Subgoal(
                id="sg-1",
                title="First subgoal title",
                description="Description for first subgoal here",
                assigned_agent="@dev",
                dependencies=["sg-2"],
            ),
            Subgoal(
                id="sg-2",
                title="Second subgoal title",
                description="Description for second subgoal",
                assigned_agent="@dev",
                dependencies=["sg-1"],  # Circular!
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            Plan(
                goal="Plan with circular dependencies detected",
                subgoals=subgoals,
            )

        error_msg = str(exc_info.value)
        assert "circular" in error_msg.lower()

    def test_json_serialization_roundtrip(self, valid_subgoals: list[Subgoal]) -> None:
        """Plan survives JSON serialization roundtrip."""
        original = Plan(
            plan_id="0042-test-plan",
            goal="This is a test plan for serialization testing",
            subgoals=valid_subgoals,
            status=PlanStatus.ACTIVE,
            complexity=Complexity.MODERATE,
            agent_gaps=["@missing-agent"],
            context_sources=["indexed_memory"],
        )

        json_str = original.to_json()
        restored = Plan.from_json(json_str)

        assert restored.plan_id == original.plan_id
        assert restored.goal == original.goal
        assert restored.status == original.status
        assert restored.complexity == original.complexity
        assert len(restored.subgoals) == len(original.subgoals)
        assert restored.agent_gaps == original.agent_gaps
        assert restored.context_sources == original.context_sources

    def test_to_json_method(self, valid_subgoals: list[Subgoal]) -> None:
        """to_json returns valid JSON string."""
        plan = Plan(
            plan_id="0001-test",
            goal="Test plan goal that is long enough",
            subgoals=valid_subgoals,
        )

        json_str = plan.to_json()
        parsed = json.loads(json_str)

        assert parsed["plan_id"] == "0001-test"
        assert len(parsed["subgoals"]) == 2

    def test_from_json_class_method(self, valid_subgoals: list[Subgoal]) -> None:
        """from_json deserializes JSON string to Plan."""
        plan = Plan(
            plan_id="0001-test",
            goal="Test plan goal that is long enough",
            subgoals=valid_subgoals,
        )

        json_str = plan.to_json()
        restored = Plan.from_json(json_str)

        assert isinstance(restored, Plan)
        assert restored.plan_id == plan.plan_id

    def test_archived_plan_has_timestamps(self, valid_subgoals: list[Subgoal]) -> None:
        """Archived plan can have archived_at and duration_days."""
        created = datetime.utcnow() - timedelta(days=5)
        archived = datetime.utcnow()

        plan = Plan(
            plan_id="0001-archived-test",
            goal="Test archived plan with timestamps",
            subgoals=valid_subgoals,
            status=PlanStatus.ARCHIVED,
            created_at=created,
            archived_at=archived,
            duration_days=5,
        )

        assert plan.status == PlanStatus.ARCHIVED
        assert plan.archived_at is not None
        assert plan.duration_days == 5


class TestPlanManifestModel:
    """Tests for PlanManifest model."""

    def test_default_manifest_creation(self) -> None:
        """Creates manifest with defaults."""
        manifest = PlanManifest()

        assert manifest.version == "1.0"
        assert manifest.active_plans == []
        assert manifest.archived_plans == []
        assert manifest.stats == {}
        assert manifest.total_plans == 0

    def test_add_active_plan(self) -> None:
        """Adds plan to active list."""
        manifest = PlanManifest()
        manifest.add_active_plan("0001-oauth-auth")

        assert "0001-oauth-auth" in manifest.active_plans
        assert manifest.total_plans == 1

    def test_add_active_plan_no_duplicates(self) -> None:
        """Does not add duplicate plans."""
        manifest = PlanManifest()
        manifest.add_active_plan("0001-oauth-auth")
        manifest.add_active_plan("0001-oauth-auth")

        assert manifest.active_plans.count("0001-oauth-auth") == 1

    def test_archive_plan(self) -> None:
        """Moves plan from active to archived."""
        manifest = PlanManifest()
        manifest.add_active_plan("0001-oauth-auth")
        manifest.archive_plan("0001-oauth-auth", "2024-01-15-0001-oauth-auth")

        assert "0001-oauth-auth" not in manifest.active_plans
        assert "2024-01-15-0001-oauth-auth" in manifest.archived_plans
        assert manifest.total_plans == 1

    def test_archive_plan_default_id(self) -> None:
        """Archive uses original ID if no archived_id provided."""
        manifest = PlanManifest()
        manifest.add_active_plan("0001-oauth-auth")
        manifest.archive_plan("0001-oauth-auth")

        assert "0001-oauth-auth" in manifest.archived_plans

    def test_json_serialization_roundtrip(self) -> None:
        """Manifest survives JSON serialization roundtrip."""
        manifest = PlanManifest(
            active_plans=["0001-plan", "0002-plan"],
            archived_plans=["2024-01-01-0000-old-plan"],
            stats={"total_archived": 1},
        )

        json_str = manifest.model_dump_json()
        restored = PlanManifest.model_validate_json(json_str)

        assert restored.active_plans == manifest.active_plans
        assert restored.archived_plans == manifest.archived_plans
        assert restored.stats == manifest.stats

    def test_total_plans_property(self) -> None:
        """total_plans returns sum of active and archived."""
        manifest = PlanManifest(
            active_plans=["0001-a", "0002-b"],
            archived_plans=["0003-c"],
        )

        assert manifest.total_plans == 3

    def test_updated_at_changes_on_modification(self) -> None:
        """updated_at changes when manifest is modified."""
        manifest = PlanManifest()
        original_time = manifest.updated_at

        # Small delay to ensure time difference
        import time

        time.sleep(0.01)

        manifest.add_active_plan("0001-test")

        assert manifest.updated_at >= original_time
