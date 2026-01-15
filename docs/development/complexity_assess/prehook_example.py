#!/usr/bin/env python3
"""Example prehook script for Claude Code model routing.

This script can be used as a pre-prompt hook to route prompts
to appropriate models based on complexity assessment.

Usage in Claude Code hooks config:
{
    "hooks": {
        "pre-prompt": {
            "command": "python3 /path/to/prehook_example.py",
            "timeout": 1000
        }
    }
}

The script reads the prompt from stdin and outputs a JSON object
with routing recommendations.
"""
import json
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from complexity_assessor import assess_prompt  # noqa: E402

# Model routing configuration
MODEL_ROUTING = {
    "simple": {
        "model": "haiku",
        "reason": "Simple lookup/display task - fast model sufficient",
        "max_tokens": 1024,
    },
    "medium": {
        "model": "sonnet",
        "reason": "Analysis/moderate edit - balanced model",
        "max_tokens": 4096,
    },
    "complex": {
        "model": "opus",
        "reason": "Major implementation - most capable model",
        "max_tokens": 8192,
    },
}


def route_prompt(prompt: str) -> dict:
    """Assess prompt complexity and return routing recommendation.

    Args:
        prompt: The user prompt to assess

    Returns:
        dict with level, score, confidence, model, and reason
    """
    result = assess_prompt(prompt)
    routing = MODEL_ROUTING[result.level]

    return {
        "level": result.level,
        "score": result.score,
        "confidence": result.confidence,
        "model": routing["model"],
        "reason": routing["reason"],
        "max_tokens": routing["max_tokens"],
        "signals": result.signals[:5],  # Top 5 signals for debugging
    }


def main():
    """Main entry point for prehook."""
    # Read prompt from stdin
    if not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    elif len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        print(
            json.dumps(
                {
                    "error": "No prompt provided",
                    "usage": 'echo "your prompt" | python3 prehook_example.py',
                }
            )
        )
        sys.exit(1)

    if not prompt:
        print(json.dumps({"level": "simple", "model": "haiku", "reason": "Empty prompt"}))
        return

    result = route_prompt(prompt)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
