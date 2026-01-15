#!/usr/bin/env python3
"""Profile memory indexing performance to identify bottlenecks.

Analyzes:
1. File parsing performance (tree-sitter operations)
2. Embedding generation (batch processing)
3. Database write operations (SQLite transactions)
4. Git blame extraction (file-level caching)

Usage:
    python profile_memory_indexing.py [--path PATH] [--num-files N]
"""

import argparse
import cProfile
import json
import pstats
import tempfile
import time
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from aurora_cli.config import Config
from aurora_cli.memory_manager import MemoryManager


@dataclass
class PhaseMetrics:
    """Metrics for a single indexing phase."""

    name: str
    duration_ms: float
    operations: int = 0
    throughput: float = 0.0  # ops/sec
    details: dict[str, Any] | None = None


@dataclass
class ProfilingReport:
    """Complete profiling report for memory indexing."""

    total_duration_ms: float
    files_indexed: int
    chunks_created: int
    phases: list[PhaseMetrics]
    hotspots: list[dict[str, Any]]
    bottlenecks: list[str]
    recommendations: list[str]


class IndexingProfiler:
    """Profiler for memory indexing operations."""

    def __init__(self, db_path: Path | None = None):
        """Initialize profiler with temporary database."""
        self.db_path = db_path or Path(tempfile.mkdtemp()) / "profile.db"
        self.config = Config(db_path=str(self.db_path))
        self.manager = MemoryManager(config=self.config)
        self.phase_times: dict[str, list[float]] = {}
        self.current_phase: str | None = None
        self.phase_start: float = 0
        self.file_count = 0
        self.chunk_count = 0

    def track_phase(self, progress):
        """Track phase transitions and timing."""
        phase = progress.phase

        # End previous phase
        if self.current_phase and self.current_phase != phase:
            duration = (time.perf_counter() - self.phase_start) * 1000
            if self.current_phase not in self.phase_times:
                self.phase_times[self.current_phase] = []
            self.phase_times[self.current_phase].append(duration)

        # Start new phase
        if self.current_phase != phase:
            self.current_phase = phase
            self.phase_start = time.perf_counter()

    def profile_indexing(self, path: Path, limit_files: int | None = None) -> ProfilingReport:
        """Profile indexing operation with detailed metrics.

        Args:
            path: Path to index
            limit_files: Limit number of files (for faster profiling)

        Returns:
            ProfilingReport with complete analysis
        """
        print(f"Profiling indexing of {path}")
        print(f"Database: {self.db_path}")
        print()

        # Discover files first
        print("Discovering files...")
        all_files = self.manager._discover_files(path)
        if limit_files:
            all_files = all_files[:limit_files]
        print(f"Found {len(all_files)} files to index")
        print()

        # Profile with cProfile
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()

        # Run indexing with phase tracking
        stats = self.manager.index_path(path, progress_callback=self.track_phase, batch_size=32)

        end_time = time.perf_counter()
        profiler.disable()

        total_duration_ms = (end_time - start_time) * 1000
        self.file_count = stats.files_indexed
        self.chunk_count = stats.chunks_created

        # Analyze profiling data
        phases = self._analyze_phases()
        hotspots = self._extract_hotspots(profiler)
        bottlenecks = self._identify_bottlenecks(phases)
        recommendations = self._generate_recommendations(phases, bottlenecks)

        return ProfilingReport(
            total_duration_ms=total_duration_ms,
            files_indexed=self.file_count,
            chunks_created=self.chunk_count,
            phases=phases,
            hotspots=hotspots,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

    def _analyze_phases(self) -> list[PhaseMetrics]:
        """Analyze timing for each indexing phase."""
        phases = []

        # Map phases to operations
        phase_info = {
            "discovering": ("File discovery", 1),
            "parsing": ("Parsing files", self.file_count),
            "git_blame": ("Git blame extraction", self.file_count),
            "embedding": ("Embedding generation", self.chunk_count),
            "storing": ("Database writes", self.chunk_count),
        }

        for phase_name, times in self.phase_times.items():
            if not times:
                continue

            total_ms = sum(times)
            label, ops = phase_info.get(phase_name, (phase_name, 1))

            throughput = ops / (total_ms / 1000) if total_ms > 0 else 0

            phases.append(
                PhaseMetrics(
                    name=label,
                    duration_ms=total_ms,
                    operations=ops,
                    throughput=throughput,
                    details={"measurements": len(times), "avg_ms": total_ms / len(times)},
                )
            )

        return sorted(phases, key=lambda p: p.duration_ms, reverse=True)

    def _extract_hotspots(self, profiler: cProfile.Profile) -> list[dict[str, Any]]:
        """Extract top function hotspots from profiler."""
        stream = StringIO()
        ps = pstats.Stats(profiler, stream=stream)
        ps.strip_dirs()
        ps.sort_stats("cumulative")

        # Get top 15 functions by cumulative time
        hotspots = []
        for func, (cc, nc, tt, ct, callers) in list(ps.stats.items())[:15]:
            # Skip built-in functions
            filename, line, func_name = func
            if "<" in filename:
                continue

            hotspots.append(
                {
                    "function": func_name,
                    "file": Path(filename).name,
                    "cumulative_time_ms": ct * 1000,
                    "total_time_ms": tt * 1000,
                    "calls": cc,
                    "time_per_call_ms": (ct / cc * 1000) if cc > 0 else 0,
                }
            )

        return hotspots

    def _identify_bottlenecks(self, phases: list[PhaseMetrics]) -> list[str]:
        """Identify performance bottlenecks from phase analysis."""
        bottlenecks = []

        if not phases:
            return bottlenecks

        total_time = sum(p.duration_ms for p in phases)

        for phase in phases:
            percentage = (phase.duration_ms / total_time * 100) if total_time > 0 else 0

            # Flag phases taking >30% of time
            if percentage > 30:
                bottlenecks.append(
                    f"{phase.name} dominates at {percentage:.1f}% of total time "
                    f"({phase.duration_ms:.0f}ms for {phase.operations} operations)"
                )

            # Flag low throughput
            if phase.throughput > 0 and phase.throughput < 10:
                bottlenecks.append(
                    f"{phase.name} has low throughput: {phase.throughput:.1f} ops/sec"
                )

        return bottlenecks

    def _generate_recommendations(
        self, phases: list[PhaseMetrics], bottlenecks: list[str]
    ) -> list[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Analyze phase performance
        phase_map = {p.name: p for p in phases}

        # Check parsing performance
        if "Parsing files" in phase_map:
            parsing = phase_map["Parsing files"]
            if parsing.throughput < 50:  # Less than 50 files/sec
                recommendations.append(
                    "Parsing is slow. Consider: (1) Parallel file parsing, "
                    "(2) Tree-sitter query optimization, (3) Caching parse results"
                )

        # Check embedding performance
        if "Embedding generation" in phase_map:
            embedding = phase_map["Embedding generation"]
            if embedding.throughput < 100:  # Less than 100 chunks/sec
                recommendations.append(
                    f"Embedding generation is slow ({embedding.throughput:.1f} chunks/sec). "
                    "Consider: (1) Larger batch sizes (current: 32), "
                    "(2) GPU acceleration with sentence-transformers, "
                    "(3) Faster embedding models (e.g., all-MiniLM-L6-v2)"
                )

        # Check database performance
        if "Database writes" in phase_map:
            db_writes = phase_map["Database writes"]
            if db_writes.throughput < 200:  # Less than 200 chunks/sec
                recommendations.append(
                    "Database writes are slow. Consider: (1) Batch transactions, "
                    "(2) Disable fsync for indexing, (3) Use WAL mode, "
                    "(4) Increase cache_size pragma"
                )

        # Check git blame performance
        if "Git blame extraction" in phase_map:
            git = phase_map["Git blame extraction"]
            percentage = git.duration_ms / sum(p.duration_ms for p in phases) * 100 if phases else 0
            if percentage > 20:
                recommendations.append(
                    f"Git blame takes {percentage:.1f}% of time. Consider: "
                    "(1) Disable git signals for initial indexing, "
                    "(2) Async git blame extraction, (3) Incremental updates only"
                )

        if not recommendations:
            recommendations.append("Performance is acceptable. No major bottlenecks detected.")

        return recommendations


def format_report(report: ProfilingReport) -> str:
    """Format profiling report as readable text."""
    lines = []

    lines.append("=" * 80)
    lines.append("MEMORY INDEXING PERFORMANCE PROFILE")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total Duration:    {report.total_duration_ms:,.0f} ms")
    lines.append(f"Files Indexed:     {report.files_indexed}")
    lines.append(f"Chunks Created:    {report.chunks_created}")
    throughput = report.files_indexed / (report.total_duration_ms / 1000)
    lines.append(f"Overall Throughput: {throughput:.1f} files/sec")
    lines.append("")

    # Phase breakdown
    lines.append("PHASE BREAKDOWN")
    lines.append("-" * 40)
    total = sum(p.duration_ms for p in report.phases)
    for phase in report.phases:
        pct = (phase.duration_ms / total * 100) if total > 0 else 0
        lines.append(f"{phase.name:25} {phase.duration_ms:8,.0f} ms ({pct:5.1f}%)")
        lines.append(f"  Operations: {phase.operations:,}")
        lines.append(f"  Throughput: {phase.throughput:.1f} ops/sec")
        if phase.details:
            avg = phase.details.get("avg_ms", 0)
            lines.append(f"  Avg per op: {avg:.2f} ms")
        lines.append("")

    # Top hotspots
    lines.append("TOP FUNCTION HOTSPOTS")
    lines.append("-" * 40)
    for i, hotspot in enumerate(report.hotspots[:10], 1):
        lines.append(f"{i:2}. {hotspot['function']:40} {hotspot['cumulative_time_ms']:8,.0f} ms")
        lines.append(f"    {hotspot['file']} ({hotspot['calls']:,} calls)")
        lines.append(f"    {hotspot['time_per_call_ms']:.2f} ms/call")
    lines.append("")

    # Bottlenecks
    if report.bottlenecks:
        lines.append("IDENTIFIED BOTTLENECKS")
        lines.append("-" * 40)
        for bottleneck in report.bottlenecks:
            lines.append(f"• {bottleneck}")
        lines.append("")

    # Recommendations
    lines.append("OPTIMIZATION RECOMMENDATIONS")
    lines.append("-" * 40)
    for i, rec in enumerate(report.recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    """Main profiling entry point."""
    parser = argparse.ArgumentParser(description="Profile Aurora memory indexing performance")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Path to index (default: current directory)",
    )
    parser.add_argument(
        "--num-files",
        type=int,
        default=None,
        help="Limit number of files to index (for faster profiling)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for report JSON (optional)",
    )

    args = parser.parse_args()

    # Run profiling
    profiler = IndexingProfiler()
    report = profiler.profile_indexing(args.path, limit_files=args.num_files)

    # Print report
    print(format_report(report))

    # Save JSON report if requested
    if args.output:
        report_dict = {
            "total_duration_ms": report.total_duration_ms,
            "files_indexed": report.files_indexed,
            "chunks_created": report.chunks_created,
            "phases": [asdict(p) for p in report.phases],
            "hotspots": report.hotspots,
            "bottlenecks": report.bottlenecks,
            "recommendations": report.recommendations,
        }
        args.output.write_text(json.dumps(report_dict, indent=2))
        print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
