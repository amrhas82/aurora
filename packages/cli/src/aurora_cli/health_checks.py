"""Health check system for AURORA CLI.

This module implements health checks for:
- Core System: CLI version, database, API keys, permissions
- Code Analysis: tree-sitter parser, index age, chunk quality
- Search & Retrieval: vector store, Git BLA, cache size, embeddings
- Configuration: config file, Git repo
- Tool Integration: CLI tools, slash commands
"""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import subprocess
from pathlib import Path
from typing import Any

from aurora_cli.config import Config


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
        self.config = config or Config()

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
                        f"DB large ({size_mb:.0f} MB)",
                        {"path": str(db_path), "size_mb": size_mb},
                    )
                return (
                    "pass",
                    f"DB ({size_mb:.1f} MB)",
                    {"path": str(db_path), "size_mb": size_mb},
                )
            return ("warning", "DB not found", {"path": str(db_path)})
        except Exception as e:
            return ("fail", f"DB check failed: {e}", {})

    def _check_permissions(self) -> HealthCheckResult:
        """Check .aurora directory permissions."""
        try:
            aurora_dir = Path.cwd() / ".aurora"
            if not aurora_dir.exists():
                return ("warning", ".aurora directory not found", {"path": str(aurora_dir)})

            # Check if writable
            if os.access(aurora_dir, os.W_OK):
                return ("pass", ".aurora directory writable", {"path": str(aurora_dir)})
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
        aurora_dir = Path.cwd() / ".aurora"
        if not aurora_dir.exists():
            issues.append(
                {
                    "name": "Missing .aurora directory",
                    "fix_func": lambda: aurora_dir.mkdir(parents=True, exist_ok=True),
                },
            )

        # Check if database missing
        db_path = Path(self.config.get_db_path())
        if not db_path.exists():

            def create_database():
                from aurora_core.store.sqlite import SQLiteStore

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
                },
            )

        # Check directory permissions
        aurora_dir = Path.cwd() / ".aurora"
        if aurora_dir.exists() and not os.access(aurora_dir, os.W_OK):
            issues.append(
                {
                    "name": ".aurora directory not writable",
                    "solution": f"Run: chmod u+w {aurora_dir}",
                },
            )

        return issues


class CodeAnalysisChecks:
    """Code analysis health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize code analysis checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()

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
        """Check if tree-sitter is available and list configured languages."""
        try:
            import tree_sitter  # noqa: F401

            # Check for available language parsers
            available_languages = []
            language_modules = [
                ("python", "tree_sitter_python"),
                ("javascript", "tree_sitter_javascript"),
                ("typescript", "tree_sitter_typescript"),
                ("go", "tree_sitter_go"),
                ("rust", "tree_sitter_rust"),
                ("java", "tree_sitter_java"),
                ("c", "tree_sitter_c"),
                ("cpp", "tree_sitter_cpp"),
                ("ruby", "tree_sitter_ruby"),
                ("php", "tree_sitter_php"),
            ]

            for lang_name, module_name in language_modules:
                try:
                    __import__(module_name)
                    available_languages.append(lang_name)
                except ImportError:
                    pass

            if available_languages:
                # Show first 5 languages
                lang_display = ", ".join(available_languages[:5])
                if len(available_languages) > 5:
                    lang_display += f" +{len(available_languages) - 5} more"
                return (
                    "pass",
                    f"Tree-sitter parsers available ({len(available_languages)} languages: {lang_display})",
                    {"languages": available_languages, "count": len(available_languages)},
                )
            return (
                "warning",
                "Tree-sitter installed but no language parsers found",
                {"languages": [], "count": 0},
            )
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
            import tree_sitter  # noqa: F401
        except ImportError:
            issues.append(
                {
                    "name": "Tree-sitter not available",
                    "solution": "Install with: pip install tree-sitter",
                },
            )

        return issues


class SearchRetrievalChecks:
    """Search and retrieval health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize search & retrieval checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all search & retrieval checks.

        Returns:
            List of health check results

        """
        results = []

        # Check vector store / embeddings
        results.append(self._check_vector_store())

        # Check sentence-transformers installed
        results.append(self._check_sentence_transformers())

        # Check embedding model cached
        results.append(self._check_embedding_model())

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

    def _check_sentence_transformers(self) -> HealthCheckResult:
        """Check if sentence-transformers package is installed."""
        try:
            import sentence_transformers  # noqa: F401

            return ("pass", "sentence-transformers installed", {})
        except ImportError:
            return (
                "fail",
                "sentence-transformers not installed",
                {
                    "solution": "Run: pip install sentence-transformers",
                    "or": "aur doctor --fix-ml",
                },
            )

    def _check_embedding_model(self) -> HealthCheckResult:
        """Check if embedding model is downloaded and cached."""
        try:
            # Skip if sentence-transformers not installed
            try:
                import sentence_transformers  # noqa: F401
            except ImportError:
                return ("skip", "Embedding model (requires sentence-transformers)", {})

            from aurora_context_code.semantic.model_utils import (
                DEFAULT_MODEL,
                get_model_cache_path,
                is_model_cached,
            )

            model_name = DEFAULT_MODEL
            cache_path = get_model_cache_path(model_name)

            if is_model_cached(model_name):
                return (
                    "pass",
                    "Embedding model cached",
                    {"model": model_name, "path": str(cache_path)},
                )

            return (
                "warning",
                "Embedding model not downloaded",
                {
                    "model": model_name,
                    "path": str(cache_path),
                    "solution": "Run: aur doctor --fix-ml",
                },
            )

        except Exception as e:
            return ("fail", f"Embedding model check failed: {e}", {})

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
            return ("warning", "Not a git repository (BLA disabled)", {})
        except FileNotFoundError:
            return ("warning", "Git not installed (BLA disabled)", {})
        except Exception as e:
            return ("fail", f"Git BLA check failed: {e}", {})

    def _check_cache_size(self) -> HealthCheckResult:
        """Check combined cache size (Aurora local + ML model)."""
        try:
            # Aurora local cache
            aurora_cache = Path.cwd() / ".aurora" / "cache"
            aurora_size = 0
            if aurora_cache.exists():
                aurora_size = sum(f.stat().st_size for f in aurora_cache.rglob("*") if f.is_file())

            # HuggingFace ML model cache
            hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
            ml_size = 0
            if hf_cache.exists():
                ml_size = sum(f.stat().st_size for f in hf_cache.rglob("*") if f.is_file())

            aurora_mb = aurora_size / (1024 * 1024)
            ml_mb = ml_size / (1024 * 1024)
            total_mb = aurora_mb + ml_mb

            details = {
                "aurora_cache_mb": round(aurora_mb, 1),
                "ml_model_mb": round(ml_mb, 1),
                "total_mb": round(total_mb, 1),
            }

            # Warn if total exceeds 2GB
            if total_mb > 2000:
                return (
                    "warning",
                    f"Cache large: {aurora_mb:.0f} MB local + {ml_mb:.0f} MB ML = {total_mb:.0f} MB",
                    details,
                )
            return (
                "pass",
                f"Cache: {aurora_mb:.0f} MB local + {ml_mb:.0f} MB ML",
                details,
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
        cache_dir = Path.cwd() / ".aurora" / "cache"
        if cache_dir.exists():
            total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)

            if size_mb > 500:

                def clear_cache():
                    import shutil

                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)

                issues.append(
                    {"name": f"Clear large cache ({size_mb:.1f} MB)", "fix_func": clear_cache},
                )

        return issues

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys

        """
        issues = []

        # Check sentence-transformers availability
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            issues.append(
                {
                    "name": "sentence-transformers not installed",
                    "solution": "Run: pip install sentence-transformers or aur doctor --fix-ml",
                },
            )

        # Check embedding model availability
        try:
            from aurora_context_code.semantic.model_utils import DEFAULT_MODEL, is_model_cached

            if not is_model_cached(DEFAULT_MODEL):
                issues.append(
                    {
                        "name": "Embedding model not downloaded",
                        "solution": f"Run: aur doctor --fix-ml (downloads {DEFAULT_MODEL})",
                    },
                )
        except Exception:
            # If check fails, skip (likely sentence-transformers not installed)
            pass

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
                    },
                )
        except FileNotFoundError:
            issues.append(
                {
                    "name": "Git not installed",
                    "solution": "Install git to enable commit-based activation (BLA)",
                },
            )

        return issues


class ConfigurationChecks:
    """Configuration health checks."""

    def __init__(self, config: Config | None = None):
        """Initialize configuration checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()

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

        return results

    def _check_config_file(self) -> HealthCheckResult:
        """Check if config file exists and is valid."""
        try:
            # Check project-local config first (created by aur init)
            project_config_path = Path.cwd() / ".aurora" / "config.json"
            if project_config_path.exists():
                # Try to validate config
                self.config.validate()
                return ("pass", "Config file valid", {"path": str(project_config_path)})

            # Fallback to global config
            global_config_path = Path.home() / ".aurora" / "config.json"
            if global_config_path.exists():
                self.config.validate()
                return ("pass", "Config file valid (global)", {"path": str(global_config_path)})

            return (
                "warning",
                "No config file (using defaults)",
                {"path": str(project_config_path)},
            )
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
            return ("warning", "Not a git repository", {})
        except FileNotFoundError:
            return ("warning", "Git not installed", {})
        except Exception as e:
            return ("fail", f"Git check failed: {e}", {})

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


class ToolIntegrationChecks:
    """Tool integration health checks (slash commands + MCP servers)."""

    def __init__(self, config: Config | None = None):
        """Initialize tool integration checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all tool integration checks.

        Returns:
            List of health check results

        """
        results = []

        # Check CLI tools installation
        results.append(self._check_cli_tools())

        # Check slash command integration
        results.append(self._check_slash_commands())

        # Check MCP tools registration
        results.append(self._check_mcp_tools())

        return results

    def _check_cli_tools(self) -> HealthCheckResult:
        """Check CLI tools installation status."""
        try:
            # Check for common AI CLI tools
            import shutil

            tools_to_check = {
                "claude": "Claude CLI",
                "cursor": "Cursor CLI",
                "aider": "Aider",
                "cline": "Cline CLI",
            }

            found_tools = []
            for cmd, name in tools_to_check.items():
                if shutil.which(cmd):
                    found_tools.append(name)

            if found_tools:
                return (
                    "pass",
                    f"CLI tools installed ({len(found_tools)} found: {', '.join(found_tools[:3])}{'...' if len(found_tools) > 3 else ''})",
                    {"found_tools": found_tools, "count": len(found_tools)},
                )
            return (
                "warning",
                "No AI CLI tools detected",
                {"found_tools": [], "count": 0},
            )
        except Exception as e:
            return ("fail", f"CLI tools check failed: {e}", {})

    def _check_slash_commands(self) -> HealthCheckResult:
        """Check slash command configuration status."""
        try:
            from aurora_cli.commands.init_helpers import detect_configured_slash_tools
            from aurora_cli.templates.slash_commands import COMMAND_TEMPLATES

            # Verify COMMAND_TEMPLATES count (should be 4: plan, tasks, implement, archive)
            expected_commands = 4
            actual_count = len(COMMAND_TEMPLATES)
            if actual_count != expected_commands:
                return (
                    "fail",
                    f"Slash command templates count mismatch: expected {expected_commands}, got {actual_count}",
                    {"expected": expected_commands, "actual": actual_count},
                )

            project_path = Path.cwd()
            configured_tools = detect_configured_slash_tools(project_path)

            # Check if any are configured
            configured_count = sum(
                1 for is_configured in configured_tools.values() if is_configured
            )

            if configured_count == 0:
                return (
                    "warning",
                    f"Slash commands available ({actual_count}) but not configured in project",
                    {"configured": False, "available": actual_count, "configured_count": 0},
                )
            return (
                "pass",
                f"Slash commands available ({actual_count}) and configured ({configured_count} tools)",
                {
                    "configured": True,
                    "available": actual_count,
                    "configured_count": configured_count,
                },
            )
        except Exception as e:
            return ("fail", f"Slash command check failed: {e}", {})

    def _check_mcp_tools(self) -> HealthCheckResult:
        """Check MCP tools registration status."""
        try:
            from aurora_mcp.server import AuroraMCPServer

            # Initialize MCP server in test mode to check registered tools
            server = AuroraMCPServer(test_mode=True)
            tools = server.list_tools()

            tool_names = [tool["name"] for tool in tools]
            required_tools = {"lsp", "mem_search"}
            missing_tools = required_tools - set(tool_names)

            if not missing_tools:
                return (
                    "pass",
                    f"MCP tools registered ({len(tools)} tools: {', '.join(tool_names)})",
                    {"tools": tool_names, "count": len(tools)},
                )
            return (
                "warning",
                f"MCP tools missing required tools: {', '.join(missing_tools)}",
                {"tools": tool_names, "missing": list(missing_tools), "count": len(tools)},
            )
        except Exception as e:
            return ("warning", f"MCP tools check failed: {e}", {"error": str(e)})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'name' and 'fix_func' keys

        """
        # Tool integration issues are fixed via 'aur init --config --tools=<tool>'
        # Not auto-fixable through doctor command
        return []

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys

        """
        issues = []

        try:
            from aurora_cli.commands.init_helpers import detect_configured_slash_tools

            project_path = Path.cwd()

            # Check slash commands
            slash_tools = detect_configured_slash_tools(project_path)
            slash_configured = sum(1 for is_configured in slash_tools.values() if is_configured)

            if slash_configured == 0:
                issues.append(
                    {
                        "name": "Slash commands not configured",
                        "solution": "Run 'aur init --config --tools=all' or specify tools like --tools=claude,cursor",
                    },
                )

        except Exception:
            # If detection fails, don't report as an issue
            pass

        return issues


class InstallationChecks:
    """Verify core package installation and Python version."""

    def __init__(self, config: Config | None = None):
        """Initialize installation checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all installation checks.

        Returns:
            List of health check results

        """
        results = []
        results.append(self._check_python_version())
        results.extend(self._check_core_packages())
        return results

    def _check_python_version(self) -> HealthCheckResult:
        """Check Python >= 3.10."""
        import sys

        version = sys.version_info
        if version >= (3, 10):
            return (
                "pass",
                f"Python {version.major}.{version.minor}.{version.micro}",
                {"version": f"{version.major}.{version.minor}.{version.micro}"},
            )
        return (
            "fail",
            f"Python {version.major}.{version.minor} (requires 3.10+)",
            {"version": f"{version.major}.{version.minor}"},
        )

    def _check_core_packages(self) -> list[HealthCheckResult]:
        """Check core Aurora packages are importable."""
        # Core packages (required)
        core_packages = [
            ("aurora_core", "Core components", False),
            ("aurora_context_code", "Context & parsing", False),
            ("aurora_soar", "SOAR orchestrator", False),
            ("aurora_reasoning", "Reasoning engine", False),
            ("aurora_cli", "CLI tools", False),
        ]
        # Optional packages (show warning if missing)
        optional_packages = [
            ("aurora_lsp", "LSP integration", True),
        ]
        packages = core_packages + optional_packages

        results = []
        for pkg, desc, is_optional in packages:
            try:
                __import__(pkg)
                # Get package version
                try:
                    # Try standard package name first (aurora-actr)
                    if pkg == "aurora_cli":
                        version = importlib.metadata.version("aurora-actr")
                    else:
                        # Try package-specific version
                        pkg_name = pkg.replace("_", "-")
                        version = importlib.metadata.version(pkg_name)
                    results.append(
                        ("pass", f"{desc} ({pkg}) v{version}", {"package": pkg, "version": version})
                    )
                except Exception:
                    # If version not found, just show package without version
                    results.append(("pass", f"{desc} ({pkg})", {"package": pkg}))
            except ImportError:
                if is_optional:
                    results.append(
                        (
                            "warning",
                            f"{desc} not available ({pkg})",
                            {"package": pkg, "optional": True},
                        )
                    )
                else:
                    results.append(("fail", f"{desc} MISSING ({pkg})", {"package": pkg}))
        return results

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            Empty list - no auto-fixable installation issues

        """
        return []

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name' and 'solution' keys

        """
        issues = []

        # Check for missing packages
        results = self._check_core_packages()
        for status, message, details in results:
            if status == "fail":
                pkg = details.get("package", "unknown")
                issues.append(
                    {
                        "name": f"Missing package: {pkg}",
                        "solution": f"Install with: pip install -e packages/{pkg.replace('aurora_', '')}",
                    },
                )

        return issues
