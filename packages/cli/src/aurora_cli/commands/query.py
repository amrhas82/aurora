"""Query command - SOAR orchestration without API requirements.

This command orchestrates the 9-phase SOAR process, blocking on stdin
for LLM reasoning phases without requiring external LLM API keys.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from aurora_soar.phases.assess import assess_complexity

console = Console()
logger = logging.getLogger(__name__)


@click.command(name="query")
@click.argument("query_text", required=True)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Run blocking interactive SOAR (reads stdin)",
)
def query_command(
    query_text: str,
    verbose: bool,
    interactive: bool,
) -> None:
    """Execute SOAR query orchestration.

    Two modes:
    1. Single-shot (default): Outputs phases 1-2 + guidance for 3-9
    2. Interactive (--interactive): Blocks on stdin at each reasoning phase

    No API key required - designed to pipe through Claude.

    Examples:
        # Single-shot mode
        aur query "How does the SOAR orchestrator work?"

        # Interactive blocking mode (pipe answers)
        echo -e '["goal1"]\\nPASS\\n["approach"]\\n["finding"]\\nsynthesis\\npattern\\nfinal answer' | aur query "question" -i

    """
    try:
        if interactive:
            _run_interactive(query_text, verbose)
        else:
            _run_single_shot(query_text, verbose)

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Query command failed: {e}", exc_info=True)
        console.print(f"\n[bold red]Error:[/] {e}", style="red")
        raise click.Abort()


def _run_interactive(query_text: str, _verbose: bool) -> None:
    """Run blocking interactive SOAR - reads stdin at each reasoning phase."""
    import os

    from aurora_context_code.semantic.model_utils import BackgroundModelLoader, is_model_cached
    from aurora_core.activation.engine import ActivationEngine
    from aurora_core.store.sqlite import SQLiteStore

    # Initialize
    db_path = str(Path.home() / ".aurora" / "memory.db")
    if not Path(db_path).exists():
        console.print("[red]Error: Memory database not found. Run 'aur mem index .' first.[/]")
        raise click.Abort()

    store = SQLiteStore(db_path)
    activation_engine = ActivationEngine()

    # Get embedding provider - prefer background loader if available
    embedding_provider = None
    try:
        loader = BackgroundModelLoader.get_instance()

        # Check if already loaded from background
        embedding_provider = loader.get_provider_if_ready()

        if embedding_provider is None and loader.is_loading():
            # Wait for background loading to complete
            console.print("[dim]Waiting for embedding model...[/]")
            embedding_provider = loader.wait_for_model(timeout=60.0)
        elif embedding_provider is None and is_model_cached():
            # Not loading but cached - load now
            os.environ["HF_HUB_OFFLINE"] = "1"
            from aurora_context_code.semantic import EmbeddingProvider

            embedding_provider = EmbeddingProvider()
    except ImportError:
        logger.debug("sentence-transformers not installed")
    except Exception as e:
        logger.warning("Failed to get embedding provider: %s", e)

    from aurora_context_code.semantic.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(store, activation_engine, embedding_provider)

    session_id = f"query-{int(time.time() * 1000)}"
    phase_data = {}

    # ===== PHASE 1: ASSESS (local) =====
    console.print("\n[bold cyan]## Phase 1/9: ASSESS[/]")
    assessment = assess_complexity(query=query_text, llm_client=None)
    complexity = assessment.get("complexity", "MEDIUM")
    confidence = assessment.get("confidence", 0.0)

    phase_data["phase_1"] = assessment
    console.print(f"Complexity: [bold]{complexity}[/]")
    console.print(f"Confidence: {confidence:.2f}")

    # ===== PHASE 2: RETRIEVE (local) =====
    console.print("\n[bold cyan]## Phase 2/9: RETRIEVE[/]")
    results = retriever.retrieve(query_text, top_k=10)
    phase_data["phase_2"] = {"total": len(results)}

    console.print(f"Found [bold]{len(results)}[/] chunks:\n")
    for i, result in enumerate(results[:5], 1):
        metadata = result.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")
        name = metadata.get("name", "")
        console.print(f"  {i}. {file_path} - {name}")

    # ===== PHASE 3: DECOMPOSE (needs input) =====
    console.print("\n[bold cyan]## Phase 3/9: DECOMPOSE[/]")
    console.print("Break query into 2-5 subgoals.")
    console.print("[dim]Enter subgoals as JSON array:[/]")

    line = sys.stdin.readline().strip()
    try:
        subgoals = json.loads(line)
    except json.JSONDecodeError:
        subgoals = [line]  # Treat as single subgoal if not JSON

    phase_data["phase_3"] = {"subgoals": subgoals}
    console.print(f"Received {len(subgoals)} subgoals")

    # ===== PHASE 4: VERIFY (needs input) =====
    console.print("\n[bold cyan]## Phase 4/9: VERIFY[/]")
    console.print("Verify decomposition completeness.")
    console.print("[dim]Enter PASS or FAIL:[/]")

    verdict = sys.stdin.readline().strip().upper()
    if verdict not in ["PASS", "FAIL"]:
        verdict = "PASS"

    phase_data["phase_4"] = {"verdict": verdict}
    console.print(f"Verdict: {verdict}")

    # ===== PHASE 5: ROUTE (needs input) =====
    console.print("\n[bold cyan]## Phase 5/9: ROUTE[/]")
    console.print("Map subgoals to approaches.")
    console.print("[dim]Enter routing as JSON array:[/]")

    line = sys.stdin.readline().strip()
    try:
        routing = json.loads(line)
    except json.JSONDecodeError:
        routing = [line]

    phase_data["phase_5"] = {"routing": routing}
    console.print(f"Routed {len(routing)} approaches")

    # ===== PHASE 6: COLLECT (needs input) =====
    console.print("\n[bold cyan]## Phase 6/9: COLLECT[/]")
    console.print("Execute subgoals, gather findings.")
    console.print("[dim]Enter findings as JSON array:[/]")

    line = sys.stdin.readline().strip()
    try:
        findings = json.loads(line)
    except json.JSONDecodeError:
        findings = [line]

    phase_data["phase_6"] = {"findings": findings}
    console.print(f"Collected {len(findings)} findings")

    # ===== PHASE 7: SYNTHESIZE (needs input) =====
    console.print("\n[bold cyan]## Phase 7/9: SYNTHESIZE[/]")
    console.print("Combine findings into coherent answer.")
    console.print("[dim]Enter synthesis:[/]")

    synthesis = sys.stdin.readline().strip()
    phase_data["phase_7"] = {"synthesis": synthesis}
    console.print("Synthesis received")

    # ===== PHASE 8: RECORD (needs input) =====
    console.print("\n[bold cyan]## Phase 8/9: RECORD[/]")
    console.print("Note any patterns worth caching.")
    console.print("[dim]Enter pattern (or 'None'):[/]")

    pattern = sys.stdin.readline().strip()
    phase_data["phase_8"] = {"pattern": pattern}
    console.print(f"Pattern: {pattern}")

    # ===== PHASE 9: RESPOND (needs input) =====
    console.print("\n[bold cyan]## Phase 9/9: RESPOND[/]")
    console.print("Format final answer.")
    console.print("[dim]Enter final answer:[/]")

    answer = sys.stdin.readline().strip()
    phase_data["phase_9"] = {"answer": answer}

    # ===== COMPLETE =====
    console.print("\n[bold green]═══ SOAR Query Complete ═══[/]\n")
    console.print(Panel(answer, border_style="green", title="Final Answer"))

    # Log to .aurora/logs/conversations/ using ConversationLogger
    from aurora_core.logging import ConversationLogger

    # Map phase_1, phase_2, etc. to assess, retrieve, etc. for ConversationLogger
    phase_name_map = {
        "phase_1": "assess",
        "phase_2": "retrieve",
        "phase_3": "decompose",
        "phase_4": "verify",
        "phase_5": "route",
        "phase_6": "collect",
        "phase_7": "synthesize",
        "phase_8": "record",
        "phase_9": "respond",
    }
    mapped_phases = {phase_name_map.get(k, k): v for k, v in phase_data.items()}

    conv_logger = ConversationLogger()
    log_path = conv_logger.log_interaction(
        query=query_text,
        query_id=session_id,
        phase_data=mapped_phases,
        execution_summary={
            "duration_ms": 0,  # Interactive mode doesn't track timing
            "overall_score": 0.0,
            "cached": False,
        },
        metadata={
            "mode": "interactive",
            "answer": answer,
            "completed_at": datetime.now().isoformat(),
        },
    )

    if log_path:
        console.print(f"\n[dim]Log saved to: {log_path}[/]")

        # Auto-index the conversation log as knowledge chunk
        try:
            from aurora_cli.config import Config
            from aurora_cli.memory_manager import MemoryManager

            db_path = Path.cwd() / ".aurora" / "memory.db"
            if db_path.exists():
                config = Config(db_path=str(db_path))
                manager = MemoryManager(config=config)
                stats = manager.index_path(log_path)
                logger.debug(
                    f"Indexed conversation log: {log_path} ({stats.chunks_created} chunks)",
                )
        except Exception as e:
            logger.warning(f"Failed to auto-index conversation log: {e}")
            # Don't fail the query if indexing fails

    logger.info(f"SOAR query completed: {session_id}")


def _run_single_shot(query_text: str, _verbose: bool) -> None:
    """Run single-shot mode - outputs phases 1-2 + guidance."""
    import os

    from aurora_context_code.semantic.model_utils import BackgroundModelLoader, is_model_cached
    from aurora_core.activation.engine import ActivationEngine
    from aurora_core.store.sqlite import SQLiteStore

    db_path = str(Path.home() / ".aurora" / "memory.db")
    if not Path(db_path).exists():
        console.print("[red]Error: Memory database not found. Run 'aur mem index .' first.[/]")
        raise click.Abort()

    store = SQLiteStore(db_path)
    activation_engine = ActivationEngine()

    # Get embedding provider - prefer background loader if available
    embedding_provider = None
    try:
        loader = BackgroundModelLoader.get_instance()

        # Check if already loaded from background
        embedding_provider = loader.get_provider_if_ready()

        if embedding_provider is None and loader.is_loading():
            # Wait for background loading to complete
            console.print("[dim]Waiting for embedding model...[/]")
            embedding_provider = loader.wait_for_model(timeout=60.0)
        elif embedding_provider is None and is_model_cached():
            # Not loading but cached - load now
            os.environ["HF_HUB_OFFLINE"] = "1"
            from aurora_context_code.semantic import EmbeddingProvider

            embedding_provider = EmbeddingProvider()
    except ImportError:
        logger.debug("sentence-transformers not installed")
    except Exception as e:
        logger.warning("Failed to get embedding provider: %s", e)

    from aurora_context_code.semantic.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(store, activation_engine, embedding_provider)

    # PHASE 1: ASSESS
    console.print("\n[bold cyan]## Phase 1: ASSESS[/]")
    assessment = assess_complexity(query=query_text, llm_client=None)
    complexity = assessment.get("complexity", "MEDIUM")
    confidence = assessment.get("confidence", 0.0)
    score = assessment.get("score", 0.5)

    console.print(f"Complexity: [bold]{complexity}[/]")
    console.print(f"Confidence: {confidence:.2f}")
    console.print(f"Score: {score:.2f}")

    # PHASE 2: RETRIEVE
    console.print("\n[bold cyan]## Phase 2: RETRIEVE[/]")
    results = retriever.retrieve(query_text, top_k=10)

    console.print(f"Found [bold]{len(results)}[/] chunks:\n")
    for i, result in enumerate(results[:10], 1):
        metadata = result.get("metadata", {})
        file_path = metadata.get("file_path", "unknown")
        name = metadata.get("name", "")
        score_val = result.get("hybrid_score", 0.0)
        display_name = f"{name}" if name else "chunk"
        console.print(f"  {i}. {file_path} - {display_name} (score: {score_val:.3f})")

    # Output guidance
    console.print("\n[bold yellow]## Remaining Phases - Complete in your response:[/]\n")

    guidance = """Phase 3: DECOMPOSE - Break query into 2-5 subgoals
Phase 4: VERIFY - Check completeness (PASS/FAIL)
Phase 5: ROUTE - Map subgoals to approaches
Phase 6: COLLECT - Execute and gather findings
Phase 7: SYNTHESIZE - Combine into coherent answer
Phase 8: RECORD - Note patterns (or None)
Phase 9: RESPOND - Format final answer

Output each phase header as you work through them."""

    console.print(Panel(guidance, border_style="yellow", title="SOAR Guidance"))
