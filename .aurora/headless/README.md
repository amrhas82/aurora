# Headless Mode

Run single-iteration autonomous reasoning experiments.

## Quick Start

1. Copy the template to create your prompt:
   ```bash
   cp prompt.md.template prompt.md
   ```

2. Edit `prompt.md` with your goal and criteria

3. Run headless mode:
   ```bash
   aur headless prompt.md
   ```

## How It Works

1. Aurora reads your prompt (goal, success criteria, constraints)
2. Runs SOAR pipeline for one iteration
3. Evaluates if goal is achieved
4. Saves progress to scratchpad.md

## Commands

```bash
# Default: 30,000 token budget, max 5 iterations
aur headless prompt.md

# Custom budget (tokens)
aur headless prompt.md --budget 50000

# More iterations
aur headless prompt.md --max-iter 10

# Show scratchpad after execution
aur headless prompt.md --show-scratchpad

# Dry run (validate without executing)
aur headless prompt.md --dry-run
```

## Files

- `prompt.md.template` - Example prompt structure (this template)
- `prompt.md` - Your task definition (copy from template)
- `scratchpad.md` - Auto-generated execution log

## Safety Features

- **Git branch check**: Prevents running on main/master by default
- **Token budget**: Stops when budget exceeded
- **Max iterations**: Prevents runaway execution
- **Scratchpad log**: Full audit trail

## Prompt Format

Required sections:
- **Goal**: What you want to achieve
- **Success Criteria**: Checklist of completion criteria

Optional sections:
- **Constraints**: Limitations or requirements
- **Context**: Additional background information
