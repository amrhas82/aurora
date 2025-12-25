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

from aurora_cli.errors import ErrorHandler, MemoryStoreError
from aurora_cli.memory_manager import MemoryManager
from aurora_core.store import SQLiteStore


__all__ = ["memory_group"]

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="mem")
def memory_group():
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
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to AURORA database (default: ./aurora.db)",
)
def index_command(path: Path, db_path: Path | None) -> None:
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
        # Index with custom database location
        aur mem index . --db-path ~/.aurora/memory.db

        \b
        # Force reindex (run index command again on same path)
        aur mem index .
        # Note: Will update existing chunks and add new ones
    """
    try:
        # Determine database path
        if db_path is None:
            db_path = Path.cwd() / "aurora.db"

        # Initialize memory store
        console.print(f"[dim]Using database: {db_path}[/]")
        store = SQLiteStore(str(db_path))

        # Initialize memory manager
        manager = MemoryManager(store)

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
        console.print(Panel.fit(
            f"[bold green]✓ Indexing complete[/]\n\n"
            f"Files indexed: [cyan]{stats.files_indexed}[/]\n"
            f"Chunks created: [cyan]{stats.chunks_created}[/]\n"
            f"Duration: [cyan]{stats.duration_seconds:.2f}s[/]\n"
            f"Errors: [yellow]{stats.errors}[/]",
            title="Index Summary",
            border_style="green",
        ))

        # Close store
        store.close()

    except MemoryStoreError as e:
        # Already has formatted error message
        logger.error(f"Index command failed: {e}", exc_info=True)
        console.print(f"\n{e}", style="red")
        raise click.Abort()
    except Exception as e:
        # Unexpected error - format it
        logger.error(f"Index command failed: {e}", exc_info=True)
        error_handler = ErrorHandler()
        error_msg = error_handler.handle_memory_error(e, "indexing files")
        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()


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
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to AURORA database (default: ./aurora.db)",
)
def search_command(
    query: str,
    limit: int,
    output_format: str,
    show_content: bool,
    db_path: Path | None,
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
        # Search in custom database
        aur mem search "config" --db-path ~/.aurora/memory.db

        \b
        # Quick alias for search with content
        aur mem search "error handling" -n 3 -c
    """
    try:
        # Determine database path
        if db_path is None:
            db_path = Path.cwd() / "aurora.db"

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

        # Initialize memory store
        console.print(f"[dim]Searching memory from {db_path}...[/]")
        store = SQLiteStore(str(db_path))

        # Initialize memory manager
        manager = MemoryManager(store)

        # Perform search
        results = manager.search(query, limit=limit)

        # Display results
        if output_format == "json":
            _display_json_results(results)
        else:
            _display_rich_results(results, query, show_content)

        # Close store
        store.close()

    except MemoryStoreError as e:
        # Already has formatted error message
        logger.error(f"Search command failed: {e}", exc_info=True)
        console.print(f"\n{e}", style="red")
        raise click.Abort()
    except Exception as e:
        # Unexpected error - format it
        logger.error(f"Search command failed: {e}", exc_info=True)
        error_handler = ErrorHandler()
        error_msg = error_handler.handle_memory_error(e, "searching memory")
        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()


@memory_group.command(name="stats")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to AURORA database (default: ./aurora.db)",
)
def stats_command(db_path: Path | None) -> None:
    """Display memory store statistics.

    Shows information about indexed chunks, files, languages, and database size.

    Examples:

        \b
        # Show stats for default database
        aur mem stats

        \b
        # Show stats for custom database
        aur mem stats --db-path ~/.aurora/memory.db
    """
    try:
        # Determine database path
        if db_path is None:
            db_path = Path.cwd() / "aurora.db"

        if not db_path.exists():
            console.print(
                f"[bold red]Error:[/] Database not found at {db_path}\n"
                f"Run 'aur mem index' first to create the database",
                style="red",
            )
            raise click.Abort()

        # Initialize memory store
        console.print(f"[dim]Loading statistics from {db_path}...[/]")
        store = SQLiteStore(str(db_path))

        # Initialize memory manager
        manager = MemoryManager(store)

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

        # Close store
        store.close()

    except MemoryStoreError as e:
        # Already has formatted error message
        logger.error(f"Stats command failed: {e}", exc_info=True)
        console.print(f"\n{e}", style="red")
        raise click.Abort()
    except Exception as e:
        # Unexpected error - format it
        logger.error(f"Stats command failed: {e}", exc_info=True)
        error_handler = ErrorHandler()
        error_msg = error_handler.handle_memory_error(e, "retrieving statistics")
        console.print(f"\n{error_msg}", style="red")
        raise click.Abort()


def _display_rich_results(results: list, query: str, show_content: bool) -> None:
    """Display search results with rich formatting.

    Args:
        results: List of SearchResult objects
        query: Original search query
        show_content: Whether to show content preview
    """
    if not results:
        console.print("\n[yellow]No results found.[/]")
        console.print(
            "Try:\n"
            "  - Broadening your search query\n"
            "  - Checking if the codebase has been indexed"
        )
        return

    console.print(f"\n[bold green]Found {len(results)} results for '{query}'[/]\n")

    # Create results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="yellow", width=40)
    table.add_column("Type", style="green", width=12)
    table.add_column("Name", style="cyan", width=25)
    table.add_column("Lines", style="dim", width=12)
    table.add_column("Score", justify="right", style="bold blue", width=10)

    if show_content:
        table.add_column("Preview", style="white", width=50)

    for result in results:
        file_path = Path(result.file_path).name  # Just filename
        element_type = result.metadata.get("type", "unknown")
        name = result.metadata.get("name", "<unnamed>")
        line_start, line_end = result.line_range
        line_range_str = f"{line_start}-{line_end}"

        # Format score with color
        score = result.hybrid_score
        score_text = _format_score(score)

        row = [
            _truncate_text(file_path, 40),
            element_type,
            _truncate_text(name, 25),
            line_range_str,
            score_text,
        ]

        if show_content:
            content_preview = _truncate_text(result.content, 50)
            row.append(content_preview)

        table.add_row(*row)

    console.print(table)

    # Show average scores
    avg_activation = sum(r.activation_score for r in results) / len(results)
    avg_semantic = sum(r.semantic_score for r in results) / len(results)
    avg_hybrid = sum(r.hybrid_score for r in results) / len(results)

    console.print("\n[dim]Average scores:[/]")
    console.print(f"  Activation: {avg_activation:.3f}")
    console.print(f"  Semantic:   {avg_semantic:.3f}")
    console.print(f"  Hybrid:     {avg_hybrid:.3f}\n")


def _display_json_results(results: list) -> None:
    """Display search results as JSON.

    Args:
        results: List of SearchResult objects
    """
    json_results = []
    for result in results:
        json_results.append({
            "chunk_id": result.chunk_id,
            "file_path": result.file_path,
            "line_start": result.line_range[0],
            "line_end": result.line_range[1],
            "content": result.content,
            "activation_score": result.activation_score,
            "semantic_score": result.semantic_score,
            "hybrid_score": result.hybrid_score,
            "metadata": result.metadata,
        })

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
