---
description: Save session context ["optional-name"]
---
The user wants to save session context. Use the aurora instructions to create a checkpoint.
<UserRequest>
  $ARGUMENTS
</UserRequest>
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.

**Usage**
Save current session context to preserve conversation state across compaction or handoffs.

**What it does**
1. Captures current conversation context and key decisions
2. Records active work in progress
3. Stores important findings and insights
4. Creates checkpoint file in `.aurora/checkpoints/`
5. Enables context restoration after compaction

**When to use**
- Before long-running tasks that may trigger compaction
- When handing off work to another agent or session
- After completing major investigation or analysis
- Before taking a break from complex multi-step work

**Commands**
```bash
# Create checkpoint with auto-generated name
aur checkpoint save

# Create checkpoint with custom name
aur checkpoint save "feature-auth-investigation"

# List available checkpoints
aur checkpoint list

# Restore from checkpoint
aur checkpoint restore <checkpoint-name>
```

**Reference**
- Checkpoints stored in `.aurora/checkpoints/`
- Automatically includes: timestamp, active plan, recent decisions
- Maximum context retention with minimal token usage
<!-- AURORA:END -->
