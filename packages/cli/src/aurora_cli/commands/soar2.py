"""AURORA SOAR2 Command — SOAR powered by bareagent (Node.js orchestration).

Experimental command that replaces the Python orchestrator's DECOMPOSE/COLLECT/
SYNTHESIZE phases with a Node.js script (soar-agent.js) using bareagent components.

Python handles: ASSESS, RETRIEVE, RECORD, RESPOND (terminal UX)
Node.js handles: DECOMPOSE (plan), COLLECT (execute steps), SYNTHESIZE
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from aurora_core.paths import get_aurora_dir

console = Console()


# ─── Terminal UX (reused from soar.py) ──────────────────────────────


def _print_phase(owner: str, phase_num: int, name: str, description: str, tool: str = "") -> None:
    if owner == "ORCHESTRATOR":
        console.print(f"\n[blue][ORCHESTRATOR][/] Phase {phase_num}: {name}")
    elif owner == "BAREAGENT":
        console.print(f"\n[magenta][BAREAGENT → {tool}][/] Phase {phase_num}: {name}")
    else:
        console.print(f"\n[green][LLM → {tool}][/] Phase {phase_num}: {name}")
    console.print(f"  {description}")


def _format_markdown_answer(text: str) -> str:
    """Format markdown answer for terminal display."""
    from aurora_cli.commands.soar import _format_markdown_answer as fmt

    return fmt(text)


# ─── Async orchestration ───────────────────────────────────────────


async def _run_soar2(
    query: str,
    model: str,
    tool: str,
    verbose: bool,
    context_files: list[str] | None,
) -> dict[str, Any]:
    """Run the SOAR2 pipeline.

    Returns dict with: answer, formatted_answer, confidence, metadata
    """
    from aurora_cli.bareagent.bridge import BareagentBridge
    from aurora_cli.config import Config
    from aurora_core.store.sqlite import SQLiteStore
    from aurora_soar.phases.assess import assess_complexity
    from aurora_soar.phases.record import record_pattern_lightweight
    from aurora_soar.phases.retrieve import retrieve_context

    # Load config
    try:
        cli_config = Config()
    except Exception:
        cli_config = None

    # Memory store
    db_path = cli_config.get_db_path() if cli_config else "./.aurora/memory.db"
    store = SQLiteStore(db_path)

    # ── Phase 1: ASSESS ──
    _print_phase("ORCHESTRATOR", 1, "Assess", "Analyzing query complexity...")
    assess_result = assess_complexity(query)
    complexity = assess_result["complexity"]
    console.print(f"  [cyan]Complexity: {complexity}[/]")

    # ── Phase 2: RETRIEVE ──
    _print_phase("ORCHESTRATOR", 2, "Retrieve", "Looking up memory index...")
    retrieve_result = retrieve_context(query, complexity, store)
    chunks_count = retrieve_result.get("chunks_retrieved", 0)
    console.print(f"  [cyan]Matched: {chunks_count} chunks from memory[/]")

    # Build context strings from chunks
    context_strings = []
    for chunk in retrieve_result.get("code_chunks", []):
        text = getattr(chunk, "content", None) or getattr(chunk, "text", str(chunk))
        if text:
            context_strings.append(text[:500])  # Truncate long chunks

    # Add context files if provided
    if context_files:
        for fpath in context_files:
            try:
                content = Path(fpath).read_text()[:2000]
                context_strings.append(f"[File: {fpath}]\n{content}")
            except Exception:
                pass

    # ── Phases 3-6: DECOMPOSE + COLLECT + SYNTHESIZE via bareagent ──
    _print_phase("BAREAGENT", 3, "Decompose", "Breaking query into steps...", tool)

    bridge = BareagentBridge(tool=tool, model=model)

    answer = ""
    confidence = 0.7
    traceability: list[dict[str, Any]] = []
    steps_completed = 0
    steps_total = 0
    error_msg = None

    async for event in bridge.run(query, context_strings, complexity):
        if event.type == "plan:ready":
            steps = event.data.get("steps", [])
            steps_total = len(steps)
            console.print(f"  [cyan]✓ {steps_total} steps planned[/]")

            # Show step table
            if verbose and steps:
                from rich.table import Table

                table = Table(show_header=True, header_style="bold")
                table.add_column("#", width=4)
                table.add_column("Action", width=60)
                table.add_column("Deps", width=10)
                for s in steps:
                    deps = ", ".join(s.get("dependsOn", []))
                    table.add_row(s["id"], s["action"][:60], deps or "—")
                console.print(table)

            _print_phase("BAREAGENT", 5, "Collect", "Executing steps...", tool)

        elif event.type == "wave:start":
            wave_num = event.data.get("wave", "?")
            wave_ids = event.data.get("steps", [])
            console.print(f"  [bold cyan][Wave {wave_num}: {', '.join(wave_ids)}][/]")

        elif event.type == "step:start":
            step_id = event.data.get("id", "?")
            console.print(f"  [dim]→ {step_id} running...[/]")

        elif event.type == "step:done":
            step_id = event.data.get("id", "?")
            steps_completed += 1
            console.print(f"  [cyan]✓ {step_id} complete ({steps_completed}/{steps_total})[/]")

        elif event.type == "step:fail":
            step_id = event.data.get("id", "?")
            err = event.data.get("error", "unknown")
            console.print(f"  [red]✗ {step_id} failed: {err}[/]")

        elif event.type == "synthesis:done":
            _print_phase("BAREAGENT", 6, "Synthesize", "Combining findings...", tool)
            answer = event.data.get("answer", "")
            confidence = event.data.get("confidence", 0.7)
            traceability = event.data.get("traceability", [])
            console.print(f"  [cyan]✓ Answer ready (confidence: {confidence:.0%})[/]")

        elif event.type == "error":
            error_msg = event.data.get("message", "Unknown error")
            console.print(f"  [red]Error: {error_msg}[/]")

    if not answer and error_msg:
        raise RuntimeError(f"SOAR2 failed: {error_msg}")

    if not answer:
        raise RuntimeError("SOAR2 produced no answer")

    # ── Phase 7: RECORD ──
    _print_phase("ORCHESTRATOR", 7, "Record", "Caching reasoning pattern...")

    # Create a lightweight SynthesisResult-like object for record_pattern_lightweight
    from aurora_soar.phases.synthesize import SynthesisResult

    synthesis_result = SynthesisResult(
        answer=answer,
        confidence=confidence,
        traceability=traceability,
        metadata={"bareagent": True, "steps_completed": steps_completed},
        timing={},
    )
    # Add summary attribute for record_pattern_lightweight
    synthesis_result.summary = answer[:500]

    soar_dir = get_aurora_dir() / "soar"
    soar_dir.mkdir(parents=True, exist_ok=True)
    log_path = str(soar_dir / "soar2_last.log")

    try:
        record_result = record_pattern_lightweight(store, query, synthesis_result, log_path)
        cached = record_result.cached
        console.print(f"  [cyan]✓ Pattern {'cached' if cached else 'recorded'}[/]")
    except Exception as e:
        console.print(f"  [yellow]⚠ Record failed: {e}[/]")

    # ── Phase 8: RESPOND ──
    _print_phase("ORCHESTRATOR", 8, "Respond", "Formatting response...")
    console.print("  [cyan]✓ Response formatted[/]")

    return {
        "answer": answer,
        "formatted_answer": answer,
        "confidence": confidence,
        "metadata": {
            "engine": "bareagent",
            "steps_total": steps_total,
            "steps_completed": steps_completed,
            "complexity": complexity,
        },
    }


# ─── Click Command ─────────────────────────────────────────────────


@click.command(name="soar2")
@click.argument("query")
@click.option(
    "--model",
    "-m",
    type=click.Choice(["sonnet", "opus"]),
    default="sonnet",
    help="Model to use (default: sonnet)",
)
@click.option(
    "--tool",
    "-t",
    type=str,
    default=None,
    help="CLI tool to pipe to (default: claude, or AURORA_SOAR_TOOL env var)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show verbose output",
)
@click.option(
    "--context",
    "-c",
    "context_files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Context files. Can be used multiple times.",
)
def soar2_command(
    query: str,
    model: str,
    tool: str | None,
    verbose: bool,
    context_files: tuple[Path, ...],
) -> None:
    r"""Execute SOAR query via bareagent orchestration (experimental).

    Uses Node.js bareagent for DECOMPOSE/COLLECT/SYNTHESIZE phases,
    while keeping ASSESS/RETRIEVE/RECORD in Python.

    \b
    [ORCHESTRATOR] Phase 1: ASSESS     - Complexity assessment (Python)
    [ORCHESTRATOR] Phase 2: RETRIEVE   - Memory lookup (Python)
    [BAREAGENT]    Phase 3: DECOMPOSE  - Break into steps (Node.js)
    [BAREAGENT]    Phase 5: COLLECT    - Execute steps (Node.js)
    [BAREAGENT]    Phase 6: SYNTHESIZE - Combine results (Node.js)
    [ORCHESTRATOR] Phase 7: RECORD     - Cache pattern (Python)
    [ORCHESTRATOR] Phase 8: RESPOND    - Format answer (Python)

    \b
    Examples:
        aur soar2 "What is SOAR?"
        aur soar2 "Compare React and Vue" --tool cursor
        aur soar2 "Explain ACT-R memory" --model opus --verbose
    """
    from aurora_cli.config import Config

    # Load config for defaults
    try:
        cli_config = Config()
    except Exception:
        cli_config = None

    # Resolve tool
    if tool is None:
        tool = os.environ.get(
            "AURORA_SOAR_TOOL",
            cli_config.soar_default_tool if cli_config else "claude",
        )

    # Resolve model
    if model == "sonnet":
        env_model = os.environ.get("AURORA_SOAR_MODEL")
        if env_model and env_model.lower() in ("sonnet", "opus"):
            model = env_model.lower()
        elif cli_config and cli_config.soar_default_model:
            model = cli_config.soar_default_model

    # Validate tool
    if not shutil.which(tool):
        console.print(f"[red]Error: Tool '{tool}' not found in PATH[/]")
        console.print(f"Install {tool} or use --tool to specify another")
        raise SystemExit(1)

    # Validate node
    if not shutil.which("node"):
        console.print("[red]Error: Node.js not found in PATH[/]")
        console.print("Install Node.js >= 18 for bareagent orchestration")
        raise SystemExit(1)

    # Header
    console.print()
    console.print(
        Panel(
            f"[cyan]{query}[/]",
            title="[bold]Aurora SOAR2[/] [dim](bareagent)[/]",
            subtitle=f"[dim]Tool: {tool}[/]",
            border_style="magenta",
        ),
    )

    start_time = time.time()

    # Ensure .aurora/soar exists
    try:
        get_aurora_dir()
    except RuntimeError as e:
        console.print(f"\n[red]Error:[/] {e}")
        console.print("\n[dim]Run this command to initialize your project:[/]")
        console.print("  [cyan]aur init[/]")
        raise SystemExit(1)

    console.print("[dim]Initializing...[/]\n")

    # Run async pipeline
    ctx_files = [str(f) for f in context_files] if context_files else None
    try:
        result = asyncio.run(_run_soar2(query, model, tool, verbose, ctx_files))
    except Exception as e:
        console.print(f"\n[red]Error during SOAR2 execution: {e}[/]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise SystemExit(1)

    # Display final answer
    elapsed_time = time.time() - start_time
    raw_answer = result.get("formatted_answer", result.get("answer", "No answer generated"))
    answer = _format_markdown_answer(raw_answer)

    console.print()
    console.print(
        Panel(
            answer,
            title="[bold]Final Answer[/]",
            border_style="green",
        ),
    )

    console.print(f"\n[dim]Completed in {elapsed_time:.1f}s[/]")
    meta = result.get("metadata", {})
    console.print(
        f"[dim]Engine: bareagent | Steps: {meta.get('steps_completed', 0)}/{meta.get('steps_total', 0)} | "
        f"Complexity: {meta.get('complexity', '?')}[/]"
    )
