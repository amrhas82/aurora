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
    """Extract user message text."""
    content = event.get("message", {}).get("content", "")

    if isinstance(content, str):
        return content[:500]
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "")[:500]
    return ""


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

    # Summarize patterns
    pattern_counts = defaultdict(int)
    for c in all_candidates:
        pattern_counts[c["anchor_signal"]] += 1

    print(f"✓ Extracted {len(all_candidates)} antigen candidates")
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"  - {count} {pattern} patterns")

    if failed:
        print(f"\n⚠  Could not find session files for {len(failed)} sessions")
    print()

    # Save candidates
    output_dir = Path(".aurora/friction")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "antigen_candidates.json"
    with open(output_file, "w") as f:
        json.dump(all_candidates, f, indent=2)

    # Also save as YAML-like for easy editing
    review_file = output_dir / "antigen_review.md"
    with open(review_file, "w") as f:
        f.write("# Antigen Candidates for Review\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"BAD sessions analyzed: {len(bad_sessions)}\n")
        f.write(f"Candidates extracted: {len(all_candidates)}\n\n")
        f.write("---\n\n")

        for i, c in enumerate(all_candidates, 1):
            f.write(f'## Candidate {i}: {c["session_id"]}\n\n')
            f.write(f'**Anchor:** {c["anchor_signal"]} at {c["anchor_ts"]}\n')
            f.write(f'**Peak friction:** {c["peak_friction"]}\n\n')

            f.write("### Trigger Pattern\n\n")
            f.write("```yaml\n")
            f.write("files:\n")
            for file in c["files"][:5]:
                f.write(f'  - "{file}"\n')
            f.write("keywords:\n")
            for kw in c["keywords"][:10]:
                f.write(f'  - "{kw}"\n')
            f.write("tool_sequence:\n")
            for tool in c["tool_sequence"][:10]:
                f.write(f'  - "{tool}"\n')
            f.write("```\n\n")

            if c["errors"]:
                f.write("### Errors\n\n")
                f.write("```\n")
                for err in c["errors"][:3]:
                    f.write(f"{err}\n")
                f.write("```\n\n")

            if c["user_context"]:
                f.write("### User Context\n\n")
                for msg in c["user_context"][:2]:
                    f.write(f"> {msg[:200]}...\n\n" if len(msg) > 200 else f"> {msg}\n\n")

            f.write("### Inhibitory Instruction\n\n")
            f.write("```\n")
            f.write("# TODO: Write what the LLM should do differently\n")
            f.write("# Based on the pattern above, what guidance would prevent this failure?\n")
            f.write("```\n\n")
            f.write("---\n\n")

    print("Output: .aurora/friction/antigen_review.md\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
