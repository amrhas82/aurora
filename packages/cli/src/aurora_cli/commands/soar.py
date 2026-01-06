"""AURORA SOAR Command - Multi-turn orchestration via claude CLI.

This module provides true multi-turn SOAR execution where Python controls
the conversation loop, making separate LLM calls for each phase.
"""

from __future__ import annotations

import logging
import subprocess
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from aurora_core.logging.conversation_logger import ConversationLogger
from aurora_core.metrics.query_metrics import QueryMetrics

console = Console()
logger = logging.getLogger(__name__)


def _run_claude(prompt: str, model: str = "sonnet", timeout: int = 120) -> str:
    """
    Run claude CLI with prompt and return output.

    Args:
        prompt: The prompt to send
        model: Model to use (sonnet or opus)
        timeout: Timeout in seconds

    Returns:
        Claude's response text
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR: Claude timed out]"
    except FileNotFoundError:
        return "[ERROR: claude CLI not found - install Claude Code]"
    except Exception as e:
        return f"[ERROR: {e}]"


def _run_aur_query(query: str) -> str:
    """
    Run local aur query for phase 1-2 context retrieval.

    Args:
        query: The query string

    Returns:
        Local context from memory index
    """
    try:
        result = subprocess.run(
            ["aur", "query", query, "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Return first 40 lines to keep context manageable
        lines = result.stdout.strip().split("\n")[:40]
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"aur query failed: {e}")
        return f"[No local context: {e}]"


def _save_log(
    query: str,
    model: str,
    context: str,
    phase3: str,
    phase4: str,
    phase5: str,
    phase6: str,
    final: str,
    duration_ms: float,
) -> Path | None:
    """Save SOAR query log using ConversationLogger."""
    # Use ConversationLogger for consistent logging
    conv_logger = ConversationLogger()

    # Generate unique query ID
    query_id = f"soar-{uuid.uuid4().hex[:8]}"

    # Build phase data in the format ConversationLogger expects
    phase_data = {
        "assess": {"context_retrieved": len(context.split("\n")), "method": "local_aur_query"},
        "retrieve": {"raw_context": context[:1000] + "..." if len(context) > 1000 else context},
        "decompose": {"subgoals": phase3},
        "verify": {"verdict": phase4},
        "collect": {"research": phase5[:2000] + "..." if len(phase5) > 2000 else phase5},
        "synthesize": {"synthesis": phase6},
        "respond": {"final_answer": final},
    }

    # Build execution summary
    execution_summary = {
        "duration_ms": round(duration_ms),
        "overall_score": 0.85,  # Placeholder - could calculate based on phase success
        "cached": False,
        "model": model,
        "method": "multi_turn_cli",
        "claude_calls": 5,
    }

    # Additional metadata
    metadata = {
        "orchestration_type": "bash_cli",
        "model": model,
        "timestamp": datetime.now().isoformat(),
    }

    log_path = conv_logger.log_interaction(
        query=query,
        query_id=query_id,
        phase_data=phase_data,
        execution_summary=execution_summary,
        metadata=metadata,
    )

    return log_path


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
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show verbose output",
)
def soar_command(query: str, model: str, verbose: bool) -> None:
    """Execute multi-turn SOAR query with separate LLM calls per phase.

    This command runs TRUE multi-turn orchestration where Python controls
    the conversation loop, making 5 separate claude CLI calls:

    \b
    - Phase 1-2: Local retrieval (aur query, no LLM)
    - Phase 3: DECOMPOSE (claude call 1)
    - Phase 4: VERIFY (claude call 2)
    - Phase 5: COLLECT (claude call 3 - may use web search)
    - Phase 6: SYNTHESIZE (claude call 4)
    - Phase 7: RESPOND (claude call 5)

    \b
    Examples:
        aur soar "What is SOAR orchestrator?"
        aur soar "State of AI datacenters in space?" --model opus
    """
    # Check claude CLI is available
    if not shutil.which("claude"):
        console.print("[red]Error: claude CLI not found[/]")
        console.print("Install Claude Code first: https://claude.ai/download")
        raise SystemExit(1)

    console.print(Panel(f"[bold cyan]SOAR Query[/]\n{query}", title="Aurora"))

    # Track execution time
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # ===== PHASE 1-2: Local retrieval =====
        task = progress.add_task("Phase 1-2: ASSESS & RETRIEVE (local)...", total=None)
        context = _run_aur_query(query)
        progress.update(task, completed=True, description="Phase 1-2: ✓ Local context retrieved")

        if verbose:
            console.print("\n[dim]## Phase 1-2: ASSESS & RETRIEVE[/]")
            console.print(f"[dim]{context[:500]}...[/]" if len(context) > 500 else f"[dim]{context}[/]")

        # ===== PHASE 3: DECOMPOSE =====
        task = progress.add_task("Phase 3: DECOMPOSE...", total=None)
        phase3_prompt = f"""You are a helpful assistant. Answer concisely.

Query: {query}

Break this query into 2-4 specific subgoals that need to be answered. List them as a numbered list:

1. [subgoal]
2. [subgoal]
..."""
        phase3 = _run_claude(phase3_prompt, model)
        progress.update(task, completed=True, description="Phase 3: ✓ Decomposed into subgoals")

        if verbose:
            console.print("\n[dim]## Phase 3: DECOMPOSE[/]")
            console.print(f"[dim]{phase3}[/]")

        # ===== PHASE 4: VERIFY =====
        task = progress.add_task("Phase 4: VERIFY...", total=None)
        phase4_prompt = f"""You are a helpful assistant. Answer with just PASS or FAIL and one sentence.

Query: {query}

Subgoals:
{phase3}

Do these subgoals completely cover all aspects of the query? Answer PASS or FAIL with brief reason."""
        phase4 = _run_claude(phase4_prompt, model)
        progress.update(task, completed=True, description="Phase 4: ✓ Verified subgoals")

        if verbose:
            console.print("\n[dim]## Phase 4: VERIFY[/]")
            console.print(f"[dim]{phase4}[/]")

        # ===== PHASE 5: COLLECT =====
        task = progress.add_task("Phase 5: COLLECT (researching, may take 30-60s)...", total=None)
        phase5_prompt = f"""You are a helpful research assistant. Be thorough but concise.

Query: {query}

Subgoals:
{phase3}

Research and answer each subgoal. Use web search if needed for current information. Provide specific facts, names, dates, and sources where possible."""
        phase5 = _run_claude(phase5_prompt, model, timeout=180)  # Longer timeout for research
        progress.update(task, completed=True, description="Phase 5: ✓ Collected research")

        if verbose:
            console.print("\n[dim]## Phase 5: COLLECT[/]")
            console.print(f"[dim]{phase5[:1000]}...[/]" if len(phase5) > 1000 else f"[dim]{phase5}[/]")

        # ===== PHASE 6: SYNTHESIZE =====
        task = progress.add_task("Phase 6: SYNTHESIZE...", total=None)
        phase6_prompt = f"""You are a helpful assistant. Synthesize concisely.

Query: {query}

Research findings:
{phase5}

Combine these findings into a coherent, well-organized answer. Resolve any conflicts. Be factual."""
        phase6 = _run_claude(phase6_prompt, model)
        progress.update(task, completed=True, description="Phase 6: ✓ Synthesized findings")

        if verbose:
            console.print("\n[dim]## Phase 6: SYNTHESIZE[/]")
            console.print(f"[dim]{phase6}[/]")

        # ===== PHASE 7: RESPOND =====
        task = progress.add_task("Phase 7: RESPOND (formatting)...", total=None)
        phase7_prompt = f"""You are a helpful assistant. Give a clear, actionable answer.

Query: {query}

Synthesized answer:
{phase6}

Format a clear final answer for the user. Use headers, bullet points, and structure. Include key facts and dates."""
        final = _run_claude(phase7_prompt, model)
        progress.update(task, completed=True, description="Phase 7: ✓ Formatted response")

    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000

    # Show final answer
    console.print("\n")
    console.print(Panel(final, title="[bold green]Final Answer[/]", border_style="green"))

    # Generate query ID for tracking
    query_id = f"soar-{uuid.uuid4().hex[:8]}"

    # Save log using ConversationLogger
    log_path = _save_log(query, model, context, phase3, phase4, phase5, phase6, final, duration_ms)
    if log_path:
        console.print(f"\n[dim]Log saved: {log_path}[/]")

    # Record metrics (QueryMetrics auto-detects project-local .aurora)
    try:
        metrics = QueryMetrics()

        # Determine complexity from verify phase output
        complexity = "MEDIUM"  # Default
        if "PASS" in phase4.upper():
            complexity = "COMPLEX" if len(phase3.split("\n")) > 3 else "MEDIUM"
        elif "FAIL" in phase4.upper():
            complexity = "COMPLEX"

        metrics.record_query(
            query_id=query_id,
            query_type="soar",
            duration_ms=duration_ms,
            query_text=query,
            complexity=complexity,
            model=model,
            success=True,
            phase_count=7,  # Phases 1-7
            claude_calls=5,
        )
    except Exception as e:
        logger.debug(f"Failed to record metrics: {e}")

    console.print(f"[dim]SOAR complete (5 claude calls, model: {model}, {duration_ms/1000:.1f}s)[/]")
