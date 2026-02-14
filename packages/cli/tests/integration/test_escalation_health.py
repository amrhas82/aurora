"""Integration tests for CLI escalation config and health checks.

Tests escalation configuration validation, decision logic,
health check categories, and ignore pattern matching.
No LLM calls — escalation uses keyword-only mode, health checks use mocked filesystem.
"""

import pytest

from aurora_cli.escalation import AutoEscalationHandler, EscalationConfig, EscalationResult
from aurora_cli.ignore_patterns import (
    DEFAULT_IGNORE_PATTERNS,
    load_ignore_patterns,
    matches_pattern,
    should_ignore,
)

# ---------------------------------------------------------------------------
# Escalation Config
# ---------------------------------------------------------------------------


class TestEscalationConfigDefaults:
    """Test default escalation configuration values."""

    def test_defaults(self):
        config = EscalationConfig()
        assert config.threshold == 0.6
        assert config.enable_keyword_only is True
        assert config.force_aurora is False
        assert config.force_direct is False


class TestEscalationConfigValidation:
    """Test configuration validation."""

    def test_threshold_out_of_range(self):
        with pytest.raises(ValueError, match="threshold must be in"):
            EscalationConfig(threshold=1.5)
        with pytest.raises(ValueError, match="threshold must be in"):
            EscalationConfig(threshold=-0.1)

    def test_threshold_boundary_values(self):
        # Boundary values should work
        EscalationConfig(threshold=0.0)
        EscalationConfig(threshold=1.0)

    def test_conflict_force_both(self):
        with pytest.raises(ValueError, match="Cannot force both"):
            EscalationConfig(force_aurora=True, force_direct=True)


class TestEscalationForceAurora:
    """Test force_aurora bypasses classification."""

    def test_force_aurora(self):
        config = EscalationConfig(force_aurora=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("any query at all")
        assert result.use_aurora is True
        assert result.complexity == "FORCED"
        assert result.method == "forced"


class TestEscalationForceDirect:
    """Test force_direct bypasses classification."""

    def test_force_direct(self):
        config = EscalationConfig(force_direct=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("any query at all")
        assert result.use_aurora is False
        assert result.complexity == "FORCED"
        assert result.method == "forced"


class TestEscalationSimpleQuery:
    """Test simple queries route to direct LLM."""

    def test_simple_query(self, monkeypatch):
        monkeypatch.setattr(
            "aurora_cli.escalation.assess_complexity",
            lambda query, **kw: {
                "complexity": "SIMPLE",
                "confidence": 0.9,
                "method": "keyword",
                "reasoning": "Simple query",
                "score": 0.2,
            },
        )
        config = EscalationConfig(threshold=0.6, enable_keyword_only=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("what is a function?")
        assert result.score < 0.6
        assert result.use_aurora is False
        assert result.method == "keyword"


class TestEscalationComplexQuery:
    """Test complex queries route to AURORA."""

    def test_complex_query(self, monkeypatch):
        monkeypatch.setattr(
            "aurora_cli.escalation.assess_complexity",
            lambda query, **kw: {
                "complexity": "COMPLEX",
                "confidence": 0.85,
                "method": "keyword",
                "reasoning": "Complex multi-step query",
                "score": 0.82,
            },
        )
        config = EscalationConfig(threshold=0.6, enable_keyword_only=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query(
            "Analyze the authentication system across all microservices, "
            "refactor the token validation logic, update the database schema"
        )
        assert result.score >= 0.6
        assert result.use_aurora is True


class TestEscalationResultFields:
    """Test EscalationResult has all expected fields."""

    def test_result_fields(self, monkeypatch):
        monkeypatch.setattr(
            "aurora_cli.escalation.assess_complexity",
            lambda query, **kw: {
                "complexity": "MEDIUM",
                "confidence": 0.8,
                "method": "keyword",
                "reasoning": "Medium complexity",
                "score": 0.45,
            },
        )
        config = EscalationConfig(enable_keyword_only=True)
        handler = AutoEscalationHandler(config=config)
        result = handler.assess_query("explain this code")

        assert isinstance(result, EscalationResult)
        assert isinstance(result.use_aurora, bool)
        assert isinstance(result.complexity, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.method, str)
        assert isinstance(result.reasoning, str)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------


class TestHealthCoreCliVersion:
    """Test CLI version health check."""

    def test_version_check(self):
        from aurora_cli.health_checks import CoreSystemChecks

        # Create with default config — version check doesn't need .aurora
        checks = CoreSystemChecks()
        result = checks._check_cli_version()
        status, message, details = result
        # Either pass with version or fail if package not installed as aurora-actr
        assert status in ("pass", "fail")
        if status == "pass":
            assert "version" in details


class TestHealthCoreDbExists:
    """Test database existence check."""

    def test_db_missing(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import CoreSystemChecks

        # Point config to a non-existent db
        class FakeConfig:
            def get_db_path(self):
                return str(tmp_path / "nonexistent.db")

        checks = CoreSystemChecks(config=FakeConfig())
        status, message, _ = checks._check_database_exists()
        assert status == "warning"
        assert "not found" in message

    def test_db_present(self, tmp_path):
        from aurora_cli.health_checks import CoreSystemChecks

        db_file = tmp_path / "memory.db"
        db_file.write_bytes(b"x" * 1024)

        class FakeConfig:
            def get_db_path(self):
                return str(db_file)

        checks = CoreSystemChecks(config=FakeConfig())
        status, message, details = checks._check_database_exists()
        assert status == "pass"
        assert "size_mb" in details


class TestHealthCorePermissions:
    """Test .aurora directory permissions check."""

    def test_permissions_no_dir(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import CoreSystemChecks

        monkeypatch.chdir(tmp_path)
        checks = CoreSystemChecks()
        status, message, _ = checks._check_permissions()
        assert status == "warning"
        assert "not found" in message

    def test_permissions_writable(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import CoreSystemChecks

        aurora_dir = tmp_path / ".aurora"
        aurora_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        checks = CoreSystemChecks()
        status, message, _ = checks._check_permissions()
        assert status == "pass"
        assert "writable" in message


class TestHealthCodeAnalysisParser:
    """Test tree-sitter availability check."""

    def test_tree_sitter_available(self):
        from aurora_cli.health_checks import CodeAnalysisChecks

        class FakeConfig:
            def get_db_path(self):
                return "/nonexistent/path.db"

        checks = CodeAnalysisChecks(config=FakeConfig())
        status, message, details = checks._check_tree_sitter()
        # tree-sitter should be available in dev environment
        assert status in ("pass", "warning")
        if status == "pass":
            assert "languages" in details
            assert details["count"] > 0


class TestHealthConfigFile:
    """Test config file presence check."""

    def test_config_missing(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import ConfigurationChecks

        monkeypatch.chdir(tmp_path)
        # No .aurora/config.json → warning
        checks = ConfigurationChecks()
        status, message, _ = checks._check_config_file()
        # Should be warning or pass depending on global config
        assert status in ("pass", "warning")


class TestHealthToolsCliAvailable:
    """Test CLI tool availability check."""

    def test_tool_found(self):
        from aurora_cli.health_checks import ToolIntegrationChecks

        class FakeConfig:
            pass

        checks = ToolIntegrationChecks(config=FakeConfig())
        status, message, details = checks._check_cli_tools()
        assert status in ("pass", "warning")
        if status == "pass":
            assert details["count"] > 0


class TestHealthRunAllCategories:
    """Test all check categories return results."""

    def test_all_categories(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import (
            CodeAnalysisChecks,
            ConfigurationChecks,
            CoreSystemChecks,
            InstallationChecks,
        )

        monkeypatch.chdir(tmp_path)

        class FakeConfig:
            def get_db_path(self):
                return str(tmp_path / "memory.db")

            def validate(self):
                pass

        config = FakeConfig()

        # Each category should return a non-empty list
        for CheckClass in (
            CoreSystemChecks,
            CodeAnalysisChecks,
            ConfigurationChecks,
            InstallationChecks,
        ):
            checks = CheckClass(config=config)
            results = checks.run_checks()
            assert len(results) > 0, f"{CheckClass.__name__} returned no results"
            for status, message, details in results:
                assert status in ("pass", "warning", "fail", "skip")


class TestHealthNoAuroraDir:
    """Test graceful behavior when .aurora/ doesn't exist."""

    def test_no_aurora_dir(self, tmp_path, monkeypatch):
        from aurora_cli.health_checks import CoreSystemChecks

        monkeypatch.chdir(tmp_path)
        checks = CoreSystemChecks()
        results = checks.run_checks()
        # Should not crash — results may be warning/fail but no exceptions
        assert len(results) > 0
        statuses = [r[0] for r in results]
        # At least some should be warning (no .aurora dir, no db)
        assert "warning" in statuses or "fail" in statuses


# ---------------------------------------------------------------------------
# Ignore Patterns
# ---------------------------------------------------------------------------


class TestIgnorePatternsDefault:
    """Test default ignore patterns."""

    def test_default_patterns(self):
        assert ".git/**" in DEFAULT_IGNORE_PATTERNS
        assert "node_modules/**" in DEFAULT_IGNORE_PATTERNS
        assert "__pycache__/**" in DEFAULT_IGNORE_PATTERNS
        assert "venv/**" in DEFAULT_IGNORE_PATTERNS
        assert "dist/**" in DEFAULT_IGNORE_PATTERNS


class TestIgnorePatternsMatch:
    """Test pattern matching logic."""

    def test_exact_match(self):
        assert matches_pattern("CHANGELOG.md", "CHANGELOG.md") is True
        assert matches_pattern("README.md", "CHANGELOG.md") is False

    def test_wildcard_match(self):
        assert matches_pattern("test.pyc", "*.pyc") is True
        assert matches_pattern("test.py", "*.pyc") is False

    def test_recursive_match(self):
        assert matches_pattern("node_modules/foo/bar.js", "node_modules/**") is True
        assert matches_pattern(".git/config", ".git/**") is True

    def test_directory_pattern(self):
        assert matches_pattern("venv/lib/site.py", "venv/**") is True

    def test_should_ignore(self, tmp_path):
        patterns = DEFAULT_IGNORE_PATTERNS
        root = tmp_path

        # Create file paths (don't need to exist for should_ignore)
        git_file = root / ".git" / "config"
        src_file = root / "src" / "main.py"

        assert should_ignore(git_file, root, patterns) is True
        assert should_ignore(src_file, root, patterns) is False

    def test_custom_pattern(self):
        assert matches_pattern("docs/secret.md", "docs/*.md") is True
        assert matches_pattern("src/secret.md", "docs/*.md") is False

    def test_load_ignore_patterns(self, tmp_path):
        """Test loading patterns from .auroraignore file."""
        ignore_file = tmp_path / ".auroraignore"
        ignore_file.write_text("# Comment\n*.log\ntmp/\n")

        patterns = load_ignore_patterns(tmp_path)
        # Should include defaults + custom
        assert "*.log" in patterns
        assert "tmp/" in patterns
        assert ".git/**" in patterns  # Default still present

    def test_load_ignore_patterns_no_file(self, tmp_path):
        """Without .auroraignore, only defaults."""
        patterns = load_ignore_patterns(tmp_path)
        assert patterns == DEFAULT_IGNORE_PATTERNS
