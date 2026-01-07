"""AURORA SOAR Command - Terminal orchestrator wrapper.

This module provides a thin wrapper around SOAROrchestrator that:
1. Creates a CLIPipeLLMClient for piping to external CLI tools
2. Displays terminal UX with phase ownership ([ORCHESTRATOR] vs [LLM -> tool])
3. Delegates all phase logic to SOAROrchestrator

The actual phase implementations live in aurora_soar.orchestrator.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

from aurora_core.paths import get_aurora_dir

console = Console()


# Phase ownership mapping - which phases are pure Python vs need LLM
PHASE_OWNERS = {
    "assess": "ORCHESTRATOR",
    "retrieve": "ORCHESTRATOR",
    "decompose": "LLM",
    "verify": "LLM",
    "route": "ORCHESTRATOR",
    "collect": "LLM",
    "synthesize": "LLM",
    "record": "ORCHESTRATOR",
    "respond": "LLM",
}

# Phase numbers
PHASE_NUMBERS = {
    "assess": 1,
    "retrieve": 2,
    "decompose": 3,
    "verify": 4,
    "route": 5,
    "collect": 6,
    "synthesize": 7,
    "record": 8,
    "respond": 9,
}

# Phase descriptions shown during execution
PHASE_DESCRIPTIONS = {
    "assess": "Analyzing query complexity...",
    "retrieve": "Looking up memory index...",
    "decompose": "Breaking query into subgoals...",
    "verify": "Validating decomposition...",
    "route": "Assigning agents to subgoals...",
    "collect": "Researching subgoals...",
    "synthesize": "Combining findings...",
    "record": "Caching reasoning pattern...",
    "respond": "Formatting response...",
}


# ============================================================================
# Helper Functions
# ============================================================================


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response.

    Handles:
    - Plain JSON
    - JSON wrapped in ```json blocks
    - JSON with surrounding commentary

    Args:
        text: LLM response text

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If no valid JSON found
    """
    # Try to find ```json blocks first
    json_block_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in response: {text[:200]}...")


def _ensure_soar_dir() -> Path:
    """Ensure .aurora/soar/ directory exists.

    Returns:
        Path to soar directory
    """
    aurora_dir = get_aurora_dir()
    soar_dir = aurora_dir / "soar"
    soar_dir.mkdir(parents=True, exist_ok=True)
    return soar_dir


def _print_phase(owner: str, phase_num: int, name: str, description: str, tool: str = "") -> None:
    """Print phase header with owner information.

    Args:
        owner: "ORCHESTRATOR" or "LLM"
        phase_num: Phase number (1-9)
        name: Phase name
        description: Brief description
        tool: Tool name for LLM phases
    """
    if owner == "ORCHESTRATOR":
        console.print(f"\n[blue][ORCHESTRATOR][/] Phase {phase_num}: {name}")
    else:
        console.print(f"\n[green][LLM → {tool}][/] Phase {phase_num}: {name}")
    console.print(f"  {description}")


def _print_phase_result(phase_num: int, result: dict[str, Any]) -> None:
    """Print phase result summary.

    Args:
        phase_num: Phase number (1-9)
        result: Phase result dictionary
    """
    if phase_num == 1:
        # Assess phase
        complexity = result.get("complexity", "UNKNOWN")
        console.print(f"  [cyan]Complexity: {complexity}[/]")
    elif phase_num == 2:
        # Retrieve phase
        chunks = result.get("chunks_retrieved", 0)
        console.print(f"  [cyan]Matched: {chunks} chunks from memory[/]")
    elif phase_num == 3:
        # Decompose phase
        count = result.get("subgoal_count", 0)
        console.print(f"  [cyan]✓ {count} subgoals identified[/]")
    elif phase_num == 4:
        # Verify phase
        verdict = result.get("verdict", "UNKNOWN")
        console.print(f"  [cyan]✓ {verdict}[/]")
    elif phase_num == 5:
        # Route phase
        agents = result.get("agents", [])
        console.print(f"  [cyan]Assigned: {', '.join(agents) if agents else 'no agents'}[/]")
    elif phase_num == 6:
        # Collect phase
        count = result.get("findings_count", 0)
        console.print(f"  [cyan]✓ Research complete ({count} findings)[/]")
    elif phase_num == 7:
        # Synthesize phase
        confidence = result.get("confidence", 0.0)
        console.print(f"  [cyan]✓ Answer ready (confidence: {confidence:.0%})[/]")
    elif phase_num == 8:
        # Record phase
        cached = result.get("cached", False)
        console.print(f"  [cyan]✓ Pattern {'cached' if cached else 'recorded'}[/]")
    elif phase_num == 9:
        # Respond phase
        console.print("  [cyan]✓ Response formatted[/]")


def _create_phase_callback(tool: str):
    """Create a phase callback for terminal display.

    Args:
        tool: CLI tool name for LLM phases

    Returns:
        Callback function for SOAROrchestrator
    """

    def callback(phase_name: str, status: str, result_summary: dict[str, Any]) -> None:
        """Display phase information in terminal."""
        owner = PHASE_OWNERS.get(phase_name, "ORCHESTRATOR")
        phase_num = PHASE_NUMBERS.get(phase_name, 0)
        description = PHASE_DESCRIPTIONS.get(phase_name, "Processing...")

        if status == "before":
            _print_phase(owner, phase_num, phase_name.capitalize(), description, tool)
        else:  # status == "after"
            _print_phase_result(phase_num, result_summary)

    return callback


# ============================================================================
# Main Command
# ============================================================================


@click.command(name="soar")
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
def soar_command(query: str, model: str, tool: str | None, verbose: bool) -> None:
    r"""Execute 9-phase SOAR query with terminal orchestration.

    Runs the SOAR pipeline via SOAROrchestrator, piping to external LLM tools:

    \b
    [ORCHESTRATOR] Phase 1: ASSESS    - Complexity assessment (Python)
    [ORCHESTRATOR] Phase 2: RETRIEVE  - Memory lookup (Python)
    [LLM]          Phase 3: DECOMPOSE - Break into subgoals
    [LLM]          Phase 4: VERIFY    - Validate decomposition
    [ORCHESTRATOR] Phase 5: ROUTE     - Agent assignment (Python)
    [LLM]          Phase 6: COLLECT   - Research/execute
    [LLM]          Phase 7: SYNTHESIZE - Combine results
    [ORCHESTRATOR] Phase 8: RECORD    - Cache pattern (Python)
    [LLM]          Phase 9: RESPOND   - Format answer

    \b
    Examples:
        aur soar "What is SOAR orchestrator?"
        aur soar "Explain ACT-R memory" --tool cursor
        aur soar "State of AI?" --model opus --verbose
    """
    # Resolve tool from CLI flag -> env var -> default
    if tool is None:
        tool = os.environ.get("AURORA_SOAR_TOOL", "claude")

    # Validate tool exists in PATH
    if not shutil.which(tool):
        console.print(f"[red]Error: Tool '{tool}' not found in PATH[/]")
        console.print(f"Install {tool} or use --tool to specify another")
        raise SystemExit(1)

    # Display header
    console.print("[bold]╭─────────── Aurora SOAR ───────────╮[/]")
    console.print(f"[bold]│[/] Query: {query[:40]}{'...' if len(query) > 40 else ''}")
    console.print("[bold]╰───────────────────────────────────╯[/]")

    start_time = time.time()
    soar_dir = _ensure_soar_dir()

    # Import here to avoid circular imports and allow lazy loading
    from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
    from aurora_core.config.loader import Config
    from aurora_core.store.memory import MemoryStore
    from aurora_soar.agent_registry import AgentRegistry
    from aurora_soar.orchestrator import SOAROrchestrator

    # Create CLI-based LLM client
    try:
        llm_client = CLIPipeLLMClient(tool=tool, soar_dir=soar_dir)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
        raise SystemExit(1)

    # Create phase callback for terminal display
    phase_callback = _create_phase_callback(tool)

    # Load dependencies
    config = Config.load()
    store = MemoryStore()  # Use in-memory store for CLI
    agent_registry = AgentRegistry()

    # Create orchestrator with CLI client and callback
    orchestrator = SOAROrchestrator(
        store=store,
        agent_registry=agent_registry,
        config=config,
        reasoning_llm=llm_client,
        solving_llm=llm_client,
        phase_callback=phase_callback,
    )

    # Execute SOAR pipeline
    try:
        verbosity = "verbose" if verbose else "normal"
        result = orchestrator.execute(query, verbosity=verbosity)
    except Exception as e:
        console.print(f"\n[red]Error during SOAR execution: {e}[/]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise SystemExit(1)

    # Display final answer
    elapsed_time = time.time() - start_time
    answer = result.get("formatted_answer", result.get("answer", "No answer generated"))

    console.print()
    console.print(
        Panel(
            answer,
            title="[bold]Final Answer[/]",
            border_style="green",
        )
    )

    # Show metadata
    console.print(f"\n[dim]Completed in {elapsed_time:.1f}s[/]")

    # Show log path if available
    log_path = result.get("metadata", {}).get("log_path")
    if log_path:
        console.print(f"[dim]Log: {log_path}[/]")
