# Headless Mode

Autonomous Claude execution loop - let Claude work on a goal until done.

## Quick Start

1. Copy the template to create your prompt:
   ```bash
   cp prompt.md.template prompt.md
   ```

2. Edit `prompt.md` with your goal

3. Run headless mode:
   ```bash
   aur headless -t claude --max=10
   ```

## How It Works

1. Claude reads your prompt (goal + instructions)
2. Claude works autonomously, rewriting scratchpad.md with current state
3. Loop checks for `STATUS: DONE` in scratchpad
4. Exits early when done, or after max iterations

## Commands

```bash
# Form 1: Default prompt (.aurora/headless/prompt.md)
aur headless --max=10

# Form 2: Custom prompt file
aur headless -p my-task.md --max=10

# Form 3: With test backpressure
aur headless --test-cmd "pytest tests/" --max=15

# Allow running on main branch (dangerous)
aur headless --allow-main
```

## Files

- `prompt.md.template` - Example prompt structure
- `prompt.md` - Your task definition (copy from template)
- `scratchpad.md` - Claude's state (rewritten each iteration)

## Key Concepts

### Scratchpad Rewrite (Not Append)
Claude rewrites scratchpad.md each iteration with current state only.
This keeps context bounded and prevents history accumulation.

### STATUS: DONE
When Claude completes the goal, it sets `STATUS: DONE` in scratchpad.
The loop detects this and exits early.

### Backpressure (Optional)
Use `--test-cmd` to run tests after each iteration.
If tests fail, Claude sees the failure next iteration.

## Safety Features

- **Git branch check**: Prevents running on main/master by default
- **Max iterations**: Prevents runaway execution
- **Scratchpad state**: Visible progress tracking

## Scratchpad Format

```markdown
# Scratchpad

## STATUS: IN_PROGRESS  (or DONE when complete)

## Completed
- Task 1
- Task 2

## Current Task
Working on X...

## Blockers
(none)

## Next Steps
- Step 1
- Step 2
```
