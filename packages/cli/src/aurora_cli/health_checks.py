"""Health check system for AURORA CLI.

This module implements health checks for:
- Core System: CLI version, database, API keys, permissions
- Code Analysis: tree-sitter parser, index age, chunk quality
- Search & Retrieval: vector store, Git BLA, cache size, embeddings
- Configuration: config file, Git repo, MCP server status
"""

from __future__ import annotations

import importlib.metadata
import os
import subprocess
from pathlib import Path
from typing import Any

from aurora_cli.config import Config, load_config


# Health check result type: (status, message, details)
# status: "pass", "warning", "fail"
# message: human-readable description
# details: dict with additional context
HealthCheckResult = tuple[str, str, dict[str, Any]]


class CoreSystemChecks:
    """Core system health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize core system checks.

        Args:
            config: Optional Config object. If None, loads from default location.
        """
        self.config = config or load_config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all core system checks.

        Returns:
            List of health check results
        """
        results = []

        # Check CLI version
        results.append(self._check_cli_version())

        # Check database existence
        results.append(self._check_database_exists())

        # Check API key configuration
        results.append(self._check_api_key())

        # Check permissions on .aurora directory
        results.append(self._check_permissions())

        return results

    def _check_cli_version(self) -> HealthCheckResult:
        """Check CLI version is available."""
        try:
            version = importlib.metadata.version("aurora-actr")
            return ("pass", f"CLI version {version}", {"version": version})
        except Exception as e:
            return ("fail", f"Cannot determine CLI version: {e}", {})

    def _check_database_exists(self) -> HealthCheckResult:
        """Check if database file exists."""
        try:
            db_path = Path(self.config.get_db_path())
            if db_path.exists():
                # Check size
                size_mb = db_path.stat().st_size / (1024 * 1024)
                if size_mb > 100:
                    return (
                        "warning",
                        f"Database large ({size_mb:.1f} MB)",
                        {"path": str(db_path), "size_mb": size_mb},
                    )
                return ("pass", "Database exists", {"path": str(db_path), "size_mb": size_mb})
            else:
                return ("warning", "Database not found", {"path": str(db_path)})
        except Exception as e:
            return ("fail", f"Database check failed: {e}", {})

    def _check_api_key(self) -> HealthCheckResult:
        """Check if API key is configured."""
        # Check environment variable
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        if env_key and env_key.strip():
            # Don't expose key, just check format
            if env_key.startswith("sk-ant-"):
                return ("pass", "API key configured (env)", {"source": "environment"})
            else:
                return (
                    "warning",
                    "API key set but format unexpected",
                    {"source": "environment"},
                )

        # Check config file
        if self.config.anthropic_api_key:
            if self.config.anthropic_api_key.startswith("sk-ant-"):
                return ("pass", "API key configured (config)", {"source": "config"})
            else:
                return ("warning", "API key set but format unexpected", {"source": "config"})

        return ("fail", "No API key configured", {})

    def _check_permissions(self) -> HealthCheckResult:
        """Check .aurora directory permissions."""
        try:
            aurora_dir = Path.home() / ".aurora"
            if not aurora_dir.exists():
                return ("warning", ".aurora directory not found", {"path": str(aurora_dir)})

            # Check if writable
            if os.access(aurora_dir, os.W_OK):
                return ("pass", ".aurora directory writable", {"path": str(aurora_dir)})
            else:
                return ("fail", ".aurora directory not writable", {"path": str(aurora_dir)})
        except Exception as e:
            return ("fail", f"Permission check failed: {e}", {})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'name' and 'fix_func' keys
        """
        issues = []

        # Check if .aurora directory missing
        aurora_dir = Path.home() / ".aurora"
        if not aurora_dir.exists():
            issues.append(
                {
                    "name": "Missing .aurora directory",
                    "fix_func": lambda: aurora_dir.mkdir(parents=True, exist_ok=True),
                }
            )

        # Check if database missing
        db_path = Path(self.config.get_db_path())
        if not db_path.exists():

            def create_database():
                from aurora.core.store.sqlite import SQLiteStore

                SQLiteStore(str(db_path))  # Database is created on init

            issues.append({"name": "Missing database", "fix_func": create_database})

        return issues

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys
        """
        issues = []

        # Check API key
        env_key = os.environ.get("ANTHROPIC_API_KEY")
        config_key = (
            self.config.anthropic_api_key if hasattr(self.config, "anthropic_api_key") else None
        )

        if not env_key and not config_key:
            issues.append(
                {
                    "name": "No API key configured",
                    "solution": "Set ANTHROPIC_API_KEY environment variable or add to config.json",
                }
            )

        # Check directory permissions
        aurora_dir = Path.home() / ".aurora"
        if aurora_dir.exists() and not os.access(aurora_dir, os.W_OK):
            issues.append(
                {
                    "name": ".aurora directory not writable",
                    "solution": f"Run: chmod u+w {aurora_dir}",
                }
            )

        return issues


class CodeAnalysisChecks:
    """Code analysis health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize code analysis checks.

        Args:
            config: Optional Config object. If None, loads from default location.
        """
        self.config = config or load_config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all code analysis checks.

        Returns:
            List of health check results
        """
        results = []

        # Check tree-sitter availability
        results.append(self._check_tree_sitter())

        # Check index age (if database exists)
        results.append(self._check_index_age())

        return results

    def _check_tree_sitter(self) -> HealthCheckResult:
        """Check if tree-sitter is available."""
        try:
            import tree_sitter

            # tree_sitter doesn't have __version__, just check it imports
            return ("pass", "Tree-sitter parser available", {})
        except ImportError:
            return (
                "warning",
                "Tree-sitter not available (fallback mode)",
                {"fallback": "text-based"},
            )

    def _check_index_age(self) -> HealthCheckResult:
        """Check age of index (database last modified time)."""
        try:
            db_path = Path(self.config.get_db_path())
            if not db_path.exists():
                return ("warning", "No index found", {"path": str(db_path)})

            # Check last modified time
            import time

            mtime = db_path.stat().st_mtime
            age_days = (time.time() - mtime) / (24 * 3600)

            if age_days > 7:
                return (
                    "warning",
                    f"Index is {age_days:.0f} days old",
                    {"age_days": age_days, "path": str(db_path)},
                )
            else:
                return (
                    "pass",
                    f"Index is {age_days:.1f} days old",
                    {"age_days": age_days, "path": str(db_path)},
                )
        except Exception as e:
            return ("fail", f"Index age check failed: {e}", {})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'name' and 'fix_func' keys
        """
        # No auto-fixable issues for code analysis yet
        return []

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys
        """
        issues = []

        # Check if tree-sitter is missing
        try:
            import tree_sitter
        except ImportError:
            issues.append(
                {
                    "name": "Tree-sitter not available",
                    "solution": "Install with: pip install tree-sitter",
                }
            )

        return issues


class SearchRetrievalChecks:
    """Search and retrieval health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize search & retrieval checks.

        Args:
            config: Optional Config object. If None, loads from default location.
        """
        self.config = config or load_config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all search & retrieval checks.

        Returns:
            List of health check results
        """
        results = []

        # Check vector store / embeddings
        results.append(self._check_vector_store())

        # Check Git BLA availability
        results.append(self._check_git_bla())

        # Check cache size
        results.append(self._check_cache_size())

        return results

    def _check_vector_store(self) -> HealthCheckResult:
        """Check if vector store / embeddings are functional."""
        try:
            db_path = Path(self.config.get_db_path())
            if not db_path.exists():
                return ("warning", "No vector store (database not found)", {"path": str(db_path)})

            # Check if embeddings table has data
            # For now, just check database exists (more detailed check would query DB)
            return ("pass", "Vector store available", {"path": str(db_path)})
        except Exception as e:
            return ("fail", f"Vector store check failed: {e}", {})

    def _check_git_bla(self) -> HealthCheckResult:
        """Check if Git BLA (Bayesian Lifetime Activation) is available."""
        try:
            # Check if we're in a git repository
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            if result.returncode == 0:
                return ("pass", "Git BLA available", {"git_dir": result.stdout.strip()})
            else:
                return ("warning", "Not a git repository (BLA disabled)", {})
        except FileNotFoundError:
            return ("warning", "Git not installed (BLA disabled)", {})
        except Exception as e:
            return ("fail", f"Git BLA check failed: {e}", {})

    def _check_cache_size(self) -> HealthCheckResult:
        """Check cache directory size."""
        try:
            cache_dir = Path.home() / ".aurora" / "cache"
            if not cache_dir.exists():
                return ("pass", "No cache directory", {"path": str(cache_dir)})

            # Calculate total size
            total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)

            if size_mb > 500:
                return (
                    "warning",
                    f"Cache large ({size_mb:.1f} MB)",
                    {"path": str(cache_dir), "size_mb": size_mb},
                )
            else:
                return (
                    "pass",
                    f"Cache size OK ({size_mb:.1f} MB)",
                    {"path": str(cache_dir), "size_mb": size_mb},
                )
        except Exception as e:
            return ("fail", f"Cache size check failed: {e}", {})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'name' and 'fix_func' keys
        """
        issues = []

        # Check if cache is too large
        cache_dir = Path.home() / ".aurora" / "cache"
        if cache_dir.exists():
            total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)

            if size_mb > 500:

                def clear_cache():
                    import shutil

                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)

                issues.append(
                    {"name": f"Clear large cache ({size_mb:.1f} MB)", "fix_func": clear_cache}
                )

        return issues

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys
        """
        issues = []

        # Check Git availability
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                issues.append(
                    {
                        "name": "Not a git repository",
                        "solution": "Run 'git init' to enable commit-based activation (BLA)",
                    }
                )
        except FileNotFoundError:
            issues.append(
                {
                    "name": "Git not installed",
                    "solution": "Install git to enable commit-based activation (BLA)",
                }
            )

        return issues


class ConfigurationChecks:
    """Configuration health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize configuration checks.

        Args:
            config: Optional Config object. If None, loads from default location.
        """
        self.config = config or load_config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all configuration checks.

        Returns:
            List of health check results
        """
        results = []

        # Check config file
        results.append(self._check_config_file())

        # Check Git repository
        results.append(self._check_git_repo())

        # Check MCP server status (if applicable)
        results.append(self._check_mcp_server())

        return results

    def _check_config_file(self) -> HealthCheckResult:
        """Check if config file exists and is valid."""
        try:
            config_path = Path.home() / ".aurora" / "config.json"
            if config_path.exists():
                # Try to validate config
                self.config.validate()
                return ("pass", "Config file valid", {"path": str(config_path)})
            else:
                return ("warning", "No config file (using defaults)", {"path": str(config_path)})
        except Exception as e:
            return ("fail", f"Config validation failed: {e}", {})

    def _check_git_repo(self) -> HealthCheckResult:
        """Check if current directory is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )

            if result.returncode == 0:
                repo_root = result.stdout.strip()
                return ("pass", "Git repository detected", {"repo_root": repo_root})
            else:
                return ("warning", "Not a git repository", {})
        except FileNotFoundError:
            return ("warning", "Git not installed", {})
        except Exception as e:
            return ("fail", f"Git check failed: {e}", {})

    def _check_mcp_server(self) -> HealthCheckResult:
        """Check MCP server status."""
        # For now, just check if MCP is enabled in config
        if self.config.mcp_always_on:
            return ("pass", "MCP server enabled in config", {"mcp_always_on": True})
        else:
            return ("pass", "MCP server disabled", {"mcp_always_on": False})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'name' and 'fix_func' keys
        """
        # No auto-fixable configuration issues yet
        return []

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys
        """
        # No manual configuration issues to report yet
        return []
