"""Init command for AURORA CLI setup."""

import json
import os
from pathlib import Path

import click

from aurora_cli.config import CONFIG_SCHEMA
from aurora_cli.errors import ErrorHandler


@click.command(name="init")
def init_command():
    """Initialize AURORA configuration.

    Creates ~/.aurora/config.json with defaults and optional API key.
    Optionally indexes the current directory for memory search.

    \b
    Examples:
        # Basic initialization (will prompt for API key)
        aur init

        \b
        # After initialization, set API key in environment
        export ANTHROPIC_API_KEY=sk-ant-...
        aur query "your question"
    """
    config_dir = Path.home() / ".aurora"
    config_path = config_dir / "config.json"

    # Check if config already exists
    if config_path.exists():
        overwrite = click.confirm(
            "Config file already exists at ~/.aurora/config.json. Overwrite?", default=False
        )
        if not overwrite:
            click.echo("Keeping existing config.")
            return

    # Prompt for API key
    api_key = click.prompt(
        "Enter Anthropic API key (or press Enter to skip)",
        default="",
        show_default=False,
    )

    # Validate API key format if provided
    if api_key and not api_key.startswith("sk-ant-"):
        click.echo(
            "⚠ Warning: API key should start with 'sk-ant-'. This may not be a valid Anthropic API key."
        )
        if not click.confirm("Continue anyway?", default=True):
            click.echo("Aborted.")
            return

    # Create config directory
    error_handler = ErrorHandler()
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        error_msg = error_handler.handle_path_error(e, str(config_dir), "creating config directory")
        click.echo(error_msg, err=True)
        return
    except Exception as e:
        error_msg = error_handler.handle_path_error(e, str(config_dir), "creating config directory")
        click.echo(error_msg, err=True)
        return

    # Prepare config data
    config_data = CONFIG_SCHEMA.copy()

    # Set API key if provided (non-empty)
    if api_key and api_key.strip():
        config_data["llm"]["anthropic_api_key"] = api_key.strip()
    else:
        # Ensure API key is None if empty
        config_data["llm"]["anthropic_api_key"] = None

    # Write config file
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
    except PermissionError as e:
        error_msg = error_handler.handle_path_error(e, str(config_path), "writing config file")
        click.echo(error_msg, err=True)
        return
    except Exception as e:
        error_msg = error_handler.handle_config_error(e, str(config_path))
        click.echo(error_msg, err=True)
        return

    # Set secure file permissions (user read/write only)
    try:
        os.chmod(config_path, 0o600)
    except Exception as e:
        click.echo(f"⚠ Warning: Could not set secure permissions on {config_path}: {e}")

    click.echo(f"✓ Configuration created at {config_path}")

    # Prompt to index current directory
    if click.confirm("Index current directory for memory search?", default=True):
        # Import memory indexing functionality
        try:
            from aurora_core.store import SQLiteStore
            from aurora_cli.memory_manager import MemoryManager
            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

            console = Console()
            console.print("[bold]Indexing current directory...[/]")

            # Initialize memory store
            db_path = Path.cwd() / "aurora.db"
            memory_store = SQLiteStore(str(db_path))
            manager = MemoryManager(memory_store)

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
                    f"[bold green]✓[/] Indexed {stats.files_indexed} files, "
                    f"{stats.chunks_created} chunks in {stats.duration_seconds:.2f}s"
                )
            else:
                console.print("[yellow]⚠[/] No Python files found to index in current directory")

        except ImportError as e:
            # Memory command not yet implemented - stub for Phase 3
            click.echo("⚠ Memory indexing not yet implemented (Phase 4)")

    # Display summary
    click.echo("\n" + "=" * 50)
    click.echo("✓ AURORA CLI initialized successfully!")
    click.echo("=" * 50)
    click.echo(f"Config file: {config_path}")
    if api_key:
        click.echo("API key: Configured")
    else:
        click.echo("API key: Not configured (set ANTHROPIC_API_KEY or edit config)")
    click.echo("\nNext steps:")
    click.echo('  1. Run "aur query \'your question\'" to start')
    if not api_key:
        click.echo("  2. Set API key: export ANTHROPIC_API_KEY=sk-ant-...")
