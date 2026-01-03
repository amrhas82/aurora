"""Tests for JSON converter."""

import pytest
from pathlib import Path
from aurora_planning.converters.json import JsonConverter


class TestJsonConverterCapability:
    """Tests for converting capabilities to JSON."""

    @pytest.fixture
    def converter(self):
        """Create JSON converter instance."""
        return JsonConverter()

    def test_convert_capability_to_json(self, converter, tmp_path):
        """Test converting a capability file to JSON."""
        # Create a capability file
        cap_dir = tmp_path / "capabilities" / "test-cap"
        cap_dir.mkdir(parents=True)
        cap_file = cap_dir / "spec.md"
        cap_file.write_text("""# Capability: Test Capability

## Purpose

This is the test capability overview.

## Requirements

### Requirement: REQ-001: Test Requirement

The system SHALL provide test functionality.

#### Scenario: Basic test
GIVEN a test state
WHEN an action occurs
THEN the result is expected
""")

        result = converter.convert_capability_to_json(str(cap_file))

        import json
        data = json.loads(result)

        # Name is extracted from directory path, not content
        assert data["name"] == "test-cap"
        assert "overview" in data
        assert "requirements" in data

    def test_convert_capability_includes_metadata(self, converter, tmp_path):
        """Test that conversion includes source path metadata."""
        cap_dir = tmp_path / "capabilities" / "meta-test"
        cap_dir.mkdir(parents=True)
        cap_file = cap_dir / "spec.md"
        cap_file.write_text("""# Capability: Meta Test

## Purpose

Overview text.

## Requirements

### Requirement: REQ-001: Test

The system SHALL work.

#### Scenario: Works
GIVEN state
WHEN action
THEN result
""")

        result = converter.convert_capability_to_json(str(cap_file))

        import json
        data = json.loads(result)

        assert "metadata" in data
        assert "sourcePath" in data["metadata"]
        assert str(cap_file) in data["metadata"]["sourcePath"]


class TestJsonConverterPlan:
    """Tests for converting plans to JSON."""

    @pytest.fixture
    def converter(self):
        """Create JSON converter instance."""
        return JsonConverter()

    def test_convert_plan_to_json(self, converter, tmp_path):
        """Test converting a plan file to JSON."""
        # Create a plan file
        plan_dir = tmp_path / "plans" / "test-plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text("""# Plan: Test Plan

## Why

This plan adds a new feature for testing purposes.

## What Changes

- **test-cap:** Add test functionality
- **other-cap:** Modify existing behavior
""")

        result = converter.convert_plan_to_json(str(plan_file))

        import json
        data = json.loads(result)

        # Name is extracted from directory path, not content
        assert data["name"] == "test-plan"
        assert "why" in data
        assert "modifications" in data

    def test_convert_plan_includes_metadata(self, converter, tmp_path):
        """Test that plan conversion includes source path metadata."""
        plan_dir = tmp_path / "plans" / "meta-plan"
        plan_dir.mkdir(parents=True)
        plan_file = plan_dir / "plan.md"
        plan_file.write_text("""# Plan: Meta Plan

## Why

Reason for the plan that is long enough.

## What Changes

- **cap:** Change something
""")

        result = converter.convert_plan_to_json(str(plan_file))

        import json
        data = json.loads(result)

        assert "metadata" in data
        assert "sourcePath" in data["metadata"]


class TestExtractNameFromPath:
    """Tests for extracting names from file paths."""

    @pytest.fixture
    def converter(self):
        """Create JSON converter instance."""
        return JsonConverter()

    def test_extract_name_from_capabilities_path(self, converter):
        """Test extracting name from capabilities path."""
        path = "/project/aurora/capabilities/my-cap/spec.md"
        name = converter._extract_name_from_path(path)
        assert name == "my-cap"

    def test_extract_name_from_plans_path(self, converter):
        """Test extracting name from plans path."""
        path = "/project/aurora/plans/my-plan/plan.md"
        name = converter._extract_name_from_path(path)
        assert name == "my-plan"

    def test_extract_name_from_filename_fallback(self, converter):
        """Test extracting name from filename when not in known directory."""
        path = "/some/path/my-file.md"
        name = converter._extract_name_from_path(path)
        assert name == "my-file"
