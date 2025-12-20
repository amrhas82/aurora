# AURORA MVP - 10 Features Discussion

**Date:** December 20, 2025
**Context:** Features discussed for adding to AURORA MVP based on ArchGW, headless agent pattern, and coding agent guide

---

## Features Discussed (11 total)

### ✅ APPROVED for MVP (6 features)

#### 1. LLM Preference Routing

**What:** Auto-select model ONCE per query based on complexity, use for entire SOAR chain

**Decision Point:** After complexity assessment, BEFORE SOAR orchestration

**Flow:**
1. Assess complexity → SIMPLE/MEDIUM/COMPLEX/CRITICAL
2. Map complexity → model tier (fast/reasoning/best)
3. Select actual model from tier:
   - SIMPLE → Haiku (~$0.001 per query)
   - MEDIUM → Sonnet (~$0.05 per query)
   - COMPLEX/CRITICAL → Opus (~$0.50 per query)
4. Pass selected model to SOAR orchestrator
5. SOAR uses THAT model for entire chain:
   - Decomposition prompt
   - Verification prompts
   - Synthesis prompt
   - (Agent execution uses solving_llm separately)

**Separation of Concerns:**
- **Preference Routing:** Chooses MODEL (one decision per query)
- **SOAR Orchestrator:** Chooses AGENTS, STEPS, ORDER (doesn't know about models)

**Why Simple Approach (not per-prompt routing):**
- Clean separation: routing decides model, SOAR decides agents/steps
- One decision point (predictable)
- Simple to implement
- Easy to debug
- Predictable costs

**Why needed:** 40% cost savings through intelligent model selection vs always-Opus
**Complexity:** Low-Medium (model mapping + config)
**Priority:** HIGH - Cost optimization critical for personal users

**Where to Document:**
- **Section 3.4** (NEW): "LLM Preference Routing" - architecture explanation
- **Appendix C**: Extend `llm.preference_routing` config section

**Config Addition:**
```json
"llm": {
  "preference_routing": {
    "enabled": true,
    "tiers": {
      "fast": {
        "model": "claude-3-haiku-20240307",
        "use_for": ["simple"]
      },
      "reasoning": {
        "model": "claude-3-5-sonnet-20241022",
        "use_for": ["medium"]
      },
      "best": {
        "model": "claude-opus-4-5-20251101",
        "use_for": ["complex", "critical"]
      }
    },
    "apply_to": "reasoning_llm"
  }
}
```

**Status:** MVP - Section 3.4 + Appendix C addition

---

#### 2. Timing Logs

**What:** Log execution time per phase + percentage of total query time

**Current State in PRD:**
- ✅ Already has per-phase `duration_ms` (Section 9.4, lines 1922-1983)
- ✅ Already has `aurora_agent_latency_ms` metric
- ✅ Already has `total_duration_ms` in execution summary

**Enhancement Needed:**
- ✅ Add `percentage` field to each phase (% of total query time)

**Example Output:**
```json
{
  "execution_summary": {
    "total_duration_ms": 12785,
    "phases": [
      {"phase": "ASSESS", "duration_ms": 450, "percentage": 3.5},
      {"phase": "RETRIEVE", "duration_ms": 320, "percentage": 2.5},
      {"phase": "DECOMPOSE", "duration_ms": 2100, "percentage": 16.4},
      {"phase": "VERIFY (Decomposition)", "duration_ms": 1800, "percentage": 14.1},
      {"phase": "ROUTE", "duration_ms": 120, "percentage": 0.9},
      {"phase": "COLLECT (Agents)", "duration_ms": 12500, "percentage": 97.8},
      {"phase": "SYNTHESIZE", "duration_ms": 1500, "percentage": 11.7},
      {"phase": "VERIFY (Synthesis)", "duration_ms": 1200, "percentage": 9.4}
    ]
  }
}
```

**Benefit:**
- Immediately identify bottlenecks (e.g., "Agents took 97.8% → optimize agents first")
- Prioritize optimization efforts
- Track performance regressions

**Why per-phase is sufficient:**
- Captures where time is spent (which phase)
- Good starting point (can add more granularity later if needed)
- Simple to implement (timestamp at phase start/end)

**Complexity:** Low (calculate percentage: `duration_ms / total * 100`)
**Priority:** HIGH - Essential for optimization

**Where to Document:**
- **Section 9.4.1** (NEW): "Timing Breakdown with Percentages" - add subsection
- **Appendix C**: Extend `logging.timing` config

**Config Addition:**
```json
"logging": {
  "timing": {
    "enabled": true,
    "include_percentages": true,
    "breakdown_level": "phase"
  }
}
```

**Status:** MVP - Enhance Section 9.4 + Appendix C addition

---

#### 3. Guardrails

**What:** Input validation layer BEFORE complexity assessment (Phase 0)

**Current State in PRD:**
- ❌ NOT documented - flow goes directly USER QUERY → COMPLEXITY ASSESSMENT
- ❌ No input validation layer exists

**What Guardrails Do:**
1. **PII Detection** - Scan for personally identifiable information
   - Emails, SSNs, credit cards, phone numbers
   - Action: Redact or reject query
   - Log: What was redacted (for audit)

2. **Length Limits** - Prevent excessive input
   - Max query length: 10,000 characters (configurable)
   - Action: Reject with helpful error message
   - Reason: Prevent token explosion, DoS

3. **Format Validation** - Ensure well-formed input
   - UTF-8 encoding check
   - Malformed input rejection (invalid characters)
   - Action: Return error with specific issue

4. **Cost Budget Pre-Check** (integration with Feature #4)
   - Check remaining budget before processing
   - Estimate query cost based on length + complexity hint
   - Action: Warn (soft limit) or block (hard limit)

**Updated Flow:**
```
USER QUERY
    ↓
0. GUARDRAILS (NEW PHASE)
   ├─ PII detection → redact/reject
   ├─ Length check → reject if > limit
   ├─ Format validation → reject if malformed
   └─ Budget pre-check → warn/block
    ↓
1. COMPLEXITY ASSESSMENT
    ↓
   ...existing flow
```

**Who writes the rules:**
- We provide basic patterns (email regex, SSN regex, etc.)
- Users can extend via config (custom PII patterns, custom length limits)
- Users can disable specific checks if needed

**Why needed:**
- Safety for personal users (prevent accidental PII leaks)
- Cost protection (prevent accidental expensive queries)
- System stability (prevent malformed input crashes)

**Complexity:** Medium (pattern matching + validation logic)
**Priority:** HIGH - Safety critical for production use

**Where to Document:**
- **Section 3.1** (NEW): "Input Processing & Guardrails" - add before complexity assessment
- **Section 4.0** (NEW): "Guardrails Layer" - detailed component spec
- **Update Section 3 flow diagram**: Add Phase 0 before Phase 1
- **Appendix C**: Add `guardrails` config section

**Config Addition:**
```json
"guardrails": {
  "enabled": true,
  "pii_detection": {
    "enabled": true,
    "action": "redact",  // Options: "redact", "reject", "warn"
    "patterns": {
      "email": "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
      "ssn": "\\b\\d{3}-\\d{2}-\\d{4}\\b",
      "credit_card": "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b",
      "phone": "\\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b"
    },
    "custom_patterns": []
  },
  "length_limits": {
    "enabled": true,
    "max_query_length": 10000,
    "action": "reject"
  },
  "format_validation": {
    "enabled": true,
    "require_utf8": true,
    "reject_control_chars": true
  },
  "cost_budget_check": {
    "enabled": true,
    "check_before_processing": true
  }
}
```

**Status:** MVP - Add Section 3.1, 4.0, update flow diagram, Appendix C

---

#### 4. Cost Budgets

**What:** Enforce spending limits to prevent runaway API costs

**Current State in PRD:**
- ✅ Cost tracking exists: `total_cost_usd` logged per query (line 517)
- ❌ NO budget enforcement (no limits, no warnings)

**What to Add:**

1. **Budget Configuration** (per-user or per-project)
   - Soft limit: Warn when 80% consumed
   - Hard limit: Block query if exceeded
   - Time period: daily, weekly, monthly
   - Reset behavior: Auto-reset or manual

2. **Pre-Query Cost Estimation**
   - Estimate cost BEFORE processing (in Guardrails Phase 0)
   - Based on: query length + complexity hint
   - Formula: `estimated_cost = base_cost * complexity_multiplier * (tokens / 1000)`
   - Check: `current_usage + estimated_cost > limit?`

3. **Budget Tracking**
   - Track cumulative costs per period
   - Store in: `~/.aurora/budget_tracker.json`
   - Fields: `period_start`, `period_end`, `consumed_usd`, `limit_usd`, `remaining_usd`

4. **User Actions**
   - Soft limit reached (80%): Display warning, allow query
   - Hard limit reached (100%): Block query, show error with budget info
   - User can override with `--force` flag (with confirmation)

**Integration with Guardrails:**
- Guardrails Phase 0 calls budget check
- If over limit → reject before any LLM calls
- If near limit → warn user, show remaining budget

**Example Flow:**
```
USER QUERY
    ↓
GUARDRAILS:
  1. PII check ✓
  2. Length check ✓
  3. Budget check:
     - Current usage: $18.50 / $20.00 (92%)
     - Estimated query cost: $0.50
     - Total would be: $19.00 (95%)
     → Action: WARN "Near budget limit (95%), proceed? [y/N]"
    ↓
COMPLEXITY ASSESSMENT
   ...
```

**Why needed:**
- Personal users can't afford $500 surprise bills
- Prevent accidental infinite loops
- Force conscious cost management
- Critical for production use

**Complexity:** Medium (cost estimation + persistent tracking)
**Priority:** HIGH - Critical safety feature for personal users

**Where to Document:**
- **Section 3.1** (Guardrails): Add budget check step
- **Section 9.4** (Logging): Add budget tracking subsection
- **Appendix C**: Add `cost_budgets` config section

**Config Addition:**
```json
"cost_budgets": {
  "enabled": true,
  "soft_limit_usd": 100.00,
  "hard_limit_usd": 500.00,
  "period": "monthly",  // Options: "daily", "weekly", "monthly"
  "auto_reset": true,
  "warn_at_percent": 80,
  "block_at_percent": 100,
  "allow_force_override": false,
  "tracking_file": "~/.aurora/budget_tracker.json"
}
```

**Budget Tracker File Format:**
```json
{
  "period_start": "2025-12-01T00:00:00Z",
  "period_end": "2025-12-31T23:59:59Z",
  "limit_usd": 100.00,
  "consumed_usd": 18.50,
  "remaining_usd": 81.50,
  "query_count": 142,
  "last_updated": "2025-12-20T14:30:00Z"
}
```

**Status:** MVP - Add to Section 3.1, 9.4, Appendix C

---

#### 5. Self-Correction Details

**What:** Clarification of TWO SEPARATE LOOPS in self-correction system

**Current State in PRD:**
- ✅ Complete documentation in Appendix D "Feedback Handling Matrix" (lines 3090-3195)
- ✅ Three checkpoints defined: Decomposition Verification, Agent Output Verification, Final Synthesis Verification
- ✅ Retry logic with configurable attempts (default: 2 retries)
- ✅ Learning from scores (cache on success ≥0.8, decay on failure <0.5)

**The TWO SEPARATE LOOPS (Need Clarification):**

**LOOP 1: Decomposition Self-Correction**
```
DECOMPOSE (Step 2)
    ↓
VERIFY Decomposition (Step 3)
    ↓
Score 0.5-0.7 AND retry_count < 2
    → LOOP BACK to DECOMPOSE (with feedback)
    → Include: "Previous decomposition failed because: X"
    → Increment retry_count
    → Try again

Score 0.5-0.7 AND retry_count ≥ 2
    → ESCALATE to Option C (or FAIL in MVP)
    → EXIT LOOP

Score ≥ 0.7
    → PASS to ROUTE TO AGENTS (Step 4)
    → EXIT LOOP
```

**LOOP 2: Agent Execution Self-Correction**
```
ROUTE TO AGENTS (Step 4)
    ↓
VERIFY Agent Output (Step 5)
    ↓
Score 0.5-0.7 AND retry_count < 2
    → LOOP BACK to ROUTE TO AGENTS (with feedback)
    → Include: "Output was insufficient because: X"
    → Try different agent if available
    → Increment retry_count
    → Try again

Score 0.5-0.7 AND retry_count ≥ 2
    → PARTIAL ACCEPT (use output but flag as low-confidence)
    → CONTINUE to SYNTHESIZE (Step 6) with warning
    → EXIT LOOP

Score ≥ 0.7
    → PASS to next subgoal or SYNTHESIZE
    → EXIT LOOP
```

**Critical Distinction:**
- **Loop 1** retries DECOMPOSITION (reasoning about how to break down the problem)
- **Loop 2** retries AGENT EXECUTION (gathering information/executing subgoals)
- These are INDEPENDENT loops - each has its own retry_count
- Each loop has its own feedback mechanism
- Each loop has different failure modes:
  - Loop 1 failure: ESCALATE or FAIL (can't break down problem)
  - Loop 2 failure: PARTIAL ACCEPT (some info is better than none)

**Why Clarification Matters:**
- Prevents confusion between "retry decomposition" vs "retry agent"
- Makes debugging easier (which loop failed?)
- Allows separate configuration (e.g., 2 retries for decomposition, 3 retries for agents)
- Clear logging per loop (which retry count are we on?)

**Current Documentation Status:**
- Appendix D has the complete logic BUT doesn't explicitly call out "TWO SEPARATE LOOPS"
- Flow diagram (lines 113-163) shows the steps but doesn't visualize the loop-back paths
- Could benefit from visual loop-back arrows in flow diagram

**Proposed Clarification (Where to Add):**

**1. Section 3 Flow Diagram Enhancement (lines 113-163)**
- Add visual loop-back arrows:
  - VERIFY (Step 3) → loops back to → DECOMPOSE (Step 2)
  - VERIFY OUTPUTS (Step 5) → loops back to → ROUTE TO AGENTS (Step 4)
- Add annotation: "Loop 1: Decomposition Retry (max 2)" and "Loop 2: Agent Retry (max 2)"

**2. New Section 7.4: "Self-Correction Loops"**
- Add dedicated section explaining the TWO SEPARATE LOOPS
- Visual diagram showing loop-back paths
- Example traces showing:
  - Successful decomposition on first try
  - Decomposition retry with feedback → success
  - Agent retry with different agent → success
  - Both loops triggering in same query

**3. Appendix D Enhancement (line 3092)**
- Add preamble: "This matrix defines TWO INDEPENDENT RETRY LOOPS:"
- Section headers:
  - "LOOP 1: Decomposition Self-Correction (Checkpoint 1)"
  - "LOOP 2: Agent Execution Self-Correction (Checkpoint 2)"
  - "Final Checkpoint: Synthesis Verification (No retry loop)"

**Config Addition:**
```json
"self_correction": {
  "decomposition_loop": {
    "enabled": true,
    "max_retries": 2,
    "pass_threshold": 0.7,
    "retry_threshold": 0.5,
    "feedback_type": "structured"
  },
  "agent_execution_loop": {
    "enabled": true,
    "max_retries": 2,
    "pass_threshold": 0.7,
    "retry_threshold": 0.5,
    "try_different_agent": true
  }
}
```

**Where to Document:**
- **Section 3 (lines 113-163)**: Update flow diagram with loop-back arrows showing:
  - VERIFY (Step 3) ⟲ DECOMPOSE (Step 2) [Loop 1]
  - VERIFY OUTPUTS (Step 5) ⟲ ROUTE TO AGENTS (Step 4) [Loop 2]
- **Section 7.4** (NEW): "Self-Correction Loops" - dedicated section explaining:
  - TWO INDEPENDENT LOOPS concept
  - Each loop has its own retry_count
  - Visual diagram with loop-back paths
  - Example execution traces
- **Appendix D (line 3092)**: Add preamble before matrix:
  ```
  This matrix defines TWO INDEPENDENT RETRY LOOPS:
  - LOOP 1: Decomposition Self-Correction (Checkpoint 1)
  - LOOP 2: Agent Execution Self-Correction (Checkpoint 2)
  - Each loop maintains its own retry_count (not shared)
  ```
- **Appendix C**: Add `self_correction` config section (separate settings per loop)

**Implementation Note:**
- Current PRD already has the complete retry logic in Appendix D
- This feature is a CLARIFICATION to make the two loops explicit
- No new logic needed, just visual and textual clarity

**Complexity:** Low (documentation clarification only, no new logic)
**Priority:** HIGH - Prevents implementation confusion about retry loops
**Status:** MVP - Add clarifications to existing documentation (already in PRD, needs visual enhancement)

---

#### 6. Headless Mode

**What:** Run AURORA in autonomous loop with human out of the loop for focused, goal-driven experiments

**Use Cases:**
1. **Autonomous validation experiments** - Verify system behavior, test pipelines, validate assumptions
2. **Continuous testing/monitoring** - Run repeated experiments, gather data, test edge cases

**Directory Structure:**
```
./headless/
  ├── prompt.md        # Goal definition and constraints
  └── scratchpad.md    # Agent memory between iterations (read/write)
```

**Pattern:**
```bash
# Single iteration
aurora --headless --prompt=./headless/prompt.md --scratchpad=./headless/scratchpad.md

# Continuous loop (external)
while :; do
  aurora --headless --prompt=./headless/prompt.md --scratchpad=./headless/scratchpad.md
  # Check exit code or scratchpad for completion signal
  if grep -q "GOAL_ACHIEVED" ./headless/scratchpad.md; then break; fi
done
```

**Termination Criteria (Either Stops Loop):**
1. **Goal Completion Check** - LLM evaluates if goal from prompt.md is met
   - Agent writes "GOAL_ACHIEVED: [reason]" to scratchpad.md
   - External loop detects this signal and breaks
2. **Max Iterations Limit** - Hard limit to prevent infinite loops
   - Configured in prompt.md: `MAX_ITERATIONS: 10`
   - Agent tracks iteration count in scratchpad.md
   - External loop counts iterations and breaks

**Safety Constraints:**

**1. Branch Isolation (Git Safety)**
- prompt.md MUST instruct agent to:
  ```markdown
  # Safety Rules (in prompt.md)

  1. CREATE AND USE HEADLESS BRANCH:
     - git checkout -b headless (if not exists)
     - ALL work happens on "headless" branch ONLY

  2. ALLOWED OPERATIONS:
     - Read any file in repository
     - Edit/create files on headless branch
     - git add, git commit (on headless branch only)

  3. FORBIDDEN OPERATIONS:
     - NO git merge (keep headless isolated)
     - NO git push (keep experiment local)
     - NO git checkout main (stay on headless)
     - NO rm -rf or destructive commands
     - NO modifying files outside project directory

  4. GOAL FOCUS:
     - ONE measurable, achievable goal per experiment
     - Write progress to scratchpad.md after each iteration
     - Write "GOAL_ACHIEVED: [reason]" when goal is met
  ```

**2. Read-Only Mode for Main Branch**
- AURORA enforces: If current branch is "main" or "master" → reject headless mode
- Error message: "Headless mode requires 'headless' branch. Run: git checkout -b headless"

**3. Complete Control for Headless Branch**
- On "headless" branch: agent can edit, add, commit freely
- All changes stay isolated (no merge, no push)
- Easy to discard: `git checkout main && git branch -D headless`

**4. Cost Budget Per Experiment**
- prompt.md can specify: `BUDGET_LIMIT: $5.00`
- AURORA tracks cumulative cost in scratchpad.md
- Stops if budget exceeded (writes "BUDGET_EXCEEDED" to scratchpad)

**CLI Integration:**

**New Flags:**
```bash
aurora --headless \
  --prompt=./headless/prompt.md \
  --scratchpad=./headless/scratchpad.md \
  --max-iterations=10 \
  --budget-limit=5.00
```

**Flag Details:**
- `--headless` - Enable headless mode (human out of the loop)
- `--prompt` - Path to prompt.md (goal definition)
- `--scratchpad` - Path to scratchpad.md (agent memory, read/write)
- `--max-iterations` - Hard limit on iterations (default: 10)
- `--budget-limit` - Max cost in USD (default: from config or unlimited)

**Validation on Start:**
- Check current git branch (must be "headless" or will create it)
- Check prompt.md exists and has valid goal
- Check scratchpad.md exists (create if missing)
- Verify safety rules are present in prompt.md (warn if missing)

**Scratchpad Format (Simple Markdown):**

```markdown
# Headless Experiment Scratchpad

**Experiment:** [Brief description from prompt.md]
**Started:** 2025-12-20 14:30:00
**Current Iteration:** 3 / 10
**Cost So Far:** $0.45 / $5.00

---

## Iteration 1 (14:30:00)
**Action:** Created test file test_aurora.py
**Observation:** File created successfully
**Next Step:** Run tests to verify behavior

## Iteration 2 (14:31:15)
**Action:** Ran pytest tests/
**Observation:** 329/329 tests passing
**Next Step:** Check if goal is met

## Iteration 3 (14:32:30)
**Action:** Verified all tests pass, checked output matches expected
**Observation:** Goal criteria satisfied (all tests pass, output correct)
**Decision:** GOAL_ACHIEVED: All tests passing, validation complete

---

**STATUS:** GOAL_ACHIEVED
**Reason:** Successfully validated that all 329 tests pass with correct output
**Total Cost:** $0.45
**Total Iterations:** 3
```

**Integration with Existing Architecture:**

**Where It Fits:**
- Headless mode is a **runtime mode** of the AURORA CLI (not a separate layer)
- Uses existing complexity assessment, SOAR, verification layers
- Only difference: No user interaction, autonomous looping, scratchpad memory

**Modified Flow for Headless Mode:**
```
START HEADLESS LOOP (iteration = 1)
    ↓
Read prompt.md (goal definition)
Read scratchpad.md (previous iteration memory)
    ↓
USER QUERY (from prompt.md + scratchpad context)
    ↓
[Normal AURORA flow: ASSESS → DECOMPOSE → VERIFY → AGENTS → SYNTHESIZE]
    ↓
Write results to scratchpad.md (append iteration log)
    ↓
Check termination:
  - Goal achieved? (LLM evaluates goal from prompt.md)
  - Max iterations reached?
  - Budget exceeded?
    ↓
If NOT terminated:
  → INCREMENT iteration
  → LOOP BACK to start
    ↓
If TERMINATED:
  → Write final status to scratchpad.md
  → EXIT with code 0 (success) or 1 (failure/timeout)
```

**Example prompt.md:**

```markdown
# Headless Experiment: Validate TTS Pipeline

## Goal
Verify that the ArabicTTS pipeline preserves 100% of input text through all processing stages.

**Success Criteria:**
- Run multipass_detector_example.py on 25 test sentences
- Compare detected characters vs original characters
- Report any phantom characters (not in original)
- Report any missing characters (in original but not detected)
- GOAL ACHIEVED = 100% character preservation (no phantoms, no missing)

## Constraints
- MAX_ITERATIONS: 10
- BUDGET_LIMIT: $2.00
- BRANCH: headless (isolated experiment)

## Safety Rules
1. Create/use "headless" branch: `git checkout -b headless`
2. Allowed: read files, edit files, git add/commit on headless
3. Forbidden: git merge, git push, rm -rf, checkout main
4. Focus: ONE goal only (character preservation validation)

## Context
- Project: /home/hamr/PycharmProjects/ArabicTTS
- Test script: tools/azure_tts/multipass_detector_example.py
- Test data: data/test_cases/*.txt (25 sentences)

## Iteration Instructions
After each iteration, write to scratchpad.md:
- What action was taken
- What was observed
- What is the next step
- Progress toward goal (% complete)
- If goal achieved: "GOAL_ACHIEVED: [reason]"
```

**Where to Document:**

**1. Section 2.5** (NEW): "Headless Mode" - Overview and use cases
- When to use headless mode vs interactive mode
- Example workflows (validation, testing, monitoring)

**2. Section 10.3** (NEW): "Headless Mode CLI" - Command reference
- Full CLI syntax with all flags
- Examples of single iteration and continuous loop
- Exit codes and signals

**3. Section 10.3.1** (NEW): "Headless Safety" - Safety constraints
- Git branch isolation
- Read-only main branch enforcement
- Allowed vs forbidden operations
- Cost budget enforcement

**4. Appendix C**: Add `headless` config section
```json
"headless": {
  "enabled": true,
  "default_max_iterations": 10,
  "default_budget_limit_usd": 5.00,
  "required_branch": "headless",
  "enforce_branch_check": true,
  "prompt_file": "./headless/prompt.md",
  "scratchpad_file": "./headless/scratchpad.md",
  "goal_achievement_signal": "GOAL_ACHIEVED",
  "budget_exceeded_signal": "BUDGET_EXCEEDED"
}
```

**5. Appendix F** (NEW): "Headless Experiment Template"
- Complete prompt.md template with safety rules
- Complete scratchpad.md template with iteration log format
- Example experiment: validation, testing, monitoring

**Why Needed:**
- Autonomous validation without human supervision
- Focused experiments on single measurable goals
- Testing workflows repeatedly (e.g., nightly validation)
- Personal users can run experiments safely (branch isolation, budget limits)

**Complexity:** Medium (loop control + state management + git safety + scratchpad I/O)
**Priority:** MEDIUM - Useful for testing and validation, not core reasoning
**Status:** MVP - Add CLI flags, branch enforcement, scratchpad I/O, goal evaluation

---

### ❌ DEFERRED / REJECTED (5 features)

#### 7. Gateway/Routing Layer
**Rejected reason:** "We already have complexity matching (Layer 1 assessment), why add gateway? Users are usually aware of where they are and they switch when they want."
**Decision:** Don't add - redundant with Layer 1 assessment
**Status:** NOT in MVP

---

#### 8. Tool/API Calling Framework
**Decision:** Stashed - agents handle this, not AURORA core
**Status:** NOT in MVP

---

#### 9. Semantic Caching
**Question:** "Don't we have ACT-R for that? ACT-R does semantic matching and retrieval"
**Decision:** Deferred to Post-MVP - ACT-R already provides pattern retrieval
**Status:** NOT in MVP

---

#### 10. Runtime Agent Discovery
**Decision:** Stashed - not priority for MVP
**Status:** NOT in MVP (use static agent registry)

---

#### 11. Async/Parallel Execution
**Decision:** Stashed - SOAR already handles execution order (sequential/parallel)
**Status:** NOT in MVP (existing SOAR execution is sufficient)

---

## Implementation Notes

### Feature Integration Points

**Layer 0: Input Processing & Guardrails**
- Add: Guardrails (#3)
- Add: Cost Budget Pre-Check (#4)

**Layer 1: Assessment & Discovery**
- Already has: Complexity assessment
- Rejected: Gateway routing (#7) - redundant

**Layer 4: Verification Layer**
- Enhance: Self-correction details (#5) - TWO SEPARATE LOOPS clarification
- Already has: Options A/B/C, scoring, retry logic

**Layer 6: LLM Integration & Synthesis**
- Add: LLM Preference Routing (#1)
- Add: Timing Logs (#2) - track per-layer execution time
- Add: Cost Tracking (#4) - accumulate query costs

**CLI / Runtime**
- Add: Headless Mode (#6) - new flag `aurora --headless`

---

## Configuration Requirements

These features require config.json additions:

```json
{
  "llm_routing": {
    "fast_model": "claude-3-haiku-20240307",
    "reasoning_model": "claude-3-5-sonnet-20241022",
    "best_model": "claude-opus-4-5-20251101",
    "auto_select": true
  },

  "guardrails": {
    "pii_detection_enabled": true,
    "max_query_length": 10000,
    "allowed_formats": ["utf-8"]
  },

  "cost_budgets": {
    "soft_limit": 100.00,
    "hard_limit": 500.00,
    "warn_at_percent": 80
  },

  "timing": {
    "enabled": true,
    "log_path": "./logs/timing/"
  },

  "headless": {
    "enabled": false,
    "max_iterations": 100,
    "scratchpad_path": "./.aurora/headless_scratch.md",
    "goal_completion_check": "manual"
  }
}
```

---

---

#### 7. Memory Integration Modes

**What:** Two modes for accessing AURORA memory within Claude Code

**The Problem:**
- AURORA has valuable ACT-R memory (reasoning patterns, code chunks, domain knowledge)
- Users need memory access WITHOUT always running full AURORA orchestration
- Need balance between "always-on" (expensive) and "manual invoke" (friction)

**Solution: Option C + Intentional Memory Recall**

### Mode 1: Smart Auto-Escalation (Default Behavior)

**All queries go through lightweight assessment:**

```
USER QUERY to Claude Code
    ↓
Lightweight Assessment (0.1s, $0.0001)
    ↓
┌─────────────────────────────────────────────┐
│ SIMPLE (90% of queries)                     │
│   - Direct LLM response                     │
│   - ACT-R passive retrieval (boost context) │
│   - Memory loaded on-demand from SQLite     │
│   - No orchestration, no verification       │
│   - Cost: ~$0.01-0.05 per query             │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ MEDIUM/COMPLEX (10% of queries)             │
│   - Auto-escalate to full AURORA            │
│   - DECOMPOSE → VERIFY → AGENTS → SYNTHESIZE│
│   - Active memory retrieval + learning      │
│   - Cost: ~$0.10-0.50 per query             │
└─────────────────────────────────────────────┘
```

**Memory Access:**
- **Passive retrieval:** Memory always available (in-process, not daemon)
- **Lazy updates:** Memory updates ONLY during AURORA runs (when learning happens)
- **On-demand loading:** SQLite database loaded when needed (fast)

**User Experience:**
- User just types query to Claude Code (normal behavior)
- AURORA auto-invokes for complex queries
- Memory automatically boosts context for all queries
- No manual commands needed for default behavior

### Mode 2: Intentional Memory Recall (Explicit Command)

**New command: `aur mem "search query"`**

```bash
# Search reasoning patterns
aur mem "how did we solve authentication bugs?"

# Search code patterns
aur mem "functions related to user login"

# Search domain knowledge
aur mem "AWS Polly configuration patterns"
```

**What it does:**
1. **Query ACT-R memory directly** (no orchestration)
2. **Semantic search** + activation ranking
3. **Return top-K chunks** with context:
   - Reasoning patterns (past decompositions, routing decisions)
   - Code chunks (functions, dependencies)
   - Domain knowledge (APIs, schemas, conventions)
4. **Read-only** - no learning, no memory updates

**Output Format:**
```
Memory Search Results for: "authentication bugs"

Found 5 relevant patterns (sorted by activation):

1. [Reasoning Pattern] ID: reas:auth-token-expiry-2024-11
   Activation: 0.89 | Last used: 2 days ago
   Context: "Fixed token expiry bug by checking refresh window"
   Decomposition: [subgoal 1: verify token age, subgoal 2: refresh if needed]

2. [Code Chunk] ID: code:src/auth/token_manager.py:validate_token
   Activation: 0.78 | Last modified: 5 days ago
   Function: validate_token(token: str) -> bool
   Context: Token validation with expiry check

3. [Reasoning Pattern] ID: reas:auth-session-timeout-2024-10
   Activation: 0.65 | Last used: 3 weeks ago
   Context: "Session timeout causing logout loop"
   Solution: Adjusted session TTL in config
```

**Use Cases:**
- "What have we tried before for this problem?"
- "Show me all functions related to X"
- "What patterns did we learn about Y?"
- "Refresh my memory about Z"

### Memory Update Strategy (Lazy Updates for MVP)

**When does memory get updated?**

1. **During full AURORA runs** (auto-invoked on complex queries)
   - Success (score ≥ 0.8): Cache reasoning pattern, boost activation
   - Failure (score < 0.5): Decay activation, mark as difficult
   - Learning loop runs after synthesis

2. **NOT updated on:**
   - Simple queries (direct LLM, no orchestration)
   - Memory-only searches (`aur mem`)
   - File saves (no daemon watching files in MVP)

3. **Explicit memory storage** (optional, Phase 2)
   - User says "remember this approach"
   - AURORA creates explicit pattern entry
   - Useful for manual capture of insights

**Why lazy updates work for MVP:**
- Personal users don't generate 1000s of queries/hour
- Memory updates naturally during complex problem-solving (when AURORA runs)
- Good enough for MVP, can add real-time updates later

### Architecture: In-Process Memory (Not Daemon)

```
┌─────────────────────────────────────────────────────┐
│                  CLAUDE CODE PROCESS                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  User Query                                          │
│      ↓                                               │
│  ┌────────────────────────────────────┐             │
│  │  Lightweight Assessment            │             │
│  │  (decide: simple or complex?)      │             │
│  └────────────────────────────────────┘             │
│      ↓                    ↓                          │
│  [SIMPLE]            [COMPLEX]                       │
│      ↓                    ↓                          │
│  ┌─────────────┐    ┌──────────────────┐            │
│  │ Direct LLM  │    │ Full AURORA      │            │
│  │     +       │    │ Orchestration    │            │
│  │ ACT-R Load  │    │     +            │            │
│  │ (on-demand) │    │ Learning Loop    │            │
│  └─────────────┘    └──────────────────┘            │
│      ↓                    ↓                          │
│      └────────────────────┘                          │
│              ↓                                       │
│  ┌────────────────────────────────────┐             │
│  │     ACT-R Memory (SQLite)          │             │
│  │  - reasoning patterns               │             │
│  │  - code chunks                      │             │
│  │  - domain knowledge                 │             │
│  │  - activation values                │             │
│  └────────────────────────────────────┘             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Key Points:**
- No separate daemon process (simpler)
- Memory loaded on-demand (fast enough for personal use)
- Updates happen in-process during AURORA runs
- Can upgrade to daemon later if needed (Phase 2)

### CLI Commands

**Implicit (default behavior):**
```bash
# Just use Claude Code normally
claude "how do I implement authentication?"

# AURORA auto-invokes if query is complex
# Memory always available for context boost
```

**Explicit memory search:**
```bash
# Search memory directly
aur mem "authentication patterns"
aur mem "functions in src/auth/"
aur mem "reasoning patterns for bug X"

# Short form
aur m "search query"
```

**Full AURORA (manual invoke):**
```bash
# Force full orchestration even if query seems simple
aur "complex query needing decomposition"
```

### Configuration

**Appendix C addition:**
```json
"memory_modes": {
  "auto_escalation": {
    "enabled": true,
    "assessment_threshold": {
      "simple": ["single_step", "factual", "lookup"],
      "complex": ["multi_step", "reasoning", "planning"]
    },
    "passive_retrieval": {
      "enabled": true,
      "max_chunks": 10,
      "activation_threshold": 0.5
    }
  },
  "explicit_recall": {
    "enabled": true,
    "command": "aur mem",
    "short_command": "aur m",
    "max_results": 10,
    "include_context": true,
    "show_activation_scores": true
  },
  "memory_updates": {
    "strategy": "lazy",  // Options: "lazy", "eager", "daemon"
    "update_on_aurora_run": true,
    "update_on_simple_query": false,
    "update_on_file_save": false  // Phase 2: enable for daemon mode
  }
}
```

### Where to Document

**1. Section 2.6** (NEW): "Memory Integration Modes"
- Overview of two modes (auto-escalation + explicit recall)
- When to use each mode
- User experience flow

**2. Section 3.2** (UPDATE): "Complexity Assessment"
- Add: Auto-escalation decision (simple vs complex)
- Lightweight assessment algorithm
- Cost implications

**3. Section 10.4** (NEW): "Memory Commands"
- `aur mem` command reference
- Output format examples
- Search patterns and tips

**4. Section 11** (UPDATE): "Memory Management"
- Lazy update strategy (MVP)
- When memory gets updated
- Future: daemon mode (Phase 2)

**5. Appendix C**: Add `memory_modes` config section

### Phase 2 Upgrade Path (Future)

**When you need real-time updates:**
- Add file watcher daemon
- Background memory maintenance (decay, spreading activation)
- Continuous code context updates
- Upgrade path: Change config `memory_updates.strategy: "daemon"`

**For MVP:**
- Lazy updates sufficient
- In-process memory loading
- No daemon complexity

### Why This Approach Works

**✅ Pros:**
1. Memory always available (valuable!)
2. Auto-invocation (smart!)
3. Explicit search when needed (intentional!)
4. No daemon complexity for MVP (simple!)
5. Can upgrade to daemon later (future-proof!)

**✅ Addresses your concerns:**
- "Memory is valuable" → Always available via passive retrieval
- "I complicate things" → MVP stays simple (no daemon)
- "Need to search memory" → Explicit `aur mem` command
- "Auto-invoke when needed" → Smart assessment auto-escalates

**Complexity:** Medium (assessment logic + memory loading + CLI command)
**Priority:** HIGH - Core integration between Claude Code and AURORA
**Status:** MVP - Essential for AURORA to be useful in daily coding

---

## Summary

**7 features APPROVED for MVP:**
1. ✅ LLM Preference Routing (Layer 6)
2. ✅ Timing Logs (All layers)
3. ✅ Guardrails (Layer 0)
4. ✅ Cost Budgets (Layer 0 + Layer 6)
5. ✅ Self-Correction Details (Layer 4 - clarification)
6. ✅ Headless Mode (CLI flag)
7. ✅ Memory Integration Modes (Auto-escalation + `aur mem`)

**5 features REJECTED/DEFERRED:**
8. ❌ Gateway Routing (redundant)
9. ❌ Tool/API Calling (agent responsibility)
10. ❌ Semantic Caching (ACT-R already does this)
11. ❌ Runtime Agent Discovery (static registry sufficient)
12. ❌ Async/Parallel (SOAR handles execution order)

---

**Note:** These 6 approved features should be documented as placeholders/integration points in the unified spec. Full implementation details to be extracted from existing docs where available, or marked as "new MVP addition" where not previously documented.
