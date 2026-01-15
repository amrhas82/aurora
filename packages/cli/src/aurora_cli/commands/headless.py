"""Headless command - autonomous Claude execution loop."""

import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console

from aurora_cli.templates.headless import SCRATCHPAD_TEMPLATE

console = Console()


@click.command(name="headless")
@click.option(
    "-t",
    "--tool",
    type=str,
    default="claude",
    help="CLI tool to execute (default: claude)",
)
@click.option(
    "--max",
    "max_iter",
    type=int,
    default=10,
    help="Maximum iterations (default: 10)",
)
@click.option(
    "-p",
    "--prompt",
    "prompt_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Prompt file (default: .aurora/headless/prompt.md)",
)
@click.option(
    "--test-cmd",
    type=str,
    default=None,
    help="Test command for backpressure (e.g., 'pytest tests/')",
)
@click.option(
    "--allow-main",
    is_flag=True,
    default=False,
    help="DANGEROUS: Allow running on main/master branch",
)
def headless_command(
    tool: str,
    max_iter: int,
    prompt_path: Path | None,
    test_cmd: str | None,
    allow_main: bool,
) -> None:
    r"""Autonomous Claude execution loop.

    Reads a prompt file, executes Claude in a loop, and lets Claude manage
    its own state via a scratchpad file. Exits early when Claude sets
    STATUS: DONE in the scratchpad.

    \b
    Examples:
        # Use default prompt (.aurora/headless/prompt.md)
        aur headless -t claude --max=10

        # Custom prompt file
        aur headless -p my-task.md -t claude --max=20

        # With test backpressure
        aur headless --test-cmd "pytest tests/" --max=15
    """
    # 1. Resolve paths
    if prompt_path is None:
        prompt_path = Path.cwd() / ".aurora" / "headless" / "prompt.md"

    scratchpad = Path.cwd() / ".aurora" / "headless" / "scratchpad.md"

    # 2. Validate prompt exists
    if not prompt_path.exists():
        console.print(f"[red]Error: Prompt not found: {prompt_path}[/]")
        console.print("[dim]Create a prompt file with your goal, or use -p to specify one.[/]")
        raise click.Abort()

    # 3. Check tool exists
    if not shutil.which(tool):
        console.print(f"[red]Error: Tool '{tool}' not found in PATH[/]")
        raise click.Abort()

    # 4. Git safety check
    if not allow_main:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            branch = result.stdout.strip()
            if branch in ["main", "master"]:
                console.print("[red]Error: Cannot run on main/master branch[/]")
                console.print(
                    "[dim]Use --allow-main to override, or create a feature branch first.[/]"
                )
                raise click.Abort()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass  # Not a git repo, continue

    # 5. Initialize scratchpad (only if it doesn't exist)
    scratchpad.parent.mkdir(parents=True, exist_ok=True)
    if not scratchpad.exists():
        scratchpad.write_text(SCRATCHPAD_TEMPLATE, encoding="utf-8")

    # 6. Read prompt
    prompt = prompt_path.read_text(encoding="utf-8")

    # 7. Loop
    console.print(f"[bold]Headless execution[/]: {tool} (max {max_iter} iterations)")
    console.print(f"[dim]Prompt: {prompt_path}[/]")
    console.print(f"[dim]Scratchpad: {scratchpad}[/]")
    if test_cmd:
        console.print(f"[dim]Backpressure: {test_cmd}[/]")
    console.print()

    for i in range(1, max_iter + 1):
        # Read current scratchpad state (Claude rewrites it)
        scratchpad_content = scratchpad.read_text(encoding="utf-8")

        # Check for early exit BEFORE running
        if "STATUS: DONE" in scratchpad_content:
            console.print(f"\n[bold green]✓ Goal achieved![/] (iteration {i - 1})")
            console.print(f"[dim]See: {scratchpad}[/]")
            return

        console.print(f"[{i}/{max_iter}] Running iteration...")

        # Build context: prompt + current scratchpad state
        context = f"{prompt}\n\n## Current Scratchpad State:\n{scratchpad_content}"

        # Execute tool (Claude will read/write files directly)
        # For claude: use --print flag with prompt as argument
        # For other tools: pass context via stdin
        try:
            if tool == "claude":
                result = subprocess.run(
                    [tool, "--print", "--dangerously-skip-permissions", context],
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout per iteration
                )
            else:
                result = subprocess.run(
                    [tool],
                    input=context,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout per iteration
                )
        except subprocess.TimeoutExpired:
            console.print("[red]Error: Tool timed out after 10 minutes[/]")
            raise click.Abort()

        if result.returncode != 0:
            console.print(f"[yellow]Warning: Tool exited with code {result.returncode}[/]")
            if result.stderr:
                console.print(f"[dim]{result.stderr[:500]}[/]")

        # Optional backpressure: run tests
        if test_cmd:
            console.print(f"[dim]Running tests: {test_cmd}[/]")
            # User-provided test command requires shell execution
            test_result = subprocess.run(
                test_cmd,
                shell=True,  # nosec B602 - user-provided test command
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for tests
            )
            if test_result.returncode != 0:
                console.print("[yellow]⚠ Tests failed, Claude will see this next iteration[/]")
            else:
                console.print("[green]✓ Tests passed[/]")

        console.print(f"[green]✓[/] Iteration {i} complete")

    # Check final state
    final_scratchpad = scratchpad.read_text(encoding="utf-8")
    if "STATUS: DONE" in final_scratchpad:
        console.print("\n[bold green]✓ Goal achieved![/]")
    else:
        console.print("\n[yellow]⚠ Max iterations reached without STATUS: DONE[/]")

    console.print(f"[dim]See: {scratchpad}[/]")
