"""Unit tests for plan ID generation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[4] / "packages" / "planning" / "src"))

from aurora_planning.id_generator import (
    extract_plan_number,
    generate_plan_id,
    generate_slug,
    parse_plan_id,
    scan_existing_plans,
    validate_plan_id_format,
)


class TestExtractPlanNumber:
    """Tests for extract_plan_number()."""

    def test_active_format(self):
        """Should extract number from active format (NNNN-slug)."""
        assert extract_plan_number("0001-oauth-auth") == 1
        assert extract_plan_number("0042-user-registration") == 42
        assert extract_plan_number("9999-test-plan") == 9999

    def test_archived_format(self):
        """Should extract number from archived format (YYYY-MM-DD-NNNN-slug)."""
        assert extract_plan_number("2026-01-03-0001-oauth-auth") == 1
        assert extract_plan_number("2026-12-31-0042-user-registration") == 42

    def test_invalid_format(self):
        """Should return None for invalid formats."""
        assert extract_plan_number("not-a-plan") is None
        assert extract_plan_number("001-short-number") is None
        assert extract_plan_number("random-directory") is None


class TestScanExistingPlans:
    """Tests for scan_existing_plans()."""

    def test_empty_directory(self, temp_plans_dir):
        """Should return 0 when no plans exist."""
        result = scan_existing_plans(temp_plans_dir)
        assert result == 0

    def test_active_plans_only(self, temp_plans_dir):
        """Should find highest number from active plans."""
        (temp_plans_dir / "active" / "0001-plan-a").mkdir(parents=True)
        (temp_plans_dir / "active" / "0005-plan-b").mkdir(parents=True)
        (temp_plans_dir / "active" / "0003-plan-c").mkdir(parents=True)

        result = scan_existing_plans(temp_plans_dir)
        assert result == 5

    def test_archived_plans_only(self, temp_plans_dir):
        """Should find highest number from archived plans."""
        (temp_plans_dir / "archive" / "2026-01-01-0010-old-plan").mkdir(parents=True)
        (temp_plans_dir / "archive" / "2026-01-02-0007-older-plan").mkdir(parents=True)

        result = scan_existing_plans(temp_plans_dir)
        assert result == 10

    def test_mixed_active_and_archived(self, temp_plans_dir):
        """Should find highest number across both active and archived."""
        (temp_plans_dir / "active" / "0005-active-plan").mkdir(parents=True)
        (temp_plans_dir / "archive" / "2026-01-01-0012-archived-plan").mkdir(parents=True)
        (temp_plans_dir / "active" / "0008-another-active").mkdir(parents=True)

        result = scan_existing_plans(temp_plans_dir)
        assert result == 12

    def test_ignores_files(self, temp_plans_dir):
        """Should ignore files, only scan directories."""
        (temp_plans_dir / "active").mkdir(parents=True, exist_ok=True)
        (temp_plans_dir / "active" / "0001-plan").mkdir()
        (temp_plans_dir / "active" / "0010-not-a-directory.txt").touch()

        result = scan_existing_plans(temp_plans_dir)
        assert result == 1


class TestGenerateSlug:
    """Tests for generate_slug()."""

    def test_basic_slugification(self):
        """Should convert text to lowercase hyphenated slug."""
        assert generate_slug("Implement OAuth Authentication") == "implement-oauth-authentication"
        assert generate_slug("User Registration Flow") == "user-registration-flow"

    def test_special_characters(self):
        """Should remove special characters."""
        assert generate_slug("OAuth 2.0 & JWT Tokens!") == "oauth-2-0-jwt-tokens"
        assert generate_slug("Fix bug #123 (critical)") == "fix-bug-123-critical"

    def test_max_length(self):
        """Should truncate to max_length."""
        long_text = "This is a very long goal description that exceeds maximum length"
        result = generate_slug(long_text, max_length=20)
        assert len(result) <= 20

    def test_non_latin_characters(self):
        """Should handle non-Latin characters gracefully."""
        result = generate_slug("测试计划", max_length=30)
        # python-slugify can transliterate some non-Latin chars
        # Just verify it returns a valid slug
        assert len(result) > 0
        assert "-" in result or result.isalnum()


class TestGeneratePlanId:
    """Tests for generate_plan_id()."""

    def test_first_plan(self, temp_plans_dir):
        """Should generate 0001-* for first plan."""
        result = generate_plan_id("Test OAuth Implementation", plans_dir=temp_plans_dir)
        assert result == "0001-test-oauth-implementation"

    def test_increments_from_existing(self, temp_plans_dir):
        """Should increment from highest existing plan number."""
        (temp_plans_dir / "active" / "0001-existing-plan").mkdir(parents=True)
        (temp_plans_dir / "active" / "0002-another-plan").mkdir(parents=True)

        result = generate_plan_id("New Plan", plans_dir=temp_plans_dir)
        assert result == "0003-new-plan"

    def test_handles_archived_plans(self, temp_plans_dir):
        """Should consider archived plans when incrementing."""
        (temp_plans_dir / "active" / "0001-active").mkdir(parents=True)
        (temp_plans_dir / "archive" / "2026-01-01-0005-archived").mkdir(parents=True)

        result = generate_plan_id("New Plan", plans_dir=temp_plans_dir)
        assert result == "0006-new-plan"

    def test_empty_goal_raises_error(self, temp_plans_dir):
        """Should raise ValueError for empty goal."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            generate_plan_id("", plans_dir=temp_plans_dir)

        with pytest.raises(ValueError, match="at least 3 characters"):
            generate_plan_id("AB", plans_dir=temp_plans_dir)

    def test_collision_handling(self, temp_plans_dir):
        """Should retry with next number on collision."""
        # Create a plan that would collide
        (temp_plans_dir / "active" / "0001-test-plan").mkdir(parents=True)

        result = generate_plan_id("Test Plan", plans_dir=temp_plans_dir)
        # Should try 0002 since 0001-test-plan exists
        assert result == "0002-test-plan"


class TestValidatePlanIdFormat:
    """Tests for validate_plan_id_format()."""

    def test_valid_formats(self):
        """Should accept valid plan IDs."""
        assert validate_plan_id_format("0001-oauth-auth") is True
        assert validate_plan_id_format("0042-user-registration") is True
        assert validate_plan_id_format("9999-test") is True
        assert validate_plan_id_format("0001-multi-word-slug") is True

    def test_invalid_formats(self):
        """Should reject invalid plan IDs."""
        assert validate_plan_id_format("1-short-number") is False  # Not 4 digits
        assert validate_plan_id_format("00001-too-many-digits") is False
        assert validate_plan_id_format("0001_underscore") is False  # No underscores
        assert validate_plan_id_format("0001") is False  # No slug
        assert validate_plan_id_format("oauth-auth") is False  # No number
        assert validate_plan_id_format("0001-UPPERCASE") is False  # Must be lowercase


class TestParsePlanId:
    """Tests for parse_plan_id()."""

    def test_valid_parsing(self):
        """Should parse valid plan IDs into components."""
        assert parse_plan_id("0001-oauth-auth") == (1, "oauth-auth")
        assert parse_plan_id("0042-user-registration") == (42, "user-registration")
        assert parse_plan_id("0100-test-plan") == (100, "test-plan")

    def test_invalid_format_raises_error(self):
        """Should raise ValueError for invalid formats."""
        with pytest.raises(ValueError, match="Invalid plan ID format"):
            parse_plan_id("not-a-plan-id")

        with pytest.raises(ValueError, match="Invalid plan ID format"):
            parse_plan_id("001-short")
