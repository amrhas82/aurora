#!/usr/bin/env python3
"""
Antigen extractor - Extract failure patterns from BAD sessions.

Usage:
    python antigen_extract.py <sessions-directory>
    python antigen_extract.py ~/.claude/projects/-home-hamr-PycharmProjects-aurora/

Reads .aurora/friction/analysis.json to find BAD sessions,
then extracts context windows around failure anchors.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def find_session_file(sessions_dir, session_id):
    """Find the JSONL file for a session ID."""
    # session_id format: "project/MMDD-HHMM-shortid"
    if "/" in session_id:
        project_name = session_id.split("/")[0]
        short_id = session_id.split("/")[-1].split("-")[-1]
    else:
        project_name = None
        short_id = session_id

    sessions_path = Path(sessions_dir)

    # First try direct search in sessions_dir
    for f in sessions_path.glob("*.jsonl"):
        if short_id in f.name:
            return f

    # If not found and we have a project name, search in subdirectories
    if project_name:
        # Look for project directory (might have full path prefix like -home-hamr-...)
        for subdir in sessions_path.iterdir():
            if subdir.is_dir() and subdir.name.endswith(project_name):
                for f in subdir.glob("*.jsonl"):
                    if short_id in f.name:
                        return f

    # Fallback: recursive search in all subdirectories
    for f in sessions_path.glob("**/*.jsonl"):
        if short_id in f.name and "sessions-index" not in f.name:
            return f

    return None


def extract_context_window(session_file, anchor_ts, window_size=5):
    """Extract N turns before an anchor timestamp."""
    with open(session_file) as f:
        events = [json.loads(line) for line in f if line.strip()]

    # Find all user/assistant turns with timestamps
    turns = []
    for event in events:
        if event.get("type") in ("user", "assistant"):
            ts = event.get("timestamp", "")
            turns.append({"ts": ts, "type": event["type"], "event": event})

    # Find anchor position
    anchor_idx = None
    for i, turn in enumerate(turns):
        if turn["ts"] == anchor_ts:
            anchor_idx = i
            break

    # If exact match not found, find closest before
    if anchor_idx is None:
        for i, turn in enumerate(turns):
            if turn["ts"] and anchor_ts and turn["ts"] <= anchor_ts:
                anchor_idx = i

    if anchor_idx is None:
        return []

    # Extract window
    start_idx = max(0, anchor_idx - window_size)
    return turns[start_idx : anchor_idx + 1]


def extract_files_from_turn(event):
    """Extract file paths mentioned in a turn."""
    files = set()
    content = event.get("message", {}).get("content", "")

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                # Tool use
                if block.get("type") == "tool_use":
                    inp = block.get("input", {})
                    if "file_path" in inp:
                        files.add(inp["file_path"])
                    if "path" in inp:
                        files.add(inp["path"])
                    if "command" in inp:
                        # Extract paths from commands
                        cmd = inp["command"]
                        matches = re.findall(r"[\w/.-]+\.(?:py|js|ts|md|json|yaml|yml)", cmd)
                        files.update(matches)
                # Tool result
                elif block.get("type") == "tool_result":
                    text = str(block.get("content", ""))
                    matches = re.findall(r"[\w/.-]+\.(?:py|js|ts|md|json|yaml|yml)", text)
                    files.update(matches)
                # Text
                elif block.get("type") == "text":
                    text = block.get("text", "")
                    matches = re.findall(r"[\w/.-]+\.(?:py|js|ts|md|json|yaml|yml)", text)
                    files.update(matches)
    elif isinstance(content, str):
        matches = re.findall(r"[\w/.-]+\.(?:py|js|ts|md|json|yaml|yml)", content)
        files.update(matches)

    return files


def extract_tools_from_turn(event):
    """Extract tool names and results from a turn."""
    tools = []
    content = event.get("message", {}).get("content", "")

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tools.append({"tool": tool_name, "action": "call"})
                elif block.get("type") == "tool_result":
                    result = str(block.get("content", ""))
                    if "Exit code 0" in result:
                        tools.append({"tool": "result", "action": "success"})
                    elif re.search(r"Exit code [1-9]|Traceback|Error", result):
                        tools.append({"tool": "result", "action": "error"})

    return tools


def extract_errors_from_turn(event):
    """Extract error messages from a turn."""
    errors = []
    content = event.get("message", {}).get("content", "")

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                result = str(block.get("content", ""))
                if re.search(r"Exit code [1-9]|Traceback|Error|error:", result, re.I):
                    # Extract first line of error
                    lines = result.split("\n")
                    for line in lines[:5]:
                        if re.search(r"Error|error:|Traceback|Exit code [1-9]", line, re.I):
                            errors.append(line.strip()[:200])
                            break

    return errors


def extract_user_message(event):
    """Extract user message text, filtering out system-injected markup."""
    content = event.get("message", {}).get("content", "")

    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                break

    # Filter out system-injected markup (not real user messages)
    if not text:
        return ""
    trimmed = text.strip()
    if trimmed.startswith("<local-command-caveat>"):
        return ""
    if trimmed.startswith("<command-message>"):
        return ""
    if trimmed.startswith("<command-name>"):
        return ""
    if trimmed.startswith("<system-reminder>"):
        return ""
    if trimmed.startswith("<local-command-stdout>"):
        return ""

    return text[:500]


def analyze_bad_session(session_file, analysis, signals):
    """Analyze a BAD session and extract antigen candidates."""
    session_id = analysis["session_id"]

    # Find anchor points (intervention, false_success, interrupt_cascade)
    anchor_signals = [
        "user_intervention",
        "session_abandoned",
        "false_success",
        "interrupt_cascade",
    ]
    anchors = [
        s for s in signals if s.get("session") == session_id and s.get("signal") in anchor_signals
    ]

    if not anchors:
        # Use highest friction point
        session_signals = [s for s in signals if s.get("session") == session_id]
        if session_signals:
            anchors = [session_signals[-1]]  # Last signal as anchor

    candidates = []

    for anchor in anchors:
        anchor_ts = anchor.get("ts", "")
        anchor_signal = anchor.get("signal", "unknown")

        # Extract context window
        window = extract_context_window(session_file, anchor_ts, window_size=5)

        if not window:
            continue

        # Analyze window
        all_files = set()
        all_tools = []
        all_errors = []
        user_messages = []

        for turn in window:
            event = turn["event"]
            all_files.update(extract_files_from_turn(event))
            all_tools.extend(extract_tools_from_turn(event))
            all_errors.extend(extract_errors_from_turn(event))
            if turn["type"] == "user":
                msg = extract_user_message(event)
                if msg and not msg.startswith("[Request interrupted"):
                    user_messages.append(msg)

        # Build tool sequence string
        tool_seq = []
        for t in all_tools:
            if t["action"] == "call":
                tool_seq.append(t["tool"])
            elif t["action"] == "error":
                if tool_seq:
                    tool_seq[-1] += ":error"
            elif t["action"] == "success":
                if tool_seq:
                    tool_seq[-1] += ":ok"

        # Extract keywords from user messages
        keywords = set()
        for msg in user_messages:
            words = re.findall(r"\b[a-z]{4,}\b", msg.lower())
            keywords.update(words[:20])

        # Remove common words
        common = {
            "this",
            "that",
            "with",
            "from",
            "have",
            "what",
            "when",
            "where",
            "which",
            "there",
            "their",
            "would",
            "could",
            "should",
            "about",
            "been",
            "were",
            "they",
            "them",
            "then",
            "than",
            "these",
            "those",
            "some",
            "into",
            "only",
            "other",
            "also",
            "just",
            "more",
            "very",
            "here",
            "after",
            "before",
            "being",
            "doing",
            "make",
            "made",
            "like",
            "want",
            "need",
            "file",
            "code",
        }
        keywords -= common

        candidate = {
            "session_id": session_id,
            "anchor_signal": anchor_signal,
            "anchor_ts": anchor_ts,
            "peak_friction": analysis.get("friction_summary", {}).get("peak", 0),
            "turns_in_window": len(window),
            "files": sorted(list(all_files))[:10],
            "tool_sequence": tool_seq[:15],
            "errors": all_errors[:5],
            "keywords": sorted(list(keywords))[:15],
            "user_context": user_messages[:3],
            "inhibitory_instruction": "# TODO: Write prevention instruction based on pattern above",
        }

        candidates.append(candidate)

    return candidates


def cluster_candidates(all_candidates):
    """Group raw candidates by (anchor_signal, tool_pattern) and score clusters."""
    signal_weights = {
        "user_intervention": 10,
        "session_abandoned": 10,
        "false_success": 8,
        "no_resolution": 8,
        "interrupt_cascade": 5,
        "tool_loop": 6,
        "rapid_exit": 6,
    }

    cluster_map = {}

    for c in all_candidates:
        # Normalize tool sequence: strip :error/:ok suffixes for grouping
        tool_norm = ",".join(
            re.sub(r":error|:ok", "", t) for t in c["tool_sequence"]
        ) or "(none)"
        key = c["anchor_signal"] + "|" + tool_norm

        if key not in cluster_map:
            cluster_map[key] = {
                "anchor_signal": c["anchor_signal"],
                "tool_pattern": tool_norm,
                "count": 0,
                "sessions": set(),
                "contexts": [],
                "errors": [],
                "files": defaultdict(int),
                "keywords": defaultdict(int),
                "peaks": [],
            }

        cl = cluster_map[key]
        cl["count"] += 1
        cl["sessions"].add(c["session_id"])
        cl["peaks"].append(c["peak_friction"])

        # Collect unique user contexts (up to 5 per cluster, deduplicated)
        if c["user_context"] and len(cl["contexts"]) < 5:
            for ctx in c["user_context"][:1]:
                if len(ctx) > 10 and ctx not in cl["contexts"]:
                    cl["contexts"].append(ctx)

        # Collect unique errors (up to 5 per cluster)
        if c["errors"] and len(cl["errors"]) < 5:
            for err in c["errors"][:1]:
                if err not in cl["errors"]:
                    cl["errors"].append(err)

        # Tally files and keywords
        for f in c["files"]:
            cl["files"][f] += 1
        for kw in c["keywords"]:
            cl["keywords"][kw] += 1

    # Score and sort clusters
    clusters = []
    for cl in cluster_map.values():
        weight = signal_weights.get(cl["anchor_signal"], 1)
        peaks = sorted(cl["peaks"])
        top_files = sorted(cl["files"].items(), key=lambda x: -x[1])[:5]
        top_keywords = sorted(cl["keywords"].items(), key=lambda x: -x[1])[:10]

        clusters.append({
            "anchor_signal": cl["anchor_signal"],
            "tool_pattern": cl["tool_pattern"],
            "count": cl["count"],
            "score": cl["count"] * weight,
            "sessions": len(cl["sessions"]),
            "median_peak": peaks[len(peaks) // 2],
            "max_peak": peaks[-1],
            "contexts": cl["contexts"],
            "errors": cl["errors"],
            "top_files": [f for f, _ in top_files],
            "top_keywords": [k for k, _ in top_keywords],
        })

    clusters.sort(key=lambda x: -x["score"])
    return clusters


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    sessions_dir = Path(sys.argv[1])

    # Load friction analysis
    analysis_file = Path(".aurora/friction/friction_analysis.json")
    if not analysis_file.exists():
        print(
            "Error: Run friction_analyze.py first to generate .aurora/friction/friction_analysis.json"
        )
        return 1

    with open(analysis_file) as f:
        analyses = json.load(f)

    # Load raw signals
    raw_file = Path(".aurora/friction/friction_raw.jsonl")
    signals = []
    if raw_file.exists():
        with open(raw_file) as f:
            signals = [json.loads(line) for line in f if line.strip()]

    # Find BAD sessions
    bad_sessions = [a for a in analyses if a.get("quality") == "BAD"]

    if not bad_sessions:
        print("No BAD sessions found. Nothing to extract.")
        return 0

    print(f"Extracting antigens from {len(bad_sessions)} BAD sessions...\n")

    # Extract antigens (quiet mode)
    all_candidates = []
    failed = []

    for analysis in sorted(
        bad_sessions, key=lambda x: x.get("friction_summary", {}).get("peak", 0), reverse=True
    ):
        session_id = analysis["session_id"]
        session_file = find_session_file(sessions_dir, session_id)

        if not session_file:
            failed.append(session_id)
            continue

        candidates = analyze_bad_session(session_file, analysis, signals)
        all_candidates.extend(candidates)

    # Cluster candidates by (anchor_signal, tool_pattern)
    clusters = cluster_candidates(all_candidates)

    # Terminal output
    print(f">> {len(all_candidates)} raw candidates -> {len(clusters)} clusters")
    for cl in clusters[:5]:
        print(
            f"  {cl['count']:3d}x {cl['anchor_signal']} | {cl['tool_pattern']}"
            f" ({cl['sessions']} sessions, score: {cl['score']})"
        )

    if failed:
        print(f"\n!!  Could not find session files for {len(failed)} sessions")
    print()

    # Save outputs
    output_dir = Path(".aurora/friction")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Raw candidates (kept for debugging)
    with open(output_dir / "antigen_candidates.json", "w") as f:
        json.dump(all_candidates, f, indent=2)

    # Clustered output (primary machine-readable artifact)
    with open(output_dir / "antigen_clusters.json", "w") as f:
        json.dump(clusters, f, indent=2)

    # Clustered review markdown (top 25)
    max_clusters = 25
    review_clusters = clusters[:max_clusters]
    review_file = output_dir / "antigen_review.md"

    with open(review_file, "w") as f:
        f.write("# Friction Antigen Clusters\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(
            f"BAD sessions: {len(bad_sessions)} | "
            f"Raw candidates: {len(all_candidates)} | "
            f"Clusters: {len(clusters)}\n\n"
        )

        # Summary table
        f.write("## Cluster Summary\n\n")
        f.write("| # | Signal | Tool Pattern | Count | Sessions | Score | Median Peak |\n")
        f.write("|---|--------|-------------|-------|----------|-------|-------------|\n")
        for idx, cl in enumerate(review_clusters, 1):
            f.write(
                f"| {idx} | {cl['anchor_signal']} | {cl['tool_pattern']} "
                f"| {cl['count']} | {cl['sessions']} | {cl['score']} "
                f"| {cl['median_peak']} |\n"
            )
        f.write("\n---\n\n")

        # Detailed clusters
        for idx, cl in enumerate(review_clusters, 1):
            f.write(f"## Cluster {idx}: {cl['anchor_signal']} | {cl['tool_pattern']}\n\n")
            f.write(
                f"**Occurrences:** {cl['count']} across {cl['sessions']} sessions | "
                f"**Score:** {cl['score']} | "
                f"**Median peak:** {cl['median_peak']} | "
                f"**Max peak:** {cl['max_peak']}\n\n"
            )

            if cl["contexts"]:
                f.write("### User Context (what the user said)\n\n")
                for ctx in cl["contexts"][:3]:
                    truncated = ctx[:300] + "..." if len(ctx) > 300 else ctx
                    f.write(f"> {truncated}\n\n")

            if cl["errors"]:
                f.write("### Errors\n\n")
                f.write("```\n")
                for err in cl["errors"][:3]:
                    f.write(f"{err}\n")
                f.write("```\n\n")

            if cl["top_files"]:
                f.write("### Files involved\n\n")
                for fp in cl["top_files"]:
                    f.write(f"- `{fp}`\n")
                f.write("\n")

            if cl["top_keywords"]:
                f.write(f"**Keywords:** {', '.join(cl['top_keywords'])}\n\n")

            f.write("---\n\n")

    print("Output: .aurora/friction/antigen_review.md\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
