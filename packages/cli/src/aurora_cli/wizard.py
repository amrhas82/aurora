"""Interactive setup wizard for AURORA CLI.

This module provides a guided setup experience for first-time users.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from aurora_cli.config import DEFAULTS_FILE, _get_aurora_home
from aurora_cli.errors import ErrorHandler


__all__ = ["InteractiveWizard"]

console = Console()


class InteractiveWizard:
    """Interactive setup wizard for AURORA configuration.

    Guides users through an 8-step setup process with auto-detection
    and input validation.
    """

    def __init__(self) -> None:
        """Initialize the wizard."""
        self.config_data: dict[str, Any] = {}
        self.should_index = False
        self.api_key: str | None = None
        self.enable_mcp = False
        self.error_handler = ErrorHandler()

    def run(self) -> None:
        """Execute the interactive setup wizard.

        Runs all 8 steps in sequence and creates configuration.
        """
        try:
            self.step_1_welcome()
            self.step_2_indexing_prompt()
            self.step_3_embeddings_provider()
            self.step_4_api_key_input()
            self.step_5_mcp_prompt()
            self.step_6_create_config()
            if self.should_index:
                self.step_7_run_index()
            self.step_8_completion()
        except click.Abort:
            console.print("\n[yellow]Setup cancelled by user[/]\n")
            raise

    def step_1_welcome(self) -> None:
        """Display welcome message and auto-detect environment."""
        console.print("\n")
        console.print(
            Panel(
                "[bold cyan]Aurora Interactive Setup[/]\n\n"
                "This wizard will guide you through setting up AURORA.\n"
                "Estimated time: 2 minutes",
                title="[bold]Welcome[/]",
                border_style="cyan",
            ),
        )

        # Auto-detect environment
        console.print("\n[bold]Environment Detection:[/]")

        # Check Python version
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        console.print(f"  • Python version: [cyan]{py_version}[/]")

        # Check if in Git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                check=False,
                timeout=2,
            )
            if result.returncode == 0:
                console.print("  • Git repository: [green]✓ Detected[/]")
            else:
                console.print("  • Git repository: [yellow]Not detected[/]")
        except Exception:
            console.print("  • Git repository: [yellow]Not detected[/]")

        # Check current directory
        cwd = Path.cwd()
        console.print(f"  • Working directory: [cyan]{cwd}[/]")

    def step_2_indexing_prompt(self) -> None:
        """Prompt user whether to index current directory."""
        console.print("\n[bold]Step 1/7: Memory Indexing[/]")
        console.print("AURORA can index your codebase for semantic search and context retrieval.")

        self.should_index = click.confirm(
            "Index current directory for memory search?",
            default=True,
        )

        if self.should_index:
            console.print("  [green]✓[/] Will index current directory")
        else:
            console.print("  [dim]Skipped - you can index later with 'aur mem index .'[/]")

    def step_3_embeddings_provider(self) -> None:
        """Prompt for embedding provider choice."""
        console.print("\n[bold]Step 2/7: LLM Provider[/]")
        console.print("Choose your LLM provider for queries and reasoning:")
        console.print("  [cyan]1.[/] Anthropic (Claude) [dim]- Recommended[/]")
        console.print("  [cyan]2.[/] OpenAI (GPT)")
        console.print("  [cyan]3.[/] Ollama (Local)")

        while True:
            choice = click.prompt(
                "Select provider",
                type=click.Choice(["1", "2", "3"], case_sensitive=False),
                default="1",
                show_choices=False,
            )

            if choice == "1":
                self.config_data["provider"] = "anthropic"
                console.print("  [green]✓[/] Using Anthropic (Claude)")
                break
            elif choice == "2":
                self.config_data["provider"] = "openai"
                console.print("  [green]✓[/] Using OpenAI (GPT)")
                break
            elif choice == "3":
                self.config_data["provider"] = "ollama"
                console.print("  [green]✓[/] Using Ollama (Local)")
                console.print("  [dim]Note: Make sure Ollama is running locally[/]")
                break

    def step_4_api_key_input(self) -> None:
        """Prompt for API key with validation."""
        # Skip API key for Ollama
        if self.config_data.get("provider") == "ollama":
            console.print("\n[bold]Step 3/7: API Key[/]")
            console.print("  [dim]Not needed for Ollama (local model)[/]")
            return

        console.print("\n[bold]Step 3/7: API Key[/]")
        console.print("Enter your API key for the selected provider.")
        console.print(
            "[dim]Note: API keys are stored in config and can also be set via environment variables[/]",
        )

        provider = self.config_data.get("provider", "anthropic")

        while True:
            api_key = click.prompt(
                "API key (or press Enter to skip)",
                default="",
                show_default=False,
                hide_input=True,
            )

            # Allow skipping
            if not api_key or not api_key.strip():
                console.print("  [yellow]⚠[/] Skipped - set API key later via environment variable")
                self.api_key = None
                break

            # Validate format based on provider
            if provider == "anthropic":
                if api_key.startswith("sk-ant-"):
                    console.print("  [green]✓[/] Valid Anthropic API key format")
                    self.api_key = api_key
                    break
                else:
                    console.print("  [red]✗[/] Invalid format. Anthropic keys start with 'sk-ant-'")
                    if not click.confirm("Try again?", default=True):
                        self.api_key = None
                        break
            elif provider == "openai":
                if api_key.startswith("sk-"):
                    console.print("  [green]✓[/] Valid OpenAI API key format")
                    self.api_key = api_key
                    break
                else:
                    console.print("  [red]✗[/] Invalid format. OpenAI keys start with 'sk-'")
                    if not click.confirm("Try again?", default=True):
                        self.api_key = None
                        break

    def step_5_mcp_prompt(self) -> None:
        """Prompt whether to enable MCP server."""
        console.print("\n[bold]Step 4/7: MCP Server[/]")
        console.print("Enable Model Context Protocol (MCP) server for Claude Desktop integration?")
        console.print("[dim]Note: Requires additional configuration in Claude Desktop settings[/]")

        self.enable_mcp = click.confirm("Enable MCP server?", default=False)

        if self.enable_mcp:
            console.print("  [green]✓[/] MCP server enabled")
            console.print("  [dim]Configure in: ~/.config/Claude/claude_desktop_config.json[/]")
        else:
            console.print("  [dim]Skipped - you can enable MCP later[/]")

    def step_6_create_config(self) -> None:
        """Create configuration file with user choices."""
        console.print("\n[bold]Step 5/7: Creating Configuration[/]")

        # Get aurora home directory
        config_dir = _get_aurora_home()
        config_path = config_dir / "config.json"

        # Check if config already exists
        if config_path.exists():
            if not click.confirm(f"Config file exists at {config_path}. Overwrite?", default=False):
                console.print("  [yellow]Keeping existing config[/]")
                return

        # Create config directory
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"  [green]✓[/] Created directory: {config_dir}")
        except PermissionError as e:
            error_msg = self.error_handler.handle_path_error(
                e,
                str(config_dir),
                "creating config directory",
            )
            console.print(f"  [red]✗[/] {error_msg}")
            raise click.Abort()

        # Prepare config data from defaults
        import json

        with open(DEFAULTS_FILE) as f:
            config_data = json.load(f)

        # Set database path
        config_data["storage"]["path"] = str(config_dir / "memory.db")

        # Set API key if provided (stored as api_key in llm section)
        if self.api_key:
            config_data["llm"]["api_key"] = self.api_key

        # Write config file
        try:
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)
            console.print(f"  [green]✓[/] Created config: {config_path}")
        except Exception as e:
            error_msg = self.error_handler.handle_config_error(e, str(config_path))
            console.print(f"  [red]✗[/] {error_msg}")
            raise click.Abort()

        # Set secure permissions
        try:
            os.chmod(config_path, 0o600)
            console.print("  [green]✓[/] Set secure permissions (0600)")
        except Exception:
            console.print("  [yellow]⚠[/] Could not set secure permissions")

    def step_7_run_index(self) -> None:
        """Run indexing with progress display."""
        console.print("\n[bold]Step 6/7: Indexing Codebase[/]")

        try:
            from aurora_cli.config import load_config
            from aurora_cli.memory_manager import MemoryManager

            # Load config
            config = load_config()
            manager = MemoryManager(config=config)

            # Create progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task_id = None

                def progress_callback(current: int, total: int) -> None:
                    nonlocal task_id
                    if task_id is None:
                        task_id = progress.add_task("Indexing files", total=total)
                    progress.update(task_id, completed=current)

                # Perform indexing
                stats = manager.index_path(Path.cwd(), progress_callback=progress_callback)

            if stats.files_indexed > 0:
                console.print(
                    f"  [green]✓[/] Indexed {stats.files_indexed} files, "
                    f"{stats.chunks_created} chunks in {stats.duration_seconds:.2f}s",
                )
            else:
                console.print("  [yellow]⚠[/] No Python files found to index")

        except Exception as e:
            console.print(f"  [red]✗[/] Indexing failed: {e}")
            console.print("  [dim]You can index later with: aur mem index .[/]")

    def step_8_completion(self) -> None:
        """Display completion summary with next steps."""
        console.print("\n")
        console.print(
            Panel(
                "[bold green]✓ Setup Complete![/]\n\nAURORA is now configured and ready to use.",
                title="[bold]Success[/]",
                border_style="green",
            ),
        )

        # Display configuration summary
        console.print("\n[bold]Configuration Summary:[/]")
        provider = self.config_data.get("provider", "anthropic")
        console.print(f"  • Provider: [cyan]{provider}[/]")
        if self.api_key:
            console.print("  • API Key: [green]✓ Configured[/]")
        else:
            console.print("  • API Key: [yellow]⚠ Not set[/]")
        if self.should_index:
            console.print("  • Indexing: [green]✓ Complete[/]")
        else:
            console.print("  • Indexing: [dim]Skipped[/]")
        if self.enable_mcp:
            console.print("  • MCP Server: [green]✓ Enabled[/]")
        else:
            console.print("  • MCP Server: [dim]Disabled[/]")

        # Next steps
        next_steps = []
        if not self.api_key:
            if provider == "anthropic":
                next_steps.append(
                    "[yellow]1. Set API key:[/]\n   [cyan]export ANTHROPIC_API_KEY=sk-ant-...[/]",
                )
            elif provider == "openai":
                next_steps.append(
                    "[yellow]1. Set API key:[/]\n   [cyan]export OPENAI_API_KEY=sk-...[/]",
                )

        next_steps.extend(
            [
                "[bold]2. Verify setup:[/]\n   [cyan]aur doctor[/]",
                "[bold]3. Check version:[/]\n   [cyan]aur version[/]",
                "[bold]4. Start querying:[/]\n   [cyan]aur query 'your question'[/]",
            ],
        )

        console.print(
            Panel("\n\n".join(next_steps), title="[bold]Next Steps[/]", border_style="green"),
        )

        console.print("\n[dim]For help: aur --help or aur <command> --help[/]\n")
