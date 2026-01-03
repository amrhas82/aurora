"""
Tests for Validator class.

Ported from: test/core/validation.test.ts (Validator describe block)
TDD approach: Tests written first based on TypeScript test behavior.

Task: 2.5 - Write tests/unit/validation/test_validator.py
"""

import os
import pytest
import tempfile
from pathlib import Path

from aurora_planning.validators.validator import Validator


class TestValidatorValidateCapability:
    """Test cases for Validator.validate_capability() (was validateSpec)."""

    def test_validates_valid_capability_file(self):
        """Should validate a valid capability (spec) file."""
        content = """# User Authentication Spec

## Purpose
This specification defines the requirements for user authentication in the system.

## Requirements

### Requirement: Secure Authentication
The system SHALL provide secure user authentication mechanisms.

#### Scenario: Successful login
Given a user with valid credentials
When they submit the login form
Then they are authenticated and redirected to the dashboard

### Requirement: Handle Invalid Credentials
The system SHALL gracefully handle incorrect credentials.

#### Scenario: Invalid credentials
Given a user with invalid credentials
When they submit the login form
Then they see an error message"""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator()
            report = validator.validate_capability(str(spec_file))

            assert report.valid is True
            assert report.summary.errors == 0

    def test_detects_missing_purpose_section(self):
        """Should detect missing Purpose (overview) section."""
        content = """# User Authentication Spec

## Requirements

### Requirement: Test
The system SHALL provide secure user authentication.

#### Scenario: Login
Given a user
When they login
Then authenticated"""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator()
            report = validator.validate_capability(str(spec_file))

            assert report.valid is False
            assert report.summary.errors > 0
            assert any("Purpose" in issue.message for issue in report.issues)

    def test_detects_missing_requirements_section(self):
        """Should detect missing Requirements section."""
        content = """# User Authentication Spec

## Purpose
This is a spec for authentication."""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator()
            report = validator.validate_capability(str(spec_file))

            assert report.valid is False
            assert any("Requirements" in issue.message for issue in report.issues)

    def test_warns_about_brief_purpose(self):
        """Should warn about brief Purpose (overview) section."""
        content = """# Test Spec

## Purpose
Brief overview

## Requirements

### Requirement: Test
The system SHALL do something.

#### Scenario: Test
Given test
When action
Then result"""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator(strict_mode=False)
            report = validator.validate_capability(str(spec_file))

            # Should pass with warnings
            assert report.valid is True
            assert report.summary.warnings > 0


class TestValidatorValidatePlan:
    """Test cases for Validator.validate_plan() (was validateChange)."""

    def test_validates_valid_plan_file(self):
        """Should validate a valid plan (change) file."""
        content = """# Add User Authentication

## Why
We need to implement user authentication to secure the application and protect user data from unauthorized access.

## What Changes
- **user-auth:** Add new user authentication specification
- **api-endpoints:** Modify to include auth endpoints"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            plan_file = plan_dir / "proposal.md"
            plan_file.write_text(content)

            validator = Validator()
            report = validator.validate_plan(str(plan_file))

            assert report.valid is True
            assert report.summary.errors == 0

    def test_detects_missing_why_section(self):
        """Should detect missing Why section."""
        content = """# Add User Authentication

## What Changes
- **user-auth:** Add new user authentication specification"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "proposal.md"
            plan_file.write_text(content)

            validator = Validator()
            report = validator.validate_plan(str(plan_file))

            assert report.valid is False
            assert any("Why" in issue.message for issue in report.issues)

    def test_detects_missing_what_changes_section(self):
        """Should detect missing What Changes section."""
        content = """# Add User Authentication

## Why
We need to implement authentication."""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_file = Path(tmpdir) / "proposal.md"
            plan_file.write_text(content)

            validator = Validator()
            report = validator.validate_plan(str(plan_file))

            assert report.valid is False
            assert any("What Changes" in issue.message for issue in report.issues)


class TestValidatorStrictMode:
    """Test cases for strict mode validation."""

    def test_strict_mode_fails_on_warnings(self):
        """Should fail on warnings in strict mode."""
        content = """# Test Spec

## Purpose
Brief overview

## Requirements

### Requirement: Test
The system SHALL do something.

#### Scenario: Test
Given test
When action
Then result"""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator(strict_mode=True)
            report = validator.validate_capability(str(spec_file))

            # Should fail due to brief overview warning
            assert report.valid is False

    def test_non_strict_mode_passes_warnings(self):
        """Should pass warnings in non-strict mode."""
        content = """# Test Spec

## Purpose
Brief overview

## Requirements

### Requirement: Test
The system SHALL do something.

#### Scenario: Test
Given test
When action
Then result"""

        with tempfile.TemporaryDirectory() as tmpdir:
            spec_file = Path(tmpdir) / "spec.md"
            spec_file.write_text(content)

            validator = Validator(strict_mode=False)
            report = validator.validate_capability(str(spec_file))

            # Should pass despite warnings
            assert report.valid is True
            assert report.summary.warnings > 0


class TestValidatorDeltaSpecs:
    """Test cases for validate_plan_modification_specs() (was validateChangeDeltaSpecs)."""

    def test_validates_requirement_with_metadata(self):
        """Should validate requirement with metadata before SHALL/MUST text."""
        delta_spec = """# Test Spec

## ADDED Requirements

### Requirement: Circuit Breaker State Management SHALL be implemented
**ID**: REQ-CB-001
**Priority**: P1 (High)

The system MUST implement a circuit breaker with three states.

#### Scenario: Normal operation
**Given** the circuit breaker is in CLOSED state
**When** a request is made
**Then** the request is executed normally"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "test-spec"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec)

            validator = Validator(strict_mode=True)
            report = validator.validate_plan_modification_specs(str(plan_dir))

            assert report.valid is True
            assert report.summary.errors == 0

    def test_validates_requirement_with_shall_in_text(self):
        """Should validate requirement with SHALL in text but not in header."""
        delta_spec = """# Test Spec

## ADDED Requirements

### Requirement: Error Handling
**ID**: REQ-ERR-001
**Priority**: P2

The system SHALL handle all errors gracefully.

#### Scenario: Error occurs
**Given** an error condition
**When** an error occurs
**Then** the error is logged and user is notified"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "test-spec"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec)

            validator = Validator(strict_mode=True)
            report = validator.validate_plan_modification_specs(str(plan_dir))

            assert report.valid is True
            assert report.summary.errors == 0

    def test_fails_when_requirement_lacks_shall_must(self):
        """Should fail when requirement text lacks SHALL/MUST."""
        delta_spec = """# Test Spec

## ADDED Requirements

### Requirement: Logging Feature
**ID**: REQ-LOG-001

The system will log all events.

#### Scenario: Event occurs
**Given** an event
**When** it occurs
**Then** it is logged"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "test-spec"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec)

            validator = Validator(strict_mode=True)
            report = validator.validate_plan_modification_specs(str(plan_dir))

            assert report.valid is False
            assert report.summary.errors > 0
            assert any("SHALL or MUST" in issue.message for issue in report.issues)

    def test_handles_requirements_without_metadata(self):
        """Should handle requirements without metadata fields."""
        delta_spec = """# Test Spec

## ADDED Requirements

### Requirement: Simple Feature
The system SHALL implement this feature.

#### Scenario: Basic usage
**Given** a condition
**When** an action occurs
**Then** a result happens"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "test-spec"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec)

            validator = Validator(strict_mode=True)
            report = validator.validate_plan_modification_specs(str(plan_dir))

            assert report.valid is True
            assert report.summary.errors == 0

    def test_case_insensitive_delta_headers(self):
        """Should treat delta headers case-insensitively."""
        delta_spec = """# Test Spec

## Added Requirements

### Requirement: Mixed Case Handling
The system MUST support mixed case delta headers.

#### Scenario: Case insensitive parsing
**Given** a delta file with mixed case headers
**When** validation runs
**Then** the delta is detected"""

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            specs_dir = plan_dir / "specs" / "test-spec"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text(delta_spec)

            validator = Validator(strict_mode=True)
            report = validator.validate_plan_modification_specs(str(plan_dir))

            assert report.valid is True
            assert report.summary.errors == 0
            assert report.summary.warnings == 0
            assert report.summary.info == 0

    def test_detects_missing_specs_directory(self):
        """Should handle missing specs directory (no deltas)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_dir = Path(tmpdir)
            # No specs/ directory created

            validator = Validator()
            report = validator.validate_plan_modification_specs(str(plan_dir))

            # Should fail because no deltas found
            assert report.valid is False
            assert any("no deltas" in issue.message.lower() or "no modifications" in issue.message.lower()
                      for issue in report.issues)
