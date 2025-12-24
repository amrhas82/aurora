"""Init command for AURORA CLI setup."""

import json
import os
from pathlib import Path

import click

from aurora_cli.config import CONFIG_SCHEMA


@click.command(name="init")
def init_command():
    """Initialize AURORA configuration.

    Creates ~/.aurora/config.json with defaults and optional API key.
    Optionally indexes the current directory for memory search.
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
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        click.echo(
            f"✗ Error: Cannot create directory {config_dir}. Check permissions.", err=True
        )
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
    except PermissionError:
        click.echo(
            f"✗ Error: Cannot write to {config_path}. Check permissions.", err=True
        )
        return

    # Set secure file permissions (user read/write only)
    try:
        os.chmod(config_path, 0o600)
    except Exception as e:
        click.echo(f"⚠ Warning: Could not set secure permissions on {config_path}: {e}")

    click.echo(f"✓ Configuration created at {config_path}")

    # Prompt to index current directory
    if click.confirm("Index current directory for memory search?", default=True):
        click.echo("⠋ Indexing files...")

        # Import memory command (will be implemented in Phase 4)
        try:
            from aurora_cli.commands.memory import index_command
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(index_command, ["."])

            if result.exit_code == 0:
                click.echo("✓ Indexed current directory")
            else:
                click.echo(f"⚠ Warning: Indexing failed: {result.output}")
        except ImportError:
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
