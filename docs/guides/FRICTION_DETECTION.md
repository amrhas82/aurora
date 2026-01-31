# Friction Detection Guide

**Status:** USEFUL (validated)
**Updated:** 2026-01-31

---

## Overview

Friction detection analyzes Claude Code session logs to:
1. Detect user frustration and failure patterns
2. Predict session abandonment (BAD sessions)
3. Track trends over time
4. Identify antigen candidates for future prevention

## Current Metrics

| Metric | Value |
|--------|-------|
| Verdict | USEFUL |
| Intervention predictability | 92% |
| Signal/noise ratio | 3.0 |
| BAD rate (interactive) | 60% |

## File Structure

**Scripts (repository):**
```
scripts/
├── friction.py             # Combined pipeline (recommended)
├── friction_analyze.py     # Session analyzer (standalone)
├── friction_config.json    # Signal weights and thresholds
└── antigen_extract.py      # Antigen extractor (standalone)
```

**Output (project-local):**
```
.aurora/friction/
├── friction_raw.jsonl        # All signals, all sessions
├── friction_analysis.json    # Per-session breakdown
├── friction_summary.json     # Aggregate stats, trends, verdict
├── antigen_candidates.json   # Extracted failure patterns
└── antigen_review.md         # Human-readable review format
```

## Quick Start

```bash
# CLI command (recommended)
aur friction run ~/.claude/projects/-home-hamr-PycharmProjects-aurora/

# Or standalone script
python scripts/friction.py ~/.claude/projects/-home-hamr-PycharmProjects-aurora/
```

This runs friction analysis and antigen extraction in sequence, then tells you where to find results.

### CLI Commands

| Command | Description |
|---------|-------------|
| `aur friction run <path>` | Full pipeline (analyze + extract) |
| `aur friction analyze <path>` | Analyze sessions only |
| `aur friction extract <path>` | Extract antigens (requires analyze first) |
| `aur friction config` | Show signal weights and thresholds |

---

## Signal Hierarchy

### Confidence Tiers

| Tier | Signals | Weight | Confidence | Use Case |
|------|---------|--------|------------|----------|
| **Gold** | `user_intervention`, `session_abandoned` | 10 | 95% | Definitive failure |
| **High** | `false_success`, `no_resolution`, `interrupt_cascade` | 7-8 | 85% | Clear failure pattern |
| **Medium** | `request_interrupted`, `tool_loop`, `rapid_exit` | 4-6 | 70% | Probable frustration |
| **Noisy** | `user_negation`, `long_silence`, `compaction`, `repeated_question` | 0.5-1 | 50% | Context only |

### Signal Reference

| Signal | Source | Weight | Description |
|--------|--------|--------|-------------|
| `user_intervention` | user | +10 | User invoked `/stash` (explicit give up) |
| `session_abandoned` | session | +10 | High friction at end, no resolution |
| `false_success` | llm | +8 | LLM claimed success but tool failed |
| `no_resolution` | session | +8 | Errors without subsequent success |
| `interrupt_cascade` | user | +7 | Multiple ESC/Ctrl+C within 60s |
| `tool_loop` | llm | +6 | Same tool called 3+ times identically |
| `rapid_exit` | session | +6 | <3 turns, ends with error |
| `user_curse` | user | +5 | Profanity detected |
| `request_interrupted` | user | +4 | User hit ESC/Ctrl+C |
| `exit_error` | tool | +1 | Command failed (non-zero exit) |
| `repeated_question` | user | +1 | Same question asked twice |
| `long_silence` | user | +0.5 | >10 min gap (noisy) |
| `user_negation` | user | +0.5 | "no", "didn't work" (noisy) |
| `compaction` | system | +0.5 | Context overflow (noisy) |
| `exit_success` | tool | 0 | Success (tracked for momentum) |

---

## Output Structure

```
.aurora/friction/
├── friction_raw.jsonl        # All signals, all sessions (tagged)
├── friction_analysis.json    # Per-session friction breakdown
├── friction_summary.json     # Aggregate stats, trends, verdict
├── antigen_candidates.json   # Extracted failure patterns
└── antigen_review.md         # Human-readable review format
```

### Sample Output

```
┌──────────────────────────────────────────────────────────┐
│ FRICTION ANALYSIS SUMMARY                                │
├──────────────────────────────────────────────────────────┤
│ Sessions analyzed:     145                               │
│ High friction (>=15):  13                                │
│ With interventions:    12                                │
└──────────────────────────────────────────────────────────┘

 Daily Trend
┌───────┬──────┬─────┬──────┬────────────┐
│ Date  │ Inter │ BAD │ Rate │ Trend      │
├───────┼──────┼─────┼──────┼────────────┤
│ 01-29 │ 6    │ 4   │ 67%  │ ██████░░░░ │
│ 01-30 │ 3    │ 2   │ 67%  │ ██████░░░░ │
│ 01-31 │ 10   │ 6   │ 60%  │ ██████░░░░ │
└───────┴──────┴─────┴──────┴────────────┘

 Session Extremes
  WORST: 0129-1503-a3ab0e5e  peak=140  turns=35  quality=BAD
  BEST:  0128-1629-67e10645  peak=0    turns=3   quality=OK

┌──────────────────────────────────────────────────────────┐
│ VERDICT                                                  │
├──────────────────────────────────────────────────────────┤
│ Status: ✓ USEFUL                                         │
│ Intervention predictability: 92% (threshold: 50%)        │
│ Signal/noise ratio: 3.6 (threshold: 1.5)                 │
└──────────────────────────────────────────────────────────┘
```

---

## Session Quality

| Quality | Meaning | Criteria |
|---------|---------|----------|
| **BAD** | User gave up | Has `user_intervention` or `session_abandoned` |
| **FRICTION** | Frustration detected | Has `user_curse` or `false_success` |
| **ROUGH** | High friction, completed | Peak >= 15, no intervention |
| **OK** | No significant friction | Low friction, completed |
| **ONE-SHOT** | Single turn | Not interactive (filtered) |

---

## Configuration

Edit `scripts/friction_config.json`:

```json
{
  "weights": {
    "user_intervention": 10,
    "session_abandoned": 10,
    "false_success": 8,
    "no_resolution": 8,
    "interrupt_cascade": 7,
    "tool_loop": 6,
    "rapid_exit": 6,
    "user_curse": 5,
    "request_interrupted": 4,
    "exit_error": 1,
    "repeated_question": 1,
    "long_silence": 0.5,
    "user_negation": 0.5,
    "compaction": 0.5,
    "exit_success": 0
  },
  "thresholds": {
    "friction_peak": 15,
    "intervention_predictability": 0.50,
    "signal_noise_ratio": 1.5
  }
}
```

### Weight Guidelines

- **10**: Definitive failure (user gave up)
- **6-8**: Clear failure pattern
- **4-5**: Probable frustration
- **1**: Low confidence, need accumulation
- **0.5**: Noisy, context only
- **0**: Track but don't count

---

## Verdict Meanings

| Status | Meaning | Action |
|--------|---------|--------|
| **USEFUL** | Friction tracking is predictive | Extract antigens, track trends |
| **INCONCLUSIVE** | Not enough correlation | Collect more data, tune weights |
| **BLOAT** | More noise than signal | Reduce noisy signal weights |

---

## Working with Results

```bash
# View verdict
jq '.verdict' .aurora/friction/friction_summary.json

# View daily trend
jq '.daily_stats' .aurora/friction/friction_summary.json

# Best/worst sessions
jq '{best: .best_session, worst: .worst_session}' .aurora/friction/friction_summary.json

# Find BAD sessions
jq '.[] | select(.quality == "BAD") | .session_id' .aurora/friction/friction_analysis.json

# Signals for specific session
grep "0131-1635" .aurora/friction/friction_raw.jsonl

# Signal counts
jq -r '.signal' .aurora/friction/friction_raw.jsonl | sort | uniq -c | sort -rn

# Review antigens
cat .aurora/friction/antigen_review.md
```

---

## Use Cases

### Current Workflow

1. **Analyze** - Run pipeline after bad sessions to understand what went wrong
2. **Extract** - Get failure patterns from BAD sessions
3. **Generate** - Create CLAUDE.md rules from patterns (manually or via LLM)
4. **Inject** - Add rules to CLAUDE.md for future sessions
5. **Validate** - Track BAD rate to see if rules help

### What This Enables

- Track BAD rate trends over time
- Identify worst sessions for investigation
- Learn from failures systematically
- Build project-specific guardrails

---

## Antigen System

An **antigen** is a learned failure pattern with a prevention instruction. Like an immune system memory, it recognizes patterns that led to failure and provides guidance to prevent recurrence.

### Complete Workflow

```bash
# Step 1: Run the pipeline
python scripts/friction.py ~/.claude/projects/-home-hamr-PycharmProjects-aurora/

# Step 2: Review what went wrong
cat .aurora/friction/antigen_review.md

# Step 3: Generate CLAUDE.md rules (pick one method)

# Method A: Ask Claude directly
cat .aurora/friction/antigen_review.md | claude "Based on these failure patterns, write specific CLAUDE.md rules to prevent them. Keep rules short and actionable."

# Method B: Manual review
# Read antigen_review.md, identify top 3 patterns, write rules yourself

# Method C: Interactive
claude "Read .aurora/friction/antigen_review.md and suggest 3-5 CLAUDE.md rules"

# Step 4: Add rules to CLAUDE.md (top of file for visibility)
# Edit CLAUDE.md, add rules under a "## Learned Rules" section
```

### Example: From Pattern to Rule

**review.md shows:**
```
Candidate 1: aurora/0129-1503-a3ab0e5e
Anchor: false_success
Tool sequence: Edit → Bash:error
Errors: Exit code 1
```

**Generated rule:**
```markdown
## Learned Rules

### After Bash commands, verify before claiming success
- Check exit code is 0
- If running tests, confirm "PASSED" in output
- If exit code != 0, report the error - don't minimize
```

### Antigen Structure

```yaml
id: "verify-before-success-claim"
trigger:
  tool_sequence: ["Edit", "Bash"]
  anchor_signals: ["false_success"]
failure_pattern:
  description: "LLM claims success after Edit→Bash without checking exit code"
  sessions: ["0131-1635", "0131-1824", "0131-0942"]
  count: 20
inhibitory_instruction: |
  After Edit → Bash sequence:
  1. WAIT for command to complete
  2. Check exit code explicitly (must be 0)
  3. If running tests, verify "PASSED" in output
  4. If exit code != 0, DO NOT claim success
  5. Read the actual error before proceeding
```

### Discovered Patterns (from 44 candidates)

| Pattern | Count | Priority | Trigger |
|---------|-------|----------|---------|
| **Edit → Bash:error → claim success** | 20+ | HIGH | `false_success` after Edit→Bash |
| **Bash → Bash:error → retry blindly** | 12 | HIGH | 2+ consecutive Bash errors |
| **"test it" → fail → claim done** | 4 | MEDIUM | User says "test"/"verify" |
| **Implement plan → cascade failure** | 3 | MEDIUM | "Implement the following plan" |
| **TaskCreate loop** | 1 | LOW | Multiple TaskCreate in sequence |

### Recommended Antigens

#### 1. verify-before-success-claim (HIGH PRIORITY)
```yaml
trigger:
  tool_sequence: ["Edit", "Bash"]
  or: ["Bash", "Bash"]
instruction: |
  After any Bash command:
  - Check exit code (must be 0 for success)
  - If running tests, verify "PASSED" or "ok" in output
  - Never claim success based on "no errors printed"
  - If exit != 0, report the error, don't minimize
```

#### 2. stop-on-repeated-failure (HIGH PRIORITY)
```yaml
trigger:
  pattern: "2+ consecutive Bash:error"
instruction: |
  After 2 consecutive command failures:
  - STOP and analyze the error pattern
  - Don't retry same command without changes
  - Read the full error output
  - If timeout (124) or killed (137), simplify the task
  - Ask user for guidance if stuck
```

#### 3. test-means-verify (MEDIUM PRIORITY)
```yaml
trigger:
  user_message_contains: ["test it", "verify", "check", "did you test"]
instruction: |
  When user asks to test/verify:
  - Run the actual test command
  - Wait for full completion
  - Check exit code AND output content
  - Only say "tests pass" if PASSED + exit 0
  - Report specific failures, don't minimize
```

### Current Injection Mode

**PRE injection only** - Add rules to CLAUDE.md before sessions.

Other modes (DURING injection, RETRIEVAL matching) are deferred until the basic workflow proves valuable.

---

## CLAUDE.md Effectiveness

**What works:**
- Short, specific rules at the top of the file
- Rules that reference concrete patterns (tool sequences, error types)
- Rules reinforced by conversation flow

**What gets ignored:**
- Vague guidance ("be careful", "think before acting")
- Rules buried in long documents
- Philosophical instructions that slow down tasks
- Subagent contexts may not inherit CLAUDE.md

**Recommendation:** Keep learned rules to 3-5 items, specific and actionable. Review and prune monthly.

---

## Roadmap

- [x] Signal detection (14 signals, 4 confidence tiers)
- [x] Session quality assessment (BAD/FRICTION/ROUGH/OK)
- [x] Daily trend tracking with visual bar
- [x] Best/worst session identification
- [x] Per-project breakdown
- [x] Antigen extraction script (`antigen_extract.py`)
- [x] Combined pipeline script (`friction.py`)
- [x] Pattern-to-rule workflow documented
- [ ] Validate rule effectiveness over time

---

## Exit Codes

- `0` - Verdict is USEFUL
- `1` - Verdict is INCONCLUSIVE or BLOAT

---

## Related

- [CLAUDE.md](../../CLAUDE.md) - Project instructions (potential antigen injection point)
- [docs/experiments/FRICTION_ANALYSIS.md](../experiments/FRICTION_ANALYSIS.md) - Original experiment (archived)
