#!/usr/bin/env python3
"""Pre-Edit hook that runs LSP check before file edits.

This hook is automatically installed by `aur init --tools=claude`.
It provides usage impact analysis before Claude edits code files.

Receives Edit tool input on stdin, runs LSP usage analysis via the
aurora MCP lsp tool, and returns context for Claude to see before
the edit proceeds.
"""

import json
import os
import sys
import warnings
from pathlib import Path

# Suppress warnings that would pollute output
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"


def find_line_number(file_path: str, old_string: str) -> int | None:
    """Find the 1-indexed line number where old_string starts."""
    try:
        with open(file_path) as f:
            content = f.read()

        if old_string not in content:
            return None

        # Find position and count newlines before it
        pos = content.find(old_string)
        line_num = content[:pos].count("\n") + 1  # 1-indexed for MCP tool
        return line_num
    except Exception:
        return None


def run_lsp_check(file_path: str, line: int, workspace: Path) -> dict | None:
    """Run LSP check using the MCP tool function directly."""
    try:
        # Add aurora packages to path
        mcp_src = workspace / "src"
        lsp_src = workspace / "packages/lsp/src"

        if mcp_src.exists():
            sys.path.insert(0, str(mcp_src))
        if lsp_src.exists():
            sys.path.insert(0, str(lsp_src))

        # Change to workspace for the tool (it uses cwd)
        original_cwd = os.getcwd()
        os.chdir(workspace)

        try:
            from aurora_mcp.lsp_tool import lsp

            # Call the same function the MCP tool uses
            # This includes intelligent column detection and hybrid fallback
            result = lsp(action="check", path=file_path, line=line)
            return result
        finally:
            os.chdir(original_cwd)

    except Exception as e:
        return {"error": str(e)}


def main():
    # Redirect stderr to suppress warnings
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")

    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Allow edit if can't parse input

    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    old_string = tool_input.get("old_string", "")
    cwd = input_data.get("cwd", "")

    # Skip non-code files
    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
    if not any(file_path.endswith(ext) for ext in code_extensions):
        sys.exit(0)  # Allow edit for non-code files

    # Find workspace (look for .aurora or .git directory)
    workspace = Path(cwd) if cwd else Path.cwd()
    for parent in [workspace] + list(workspace.parents):
        if (parent / ".aurora").exists() or (parent / ".git").exists():
            workspace = parent
            break

    # Find line number from old_string (1-indexed for MCP tool)
    line = find_line_number(file_path, old_string)
    if line is None:
        sys.exit(0)  # Allow edit if can't find line

    # Run LSP check
    result = run_lsp_check(file_path, line, workspace)

    # Restore stderr for output
    sys.stderr = old_stderr

    if result and not result.get("error"):
        used_by = result.get("used_by", 0)
        text_matches = result.get("text_matches", 0)
        text_files = result.get("text_files", 0)
        top_refs = result.get("top_refs", [])
        risk = result.get("risk", "low")
        symbol = result.get("symbol") or "unknown"
        note = result.get("note", "")

        # Build context message
        context = f"LSP CHECK: '{symbol}' @ line {line}"

        if used_by > 0:
            context += f" | {used_by} LSP refs"

        if text_matches > 0:
            context += f" | {text_matches} text matches in {text_files} files"

        context += f" | Risk: {risk.upper()}"

        # Show concrete references so the agent can reason about impact
        if top_refs:
            context += "\nTop refs: " + ", ".join(top_refs)

        if note:
            context += f"\n{note}"

        if risk == "high":
            context += "\n!! HIGH IMPACT: Review all usages before editing!"

        # Return context to Claude
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": context,
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Allow edit (no significant findings or error)
    sys.exit(0)


if __name__ == "__main__":
    main()
