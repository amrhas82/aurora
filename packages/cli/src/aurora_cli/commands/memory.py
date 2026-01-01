"""Memory command implementation for AURORA CLI.

This module implements the 'aur mem' command group for memory management:
- aur mem index: Index code files into memory store
- aur mem search: Search indexed chunks
- aur mem stats: Display memory store statistics

Usage:
    aur mem index <path>
    aur mem search "query text" [options]
    aur mem stats
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aurora_cli.config import Config, load_config
from aurora_cli.errors import ErrorHandler, MemoryStoreError, handle_errors
from aurora_cli.memory_manager import MemoryManager, SearchResult


__all__ = ["memory_group"]

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="mem")
def memory_group() -> None:
    """Memory management commands for indexing and searching code.

    \b
    Commands:
        index   - Index code files into memory store
        search  - Search indexed chunks with hybrid retrieval
        stats   - Display memory store statistics

    \b
    Examples:
        aur mem index .                      # Index current directory
        aur mem search "authentication"      # Search for code
        aur mem stats                        # Show database stats
    """
    pass


@memory_group.command(name="index")
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.pass_context
@handle_errors
def index_command(ctx: click.Context, path: Path) -> None:
    """Index code files into memory store.

    PATH is the directory or file to index. Defaults to current directory.
    Recursively scans for Python files and extracts functions, classes, and docstrings.

    \b
    Examples:
        # Index current directory (default)
        aur mem index

        \b
        # Index specific directory or file
        aur mem index /path/to/project
        aur mem index src/main.py

        \b
        # Force reindex (run index command again on same path)
        aur mem index .
        # Note: Will update existing chunks and add new ones
    """
    # Load configuration
    config = load_config()
    db_path = config.get_db_path()

    # Initialize memory manager with config
    console.print(f"[dim]Using database: {db_path}[/]")
    manager = MemoryManager(config=config)

    # Create progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task_id: TaskID | None = None

        def progress_callback(current: int, total: int) -> None:
            nonlocal task_id
            if task_id is None:
                task_id = progress.add_task(
                    f"Indexing {path}",
                    total=total,
                )
            progress.update(task_id, completed=current)

        # Perform indexing
        stats = manager.index_path(path, progress_callback=progress_callback)

    # Display summary
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]✓ Indexing complete[/]\n\n"
            f"Files indexed: [cyan]{stats.files_indexed}[/]\n"
            f"Chunks created: [cyan]{stats.chunks_created}[/]\n"
            f"Duration: [cyan]{stats.duration_seconds:.2f}s[/]\n"
            f"Errors: [red]{stats.errors}[/]\n"
            f"Warnings: [yellow]{stats.warnings}[/]",
            title="Index Summary",
            border_style="green",
        )
    )


@memory_group.command(name="search")
@click.argument("query", type=str)
@click.option(
    "--limit",
    "-n",
    type=int,
    default=5,
    help="Maximum number of results to return (default: 5)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "json"]),
    default="rich",
    help="Output format (default: rich)",
)
@click.option(
    "--show-content",
    "-c",
    is_flag=True,
    default=False,
    help="Show content preview for each result",
)
@click.option(
    "--min-score",
    type=float,
    default=None,
    help="Minimum semantic score threshold (0.0-1.0, default: from config or 0.35)",
)
@click.option(
    "--type",
    "-t",
    "chunk_type",
    type=click.Choice(["function", "class", "method", "knowledge", "document"]),
    default=None,
    help="Filter results by chunk type (function, class, method, knowledge, document)",
)
@click.option(
    "--show-scores",
    is_flag=True,
    default=False,
    help="Show detailed score breakdown (BM25, Semantic, Activation)",
)
@click.pass_context
@handle_errors
def search_command(
    ctx: click.Context,
    query: str,
    limit: int,
    output_format: str,
    show_content: bool,
    min_score: float | None,
    chunk_type: str | None,
    show_scores: bool,
) -> None:
    """Search AURORA memory for relevant chunks.

    QUERY is the text to search for in memory. Uses hybrid retrieval
    (activation + semantic similarity) to find relevant chunks.

    \b
    Examples:
        # Basic search (returns top 5 results)
        aur mem search "authentication"

        \b
        # Search with more results and content preview
        aur mem search "calculate total" --limit 10 --show-content

        \b
        # Search with JSON output (for scripting)
        aur mem search "database" --format json

        \b
        # Quick alias for search with content
        aur mem search "error handling" -n 3 -c
    """
    # Load configuration
    config = load_config()
    db_path = Path(config.get_db_path())

    if not db_path.exists():
        error_handler = ErrorHandler()
        error = FileNotFoundError(f"Database not found at {db_path}")
        error_msg = error_handler.handle_path_error(error, str(db_path), "opening database")
        console.print(
            f"\n{error_msg}\n\n"
            "[green]Hint:[/] Run [cyan]aur mem index .[/] to create and populate the database.",
            style="red",
        )
        raise click.Abort()

    # Initialize memory manager with config
    console.print(f"[dim]Searching memory from {db_path}...[/]")
    manager = MemoryManager(config=config)

    # Perform search
    results = manager.search(query, limit=limit, min_semantic_score=min_score)

    # Filter by chunk type if specified
    if chunk_type:
        results = [r for r in results if r.metadata.get("type") == chunk_type]
        if not results:
            console.print(f"\n[yellow]No results found with type='{chunk_type}'[/]\n")
            return

    # Display results
    if output_format == "json":
        _display_json_results(results)
    else:
        _display_rich_results(results, query, show_content, config, show_scores)


@memory_group.command(name="stats")
@click.pass_context
@handle_errors
def stats_command(ctx: click.Context) -> None:
    """Display memory store statistics.

    Shows information about indexed chunks, files, languages, and database size.

    Examples:

        \b
        # Show stats for database
        aur mem stats
    """
    # Load configuration
    config = load_config()
    db_path = Path(config.get_db_path())

    if not db_path.exists():
        console.print(
            f"[bold red]Error:[/] Database not found at {db_path}\n"
            f"Run 'aur mem index' first to create the database",
            style="red",
        )
        raise click.Abort()

    # Initialize memory manager with config
    console.print(f"[dim]Loading statistics from {db_path}...[/]")
    manager = MemoryManager(config=config)

    # Get statistics
    stats = manager.get_stats()

    # Display statistics table
    table = Table(title="Memory Store Statistics", show_header=False)
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="white")

    table.add_row("Total Chunks", f"[bold]{stats.total_chunks:,}[/]")
    table.add_row("Total Files", f"[bold]{stats.total_files:,}[/]")
    table.add_row("Database Size", f"[bold]{stats.database_size_mb:.2f} MB[/]")

    if stats.languages:
        table.add_row("", "")  # Separator
        table.add_row("[bold]Languages", "")
        for lang, count in sorted(stats.languages.items(), key=lambda x: x[1], reverse=True):
            table.add_row(f"  {lang}", f"{count:,} chunks")

    console.print()
    console.print(table)
    console.print()


def _display_rich_results(
    results: list[SearchResult],
    query: str,
    show_content: bool,
    config: Config,
    show_scores: bool = False,
) -> None:
    """Display search results with rich formatting.

    Args:
        results: List of SearchResult objects
        query: Original search query
        show_content: Whether to show content preview
        config: Configuration object with threshold settings
        show_scores: Whether to show detailed score breakdown
    """
    if not results:
        console.print("\n[yellow]No relevant results found.[/]")
        console.print(
            "All results were below the semantic threshold.\n"
            "Try:\n"
            "  - Broadening your search query\n"
            "  - Lowering the threshold with --min-score 0.2\n"
            "  - Checking if the codebase has been indexed"
        )
        return

    console.print(f"\n[bold green]Found {len(results)} results for '{query}'[/]\n")

    # Check if all results have low semantic quality
    avg_semantic = sum(r.semantic_score for r in results) / len(results)
    if avg_semantic < 0.4:
        console.print(
            "[yellow]⚠️  Warning: All results have weak semantic relevance[/]\n"
            "Results shown are based primarily on recent access history, not semantic match.\n"
            "[dim]Consider:[/]\n"
            "  • [cyan]Broadening your search query[/]\n"
            "  • [cyan]Re-indexing if files are missing[/]: aur mem index .\n"
            "  • [cyan]Using grep for exact matches[/]: grep -r 'term' .\n"
        )

    # Create results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="yellow", width=30)
    table.add_column("Type", style="green", width=10)
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Lines", style="dim", width=10)
    table.add_column("Commits", style="magenta", width=8, justify="right")
    table.add_column("Modified", style="dim cyan", width=10)
    table.add_column("Score", justify="right", style="bold blue", width=8)

    if show_content:
        table.add_column("Preview", style="white", width=50)

    # Mark results with weak semantic relevance as "low"
    # These are results boosted mainly by activation (recency) rather than semantic match
    # Use a threshold relative to normalized semantic scores (0-1 range after min-max normalization)
    semantic_low_threshold = 0.4  # Normalized semantic score threshold

    for result in results:
        file_path = Path(result.file_path).name  # Just filename
        element_type = result.metadata.get("type", "unknown")
        name = result.metadata.get("name", "<unnamed>")
        line_start, line_end = result.line_range
        line_range_str = f"{line_start}-{line_end}"

        # Get git metadata (may not be available for all chunks)
        commit_count = result.metadata.get("commit_count")
        last_modified = result.metadata.get("last_modified")

        # Format git metadata for display
        commits_text = str(commit_count) if commit_count is not None else "-"

        # Format last_modified timestamp as relative time
        if last_modified:
            from datetime import datetime
            try:
                # last_modified is a Unix timestamp
                mod_time = datetime.fromtimestamp(last_modified)
                now = datetime.now()
                delta = now - mod_time

                if delta.days > 365:
                    modified_text = f"{delta.days // 365}y ago"
                elif delta.days > 30:
                    modified_text = f"{delta.days // 30}mo ago"
                elif delta.days > 0:
                    modified_text = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    modified_text = f"{delta.seconds // 3600}h ago"
                else:
                    modified_text = "recent"
            except (ValueError, OSError):
                modified_text = "-"
        else:
            modified_text = "-"

        # Format score with color and low confidence indicator
        score = result.hybrid_score
        semantic_score = result.semantic_score

        # Mark results with weak semantic relevance (normalized score < 0.4)
        # These passed the filter but are mainly showing due to recent access
        is_low_confidence = semantic_score < semantic_low_threshold

        if is_low_confidence:
            # Display score with yellow/red color and low confidence indicator
            score_text = _format_score(score)
            score_text.append(" (low)", style="dim yellow")
        else:
            score_text = _format_score(score)

        row = [
            _truncate_text(file_path, 30),
            element_type,
            _truncate_text(name, 20),
            line_range_str,
            commits_text,
            modified_text,
            score_text,
        ]

        if show_content:
            content_preview = _truncate_text(result.content, 50)
            row.append(content_preview)

        table.add_row(*row)  # type: ignore[arg-type]

    console.print(table)

    # Show average scores
    avg_activation = sum(r.activation_score for r in results) / len(results)
    avg_semantic = sum(r.semantic_score for r in results) / len(results)
    avg_hybrid = sum(r.hybrid_score for r in results) / len(results)

    console.print("\n[dim]Average scores:[/]")
    console.print(f"  Activation: {avg_activation:.3f}")
    console.print(f"  Semantic:   {avg_semantic:.3f}")
    console.print(f"  Hybrid:     {avg_hybrid:.3f}\n")

    # Show detailed score breakdown if requested
    if show_scores:
        console.print("[bold cyan]Score Breakdown:[/]\n")
        score_table = Table(show_header=True, header_style="bold magenta")
        score_table.add_column("Rank", style="dim", width=6)
        score_table.add_column("Name", style="cyan", width=30)
        score_table.add_column("BM25", justify="right", style="yellow", width=10)
        score_table.add_column("Semantic", justify="right", style="green", width=10)
        score_table.add_column("Activation", justify="right", style="blue", width=10)
        score_table.add_column("Hybrid", justify="right", style="bold magenta", width=10)

        for i, result in enumerate(results, 1):
            name = result.metadata.get("name", "<unnamed>")
            score_table.add_row(
                str(i),
                _truncate_text(name, 30),
                f"{result.bm25_score:.3f}",
                f"{result.semantic_score:.3f}",
                f"{result.activation_score:.3f}",
                f"{result.hybrid_score:.3f}",
            )

        console.print(score_table)
        console.print()


def _display_json_results(results: list[SearchResult]) -> None:
    """Display search results as JSON.

    Args:
        results: List of SearchResult objects
    """
    json_results = []
    for result in results:
        json_results.append(
            {
                "chunk_id": result.chunk_id,
                "file_path": result.file_path,
                "line_start": result.line_range[0],
                "line_end": result.line_range[1],
                "content": result.content,
                "activation_score": result.activation_score,
                "semantic_score": result.semantic_score,
                "hybrid_score": result.hybrid_score,
                "metadata": result.metadata,
            }
        )

    console.print(json.dumps(json_results, indent=2))


def _format_score(score: float) -> Text:
    """Format score with color gradient.

    Args:
        score: Score value (0.0 - 1.0)

    Returns:
        Rich Text object with colored score
    """
    if score >= 0.7:
        color = "green"
    elif score >= 0.4:
        color = "yellow"
    else:
        color = "red"

    return Text(f"{score:.3f}", style=f"bold {color}")


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text for display.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


if __name__ == "__main__":
    memory_group()
