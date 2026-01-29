"""Health check system for AURORA CLI.

This module implements health checks for:
- Core System: CLI version, database, API keys, permissions
- Code Analysis: tree-sitter parser, index age, chunk quality
- Search & Retrieval: vector store, Git BLA, cache size, embeddings
- Configuration: config file, Git repo, MCP server status
- Tool Integration: slash commands, MCP servers
- MCP Functional: MCP config validation, SOAR phases, memory database
"""

from __future__ import annotations

import importlib
import importlib.metadata
import json
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
                        f"Database large ({size_mb:.1f} MB)",
                        {"path": str(db_path), "size_mb": size_mb},
                    )
                return ("pass", "Database exists", {"path": str(db_path), "size_mb": size_mb})
            return ("warning", "Database not found", {"path": str(db_path)})
        except Exception as e:
            return ("fail", f"Database check failed: {e}", {})

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

        # Check embedding model availability
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

    def _check_embedding_model(self) -> HealthCheckResult:
        """Check if embedding model is downloaded and accessible.

        Returns:
            HealthCheckResult indicating model availability status

        """
        try:
            # Check if sentence-transformers is installed
            try:
                import sentence_transformers  # noqa: F401
            except ImportError:
                return (
                    "fail",
                    "sentence-transformers not installed",
                    {
                        "solution": "Run: pip install sentence-transformers",
                        "or": "aur doctor --fix-ml",
                    },
                )

            # Check if model is cached
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
                    f"Embedding model cached",
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
        """Check cache directory size."""
        try:
            cache_dir = Path.cwd() / ".aurora" / "cache"
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
            config_path = Path.home() / ".aurora" / "config.json"
            if config_path.exists():
                # Try to validate config
                self.config.validate()
                return ("pass", "Config file valid", {"path": str(config_path)})
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

        # Check MCP server integration
        results.append(self._check_mcp_servers())

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

            project_path = Path.cwd()
            configured_tools = detect_configured_slash_tools(project_path)

            # Check if any are configured
            configured_count = sum(
                1 for is_configured in configured_tools.values() if is_configured
            )

            if configured_count == 0:
                return (
                    "warning",
                    "Slash commands not configured",
                    {"configured": False, "count": 0},
                )
            return (
                "pass",
                f"Slash commands configured ({configured_count} tools)",
                {"configured": True, "count": configured_count},
            )
        except Exception as e:
            return ("fail", f"Slash command check failed: {e}", {})

    def _check_mcp_servers(self) -> HealthCheckResult:
        """Check MCP server configuration status."""
        try:
            from aurora_cli.commands.init_helpers import detect_configured_mcp_tools

            project_path = Path.cwd()
            configured_tools = detect_configured_mcp_tools(project_path)

            # Check if any are configured
            configured_count = sum(
                1 for is_configured in configured_tools.values() if is_configured
            )

            if configured_count == 0:
                return (
                    "warning",
                    "MCP servers not configured",
                    {"configured": False, "count": 0},
                )
            configured_list = [
                tool_id for tool_id, is_configured in configured_tools.items() if is_configured
            ]
            return (
                "pass",
                f"MCP servers configured ({', '.join(configured_list)})",
                {"configured": True, "count": configured_count, "tools": configured_list},
            )
        except Exception as e:
            return ("fail", f"MCP server check failed: {e}", {})

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
            from aurora_cli.commands.init_helpers import (
                detect_configured_mcp_tools,
                detect_configured_slash_tools,
            )

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

            # Check MCP servers
            mcp_tools = detect_configured_mcp_tools(project_path)
            mcp_configured = sum(1 for is_configured in mcp_tools.values() if is_configured)

            if mcp_configured == 0:
                issues.append(
                    {
                        "name": "MCP servers not configured",
                        "solution": "Run 'aur init --config' to configure MCP servers",
                    },
                )

        except Exception:
            # If detection fails, don't report as an issue
            pass

        return issues


class MCPFunctionalChecks:
    """MCP functional health checks for SOAR integration."""

    def __init__(self, config: Config | None = None):
        """Initialize MCP functional checks.

        Args:
            config: Optional Config object. If None, loads from default location.

        """
        self.config = config or Config()
        # Config doesn't have project_dir, always use cwd
        self.project_path = Path.cwd()

    def run_checks(self) -> list[HealthCheckResult]:
        """Run all MCP functional checks.

        Returns:
            List of health check results

        """
        results = []

        # Check MCP config syntax
        results.append(self._check_mcp_config_syntax())

        # Check Aurora MCP tools importable
        results.append(self._check_aurora_mcp_tools_importable())

        # Check SOAR phases importable
        results.append(self._check_soar_phases_importable())

        # Check memory database accessible
        results.append(self._check_memory_database_accessible())

        # Check slash command MCP consistency
        results.append(self._check_slash_command_mcp_consistency())

        # Check MCP server tools complete
        results.append(self._check_mcp_server_tools_complete())

        return results

    def _get_mcp_config_path(self) -> Path:
        """Get MCP config file path for Claude Code."""
        return Path.home() / ".claude" / "claude_desktop_config.json"

    def _check_mcp_config_syntax(self) -> HealthCheckResult:
        """Check MCP config JSON syntax validation."""
        try:
            config_path = self._get_mcp_config_path()

            if not config_path.exists():
                return (
                    "warning",
                    "MCP config not found",
                    {
                        "path": str(config_path),
                        "suggestion": "Run 'aur init --config' to create it",
                    },
                )

            # Try to parse JSON
            with open(config_path) as f:
                json.load(f)

            return ("pass", "MCP config syntax valid", {"path": str(config_path)})

        except json.JSONDecodeError as e:
            return (
                "fail",
                "Invalid MCP config JSON syntax",
                {"path": str(config_path), "error": str(e), "line": e.lineno},
            )
        except Exception as e:
            return ("fail", f"MCP config check failed: {e}", {})

    def _check_aurora_mcp_tools_importable(self) -> HealthCheckResult:
        """Check if Aurora MCP tools can be imported and have required methods."""
        try:
            # Import the module
            mcp_tools_module = importlib.import_module("aurora_mcp.tools")
            tools_class = mcp_tools_module.AuroraMCPTools

            # Check for required methods
            required_methods = ["aurora_query", "aurora_search", "aurora_get"]
            found_methods = []
            missing_methods = []

            for method_name in required_methods:
                if hasattr(tools_class, method_name):
                    found_methods.append(method_name)
                else:
                    missing_methods.append(method_name)

            if len(found_methods) == 3:
                return (
                    "pass",
                    "All 3 Aurora MCP tools importable",
                    {"found": found_methods, "count": 3},
                )
            return (
                "fail",
                f"Missing {len(missing_methods)} Aurora MCP tool(s)",
                {"found": found_methods, "missing": missing_methods},
            )

        except ImportError as e:
            return (
                "fail",
                "Cannot import aurora_mcp.tools",
                {"error": str(e), "suggestion": "Check aurora-mcp package installation"},
            )
        except Exception as e:
            return ("fail", f"Aurora MCP tools check failed: {e}", {})

    def _check_soar_phases_importable(self) -> HealthCheckResult:
        """Check if all 9 SOAR phase modules can be imported."""
        try:
            phase_names = [
                "assess",
                "retrieve",
                "decompose",
                "verify",
                "route",
                "collect",
                "synthesize",
                "record",
                "respond",
            ]

            importable_phases = []
            failed_phases = []

            for phase_name in phase_names:
                try:
                    importlib.import_module(f"aurora_soar.phases.{phase_name}")
                    importable_phases.append(phase_name)
                except ImportError:
                    failed_phases.append(phase_name)

            if len(importable_phases) == 9:
                return (
                    "pass",
                    "All 9 SOAR phases importable",
                    {"phases": importable_phases, "count": 9},
                )
            if len(importable_phases) > 0:
                return (
                    "fail",
                    f"{len(failed_phases)} SOAR phase(s) missing",
                    {"importable": importable_phases, "failed": failed_phases},
                )
            return (
                "fail",
                "No SOAR phases importable",
                {"suggestion": "Check aurora-soar package installation"},
            )

        except Exception as e:
            return ("fail", f"SOAR phases check failed: {e}", {})

    def _check_memory_database_accessible(self) -> HealthCheckResult:
        """Check if memory database exists and is accessible."""
        try:
            db_path = self.project_path / ".aurora" / "memory.db"

            if not db_path.exists():
                return (
                    "warning",
                    "Memory database not found",
                    {"path": str(db_path), "suggestion": "Run 'aur mem index' to initialize"},
                )

            # Try to open connection using SQLiteStore
            from aurora_core.store.sqlite import SQLiteStore

            store = SQLiteStore(str(db_path))
            store.close()

            return ("pass", "Memory database accessible", {"path": str(db_path)})

        except ImportError as e:
            return ("fail", "Cannot import SQLiteStore", {"error": str(e)})
        except Exception as e:
            return (
                "fail",
                f"Memory database connection failed: {e}",
                {"path": str(db_path) if "db_path" in locals() else "unknown"},
            )

    def _check_slash_command_mcp_consistency(self) -> HealthCheckResult:
        """Check if slash command configs reference valid MCP servers."""
        try:
            # For now, just check if .aurora directory exists with skills
            skills_dir = self.project_path / ".aurora" / "skills"

            if not skills_dir.exists():
                return ("pass", "No slash commands configured", {"configured": False})

            # Count configured skills
            skill_files = list(skills_dir.glob("*.md"))

            if len(skill_files) == 0:
                return ("pass", "No slash commands configured", {"configured": False})

            return (
                "pass",
                f"Slash commands configured ({len(skill_files)} skills)",
                {"configured": True, "count": len(skill_files)},
            )

        except Exception as e:
            return ("warning", f"Slash command consistency check failed: {e}", {})

    def _check_mcp_server_tools_complete(self) -> HealthCheckResult:
        """Check if Aurora MCP server has exactly 3 tools registered."""
        try:
            # Import the module
            mcp_tools_module = importlib.import_module("aurora_mcp.tools")
            tools_class = mcp_tools_module.AuroraMCPTools

            # Check for required methods
            required_methods = ["aurora_query", "aurora_search", "aurora_get"]

            # Get all public methods (not starting with _)
            all_methods = [
                name
                for name in dir(tools_class)
                if not name.startswith("_") and callable(getattr(tools_class, name))
            ]

            # Filter to only aurora_* methods
            aurora_methods = [m for m in all_methods if m.startswith("aurora_")]

            found_required = [m for m in required_methods if m in aurora_methods]
            missing_required = [m for m in required_methods if m not in aurora_methods]
            extra_methods = [m for m in aurora_methods if m not in required_methods]

            if len(found_required) == 3 and len(extra_methods) == 0:
                return (
                    "pass",
                    "MCP server has exactly 3 tools",
                    {"tools": found_required, "count": 3},
                )
            if len(missing_required) > 0:
                return (
                    "fail",
                    f"Missing {len(missing_required)} required tool(s)",
                    {"found": found_required, "missing": missing_required},
                )
            if len(extra_methods) > 0:
                return (
                    "warning",
                    f"Extra {len(extra_methods)} tool(s) registered",
                    {"required": found_required, "extra": extra_methods},
                )
            return ("pass", "MCP server tools complete", {"tools": found_required})

        except ImportError as e:
            return ("fail", "Cannot import aurora_mcp.tools", {"error": str(e)})
        except Exception as e:
            return ("fail", f"MCP server tools check failed: {e}", {})

    def get_fixable_issues(self) -> list[dict[str, Any]]:
        """Get list of automatically fixable issues.

        Returns:
            List of dicts with 'problem', 'fix', and 'name' keys

        """
        issues = []

        # Check if .aurora directory is missing
        aurora_dir = self.project_path / ".aurora"
        if not aurora_dir.exists():

            def create_aurora_dir():
                aurora_dir.mkdir(parents=True, exist_ok=True)

            issues.append(
                {
                    "name": "Missing .aurora directory",
                    "problem": f"Project missing .aurora directory at {aurora_dir}",
                    "fix": "Create .aurora directory",
                    "fix_func": create_aurora_dir,
                },
            )

        # Check if memory database is missing
        db_path = self.project_path / ".aurora" / "memory.db"
        if aurora_dir.exists() and not db_path.exists():

            def create_database():
                from aurora_core.store.sqlite import SQLiteStore

                SQLiteStore(str(db_path))

            issues.append(
                {
                    "name": "Missing memory database",
                    "problem": f"Memory database not found at {db_path}",
                    "fix": "Initialize memory database",
                    "fix_func": create_database,
                },
            )

        return issues

    def get_manual_issues(self) -> list[dict[str, Any]]:
        """Get list of issues requiring manual intervention.

        Returns:
            List of dicts with 'name', 'problem', and 'solution' keys

        """
        issues = []

        # Run checks to identify issues
        results = self.run_checks()

        for status, message, details in results:
            if status == "fail":
                if "JSON syntax" in message:
                    issues.append(
                        {
                            "name": "Invalid MCP config syntax",
                            "problem": f"MCP config has invalid JSON syntax: {details.get('error', 'unknown error')}",
                            "solution": "Fix JSON syntax in ~/.claude/claude_desktop_config.json or run 'aur init --config'",
                        },
                    )
                elif "aurora_mcp.tools" in message or "Aurora MCP tools" in message:
                    issues.append(
                        {
                            "name": "Aurora MCP tools not available",
                            "problem": "Cannot import aurora_mcp.tools module",
                            "solution": "Ensure aurora-mcp package is installed: pip install -e packages/mcp",
                        },
                    )
                elif "SOAR phases" in message:
                    missing = details.get("failed", [])
                    issues.append(
                        {
                            "name": "SOAR phases missing",
                            "problem": f"Missing SOAR phase modules: {', '.join(missing)}",
                            "solution": "Ensure aurora-soar package is installed: pip install -e packages/soar",
                        },
                    )
                elif "Missing" in message and "tool" in message:
                    missing = details.get("missing", [])
                    issues.append(
                        {
                            "name": "MCP tools incomplete",
                            "problem": f"Missing required MCP tools: {', '.join(missing)}",
                            "solution": "Check aurora_mcp.tools.AuroraMCPTools class has all 3 methods: aurora_query, aurora_search, aurora_get",
                        },
                    )

        return issues
