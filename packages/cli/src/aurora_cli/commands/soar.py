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
# Note: Simplified 7-phase pipeline (route merged into verify)
PHASE_OWNERS = {
    "assess": "ORCHESTRATOR",
    "retrieve": "ORCHESTRATOR",
    "decompose": "LLM",
    "verify": "LLM",  # Now includes agent assignment (was separate route phase)
    "collect": "LLM",
    "synthesize": "LLM",
    "record": "ORCHESTRATOR",
    "respond": "LLM",
}

# Phase numbers (7-phase simplified pipeline)
PHASE_NUMBERS = {
    "assess": 1,
    "retrieve": 2,
    "decompose": 3,
    "verify": 4,  # Includes agent assignment
    "collect": 5,  # Was 6
    "synthesize": 6,  # Was 7
    "record": 7,  # Was 8
    "respond": 8,  # Was 9
}

# Phase descriptions shown during execution
PHASE_DESCRIPTIONS = {
    "assess": "Analyzing query complexity...",
    "retrieve": "Looking up memory index...",
    "decompose": "Breaking query into subgoals...",
    "verify": "Validating decomposition and assigning agents...",
    "collect": "Researching subgoals...",
    "synthesize": "Combining findings...",
    "record": "Caching reasoning pattern...",
    "respond": "Formatting response...",
}


# ============================================================================
# Helper Functions
# ============================================================================


def _format_markdown_answer(text: str) -> str:
    """Format markdown answer with better visual hierarchy for terminal.

    Args:
        text: Raw markdown text

    Returns:
        Formatted text with visual separators and proper spacing
    """
    # First, ensure paragraph breaks are preserved
    # If text has no blank lines but has multiple sentences, add paragraph spacing
    if "\n\n" not in text and len(text) > 500:
        # Split on sentence boundaries that look like paragraph breaks
        # (period followed by space and capital letter, with certain keywords)
        import re

        # Add blank lines before common paragraph starters
        paragraph_starters = [
            r"\. (The next|On the|In the|After|When|But|However|Meanwhile|Finally|Later|Then|Now|As |It was|She |He |They |We |This |That )",
            r"\. \n",  # Already has newline
        ]
        for pattern in paragraph_starters:
            text = re.sub(pattern, lambda m: ". \n\n" + m.group(0)[2:], text)

    lines = text.split("\n")
    formatted_lines = []
    in_code_block = False

    for line in lines:
        # Detect code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            formatted_lines.append(line)
            continue

        # Don't format inside code blocks
        if in_code_block:
            formatted_lines.append(line)
            continue

        # Format H2 headers (##)
        if line.strip().startswith("## "):
            title = line.strip()[3:]
            formatted_lines.append("")
            formatted_lines.append(f"[bold cyan]{title}[/]")
            formatted_lines.append("─" * min(len(title), 80))
            continue

        # Format H3 headers (###)
        if line.strip().startswith("### "):
            title = line.strip()[4:]
            formatted_lines.append("")
            formatted_lines.append(f"[bold]{title}[/]")
            continue

        # Format bullet points
        if line.strip().startswith("- "):
            content = line.strip()[2:]
            formatted_lines.append(f"  • {content}")
            continue

        # Format numbered lists
        if line.strip() and line.strip()[0].isdigit() and ". " in line.strip()[:4]:
            formatted_lines.append(f"  {line.strip()}")
            continue

        # Format bold (**text**)
        line = line.replace("**", "[bold]").replace("**", "[/]")

        # Regular line
        formatted_lines.append(line)

    return "\n".join(formatted_lines)


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
        phase_num: Phase number (1-8, simplified pipeline)
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
        # Verify phase (now includes agent assignment)
        verdict = result.get("verdict", "UNKNOWN")
        score = result.get("overall_score", 0.0)
        agents_assigned = result.get("agents_assigned", 0)

        # Check if this is a devil's advocate pass (0.6 <= score < 0.7)
        if verdict == "PASS" and 0.6 <= score < 0.7:
            console.print(f"  [yellow]⚠️  PASS (marginal - score: {score:.2f})[/]")
            issues_count = len(result.get("issues", []))
            console.print(
                f"  [yellow]└─ {issues_count} concerns, {agents_assigned} subgoals routed[/]"
            )
        else:
            if agents_assigned > 0:
                console.print(f"  [cyan]✓ {verdict} ({agents_assigned} subgoals routed)[/]")
            else:
                console.print(f"  [cyan]✓ {verdict}[/]")
    elif phase_num == 5:
        # Collect phase (was 6)
        count = result.get("findings_count", 0)
        console.print(f"  [cyan]✓ Research complete ({count} findings)[/]")
    elif phase_num == 6:
        # Synthesize phase (was 7)
        confidence = result.get("confidence", 0.0)
        console.print(f"  [cyan]✓ Answer ready (confidence: {confidence:.0%})[/]")
    elif phase_num == 7:
        # Record phase (was 8)
        cached = result.get("cached", False)
        console.print(f"  [cyan]✓ Pattern {'cached' if cached else 'recorded'}[/]")
    elif phase_num == 8:
        # Respond phase (was 9)
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
    r"""Execute SOAR query with terminal orchestration (7+1 phase pipeline).

    Runs the SOAR pipeline via SOAROrchestrator, piping to external LLM tools:

    \b
    [ORCHESTRATOR] Phase 1: ASSESS     - Complexity assessment (Python)
    [ORCHESTRATOR] Phase 2: RETRIEVE   - Memory lookup (Python)
    [LLM]          Phase 3: DECOMPOSE  - Break into subgoals
    [LLM]          Phase 4: VERIFY     - Validate & assign agents
    [LLM]          Phase 5: COLLECT    - Research/execute
    [LLM]          Phase 6: SYNTHESIZE - Combine results
    [ORCHESTRATOR] Phase 7: RECORD     - Cache pattern (Python)
    [LLM]          Phase 8: RESPOND    - Format answer

    \b
    Examples:
        aur soar "What is SOAR orchestrator?"
        aur soar "Explain ACT-R memory" --tool cursor
        aur soar "State of AI?" --model opus --verbose
    """
    # Load config for defaults
    from aurora_cli.config import load_config

    try:
        cli_config = load_config()
    except Exception:
        # If config loading fails, use hardcoded defaults
        cli_config = None

    # Resolve tool from CLI flag -> env var -> config -> default
    if tool is None:
        tool = os.environ.get(
            "AURORA_SOAR_TOOL",
            cli_config.soar_default_tool if cli_config else "claude",
        )

    # Resolve model from CLI flag -> env var -> config -> default
    if model == "sonnet":  # Check if it's the Click default
        env_model = os.environ.get("AURORA_SOAR_MODEL")
        if env_model and env_model.lower() in ("sonnet", "opus"):
            model = env_model.lower()
        elif cli_config and cli_config.soar_default_model:
            model = cli_config.soar_default_model

    # Validate tool exists in PATH
    if not shutil.which(tool):
        console.print(f"[red]Error: Tool '{tool}' not found in PATH[/]")
        console.print(f"Install {tool} or use --tool to specify another")
        raise SystemExit(1)

    # Display header with full query in a proper box
    console.print()
    console.print(
        Panel(
            f"[cyan]{query}[/]",
            title="[bold]Aurora SOAR[/]",
            subtitle=f"[dim]Tool: {tool}[/]",
            border_style="blue",
        )
    )

    start_time = time.time()
    soar_dir = _ensure_soar_dir()

    # Import here to avoid circular imports and allow lazy loading
    from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
    from aurora_core.config.loader import Config
    from aurora_core.store.sqlite import SQLiteStore
    from aurora_soar.agent_registry import AgentRegistry
    from aurora_soar.orchestrator import SOAROrchestrator

    # Create CLI-based LLM client
    try:
        llm_client = CLIPipeLLMClient(tool=tool, model=model, soar_dir=soar_dir)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
        raise SystemExit(1)

    # Create phase callback for terminal display
    phase_callback = _create_phase_callback(tool)

    # Load dependencies
    config = Config.load()
    store = SQLiteStore()  # Use SQLite store for persistence (~/.aurora/memory.db)

    # Discover available agents using the same system as 'aur agents list'
    from aurora_cli.commands.agents import get_manifest
    from aurora_soar.agent_registry import AgentInfo as SoarAgentInfo

    manifest = get_manifest()  # Uses its own config loading

    # Populate agent registry with discovered agents
    agent_registry = AgentRegistry()
    for agent in manifest.agents:
        agent_registry.register(
            SoarAgentInfo(
                id=agent.id,
                name=agent.role or agent.id,
                description=agent.goal or "",
                capabilities=agent.skills or [],
                agent_type="local",
            )
        )

    # Show agent discovery count
    agent_count = len(manifest.agents)
    console.print(f"[dim]Discovered {agent_count} agent{'s' if agent_count != 1 else ''}[/]\n")

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
    raw_answer = result.get("formatted_answer", result.get("answer", "No answer generated"))
    answer = _format_markdown_answer(raw_answer)

    # Check if verification had devil's advocate concerns
    phases = result.get("metadata", {}).get("phases", {})
    verify_phase = phases.get("phase4_verify", {})
    verification = verify_phase.get("verification", {})
    overall_score = verification.get("overall_score", 1.0)
    verdict = verification.get("verdict", "UNKNOWN")
    issues = verification.get("issues", [])
    suggestions = verification.get("suggestions", [])

    # Show verification concerns box if marginal pass
    if verdict == "PASS" and 0.6 <= overall_score < 0.7 and issues:
        console.print()
        concern_text = f"This decomposition passed verification but had concerns (score {overall_score:.2f})\n\n"
        concern_text += "[bold]Top Issues:[/]\n"
        for i, issue in enumerate(issues[:5], 1):
            concern_text += f" {i}. {issue}\n"

        if len(issues) > 5:
            concern_text += f" ... and {len(issues) - 5} more\n"

        if suggestions:
            concern_text += f"\n[bold]Suggestions:[/] {len(suggestions)} improvements recommended\n"

        # Get log path for full details
        log_path = result.get("metadata", {}).get("log_path")
        if log_path:
            concern_text += f"\n[dim]See full analysis: {log_path}[/]"

        console.print(
            Panel(
                concern_text,
                title="[yellow]⚠️  Verification Concerns[/]",
                border_style="yellow",
            )
        )

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
