"""Conversation logging for Aurora SOAR pipeline.

Logs SOAR interactions to markdown files with structured phase data.
"""

import json
import re
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aurora_core.paths import get_conversations_dir


class ChunkAwareEncoder(json.JSONEncoder):
    """JSON encoder that handles CodeChunk and other dataclass-like objects."""

    def default(self, obj: Any) -> Any:
        # Handle objects with to_json method (like CodeChunk)
        if hasattr(obj, "to_json"):
            return obj.to_json()
        # Handle objects with __dict__ (most Python objects)
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        # Handle datetime objects
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        # Handle bytes
        if isinstance(obj, bytes):
            return "<binary data>"
        return super().default(obj)


class VerbosityLevel(str, Enum):
    """Verbosity levels for SOAR output."""

    QUIET = "quiet"  # Single line with score
    NORMAL = "normal"  # Phase progress with key metrics
    VERBOSE = "verbose"  # Full trace with detailed metadata
    JSON = "json"  # Structured JSON logs


class ConversationLogger:
    """Logs SOAR conversations to markdown files.

    Creates timestamped markdown logs in ./.aurora/logs/conversations/YYYY/MM/
    with structured phase data and execution summary.

    Attributes:
        base_path: Base directory for conversation logs
        enabled: Whether logging is enabled

    """

    def __init__(self, base_path: Path | None = None, enabled: bool = True):
        """Initialize conversation logger.

        Args:
            base_path: Base directory for logs (default: project-local .aurora/logs/conversations)
            enabled: Whether to enable logging

        """
        if base_path is None:
            base_path = get_conversations_dir()

        self.base_path = base_path
        self.enabled = enabled

    def log_interaction(
        self,
        query: str,
        query_id: str,
        phase_data: dict[str, Any],
        execution_summary: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> Path | None:
        """Log a SOAR interaction to a markdown file.

        Args:
            query: User query
            query_id: Unique query identifier
            phase_data: Dictionary mapping phase names to phase output data
            execution_summary: Summary with duration, score, cached status
            metadata: Optional additional metadata

        Returns:
            Path to created log file, or None if logging disabled/failed

        """
        if not self.enabled:
            return None

        try:
            # Generate filename from query keywords
            filename = self._generate_filename(query)

            # Ensure directory exists
            log_dir = self._get_log_directory()
            log_dir.mkdir(parents=True, exist_ok=True)

            # Handle duplicate filenames
            log_path = self._get_unique_path(log_dir / filename)

            # Format markdown log
            content = self._format_log(
                query=query,
                query_id=query_id,
                phase_data=phase_data,
                execution_summary=execution_summary,
                metadata=metadata,
            )

            # Write synchronously (fast enough for logging)
            log_path.write_text(content)

            return log_path

        except Exception as e:
            # Log error to stderr but don't fail
            print(f"Warning: Failed to write conversation log: {e}", file=sys.stderr)
            return None

    def _get_log_directory(self) -> Path:
        """Get log directory for current year/month."""
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        return self.base_path / year / month

    def _extract_keywords(self, query: str, max_keywords: int = 2) -> list[str]:
        """Extract keywords from query for filename.

        Args:
            query: User query
            max_keywords: Maximum keywords to extract

        Returns:
            List of keywords (lowercase, alphanumeric)

        """
        # Common stop words to filter
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "will",
            "with",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "can",
            "could",
            "should",
            "would",
            "do",
            "does",
            "did",
        }

        # Extract words (alphanumeric only)
        words = re.findall(r"\b[a-zA-Z0-9]+\b", query.lower())

        # Filter stop words and keep meaningful words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Return first max_keywords
        return keywords[:max_keywords]

    def _generate_filename(self, query: str) -> str:
        """Generate filename from query keywords.

        Format: keyword1-keyword2-YYYY-MM-DD.md

        Args:
            query: User query

        Returns:
            Filename string

        """
        keywords = self._extract_keywords(query)

        # Default to "query" if no keywords found
        if not keywords:
            keywords = ["query"]

        # Join keywords with hyphen
        keyword_part = "-".join(keywords)

        # Add date
        date_part = datetime.now().strftime("%Y-%m-%d")

        return f"{keyword_part}-{date_part}.md"

    def _get_unique_path(self, path: Path) -> Path:
        """Get unique path by appending -2, -3, etc. if file exists.

        Args:
            path: Desired file path

        Returns:
            Unique file path

        """
        if not path.exists():
            return path

        # Split stem and suffix
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        # Try incrementing number
        counter = 2
        while True:
            new_path = parent / f"{stem}-{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def _format_log(
        self,
        query: str,
        query_id: str,
        phase_data: dict[str, Any],
        execution_summary: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Format conversation log as markdown.

        Args:
            query: User query
            query_id: Query identifier
            phase_data: Phase output data
            execution_summary: Execution summary
            metadata: Optional metadata

        Returns:
            Markdown-formatted log content

        """
        lines = []

        # Front matter
        lines.append("# SOAR Conversation Log")
        lines.append("")
        lines.append(f"**Query ID**: {query_id}")
        lines.append(f"**Timestamp**: {datetime.now().isoformat()}")
        lines.append(f"**User Query**: {query}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Subgoal breakdown section (from decompose phase)
        if "decompose" in phase_data:
            decompose_data = phase_data["decompose"]
            decomposition = decompose_data.get("decomposition", {})

            if isinstance(decomposition, dict):
                goal = decomposition.get("goal", "")
                subgoals = decomposition.get("subgoals", [])

                if goal or subgoals:
                    lines.append("## Subgoal Breakdown")
                    lines.append("")

                    if goal:
                        lines.append(f"**Goal**: {goal}")
                        lines.append("")

                    if subgoals:
                        lines.append("**Subgoals**:")
                        lines.append("")
                        for i, subgoal in enumerate(subgoals, 1):
                            if isinstance(subgoal, dict):
                                desc = subgoal.get("description", "")
                                agent = subgoal.get("agent", "N/A")
                                criticality = subgoal.get("criticality", "N/A")
                                dependencies = subgoal.get("dependencies", [])

                                lines.append(f"{i}. **{desc}**")
                                lines.append(f"   - Agent: `{agent}`")
                                lines.append(f"   - Criticality: {criticality}")
                                if dependencies:
                                    deps_str = ", ".join(str(d) for d in dependencies)
                                    lines.append(f"   - Dependencies: [{deps_str}]")
                                lines.append("")

                    lines.append("---")
                    lines.append("")

        # Phase sections with numbers
        phase_order = [
            ("assess", 1),
            ("retrieve", 2),
            ("decompose", 3),
            ("verify", 4),
            ("route", 5),
            ("collect", 6),
            ("synthesize", 7),
            ("record", 8),
            ("respond", 9),
        ]

        for phase_name, phase_num in phase_order:
            if phase_name in phase_data:
                lines.append(f"## Phase {phase_num}: {phase_name.capitalize()}")
                lines.append("")

                # Format phase data as JSON block
                phase_json = json.dumps(phase_data[phase_name], indent=2, cls=ChunkAwareEncoder)
                lines.append("```json")
                lines.append(phase_json)
                lines.append("```")
                lines.append("")

        # Execution summary
        lines.append("## Execution Summary")
        lines.append("")

        duration = execution_summary.get("duration_ms", 0)
        score = execution_summary.get("overall_score", 0.0)
        cached = execution_summary.get("cached", False)

        lines.append(f"- **Duration**: {duration}ms")
        lines.append(f"- **Overall Score**: {score:.2f}")
        lines.append(f"- **Cached**: {cached}")

        if "cost_usd" in execution_summary:
            lines.append(f"- **Cost**: ${execution_summary['cost_usd']:.4f}")

        if "tokens_used" in execution_summary:
            tokens = execution_summary["tokens_used"]
            if isinstance(tokens, dict):
                input_tokens = tokens.get("input", 0)
                output_tokens = tokens.get("output", 0)
                lines.append(f"- **Tokens Used**: {input_tokens} input + {output_tokens} output")
            else:
                lines.append(f"- **Tokens Used**: {tokens}")

        lines.append("")

        # Additional metadata
        if metadata:
            lines.append("## Metadata")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(metadata, indent=2, cls=ChunkAwareEncoder))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def rotate_logs(self, max_files_per_month: int = 100) -> None:
        """Rotate logs by archiving old files.

        Args:
            max_files_per_month: Maximum log files to keep per month

        """
        if not self.enabled:
            return

        try:
            # Get current month directory
            log_dir = self._get_log_directory()
            if not log_dir.exists():
                return

            # Get all log files in current month sorted by modification time
            log_files = sorted(log_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

            # Archive files beyond limit
            if len(log_files) > max_files_per_month:
                archive_dir = self.base_path / "archive"
                archive_dir.mkdir(parents=True, exist_ok=True)

                for log_file in log_files[max_files_per_month:]:
                    archive_path = archive_dir / log_file.name
                    log_file.rename(archive_path)

        except Exception as e:
            print(f"Warning: Failed to rotate logs: {e}", file=sys.stderr)
