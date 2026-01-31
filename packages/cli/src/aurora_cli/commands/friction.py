"""Friction analysis commands.

Analyze Claude Code session logs to detect failure patterns and extract antigens.
"""

import importlib.util
import json
import sys
from pathlib import Path

import click
from rich.console import Console


console = Console()


def _get_scripts_dir() -> Path:
    """Find the scripts directory."""
    # Try relative to this file (development)
    dev_path = Path(__file__).parents[4] / "scripts"
    if dev_path.exists():
        return dev_path

    # Try relative to cwd (running from repo root)
    cwd_path = Path.cwd() / "scripts"
    if cwd_path.exists():
        return cwd_path

    raise FileNotFoundError("Cannot find scripts directory")


def _load_script_module(script_name: str):
    """Dynamically load a script module."""
    scripts_dir = _get_scripts_dir()
    script_path = scripts_dir / f"{script_name}.py"

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    spec = importlib.util.spec_from_file_location(script_name, script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[script_name] = module
    spec.loader.exec_module(module)
    return module


@click.group("friction", invoke_without_command=True)
@click.argument("sessions_dir", type=click.Path(exists=True, path_type=Path), required=False)
@click.pass_context
def friction_group(ctx: click.Context, sessions_dir: Path | None) -> None:
    """Analyze session friction and extract failure patterns.

    \b
    Usage:
        aur friction <sessions-dir>    Run full analysis pipeline
        aur friction config            Show signal weights

    \b
    Example:
        aur friction ~/.claude/projects/-home-user-myproject/
    """
    if ctx.invoked_subcommand is None:
        if sessions_dir is None:
            click.echo(ctx.get_help())
            return

        # Run full pipeline
        original_argv = sys.argv
        sys.argv = ["friction", str(sessions_dir)]

        try:
            module = _load_script_module("friction")
            result = module.main()
            sys.exit(result)
        finally:
            sys.argv = original_argv


@friction_group.command("config")
def config_command() -> None:
    """Show current friction signal weights."""
    try:
        scripts_dir = _get_scripts_dir()
        config_path = scripts_dir / "friction_config.json"
    except FileNotFoundError:
        console.print("[red]Scripts directory not found[/]")
        sys.exit(1)

    if not config_path.exists():
        console.print("[red]Config not found at expected location[/]")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    console.print("\n[bold]Signal Weights[/]\n")
    for signal, weight in sorted(config["weights"].items(), key=lambda x: -x[1]):
        if weight > 0:
            console.print(f"  {signal:25s} {weight:+.1f}")

    console.print("\n[bold]Thresholds[/]\n")
    for key, value in config["thresholds"].items():
        console.print(f"  {key:30s} {value}")

    console.print(f"\n[dim]Config: {config_path}[/]")
