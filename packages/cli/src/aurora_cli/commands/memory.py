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
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aurora_cli.config import Config, load_config
from aurora_cli.errors import ErrorHandler, handle_errors
from aurora_cli.memory_manager import IndexProgress, MemoryManager, SearchResult
from aurora_core.metrics.query_metrics import QueryMetrics

__all__ = ["memory_group", "run_indexing", "display_indexing_summary"]

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="mem")
def memory_group() -> None:
    r"""Memory management commands for indexing and searching code.

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


class _WarningFilter(logging.Filter):
    """Filter that suppresses warnings during indexing while counting them.

    Warnings are collected and displayed in the final summary instead of
    interrupting the progress bar during indexing.
    """

    def __init__(self) -> None:
        super().__init__()
        self.warning_count = 0
        self.warning_messages: list[str] = []

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress WARNING level logs, True otherwise."""
        if record.levelno == logging.WARNING:
            self.warning_count += 1
            self.warning_messages.append(record.getMessage())
            return False  # Suppress the warning
        return True  # Allow other log levels through


def run_indexing(
    path: Path,
    config: Config | None = None,
    show_db_path: bool = True,
    output_console: Console | None = None,
) -> tuple[Any, int]:
    """Run memory indexing with progress display.

    This is the shared implementation used by both `aur mem index` and `aur init`.

    Args:
        path: Directory or file to index
        config: Config object with db_path. If None, loads default config.
        show_db_path: Whether to print the database path being used
        output_console: Console instance for output. Uses module console if None.

    Returns:
        Tuple of (IndexStats, total_warnings) from the indexing operation

    Raises:
        Any exceptions from MemoryManager.index_path()
    """
    from aurora_cli.memory_manager import IndexProgress, MemoryManager

    out = output_console or console

    # Load configuration if not provided
    if config is None:
        config = load_config()

    db_path_str = config.get_db_path()

    # Initialize memory manager with config
    if show_db_path:
        out.print(f"[dim]Using database: {db_path_str}[/]")

    manager = MemoryManager(config=config)

    # Suppress parse warnings during indexing for cleaner progress output
    # Warnings are counted via filter and displayed in the final summary
    parser_logger = logging.getLogger("aurora_context_code.languages.python")
    warning_filter = _WarningFilter()
    parser_logger.addFilter(warning_filter)

    try:
        # Use Live display for more control over layout
        total_files: int = 0
        files_processed: int = 0
        current_phase: str = "discovering"

        # Phase descriptions
        phase_details = {
            "discovering": "Scanning directory...",
            "parsing": "Parsing source files...",
            "git_blame": "Extracting git history...",
            "embedding": "Generating embeddings...",
            "storing": "Writing to database...",
            "complete": "Done",
        }

        def make_progress_display() -> Table:
            """Create the progress display table."""
            # Calculate percentage
            pct = (files_processed / total_files * 100) if total_files > 0 else 0
            filled = int(pct / 100 * 40)
            bar = "[green]" + "━" * filled + "[/]" + "[dim]" + "━" * (40 - filled) + "[/]"

            table = Table.grid(padding=0)
            table.add_column()

            # Main progress line
            files_str = f"{files_processed}/{total_files} files" if total_files > 0 else ""
            table.add_row(f"Indexing files {bar} {pct:3.0f}% {files_str}")

            # Phase detail line
            phase_detail = phase_details.get(current_phase, "")
            table.add_row(f"  [dim]{phase_detail}[/]")

            return table

        def progress_callback(prog: IndexProgress) -> None:
            nonlocal total_files, files_processed, current_phase

            current_phase = prog.phase

            # Track total files from parsing phase
            if prog.phase == "parsing" and prog.total > 0:
                total_files = prog.total

            # Track files processed (only advances during parsing/git_blame)
            if prog.phase in ("parsing", "git_blame"):
                files_processed = prog.current

            # When complete, ensure bar shows 100%
            if prog.phase == "complete" and total_files > 0:
                files_processed = total_files

            live.update(make_progress_display())

        with Live(make_progress_display(), console=out, refresh_per_second=10) as live:
            # Perform indexing
            stats = manager.index_path(path, progress_callback=progress_callback)
    finally:
        # Always remove the filter when done
        parser_logger.removeFilter(warning_filter)

    # Calculate total warnings
    total_warnings = stats.warnings + warning_filter.warning_count

    return stats, total_warnings


def display_indexing_summary(
    stats: Any,
    total_warnings: int,
    output_console: Console | None = None,
    log_path: Path | None = None,
) -> None:
    """Display indexing summary with stats and any issues.

    Args:
        stats: IndexStats from run_indexing
        total_warnings: Total warning count from run_indexing
        output_console: Console instance for output. Uses module console if None.
        log_path: Optional path to the index log file for skipped files info.
    """
    out = output_console or console

    out.print()
    out.print("[bold green]Indexing Complete[/]")
    out.print(f"  Files indexed:  {stats.files_indexed}")
    out.print(f"  Chunks created: {stats.chunks_created}")
    out.print(f"  Duration:       {stats.duration_seconds:.2f}s")

    # Display error/warning summary table if there are issues
    if stats.errors > 0 or total_warnings > 0:
        out.print()
        out.print("[bold]Indexing Issues Summary:[/]")
        out.print("┌─────────────┬───────┬────────────────────────────────────────┐")
        out.print("│ Issue Type  │ Count │ What To Do                             │")
        out.print("├─────────────┼───────┼────────────────────────────────────────┤")

        if stats.errors > 0:
            out.print(
                f"│ [red]Errors[/]      │ {stats.errors:5} │ Files that failed to parse             │"
            )
            out.print("│             │       │ → May be corrupted or binary files     │")
            out.print("│             │       │ → Action: Check with aur mem stats     │")

        if total_warnings > 0:
            if stats.errors > 0:
                out.print("├─────────────┼───────┼────────────────────────────────────────┤")
            out.print(
                f"│ [yellow]Warnings[/]    │ {total_warnings:5} │ Files with syntax/parse issues         │"
            )
            out.print("│             │       │ → Partial indexing succeeded           │")
            out.print("│             │       │ → Details: aur mem stats               │")

        out.print("└─────────────┴───────┴────────────────────────────────────────┘")

        # Show helpful follow-up hints
        out.print()
        out.print("[dim]For more details: aur mem stats[/]")
        if log_path and log_path.exists():
            out.print(f"[dim]Skipped files logged to: {log_path}[/]")


@memory_group.command(name="index")
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Database path (overrides config, useful for testing)",
)
@click.pass_context
@handle_errors
def index_command(ctx: click.Context, path: Path, db_path: Path | None) -> None:
    r"""Index code files into memory store.

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

        \b
        # Use custom database path
        aur mem index . --db-path /tmp/test.db
    """
    # Load configuration
    config = load_config()

    # Override db_path if provided
    if db_path:
        config.db_path = str(db_path)

    # Use shared indexing function
    stats, total_warnings = run_indexing(path, config=config)

    # Determine log path for display
    db_path_resolved = Path(config.get_db_path())
    log_path = db_path_resolved.parent / "logs" / "index.log"

    # Display summary
    display_indexing_summary(stats, total_warnings, log_path=log_path)


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
    type=click.Choice(["function", "class", "method", "knowledge", "document", "kb", "code"]),
    default=None,
    help="Filter results by chunk type (function, class, method, kb, code)",
)
@click.option(
    "--show-scores",
    is_flag=True,
    default=False,
    help="Display detailed score breakdown with explanations. Shows BM25 (keyword matching), "
    "Semantic (conceptual relevance), and Activation (recency/frequency) scores in rich "
    "box-drawing format. Includes intelligent explanations for each score component.",
)
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Database path (overrides config, useful for testing)",
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
    db_path: Path | None,
) -> None:
    r"""Search AURORA memory for relevant chunks.

    QUERY is the text to search for in memory. Uses hybrid retrieval
    (activation + semantic similarity) to find relevant chunks.

    \b
    Note: Type column displays abbreviated type names (func, meth, class, code,
    reas, know, doc) for improved readability.

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

        \b
        # Show detailed score explanations
        aur mem search "authentication" --show-scores
    """
    # Load configuration
    config = load_config()

    # Override db_path if provided
    if db_path:
        config.db_path = str(db_path)

    db_path_resolved = Path(config.get_db_path())

    if not db_path_resolved.exists():
        error_handler = ErrorHandler()
        error = FileNotFoundError(f"Database not found at {db_path_resolved}")
        error_msg = error_handler.handle_path_error(
            error, str(db_path_resolved), "opening database"
        )
        console.print(
            f"\n{error_msg}\n\n"
            "[green]Hint:[/] Run [cyan]aur mem index .[/] to create and populate the database.",
            style="red",
        )
        raise click.Abort()

    # Initialize memory manager with config
    console.print(f"[dim]Searching memory from {db_path_resolved}...[/]")
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

    # Save results to cache for 'aur mem get' command
    _save_search_cache(results)


@memory_group.command(name="get")
@click.argument("index", type=int)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "json"]),
    default="rich",
    help="Output format",
)
@click.pass_context
@handle_errors
def get_command(ctx: click.Context, index: int, output_format: str) -> None:
    r"""Retrieve full content of a search result by index.

    INDEX is the 1-based result number from the last search.

    \b
    Examples:
        # Get first result from last search
        aur mem get 1

        \b
        # Get third result with JSON output
        aur mem get 3 --format json
    """
    # Load cached results
    results = _load_search_cache()

    if not results:
        console.print("\n[yellow]No search results cached.[/]")
        console.print("[dim]Run 'aur mem search <query>' first.[/]\n")
        raise click.Abort()

    # Validate index (1-based)
    if index < 1 or index > len(results):
        console.print(f"\n[red]Index {index} out of range.[/]")
        console.print(f"[dim]Last search had {len(results)} results (valid: 1-{len(results)})[/]\n")
        raise click.Abort()

    # Get result (convert to 0-based)
    result = results[index - 1]

    # Display
    if output_format == "json":
        click.echo(json.dumps(result.__dict__, indent=2, default=str))
    else:
        _display_single_result(result, index, len(results))


@memory_group.command(name="stats")
@click.option(
    "--db-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Database path (overrides config, useful for testing)",
)
@click.pass_context
@handle_errors
def stats_command(ctx: click.Context, db_path: Path | None) -> None:
    r"""Display memory store statistics.

    Shows information about indexed chunks, files, languages, and database size.

    \b
    Examples:
        # Show stats for database
        aur mem stats

        \b
        # Show stats for custom database
        aur mem stats --db-path /tmp/test.db
    """
    # Load configuration
    config = load_config()

    # Override db_path if provided
    if db_path:
        config.db_path = str(db_path)

    db_path_resolved = Path(config.get_db_path())

    if not db_path_resolved.exists():
        console.print(
            f"[bold red]Error:[/] Database not found at {db_path_resolved}\n"
            f"Run 'aur mem index' first to create the database",
            style="red",
        )
        raise click.Abort()

    # Initialize memory manager with config
    console.print(f"[dim]Loading statistics from {db_path_resolved}...[/]")
    manager = MemoryManager(config=config)

    # Get statistics
    stats = manager.get_stats()

    # Display statistics table
    table = Table(title="Memory Store Statistics", show_header=False)
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Value", style="white")

    table.add_row("Total Chunks", f"[bold]{stats.total_chunks:,}[/]")
    # Use files_by_language sum if available (more accurate), else fall back to DB count
    total_indexed_files = (
        sum(stats.files_by_language.values()) if stats.files_by_language else stats.total_files
    )
    table.add_row("Total Files", f"[bold]{total_indexed_files:,}[/]")
    table.add_row("Database Size", f"[bold]{stats.database_size_mb:.2f} MB[/]")

    # Add indexing metadata if available
    if stats.last_indexed:
        from datetime import datetime

        try:
            indexed_time = datetime.fromisoformat(stats.last_indexed)
            time_ago = datetime.now(indexed_time.tzinfo or None) - indexed_time
            hours_ago = time_ago.total_seconds() / 3600
            if hours_ago < 1:
                time_str = f"{int(time_ago.total_seconds() / 60)} minutes ago"
            elif hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                time_str = f"{int(hours_ago / 24)} days ago"
            table.add_row("Last Indexed", time_str)
        except Exception:
            table.add_row("Last Indexed", "Unknown")

    # Show success rate if there were issues
    if stats.success_rate < 1.0:
        success_pct = stats.success_rate * 100
        table.add_row("Success Rate", f"[yellow]{success_pct:.1f}%[/]")

    # Show log location hint (after table, but calculate path now)
    log_path = db_path_resolved.parent / "logs" / "index.log"
    show_log_hint = stats.success_rate < 1.0 and log_path.exists()

    # Show files breakdown by language (from indexed files, not chunks)
    if stats.files_by_language:
        for lang, count in sorted(
            stats.files_by_language.items(), key=lambda x: x[1], reverse=True
        ):
            table.add_row(f"  {lang}", f"{count:,} files")
    elif stats.languages:
        # Fallback to chunk-based language display if no file breakdown
        for lang, count in sorted(stats.languages.items(), key=lambda x: x[1], reverse=True):
            table.add_row(f"  {lang}", f"{count:,} chunks")

    console.print()
    console.print(table)

    # Show log hint if there were skipped files
    if show_log_hint:
        console.print(f"[dim]Skipped files logged to: {log_path}[/]")

    console.print()

    # Display errors and warnings if present
    if stats.failed_files or stats.warnings:
        console.print("[bold yellow]Indexing Issues[/]\n")

        if stats.failed_files:
            console.print(f"[yellow]{len(stats.failed_files)} files failed to index[/]\n")
            console.print("[bold]Failed Files:[/]")
            for file_path, error in stats.failed_files[:10]:  # Show first 10
                console.print(f"  • [red]{Path(file_path).name}[/]: {error}")
            if len(stats.failed_files) > 10:
                console.print(f"  [dim]... and {len(stats.failed_files) - 10} more[/]")
            console.print()

        if stats.warnings:
            console.print(f"[yellow]{len(stats.warnings)} warnings[/]\n")
            console.print("[bold]Warnings:[/]")
            for warning in stats.warnings[:10]:  # Show first 10
                console.print(f"  • {warning}")
            if len(stats.warnings) > 10:
                console.print(f"  [dim]... and {len(stats.warnings) - 10} more[/]")
            console.print()

        console.print("[dim]💡 Run 'aur mem index .' to re-index[/]\n")

    # Display query metrics (simplified summary)
    try:
        query_metrics = QueryMetrics()
        metrics_summary = query_metrics.get_summary()

        if metrics_summary.total_queries > 0:
            metrics_table = Table(title="Usage Summary", show_header=False)
            metrics_table.add_column("Metric", style="cyan", width=24)
            metrics_table.add_column("Value", style="white")

            # Query counts in one line
            metrics_table.add_row(
                "Queries",
                f"[bold]{metrics_summary.total_queries}[/] total "
                f"({metrics_summary.total_soar_queries} SOAR, "
                f"{metrics_summary.total_simple_queries} simple)",
            )

            # Average duration
            if metrics_summary.avg_duration_ms > 0:
                avg_sec = metrics_summary.avg_duration_ms / 1000
                metrics_table.add_row("Avg Time", f"{avg_sec:.1f}s")

            # Complexity breakdown in one line
            if metrics_summary.complexity_breakdown:
                breakdown = metrics_summary.complexity_breakdown
                parts = []
                for level in ["SIMPLE", "MEDIUM", "COMPLEX"]:
                    if level in breakdown:
                        parts.append(f"{breakdown[level]} {level.lower()}")
                if parts:
                    metrics_table.add_row("By Complexity", ", ".join(parts))

            # Goals created (count plans in active directory)
            try:
                plans_dir = Path.cwd() / ".aurora" / "plans" / "active"
                if plans_dir.exists():
                    goals_count = len([d for d in plans_dir.iterdir() if d.is_dir()])
                    if goals_count > 0:
                        metrics_table.add_row("Goals Created", f"{goals_count}")
            except Exception:
                pass

            console.print(metrics_table)
            console.print()
    except Exception as e:
        # Silently skip if metrics table doesn't exist yet
        logger.debug(f"Query metrics not available: {e}")


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
            "[yellow]Warning: All results have weak semantic relevance[/]\n"
            "Results shown are based primarily on recent access history, not semantic match.\n"
            "[dim]Consider:[/]\n"
            "  • [cyan]Broadening your search query[/]\n"
            "  • [cyan]Re-indexing if files are missing[/]: aur mem index .\n"
            "  • [cyan]Using grep for exact matches[/]: grep -r 'term' .\n"
        )

    # Create results table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File", style="yellow", width=28)
    table.add_column("Type", style="green", width=8)
    table.add_column("Name", style="cyan", width=18)
    table.add_column("Lines", style="dim", width=9)
    table.add_column("Commits", style="magenta", width=7, justify="right")
    table.add_column("Modified", style="dim cyan", width=9)
    table.add_column("Score", justify="right", style="bold blue", width=7)

    if show_content:
        table.add_column("Preview", style="white", width=50)

    # Mark results with weak semantic relevance as "low"
    # These are results boosted mainly by activation (recency) rather than semantic match
    # Use a threshold relative to normalized semantic scores (0-1 range after min-max normalization)
    semantic_low_threshold = 0.4  # Normalized semantic score threshold

    for result in results:
        file_path = Path(result.file_path).name  # Just filename
        element_type_full = result.metadata.get("type", "unknown")
        element_type = _get_type_abbreviation(element_type_full)
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
    console.print(f"  Hybrid:     {avg_hybrid:.3f}")

    # Show helpful tips for follow-up commands
    console.print("\n[dim]Refine your search:[/]")
    console.print("  --show-scores    Detailed score breakdown (BM25, semantic, activation)")
    console.print("  --show-content   Preview code snippets")
    console.print("  --limit N        More results (e.g., --limit 20)")
    console.print("  --type TYPE      Filter: function, class, method, kb, code")
    console.print("  --min-score 0.5  Higher relevance threshold")
    console.print()

    # Show detailed score breakdown if requested
    if show_scores:
        console.print("[bold cyan]Detailed Score Breakdown:[/]\n")

        # Detect terminal width (default 80, Rich typically sets this)
        terminal_width = console.width if hasattr(console, "width") and console.width > 0 else 80

        for i, result in enumerate(results, 1):
            box = _format_score_box(result, rank=i, query=query, terminal_width=terminal_width)
            console.print(box)
            # Add spacing between boxes (empty line)
            if i < len(results):
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


def _get_type_abbreviation(element_type: str) -> str:
    """Get abbreviated type name for display.

    Maps full type names to abbreviated forms for improved readability in tables.

    Args:
        element_type: Full type name (e.g., "function", "knowledge")

    Returns:
        Abbreviated type (e.g., "func", "know")

    Examples:
        >>> _get_type_abbreviation("function")
        'func'
        >>> _get_type_abbreviation("knowledge")
        'know'
        >>> _get_type_abbreviation("UNKNOWN")
        'unk'
    """
    # Mapping of full type names to abbreviations
    type_mapping = {
        "function": "func",
        "method": "meth",
        "class": "class",
        "code": "code",
        "reasoning": "reas",
        "knowledge": "know",
        "document": "doc",
        "kb": "kb",  # Knowledge base (markdown files)
        "section": "sect",  # Markdown sections
    }

    # Case-insensitive lookup with default to "unk" for unknown types
    return type_mapping.get(element_type.lower(), "unk")


def _format_score_box(
    result: SearchResult, rank: int, query: str = "", terminal_width: int = 78
) -> Text:
    """Format search result with rich box-drawing for score display.

    Creates a visually formatted box containing:
    - Header with file, type, name, line range
    - Final hybrid score
    - Individual score components (BM25, Semantic, Activation) with explanations
    - Git metadata (commits, last modified) if available

    Args:
        result: SearchResult object with scores and metadata
        rank: Result rank (1-based)
        query: Search query text for explanation generation
        terminal_width: Terminal width for box sizing (default 78)

    Returns:
        Rich Text object with formatted box using Unicode box-drawing characters

    Example output:
        ┌─ auth.py | func | authenticate (Lines 45-67) ─────────┐
        │ Final Score: 0.856                                     │
        │   ├─ BM25:       0.950 ⭐ (exact keyword match on "auth") │
        │   ├─ Semantic:   0.820 (high conceptual relevance)     │
        │   └─ Activation: 0.650 (accessed 3x, 23 commits, 2 days ago) │
        │ Git: 23 commits, last modified 2 days ago              │
        └─────────────────────────────────────────────────────────┘
    """
    # Extract metadata
    file_path = result.metadata.get("file_path", "unknown")
    element_type_full = result.metadata.get("type", "unknown")
    element_type = _get_type_abbreviation(element_type_full)
    name = result.metadata.get("name", "<unnamed>")
    line_start = result.metadata.get("line_start", 0)
    line_end = result.metadata.get("line_end", 0)

    # Get just filename from path
    file_name = Path(file_path).name if file_path != "unknown" else file_path

    # Format line range
    if line_start > 0 and line_end > 0:
        line_range = f"Lines {line_start}-{line_end}"
    else:
        line_range = "-"

    # Build header content
    header_content = f"{file_name} | {element_type} | {name} ({line_range})"

    # Calculate padding for header (width - 4 for corners/spaces - content length)
    content_width = terminal_width - 4
    if len(header_content) > content_width - 4:
        # Truncate name if too long
        available_for_name = (
            content_width - len(file_name) - len(element_type) - len(line_range) - 15
        )
        if available_for_name > 10:
            name = _truncate_text(name, available_for_name)
        else:
            name = _truncate_text(name, 10)
        header_content = f"{file_name} | {element_type} | {name} ({line_range})"

    # Truncate again if still too long
    if len(header_content) > content_width - 4:
        header_content = _truncate_text(header_content, content_width - 4)

    header_padding = content_width - len(header_content) - 2
    header_line = f"┌─ {header_content} {'─' * header_padding}┐"

    # Build box lines
    lines = []
    lines.append(header_line)

    # Final score line
    score_text = f"Final Score: {result.hybrid_score:.3f}"
    score_padding = content_width - len(score_text)
    lines.append(f"│ {score_text}{' ' * score_padding}│")

    # Generate explanations for each score component
    bm25_explanation = _explain_bm25_score(query, result.content, result.bm25_score)
    semantic_explanation = _explain_semantic_score(result.semantic_score)
    activation_explanation = _explain_activation_score(result.metadata, result.activation_score)

    # BM25 score line with explanation
    bm25_score_str = f"  ├─ BM25:       {result.bm25_score:.3f}"
    if bm25_explanation:
        # Add star emoji for exact matches
        if "exact keyword match" in bm25_explanation:
            bm25_text = f"{bm25_score_str} ⭐ ({bm25_explanation})"
        else:
            bm25_text = f"{bm25_score_str} ({bm25_explanation})"
    else:
        bm25_text = bm25_score_str

    # Truncate if too long to fit
    if len(bm25_text) > content_width - 2:
        bm25_text = _truncate_text(bm25_text, content_width - 2)
    bm25_padding = content_width - len(bm25_text)
    lines.append(f"│{bm25_text}{' ' * bm25_padding} │")

    # Semantic score line with explanation
    semantic_score_str = f"  ├─ Semantic:   {result.semantic_score:.3f}"
    if semantic_explanation:
        semantic_text = f"{semantic_score_str} ({semantic_explanation})"
    else:
        semantic_text = semantic_score_str

    # Truncate if too long to fit
    if len(semantic_text) > content_width - 2:
        semantic_text = _truncate_text(semantic_text, content_width - 2)
    semantic_padding = content_width - len(semantic_text)
    lines.append(f"│{semantic_text}{' ' * semantic_padding} │")

    # Activation score line (last, uses └) with explanation
    activation_score_str = f"  └─ Activation: {result.activation_score:.3f}"
    if activation_explanation:
        activation_text = f"{activation_score_str} ({activation_explanation})"
    else:
        activation_text = activation_score_str

    # Truncate if too long to fit
    if len(activation_text) > content_width - 2:
        activation_text = _truncate_text(activation_text, content_width - 2)
    activation_padding = content_width - len(activation_text)
    lines.append(f"│{activation_text}{' ' * activation_padding} │")

    # Git metadata line (if available)
    commit_count = result.metadata.get("commit_count")
    last_modified = result.metadata.get("last_modified")

    if commit_count is not None or last_modified:
        git_parts = []
        if commit_count is not None:
            plural = "commit" if commit_count == 1 else "commits"
            git_parts.append(f"{commit_count} {plural}")
        if last_modified:
            git_parts.append(f"last modified {last_modified}")

        if git_parts:
            git_text = f"Git: {', '.join(git_parts)}"
            # Truncate if too long
            max_git_length = content_width - 2
            if len(git_text) > max_git_length:
                git_text = _truncate_text(git_text, max_git_length)
            git_padding = content_width - len(git_text)
            lines.append(f"│ {git_text}{' ' * git_padding}│")

    # Footer line
    footer_line = f"└{'─' * content_width}┘"
    lines.append(footer_line)

    # Create Rich Text with styling
    text = Text()
    for i, line in enumerate(lines):
        if i == 0:
            # Header in cyan
            text.append(line + "\n", style="cyan")
        elif "Final Score:" in line:
            # Final score in bold
            text.append(line + "\n", style="bold white")
        elif "BM25:" in line:
            # BM25 in yellow
            text.append(line + "\n", style="yellow")
        elif "Semantic:" in line:
            # Semantic in green
            text.append(line + "\n", style="green")
        elif "Activation:" in line:
            # Activation in blue
            text.append(line + "\n", style="blue")
        elif "Git:" in line:
            # Git metadata in dim
            text.append(line + "\n", style="dim")
        else:
            # Footer
            text.append(line + "\n", style="cyan")

    return text


def _explain_bm25_score(query: str, chunk_content: str, bm25_score: float) -> str:
    """Generate human-readable explanation for BM25 score.

    Analyzes query term matching to produce explanations like:
    - "exact keyword match on 'auth', 'user'"
    - "strong term overlap (2/3 terms)"
    - "partial match (1/4 terms)"
    - "" (empty string for no match)

    Args:
        query: Search query text
        chunk_content: Content of chunk that was scored
        bm25_score: BM25 score value (unused but included for consistency)

    Returns:
        Human-readable explanation string (may be empty if no match)

    Examples:
        >>> _explain_bm25_score("authenticate", "authenticate_user() impl", 0.95)
        "exact keyword match on 'authenticate'"

        >>> _explain_bm25_score("user auth flow", "User authentication...", 0.75)
        "strong term overlap (2/3 terms)"
    """
    # Import tokenizer from BM25Scorer
    from aurora_context_code.semantic.bm25_scorer import tokenize

    # Handle empty query
    if not query or not query.strip():
        return ""

    # Tokenize query and content (tokenizer handles lowercasing internally)
    query_terms = set(tokenize(query))
    content_tokens = set(tokenize(chunk_content))

    # Find exact matches
    exact_matches = query_terms & content_tokens

    # Calculate match ratio
    if len(query_terms) == 0:
        return ""

    match_ratio = len(exact_matches) / len(query_terms)

    # Generate explanation based on ratio
    if match_ratio == 1.0:
        # All query terms present - exact match
        if len(exact_matches) == 0:
            return ""
        # Format matched terms (limit to first 3 for brevity)
        matched_list = sorted(list(exact_matches))[:3]
        if len(exact_matches) == 1:
            return f"exact keyword match on '{matched_list[0]}'"
        elif len(exact_matches) <= 3:
            terms_str = "', '".join(matched_list)
            return f"exact keyword match on '{terms_str}'"
        else:
            terms_str = "', '".join(matched_list)
            return f"exact keyword match on '{terms_str}', +{len(exact_matches) - 3} more"

    elif match_ratio >= 0.5:
        # ≥50% query terms present - strong overlap
        return f"strong term overlap ({len(exact_matches)}/{len(query_terms)} terms)"

    elif match_ratio > 0:
        # Some terms present but <50% - partial match
        return f"partial match ({len(exact_matches)}/{len(query_terms)} terms)"

    else:
        # No matches
        return ""


def _format_relative_time(seconds_ago: float) -> str:
    """Format timestamp as relative time string.

    Args:
        seconds_ago: Seconds since the event

    Returns:
        Human-readable relative time (e.g., "2 days ago", "3 weeks ago")
    """
    from datetime import timedelta

    delta = timedelta(seconds=seconds_ago)
    days = delta.days

    if days == 0:
        hours = int(delta.seconds / 3600)
        if hours == 0:
            minutes = int(delta.seconds / 60)
            if minutes == 0:
                return "just now"
            elif minutes == 1:
                return "1 minute ago"
            else:
                return f"{minutes} minutes ago"
        elif hours == 1:
            return "1 hour ago"
        else:
            return f"{hours} hours ago"
    elif days == 1:
        return "1 day ago"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        weeks = days // 7
        if weeks == 1:
            return "1 week ago"
        else:
            return f"{weeks} weeks ago"
    elif days < 365:
        months = days // 30
        if months == 1:
            return "1 month ago"
        else:
            return f"{months} months ago"
    else:
        years = days // 365
        if years == 1:
            return "1 year ago"
        else:
            return f"{years} years ago"


def _explain_semantic_score(semantic_score: float) -> str:
    """Generate human-readable explanation for semantic score.

    Uses threshold-based relevance levels to describe semantic similarity:
    - ≥0.9: "very high conceptual relevance"
    - 0.8-0.89: "high conceptual relevance"
    - 0.7-0.79: "moderate conceptual relevance"
    - <0.7: "low conceptual relevance"

    Args:
        semantic_score: Semantic similarity score (0.0-1.0)

    Returns:
        Human-readable relevance level description

    Examples:
        >>> _explain_semantic_score(0.95)
        "very high conceptual relevance"

        >>> _explain_semantic_score(0.75)
        "moderate conceptual relevance"
    """
    if semantic_score >= 0.9:
        return "very high conceptual relevance"
    elif semantic_score >= 0.8:
        return "high conceptual relevance"
    elif semantic_score >= 0.7:
        return "moderate conceptual relevance"
    else:
        return "low conceptual relevance"


def _explain_activation_score(metadata: dict[str, Any], activation_score: float) -> str:
    """Generate human-readable explanation for activation score.

    Combines access frequency, git commit history, and recency information
    into a concise explanation string.

    Args:
        metadata: Chunk metadata dictionary with optional keys:
            - access_count: Number of times accessed (required, defaults to 0)
            - commit_count: Number of git commits (optional)
            - last_modified: Timestamp of last modification (optional)
        activation_score: Activation score value (unused but included for consistency)

    Returns:
        Explanation string (e.g., "accessed 3x, 23 commits, last used 2 days ago")

    Examples:
        >>> metadata = {"access_count": 5, "commit_count": 23}
        >>> _explain_activation_score(metadata, 0.85)
        "accessed 5x, 23 commits"

        >>> metadata = {"access_count": 1}
        >>> _explain_activation_score(metadata, 0.45)
        "accessed 1x"
    """
    from datetime import datetime

    # Extract metadata fields
    access_count = metadata.get("access_count", 0)
    commit_count = metadata.get("commit_count")
    last_modified = metadata.get("last_modified")

    # Build explanation parts
    parts = []

    # Access count (always present)
    parts.append(f"accessed {access_count}x")

    # Git commit count (if available)
    if commit_count is not None and commit_count > 0:
        plural = "commit" if commit_count == 1 else "commits"
        parts.append(f"{commit_count} {plural}")

    # Recency (if available)
    if last_modified is not None:
        try:
            # Calculate time ago
            now = datetime.now().timestamp()
            seconds_ago = now - last_modified
            recency_str = _format_relative_time(seconds_ago)
            parts.append(f"last used {recency_str}")
        except (ValueError, TypeError):
            # Invalid timestamp, skip recency
            pass

    return ", ".join(parts)


def _save_search_cache(results: list[SearchResult]) -> None:
    """Save search results to cache file for 'aur mem get' command.

    Args:
        results: List of search results to cache
    """
    import pickle
    import tempfile

    cache_file = Path(tempfile.gettempdir()) / "aurora_search_cache.pkl"
    try:
        with open(cache_file, "wb") as f:
            pickle.dump(results, f)
    except Exception as e:
        logger.warning(f"Failed to cache search results: {e}")


def _load_search_cache() -> list[SearchResult] | None:
    """Load cached search results from file.

    Returns:
        List of cached results, or None if cache doesn't exist or is expired
    """
    import pickle
    import tempfile
    import time

    cache_file = Path(tempfile.gettempdir()) / "aurora_search_cache.pkl"

    if not cache_file.exists():
        return None

    # Check if cache is expired (10 minutes)
    cache_age = time.time() - cache_file.stat().st_mtime
    if cache_age > 600:
        return None

    try:
        with open(cache_file, "rb") as f:
            return pickle.load(f)  # nosec B301 - local trusted cache file
    except Exception as e:
        logger.warning(f"Failed to load search cache: {e}")
        return None


def _display_single_result(result: SearchResult, index: int, total: int) -> None:
    """Display a single search result with full content.

    Args:
        result: Search result to display
        index: 1-based index in result list
        total: Total number of results
    """
    # Header
    console.print()
    console.print(f"[bold cyan]Result #{index} of {total}[/]")
    console.print()

    # Metadata table
    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")

    meta_table.add_row("File:", result.file_path)
    if result.metadata.get("name"):
        meta_table.add_row("Name:", result.metadata["name"])
    if result.line_range and result.line_range != (0, 0):
        meta_table.add_row("Lines:", f"{result.line_range[0]}-{result.line_range[1]}")
    meta_table.add_row("Score:", f"{result.hybrid_score:.3f}")
    meta_table.add_row("  BM25:", f"{result.bm25_score:.3f}")
    meta_table.add_row("  Semantic:", f"{result.semantic_score:.3f}")
    meta_table.add_row("  Activation:", f"{result.activation_score:.3f}")

    console.print(meta_table)
    console.print()

    # Content with syntax highlighting
    # Detect language from file extension
    file_ext = Path(result.file_path).suffix.lstrip(".")
    lang_map = {"py": "python", "js": "javascript", "ts": "typescript", "md": "markdown"}
    language = lang_map.get(file_ext, file_ext or "text")

    syntax = Syntax(result.content, language, theme="monokai", line_numbers=False)
    console.print(Panel(syntax, border_style="dim"))
    console.print()


if __name__ == "__main__":
    memory_group()
