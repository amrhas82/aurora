"""Headless execution templates for autonomous Claude loops."""

PROMPT_TEMPLATE = """# Goal
{goal}

# Instructions
1. FIRST: Create and checkout a /headless branch if not already on one
2. You have full access to the codebase
3. Each iteration, REWRITE .aurora/headless/scratchpad.md with current state
4. Keep scratchpad concise - current state only, not history
5. Run tests to verify your work
6. When completely done, set STATUS: DONE in scratchpad

# Scratchpad Location
.aurora/headless/scratchpad.md
"""

SCRATCHPAD_TEMPLATE = """# Scratchpad

## STATUS: NOT_STARTED

## Completed
(none yet)

## Current Task
(waiting for first iteration)

## Blockers
(none)

## Next Steps
(TBD)
"""
