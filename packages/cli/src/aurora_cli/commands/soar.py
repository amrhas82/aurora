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


def _start_background_model_loading(verbose: bool = False) -> None:
    """Start loading the embedding model in the background.

    This is non-blocking - the model loads in a background thread while
    other initialization continues. When embeddings are actually needed,
    the code will wait for loading to complete (with a spinner if still loading).

    Uses lightweight cache checking to avoid importing torch/sentence-transformers
    until actually needed in the background thread.

    Args:
        verbose: Whether to enable verbose logging

    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Use lightweight cache check that doesn't import torch
        from aurora_context_code.model_cache import is_model_cached_fast, start_background_loading

        # Only start background loading if model is cached
        # If not cached, we'll handle download later when actually needed
        if not is_model_cached_fast():
            logger.debug("Model not cached, skipping background load")
            return

        # Start loading in background thread (imports torch there, not here)
        start_background_loading()
        logger.debug("Background model loading started")

    except ImportError:
        # aurora_context_code not installed
        if verbose:
            logger.debug("Context code package not available")
    except Exception as e:
        logger.debug("Background model loading failed to start: %s", e)


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
        # Don't show in-memory cache status here - file cache will be shown later if applicable
        console.print(f"  [cyan]✓ {count} subgoals {'loaded' if result.get('cached') else 'identified'}[/]")
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
                f"  [yellow]└─ {issues_count} concerns, {agents_assigned} subgoals routed[/]",
            )
        else:
            if agents_assigned > 0:
                console.print(f"  [cyan]✓ {verdict} ({agents_assigned} subgoals routed)[/]")
            else:
                console.print(f"  [cyan]✓ {verdict}[/]")

        # Display subgoal table if available
        subgoals = result.get("subgoals", [])
        if subgoals:
            from rich.panel import Panel
            from rich.table import Table

            table = Table(title="Plan Decomposition", show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=4)
            table.add_column("Subgoal", width=45)
            table.add_column("Agent", width=20)
            table.add_column("Match", width=12)

            for sg in subgoals:
                agent_name = sg.get("agent", "unknown")
                is_spawn = sg.get("is_spawn", False)
                match_quality = sg.get("match_quality", "acceptable")
                ideal_agent = sg.get("ideal_agent", "")

                # Agent display with color based on match quality
                if is_spawn:
                    agent_display = f"[yellow]@{agent_name}*[/]"
                    match_display = "[yellow]✗ Spawned[/]"
                elif match_quality == "excellent":
                    agent_display = f"[green]@{agent_name}[/]"
                    match_display = "[green]✓ Excellent[/]"
                elif match_quality == "acceptable":
                    agent_display = f"[cyan]@{agent_name}[/]"
                    match_display = "[yellow]⚠ Acceptable[/]"
                else:  # insufficient (shouldn't reach here if spawn logic works)
                    agent_display = f"[red]@{agent_name}[/]"
                    match_display = "[red]✗ Weak[/]"

                # Truncate description if needed
                desc_text = sg.get("description", "")[:45]

                table.add_row(
                    str(sg.get("index", "?")),
                    desc_text,
                    agent_display,
                    match_display,
                )

                # Show ideal agent suggestion for acceptable matches
                if match_quality == "acceptable" and ideal_agent:
                    table.add_row(
                        "",
                        f"[dim]→ Suggest: {ideal_agent}[/]",
                        "",
                        "",
                    )

            console.print()
            console.print(table)

            # Display summary panel
            total = len(subgoals)
            # Count gaps using is_spawn flag (set by verify_lite for missing agents)
            gap_subgoals = [sg for sg in subgoals if sg.get("is_spawn", False)]
            gaps = len(gap_subgoals)
            assigned = total - gaps

            # Build summary text with proper grammar
            subgoal_word = "subgoal" if total == 1 else "subgoals"
            summary_parts = [f"[bold]{total} {subgoal_word}[/]", f"[cyan]{assigned} assigned[/]"]
            if gaps > 0:
                summary_parts.append(f"[yellow]{gaps} spawned[/]")
            summary_text = " • ".join(summary_parts)

            # Show spawned agents (will use fallback LLM)
            if gap_subgoals:
                gap_agents = sorted(set(sg.get("agent", "unknown") for sg in gap_subgoals))
                gap_list = ", ".join(f"@{a}" for a in gap_agents)
                summary_text += f"\n\n[yellow]Spawned (no matching agent):[/] {gap_list}"

            console.print(Panel(summary_text, title="Summary", border_style="dim"))
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
@click.option(
    "--context",
    "-c",
    "context_files",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Context files for informed decomposition. Can be used multiple times.",
)
@click.option(
    "--early-detection-interval",
    type=float,
    default=None,
    help="Early detection check interval in seconds (default: 2.0)",
)
@click.option(
    "--early-detection-stall-threshold",
    type=float,
    default=None,
    help="Stall threshold for early detection in seconds (default: 15.0)",
)
@click.option(
    "--early-detection-min-output",
    type=int,
    default=None,
    help="Minimum output bytes before stall check (default: 100)",
)
@click.option(
    "--disable-early-detection",
    is_flag=True,
    default=False,
    help="Disable early failure detection",
)
def soar_command(
    query: str,
    model: str,
    tool: str | None,
    verbose: bool,
    context_files: tuple[Path, ...],
    early_detection_interval: float | None,
    early_detection_stall_threshold: float | None,
    early_detection_min_output: int | None,
    disable_early_detection: bool,
) -> None:
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
        aur soar "Refactor auth" --context src/auth.py --context docs/auth.md
    """
    # Load config for defaults
    from aurora_cli.config import Config

    try:
        cli_config = Config()
    except Exception:
        # If config loading fails, use hardcoded defaults
        cli_config = None

    # Start background model loading early (non-blocking)
    # The model will load in parallel with other initialization
    _start_background_model_loading(verbose)

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
        ),
    )

    start_time = time.time()

    # Ensure project is initialized
    try:
        soar_dir = _ensure_soar_dir()
    except RuntimeError as e:
        console.print(f"\n[red]Error:[/] {e}")
        console.print("\n[dim]Run this command to initialize your project:[/]")
        console.print("  [cyan]aur init[/]")
        raise SystemExit(1)

    # Import here to avoid circular imports and allow lazy loading
    from aurora_cli.llm.cli_pipe_client import CLIPipeLLMClient
    from aurora_core.store.sqlite import SQLiteStore
    from aurora_soar.orchestrator import SOAROrchestrator

    # Create CLI-based LLM client
    try:
        llm_client = CLIPipeLLMClient(tool=tool, model=model, soar_dir=soar_dir)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/]")
        raise SystemExit(1)

    # Create phase callback for terminal display
    phase_callback = _create_phase_callback(tool)

    # Load config - cli_config was already loaded at top of function
    config = cli_config

    # Apply CLI overrides for early detection settings
    if (
        disable_early_detection
        or early_detection_interval is not None
        or early_detection_stall_threshold is not None
        or early_detection_min_output is not None
    ):
        # Build early_detection config override
        early_detection_config = (
            config.get("early_detection", {}).copy() if config.get("early_detection") else {}
        )

        if disable_early_detection:
            early_detection_config["enabled"] = False
        if early_detection_interval is not None:
            early_detection_config["check_interval"] = early_detection_interval
        if early_detection_stall_threshold is not None:
            early_detection_config["stall_threshold"] = early_detection_stall_threshold
        if early_detection_min_output is not None:
            early_detection_config["min_output_bytes"] = early_detection_min_output

        # Update config with overrides
        config._data["early_detection"] = early_detection_config

    # Use project-local memory store (consistent with aur init and aur mem index)
    # cli_config.get_db_path() returns ./.aurora/memory.db by default
    db_path = cli_config.get_db_path() if cli_config else "./.aurora/memory.db"
    store = SQLiteStore(db_path)

    # Use discovery adapter instead of explicit registry for lazy loading
    # This defers agent loading until actually needed by orchestrator
    agent_registry = None  # Let orchestrator use discovery_adapter

    # Show startup message without blocking on agent discovery
    console.print("[dim]Initializing...[/]\n")

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
        # Pass context files if provided
        ctx_files = [str(f) for f in context_files] if context_files else None
        result = orchestrator.execute(query, verbosity=verbosity, context_files=ctx_files)
    except Exception as e:
        console.print(f"\n[red]Error during SOAR execution: {e}[/]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise SystemExit(1)

    # Check for file-based cache hit (goals.json or conversation log)
    metadata = result.get("metadata", {})
    cache_source = metadata.get("cache_source")
    if cache_source:
        # Determine cache source type
        cache_source_str = str(cache_source)
        if "goals.json" in cache_source_str:
            source_type = "goals.json"
        elif "/logs/conversations/" in cache_source_str:
            source_type = "previous SOAR conversation"
        else:
            source_type = "cache"

        console.print(
            f"  [green]✓ Using cached decomposition from {source_type}[/] "
            "[dim](use --no-cache for fresh)[/]"
        )

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
            ),
        )

    console.print()
    console.print(
        Panel(
            answer,
            title="[bold]Final Answer[/]",
            border_style="green",
        ),
    )

    # Show metadata
    console.print(f"\n[dim]Completed in {elapsed_time:.1f}s[/]")

    # Show log path if available
    log_path = result.get("metadata", {}).get("log_path")
    if log_path:
        console.print(f"[dim]Log: {log_path}[/]")
