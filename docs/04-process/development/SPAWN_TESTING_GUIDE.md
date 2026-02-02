# Manual Test Plan for `aur spawn`

## Prerequisites

```bash
cd /home/hamr/PycharmProjects/aurora

# Ensure you're in the aurora project directory
# Test tasks file: docs/examples/spawn_test_tasks.md (included in repo)
```

## Test 1: Basic Dry Run

**Purpose**: Verify task file parsing without execution

```bash
aur spawn docs/examples/spawn_test_tasks.md --dry-run
```

**Expected Output**:
```
Loaded 5 tasks from docs/examples/spawn_test_tasks.md
Dry-run mode: tasks validated but not executed.
  [ ] 1. Echo hello world (agent: self)
  [ ] 2. List current directory (agent: self)
  [ ] 3. Show current date (agent: self)
  [ ] 4. Display environment PATH (agent: self)
  [ ] 5. Count files in current directory (agent: self)
```

**✅ Pass Criteria**: All 5 tasks listed, no errors

---

## Test 2: Execution Preview

**Purpose**: Verify preview gate before execution

```bash
aur spawn docs/examples/spawn_test_tasks.md
```

**Expected Output**:
```
Loaded 5 tasks from docs/examples/spawn_test_tasks.md

Execution Preview table displayed with:
- 5 tasks shown
- Agent assignments (all @self)
- Status column showing [ ]

Summary panel:
"✓ 5 task(s) with available agents"

Options:
  [P]roceed   - Execute (try ad-hoc agents → fallback to LLM)
  [F]allback  - Execute (LLM directly for gaps, faster)
  [A]bort     - Cancel and restart

Choice [P]:
```

**Test Actions**:
1. Type `A` and press Enter
2. Should see: "Execution cancelled by user."

**✅ Pass Criteria**: Preview shown, abort works correctly

---

## Test 3: Skip Preview with --yes

**Purpose**: Verify --yes flag skips prompts

```bash
aur spawn docs/examples/spawn_test_tasks.md --yes --no-checkpoint
```

**Expected Output**:
```
Loaded 5 tasks from docs/examples/spawn_test_tasks.md
Executing tasks in parallel...
[Tasks execute without preview prompt]
```

**✅ Pass Criteria**: No preview prompt, execution starts immediately

---

## Test 4: List Checkpoints (Empty)

**Purpose**: Verify checkpoint listing when none exist

```bash
aur spawn --list-checkpoints
```

**Expected Output**:
```
No resumable checkpoints found.
```

**✅ Pass Criteria**: Message shown, no errors

---

## Test 5: Checkpoint Creation

**Purpose**: Verify checkpoint is created during execution

**Note**: This test will fail during actual execution because it tries to pipe to `claude` CLI tool.
The goal is to verify that checkpoint infrastructure works up to that point.

```bash
aur spawn docs/examples/spawn_test_tasks.md --yes
```

**Expected**:
- Checkpoint ID displayed: `Checkpoint: spawn-<timestamp>`
- Execution starts (may fail at LLM call)
- Check if checkpoint file was created:

```bash
ls -la .aurora/checkpoints/
```

**✅ Pass Criteria**:
- Checkpoint file `spawn-*.json` exists
- File contains JSON with task states

**Inspect checkpoint**:
```bash
cat .aurora/checkpoints/spawn-*.json | python3 -m json.tool
```

Should show JSON with:
- `execution_id`
- `tasks` array
- `last_checkpoint` timestamp

---

## Test 6: Policy Check - Destructive Operation

**Purpose**: Verify policy enforcement detects destructive keywords

Create a test file with destructive task:

```bash
cat > test_destructive.md << 'EOF'
# Destructive Tasks

- [ ] 1. Delete all log files
<!-- agent: self -->

- [ ] 2. Remove temporary directory
<!-- agent: self -->
EOF
```

**Run**:
```bash
aur spawn test_destructive.md
```

**Expected Output**:
```
Policy check triggers:
Warning: Deleting 1 files (limit: 5)
Task: Delete all log files
Proceed with this task? [y/N]:
```

**Test Actions**:
1. Type `n` and press Enter
2. Should see: "Execution cancelled by user."

**✅ Pass Criteria**: Policy warning shown, user can abort

---

## Test 7: Clean Checkpoints

**Purpose**: Verify checkpoint cleanup

```bash
# Clean checkpoints older than 1 day
aur spawn --clean-checkpoints 1
```

**Expected Output**:
```
Removed N old checkpoint(s)
# OR
No old checkpoints to clean
```

**✅ Pass Criteria**: Command completes without error

---

## Test 8: Resume (Will Fail - No Checkpoint)

**Purpose**: Verify resume error handling

```bash
aur spawn --resume nonexistent-id
```

**Expected Output**:
```
Error: Checkpoint not found: nonexistent-id
```

**✅ Pass Criteria**: Clear error message, no crash

---

## Test 9: Disable Checkpoint

**Purpose**: Verify --no-checkpoint flag

```bash
aur spawn docs/examples/spawn_test_tasks.md --yes --no-checkpoint
```

**Expected**:
- No "Checkpoint:" message in output
- No checkpoint file created in `.aurora/checkpoints/`

**✅ Pass Criteria**: No checkpoint created

---

## Test 10: aur goals with Review (Requires Memory)

**Purpose**: Verify decomposition review in goals command

**Prerequisites**:
```bash
# Initialize aurora and index memory
aur init
aur mem index .
```

**Run**:
```bash
aur goals "Add authentication to the API"
```

**Expected Output**:
```
Decomposition Summary displayed
Memory search results shown
Decomposition Summary table with subgoals
Agent matching results

[Table showing subgoals with agent assignments]

Options:
  [P]roceed   - Execute (try ad-hoc agents → fallback to LLM)
  [F]fallback  - Execute (LLM directly for gaps, faster)
  [A]bort     - Cancel and restart

Choice [P]:
```

**Test Actions**:
1. Review the decomposition
2. Type `P` to proceed OR `A` to abort

**✅ Pass Criteria**:
- Review UI shown with rich table
- Agent gaps highlighted if present
- Choice prompt works

---

## Test 11: Policy Configuration

**Purpose**: Verify custom policies can be loaded

**Create custom policies**:
```bash
cat > .aurora/policies.yaml << 'EOF'
budget:
  monthly_limit_usd: 50.0
  warn_at_percent: 80

agent_recovery:
  timeout_seconds: 60
  max_retries: 1
  fallback_to_llm: true

destructive:
  file_delete:
    action: prompt
    max_files: 2

safety:
  max_files_modified: 10
  max_lines_changed: 500
EOF
```

**Verify policies loaded** (check via Python):
```bash
python3 << 'EOF'
from aurora_cli.policies import PoliciesEngine

engine = PoliciesEngine()
print(f"Timeout: {engine.config.agent_recovery.timeout_seconds}s")
print(f"Max retries: {engine.config.agent_recovery.max_retries}")
print(f"Max files for delete: {engine.config.destructive.file_delete['max_files']}")
EOF
```

**Expected**:
```
Timeout: 60s
Max retries: 1
Max files for delete: 2
```

**✅ Pass Criteria**: Custom policy values loaded correctly

---

## Quick Test Summary

Run these commands in sequence for quick validation:

```bash
# Navigate to project
cd /home/hamr/PycharmProjects/aurora

# Test 1: Dry run
aur spawn docs/examples/spawn_test_tasks.md --dry-run

# Test 2: List empty checkpoints
aur spawn --list-checkpoints

# Test 3: Show preview and abort
aur spawn docs/examples/spawn_test_tasks.md
# (Type 'A' to abort)

# Test 4: Skip preview with --yes
aur spawn docs/examples/spawn_test_tasks.md --yes --no-checkpoint
# (Will fail at LLM call, that's expected)

# Test 5: Verify policies load
python3 -c "from aurora_cli.policies import PoliciesEngine; p = PoliciesEngine(); print('Policies OK:', p.config.agent_recovery.timeout_seconds)"

# Test 6: Clean up
rm -f test_destructive.md
aur spawn --clean-checkpoints 0  # Clean all
```

---

## Expected Failures

Some tests **will fail** at the LLM execution step because:
- The `claude` CLI tool needs to be installed and configured
- Tasks try to spawn subprocesses that pipe to LLM tools

**This is expected!** The goal is to verify:
- ✅ Task parsing works
- ✅ Policy checks work
- ✅ Preview gates work
- ✅ Checkpoint infrastructure works
- ✅ Error handling is graceful

The actual LLM execution would work in a real environment with `claude` CLI installed.

---

## Success Criteria Summary

| Test | Component | Pass Criteria |
|------|-----------|---------------|
| 1 | Task parsing | 5 tasks listed |
| 2 | Preview gate | Table shown, abort works |
| 3 | --yes flag | No preview, immediate start |
| 4 | List checkpoints | No errors when empty |
| 5 | Checkpoint creation | File created in .aurora/checkpoints/ |
| 6 | Policy enforcement | Warning shown for delete |
| 7 | Clean checkpoints | Command completes |
| 8 | Resume error | Clear error message |
| 9 | --no-checkpoint | No checkpoint file |
| 10 | aur goals review | Rich table, prompts work |
| 11 | Custom policies | Values loaded correctly |

---

## Timeout Architecture

Three systems control agent timeouts. Understanding these prevents premature termination:

### 1. SpawnPolicy.timeout_policy (Primary - spawner/execution.py)
The **authoritative** timeout source. Policy presets:
- `default`: 60s base, 180s global max
- `patient`: 120s base, 600s global max (for LLM tasks)
- `aggressive`: 30s base, 90s global max

### 2. ProactiveHealthConfig (Monitoring - spawner/observability.py)
Background health checks. Key settings:
- `no_output_threshold`: 120s (warn if no output)
- `terminate_on_failure`: **False** (disabled - lets policy timeouts control)

### 3. EarlyDetectionConfig (Stall detection - spawner/early_detection.py)
Detects truly stuck agents. Key settings:
- `stall_threshold`: 120s (match patient policy)
- `min_output_bytes`: 100 (must have output before stall check)
- `terminate_on_stall`: **False** (disabled - lets policy timeouts control)

### How They Work Together
1. SpawnPolicy timeout is the **only** thing that kills agents
2. ProactiveHealthConfig emits warnings but doesn't terminate
3. EarlyDetectionConfig only terminates after 2+ consecutive stall detections AND 120s of no output

### Reset at Phase Start
Both singletons must be reset at collect phase start (orchestrator.py:637-639):
```python
reset_health_monitor()
reset_early_detection_monitor()
```

---

## Troubleshooting

**Issue**: `ModuleNotFoundError`
**Fix**: Ensure packages installed: `./install.sh`

**Issue**: `FileNotFoundError: docs/examples/spawn_test_tasks.md`
**Fix**: Run from project root: `cd /home/hamr/PycharmProjects/aurora`

**Issue**: `.aurora directory not found`
**Fix**: Run `aur init` first

**Issue**: `Tool 'claude' not found`
**Fix**: This is expected if claude CLI not installed. Tests verify infrastructure, not actual execution.

**Issue**: `Early termination triggered` or agents dying too quickly
**Fix**: Check that all three timeout systems are aligned to 120s. Ensure `terminate_on_failure: False` in ProactiveHealthConfig and `stall_threshold: 120.0` in EarlyDetectionConfig.

---

## Next Steps After Testing

If all infrastructure tests pass:

1. **Install claude CLI** for full end-to-end testing
2. **Run unit tests**: `pytest tests/unit/cli/policies/ -v`
3. **Run integration tests**: `pytest tests/integration/ -v`
4. **Run e2e tests**: `pytest tests/e2e/ -v`
5. **Review logs** in `.aurora/logs/` for any issues
