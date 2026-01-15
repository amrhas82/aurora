"""Contract tests for aurora_planning package.

These tests verify that the Plan and Modification schema contracts are honored.
Contract tests ensure:
- Input validation (required fields, constraints)
- Output shape and type guarantees
- Schema backward compatibility
- Error handling consistency
"""

import pytest
from pydantic import ValidationError

from aurora_planning.schemas.base import Requirement, Scenario
from aurora_planning.schemas.plan import (
    Modification,
    ModificationOperation,
    Plan,
    PlanMetadata,
    RenameInfo,
)


class TestPlanSchemaContract:
    """Contract tests for Plan schema validation."""

    def test_plan_requires_all_mandatory_fields(self):
        """Contract: Plan must require name, why, what_changes, and modifications."""
        # Missing all fields
        with pytest.raises(ValidationError) as exc_info:
            Plan()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert "name" in required_fields
        assert "why" in required_fields
        assert "what_changes" in required_fields
        assert "modifications" in required_fields

    def test_plan_name_cannot_be_empty(self):
        """Contract: Plan name must not be empty string."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="",
                why="Because we need to test this feature properly and ensure quality.",
                what_changes="Add new feature",
                modifications=[
                    Modification(
                        capability="test-feature",
                        operation=ModificationOperation.ADDED,
                        description="New test feature",
                    )
                ],
            )

        assert any("name" in str(error).lower() for error in exc_info.value.errors())

    def test_plan_name_whitespace_only_is_invalid(self):
        """Contract: Plan name with only whitespace is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="   ",
                why="Because we need to test this feature properly and ensure quality.",
                what_changes="Add new feature",
                modifications=[
                    Modification(
                        capability="test-feature",
                        operation=ModificationOperation.ADDED,
                        description="New test feature",
                    )
                ],
            )

        assert any("name" in str(error).lower() for error in exc_info.value.errors())

    def test_plan_why_has_minimum_length(self):
        """Contract: Plan why section must meet minimum length (50 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="Test Plan",
                why="Too short",  # Less than 50 characters
                what_changes="Add new feature",
                modifications=[
                    Modification(
                        capability="test-feature",
                        operation=ModificationOperation.ADDED,
                        description="New test feature",
                    )
                ],
            )

        assert any("why" in str(error).lower() for error in exc_info.value.errors())

    def test_plan_why_has_maximum_length(self):
        """Contract: Plan why section must not exceed maximum length (1000 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="Test Plan",
                why="x" * 1001,  # Exceeds 1000 characters
                what_changes="Add new feature",
                modifications=[
                    Modification(
                        capability="test-feature",
                        operation=ModificationOperation.ADDED,
                        description="New test feature",
                    )
                ],
            )

        assert any("why" in str(error).lower() for error in exc_info.value.errors())

    def test_plan_requires_at_least_one_modification(self):
        """Contract: Plan must have at least one modification."""
        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="Test Plan",
                why="Because we need to test this feature properly and ensure quality.",
                what_changes="Add new feature",
                modifications=[],  # Empty list
            )

        assert any("modification" in str(error).lower() for error in exc_info.value.errors())

    def test_plan_respects_max_modifications_limit(self):
        """Contract: Plan must not exceed max modifications limit (100)."""
        # Create 101 modifications
        too_many_mods = [
            Modification(
                capability=f"feature-{i}",
                operation=ModificationOperation.ADDED,
                description=f"Feature {i}",
            )
            for i in range(101)
        ]

        with pytest.raises(ValidationError) as exc_info:
            Plan(
                name="Test Plan",
                why="Because we need to test this feature properly and ensure quality.",
                what_changes="Add many features",
                modifications=too_many_mods,
            )

        assert any("modification" in str(error).lower() for error in exc_info.value.errors())

    def test_valid_plan_accepts_all_fields(self):
        """Contract: Valid Plan with all fields should be accepted."""
        plan = Plan(
            name="Test Plan",
            why="Because we need to test this feature properly to ensure quality",
            what_changes="Add new feature with proper validation",
            modifications=[
                Modification(
                    capability="test-feature",
                    operation=ModificationOperation.ADDED,
                    description="New test feature with validation",
                )
            ],
            metadata=PlanMetadata(
                version="1.0.0", format="aurora-plan", source_path="/path/to/plan.json"
            ),
        )

        assert plan.name == "Test Plan"
        assert len(plan.modifications) == 1
        assert plan.metadata is not None
        assert plan.metadata.version == "1.0.0"


class TestModificationSchemaContract:
    """Contract tests for Modification schema validation."""

    def test_modification_requires_all_mandatory_fields(self):
        """Contract: Modification must require capability, operation, and description."""
        with pytest.raises(ValidationError) as exc_info:
            Modification()

        errors = exc_info.value.errors()
        required_fields = {error["loc"][0] for error in errors if error["type"] == "missing"}
        assert "capability" in required_fields
        assert "operation" in required_fields
        assert "description" in required_fields

    def test_modification_capability_cannot_be_empty(self):
        """Contract: Modification capability must not be empty."""
        with pytest.raises(ValidationError) as exc_info:
            Modification(
                capability="",
                operation=ModificationOperation.ADDED,
                description="Test modification",
            )

        assert any("capability" in str(error).lower() for error in exc_info.value.errors())

    def test_modification_description_cannot_be_empty(self):
        """Contract: Modification description must not be empty."""
        with pytest.raises(ValidationError) as exc_info:
            Modification(
                capability="test-feature", operation=ModificationOperation.ADDED, description=""
            )

        assert any("description" in str(error).lower() for error in exc_info.value.errors())

    def test_modification_operation_must_be_valid_enum(self):
        """Contract: Modification operation must be a valid ModificationOperation."""
        with pytest.raises(ValidationError) as exc_info:
            Modification(
                capability="test-feature",
                operation="INVALID_OPERATION",  # Not a valid enum value
                description="Test modification",
            )

        assert any("operation" in str(error).lower() for error in exc_info.value.errors())

    def test_valid_modification_all_operations(self):
        """Contract: Valid Modification with each operation type should be accepted."""
        operations = [
            ModificationOperation.ADDED,
            ModificationOperation.MODIFIED,
            ModificationOperation.REMOVED,
            ModificationOperation.RENAMED,
        ]

        for op in operations:
            mod = Modification(
                capability="test-feature", operation=op, description="Test modification"
            )
            assert mod.operation == op
            assert mod.capability == "test-feature"
            assert mod.description == "Test modification"

    def test_modification_accepts_optional_requirement(self):
        """Contract: Modification can have optional requirement field."""
        req = Requirement(text="The system SHALL implement test feature")
        mod = Modification(
            capability="test-feature",
            operation=ModificationOperation.ADDED,
            description="Test modification",
            requirement=req,
        )

        assert mod.requirement is not None
        assert "SHALL" in mod.requirement.text

    def test_modification_accepts_optional_requirements_list(self):
        """Contract: Modification can have optional requirements list."""
        reqs = [
            Requirement(text="The system SHALL implement requirement 1"),
            Requirement(text="The system MUST implement requirement 2"),
        ]
        mod = Modification(
            capability="test-feature",
            operation=ModificationOperation.ADDED,
            description="Test modification",
            requirements=reqs,
        )

        assert mod.requirements is not None
        assert len(mod.requirements) == 2
        assert "SHALL" in mod.requirements[0].text
        assert "MUST" in mod.requirements[1].text

    def test_modification_renamed_operation_with_rename_info(self):
        """Contract: RENAMED operation can include rename information."""
        rename_info = RenameInfo(from_name="old-feature", to_name="new-feature")
        mod = Modification(
            capability="test-feature",
            operation=ModificationOperation.RENAMED,
            description="Rename feature",
            rename=rename_info,
        )

        assert mod.rename is not None
        assert mod.rename.from_name == "old-feature"
        assert mod.rename.to_name == "new-feature"


class TestRenameInfoSchemaContract:
    """Contract tests for RenameInfo schema."""

    def test_rename_info_requires_both_fields(self):
        """Contract: RenameInfo must require both from_name and to_name."""
        with pytest.raises(ValidationError):
            RenameInfo()

    def test_rename_info_accepts_alias_from(self):
        """Contract: RenameInfo accepts 'from' as alias for from_name."""
        # Using dictionary to pass alias
        rename_dict = {"from": "old-name", "to": "new-name"}
        rename = RenameInfo.model_validate(rename_dict)

        assert rename.from_name == "old-name"
        assert rename.to_name == "new-name"

    def test_rename_info_accepts_alias_to(self):
        """Contract: RenameInfo accepts 'to' as alias for to_name."""
        rename_dict = {"from": "old-name", "to": "new-name"}
        rename = RenameInfo.model_validate(rename_dict)

        assert rename.from_name == "old-name"
        assert rename.to_name == "new-name"


class TestPlanMetadataSchemaContract:
    """Contract tests for PlanMetadata schema."""

    def test_plan_metadata_has_default_values(self):
        """Contract: PlanMetadata provides default values for version and format."""
        metadata = PlanMetadata()

        assert metadata.version == "1.0.0"
        assert metadata.format == "aurora-plan"
        assert metadata.source_path is None

    def test_plan_metadata_accepts_custom_values(self):
        """Contract: PlanMetadata accepts custom values."""
        metadata = PlanMetadata(
            version="2.0.0", format="custom-format", source_path="/path/to/source.json"
        )

        assert metadata.version == "2.0.0"
        assert metadata.format == "custom-format"
        assert metadata.source_path == "/path/to/source.json"


class TestSchemaSerializationContract:
    """Contract tests for schema serialization and deserialization."""

    def test_plan_can_be_serialized_to_dict(self):
        """Contract: Plan can be serialized to dictionary."""
        plan = Plan(
            name="Test Plan",
            why="Because we need to test this feature properly and ensure quality.",
            what_changes="Add new feature",
            modifications=[
                Modification(
                    capability="test-feature",
                    operation=ModificationOperation.ADDED,
                    description="New test feature",
                )
            ],
        )

        plan_dict = plan.model_dump()

        assert isinstance(plan_dict, dict)
        assert plan_dict["name"] == "Test Plan"
        assert len(plan_dict["modifications"]) == 1
        assert plan_dict["modifications"][0]["capability"] == "test-feature"

    def test_plan_can_be_deserialized_from_dict(self):
        """Contract: Plan can be created from valid dictionary."""
        plan_dict = {
            "name": "Test Plan",
            "why": "Because we need to test this feature properly and ensure quality.",
            "what_changes": "Add new feature",
            "modifications": [
                {
                    "capability": "test-feature",
                    "operation": "ADDED",
                    "description": "New test feature",
                }
            ],
        }

        plan = Plan.model_validate(plan_dict)

        assert plan.name == "Test Plan"
        assert len(plan.modifications) == 1
        assert plan.modifications[0].capability == "test-feature"

    def test_plan_serialization_round_trip(self):
        """Contract: Plan survives serialization round-trip."""
        original = Plan(
            name="Test Plan",
            why="Because we need to test this feature properly for quality assurance",
            what_changes="Add comprehensive testing",
            modifications=[
                Modification(
                    capability="testing-framework",
                    operation=ModificationOperation.MODIFIED,
                    description="Enhance testing capabilities",
                    requirement=Requirement(
                        text="The system SHALL have better tests",
                        scenarios=[
                            Scenario(raw_text="Given a test suite, when tests run, then all pass")
                        ],
                    ),
                )
            ],
            metadata=PlanMetadata(
                version="1.0.0", format="aurora-plan", source_path="/path/to/plan.json"
            ),
        )

        # Serialize to dict
        plan_dict = original.model_dump()

        # Deserialize back to Plan
        restored = Plan.model_validate(plan_dict)

        # Verify all fields preserved
        assert restored.name == original.name
        assert restored.why == original.why
        assert restored.what_changes == original.what_changes
        assert len(restored.modifications) == len(original.modifications)
        assert restored.modifications[0].capability == original.modifications[0].capability
        assert (
            restored.modifications[0].requirement.text == original.modifications[0].requirement.text
        )
        assert restored.metadata.version == original.metadata.version


class TestSchemaBackwardCompatibility:
    """Contract tests for backward compatibility."""

    def test_plan_ignores_extra_fields_by_default(self):
        """Contract: Plan ignores extra fields (Pydantic v2 default behavior)."""
        plan_dict = {
            "name": "Test Plan",
            "why": "Because we need to test this feature properly and ensure quality.",
            "what_changes": "Add new feature",
            "modifications": [
                {
                    "capability": "test-feature",
                    "operation": "ADDED",
                    "description": "New test feature",
                }
            ],
            "extra_field": "This should be ignored",  # Extra field
        }

        # Pydantic v2 by default ignores extra fields
        plan = Plan.model_validate(plan_dict)
        assert plan.name == "Test Plan"
        # Extra field is not accessible on the model
        assert not hasattr(plan, "extra_field")

    def test_modification_optional_fields_are_truly_optional(self):
        """Contract: Modification optional fields can be omitted."""
        # Minimal valid modification (no optional fields)
        mod = Modification(
            capability="test-feature",
            operation=ModificationOperation.ADDED,
            description="Test modification",
        )

        assert mod.requirement is None
        assert mod.requirements is None
        assert mod.rename is None
