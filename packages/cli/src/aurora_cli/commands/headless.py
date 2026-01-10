"""Simple headless command - pipe prompt to CLI tool in a loop."""

import shutil
import subprocess
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command(name="headless")
@click.argument(
    "prompt_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--max-iter",
    "-m",
    type=int,
    default=10,
    help="Maximum number of iterations (default: 10)",
)
@click.option(
    "--tool",
    "-t",
    type=str,
    default="claude",
    help="CLI tool to pipe to (default: claude)",
)
@click.option(
    "--allow-main",
    is_flag=True,
    default=False,
    help="DANGEROUS: Allow running on main/master branch",
)
def headless_command(
    prompt_path: Path | None,
    max_iter: int,
    tool: str,
    allow_main: bool,
) -> None:
    """Simple headless: pipe prompt to CLI tool in a loop.

    Reads a prompt file, pipes it to an external CLI tool (like claude),
    and tracks iterations in a scratchpad file.

    Examples:
        # Use default prompt (.aurora/headless/prompt.md)
        aur headless

        # Custom prompt and tool
        aur headless my-task.md --tool cursor --max-iter 20
    """
    # 1. Resolve paths
    if prompt_path is None:
        prompt_path = Path.cwd() / ".aurora" / "headless" / "prompt.md"

    scratchpad = Path.cwd() / ".aurora" / "headless" / "scratchpad.md"

    # 2. Validate prompt exists
    if not prompt_path.exists():
        console.print(f"[red]Error: Prompt not found: {prompt_path}[/]")
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
                console.print(
                    "[red]Error: Cannot run on main/master (use --allow-main to override)[/]"
                )
                raise click.Abort()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass  # Not a git repo, continue

    # 5. Initialize scratchpad
    scratchpad.parent.mkdir(parents=True, exist_ok=True)
    scratchpad.write_text("# Headless Execution\n\n", encoding="utf-8")

    # 6. Read prompt
    prompt = prompt_path.read_text(encoding="utf-8")

    # 7. Loop
    console.print(f"Running {max_iter} iterations with tool: {tool}")

    for i in range(1, max_iter + 1):
        console.print(f"\n[{i}/{max_iter}] Running iteration...")

        # Build context: prompt + previous work
        previous_work = scratchpad.read_text(encoding="utf-8")
        context = f"{prompt}\n\n## Previous Work:\n{previous_work}"

        # Pipe to tool
        try:
            result = subprocess.run(
                [tool, "-p"],
                input=context,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
        except subprocess.TimeoutExpired:
            console.print(f"[red]Error: Tool timed out after 5 minutes[/]")
            raise click.Abort()

        if result.returncode != 0:
            console.print(f"[red]Error: Tool failed: {result.stderr}[/]")
            raise click.Abort()

        # Append to scratchpad
        with scratchpad.open("a", encoding="utf-8") as f:
            f.write(f"\n## Iteration {i}\n{result.stdout}\n")

        console.print(f"[green]✓[/] Iteration {i} complete")

    console.print(f"\n[bold green]✓ Done![/] See: {scratchpad}")
