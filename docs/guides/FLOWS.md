# Aurora Flows Guide

High-level workflows for planning, research, and execution.

---

## Flow Overview

| Flow | Commands | Purpose |
|------|----------|---------|
| [Optimum Plan](#1-optimum-plan-flow) | `aur goals` -> `/aur:plan` -> `/aur:implement` | Memory-informed planning for complex features |
| [Regular Plan](#2-regular-plan-flow) | `/aur:plan` -> `/aur:implement` | Direct planning when requirements are clear |
| [Research](#3-research-flow) | `aur soar` | Answer questions with parallel agent research |
| [Execution](#4-execution-flow) | `aur spawn` | Run tasks with safeguards |
| [Memory Search](#5-memory-search-flow) | `/aur:search` -> `/aur:get` | Find and retrieve code chunks |

---

## 1. Optimum Plan Flow

**Use when:** Large features, complex refactors, unclear requirements.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPTIMUM PLAN FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TERMINAL                                                                    │
│  ┌────────────────────────────────────────┐                                 │
│  │  $ aur goals "Add OAuth2 auth"         │                                 │
│  │        --context src/auth/             │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  1. Memory Search                      │                                 │
│  │     - Finds relevant code              │                                 │
│  │     - Ranks by activation + BM25       │                                 │
│  │                                        │                                 │
│  │  2. Goal Decomposition                 │                                 │
│  │     - Breaks into 3-7 subgoals         │                                 │
│  │     - Each subgoal is actionable       │                                 │
│  │                                        │                                 │
│  │  3. Agent Matching                     │                                 │
│  │     - Assigns agents to subgoals       │                                 │
│  │     - Confidence scores (0.0-1.0)      │                                 │
│  │                                        │                                 │
│  │  4. Gap Detection                      │                                 │
│  │     - Identifies missing agents        │                                 │
│  │     - Suggests capabilities needed     │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  OUTPUT: .aurora/plans/0001-add-oauth2-auth/goals.json                      │
│                                                                              │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  CLAUDE CODE                                                                 │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:plan goals.json                  │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  Reads goals.json and generates:       │                                 │
│  │                                        │                                 │
│  │  - prd.md (requirements)               │                                 │
│  │  - tasks.md (with @agent hints)        │                                 │
│  │  - specs/ (detailed specifications)    │                                 │
│  │  - design.md (architecture decisions)  │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:implement                        │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  Sequential execution:                 │                                 │
│  │  - Reads tasks.md                      │                                 │
│  │  - Executes each task                  │                                 │
│  │  - Creates checkpoints                 │                                 │
│  │  - Validates completion                │                                 │
│  │  - Updates specs/ as needed            │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example session:**

```bash
# Terminal
$ aur goals "Add OAuth2 authentication with Google" --context src/auth/

Memory found 4 relevant files:
  src/auth/login.py (0.91)
  src/auth/session.py (0.85)
  src/models/user.py (0.79)
  src/api/routes.py (0.72)

Decomposition:
  sg-1: Add OAuth provider configuration (@full-stack-dev)
  sg-2: Implement Google OAuth callback (@full-stack-dev)
  sg-3: Create session management for OAuth users (@full-stack-dev)
  sg-4: Update login UI with Google button (@ux-expert)
  sg-5: Write OAuth integration tests (@qa-test-architect)

Agent gaps: None

Output: .aurora/plans/0001-add-oauth2-auth/goals.json

# Claude Code
/aur:plan goals.json
# Generates: prd.md, tasks.md, specs/, design.md

/aur:implement
# Executes tasks sequentially with checkpoints
```

---

## 2. Regular Plan Flow

**Use when:** Requirements are clear, simple features, quick changes.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           REGULAR PLAN FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CLAUDE CODE                                                                 │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:plan "Add logout button to       │                                 │
│  │            navbar with confirmation"   │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  Generates directly:                   │                                 │
│  │                                        │                                 │
│  │  - prd.md (brief requirements)         │                                 │
│  │  - tasks.md (actionable tasks)         │                                 │
│  │  - specs/ (if needed)                  │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:implement                        │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  Sequential execution with checkpoints │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example session:**

```bash
# Claude Code
/aur:plan "Add logout button to navbar with confirmation dialog"
# Generates tasks.md with 3-4 tasks

/aur:implement
# Executes: create component, add route, update navbar, add tests
```

**Difference from Optimum:**
- No upfront `aur goals` terminal command
- No memory-informed decomposition
- Faster for simple, well-understood changes

---

## 3. Research Flow

**Use when:** Understanding codebases, answering complex questions, architectural research.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             RESEARCH FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TERMINAL                                                                    │
│  ┌────────────────────────────────────────┐                                 │
│  │  $ aur soar "How does the payment      │                                 │
│  │             processing flow work?"     │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 1: ASSESS                       │                                 │
│  │  - Determines complexity               │                                 │
│  │  - Routes to appropriate depth         │                                 │
│  │    SIMPLE: Direct answer               │                                 │
│  │    MEDIUM: Some research               │                                 │
│  │    COMPLEX: Full parallel research     │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 2: RETRIEVE                     │                                 │
│  │  - Searches indexed memory             │                                 │
│  │  - Finds relevant code chunks          │                                 │
│  │  - Uses activation + BM25 + semantic   │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 3-5: DECOMPOSE -> VERIFY ->     │                                 │
│  │             ROUTE                      │                                 │
│  │  - Breaks into sub-questions           │                                 │
│  │  - Validates decomposition             │                                 │
│  │  - Assigns ad-hoc agents               │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 6: COLLECT (Parallel Research)  │                                 │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐  │                                 │
│  │  │ Agent 1  │ │ Agent 2  │ │Agent 3 │  │                                 │
│  │  │ Q: Entry │ │ Q: Flow  │ │Q: Error│  │                                 │
│  │  │ points?  │ │ steps?   │ │ cases? │  │                                 │
│  │  └──────────┘ └──────────┘ └────────┘  │                                 │
│  │       │            │            │      │                                 │
│  │       v            v            v      │                                 │
│  │  Lightweight agent recovery:           │                                 │
│  │  - Timeout detection                   │                                 │
│  │  - Retry with context                  │                                 │
│  │  - Fallback to simpler query           │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 7: SYNTHESIZE                   │                                 │
│  │  - Combines agent outputs              │                                 │
│  │  - Resolves conflicts                  │                                 │
│  │  - Creates coherent answer             │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PHASE 8-9: RECORD -> RESPOND          │                                 │
│  │  - Stores reasoning trace in memory    │                                 │
│  │  - Formats final answer                │                                 │
│  │  - Includes citations to code          │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
│  OUTPUT: Synthesized answer with citations                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example session:**

```bash
$ aur soar "How does the payment processing flow work?" --verbose

[ASSESS] Complexity: COMPLEX (score: 34)
[RETRIEVE] Found 8 relevant chunks
[DECOMPOSE] Sub-questions:
  1. What are the payment entry points?
  2. What is the checkout-to-payment flow?
  3. How are payment errors handled?
[ROUTE] Assigned 3 ad-hoc agents
[COLLECT] Parallel research...
  Agent 1: Complete (12s)
  Agent 2: Complete (15s)
  Agent 3: Complete (11s)
[SYNTHESIZE] Combining results...
[RECORD] Saved to memory
[RESPOND]

The payment flow starts at src/checkout/cart.py:checkout()
which calls src/payments/processor.py:create_intent()...
```

---

## 4. Execution Flow

**Use when:** Running task lists, batch operations, parallel execution.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXECUTION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TERMINAL                                                                    │
│  ┌────────────────────────────────────────┐                                 │
│  │  $ aur spawn tasks.md --verbose        │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PARSE TASKS                           │                                 │
│  │  - Reads tasks.md                      │                                 │
│  │  - Extracts agent assignments          │                                 │
│  │  - Builds dependency graph             │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  GATE CHECKS                           │                                 │
│  │                                        │                                 │
│  │  Scope Creep Detection:                │                                 │
│  │  - Compares task to original goal      │                                 │
│  │  - Flags divergent tasks               │                                 │
│  │                                        │                                 │
│  │  Budget Limits:                        │                                 │
│  │  - Tracks token/API usage              │                                 │
│  │  - Warns before exceeding              │                                 │
│  │                                        │                                 │
│  │  Dangerous Command Detection:          │                                 │
│  │  - Blocks rm -rf, force pushes         │                                 │
│  │  - Requires explicit confirmation      │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PARALLEL EXECUTION                    │                                 │
│  │                                        │                                 │
│  │  Independent tasks run in parallel:    │                                 │
│  │  ┌────────┐ ┌────────┐ ┌────────┐     │                                 │
│  │  │ Task 1 │ │ Task 2 │ │ Task 3 │     │                                 │
│  │  └────────┘ └────────┘ └────────┘     │                                 │
│  │                                        │                                 │
│  │  Dependent tasks wait:                 │                                 │
│  │  Task 4 (depends: 1,2) -> waits        │                                 │
│  │  Task 5 (depends: 4) -> waits          │                                 │
│  │                                        │                                 │
│  │  Max concurrent: 5 (configurable)      │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  PROGRESS TRACKING                     │                                 │
│  │  - Updates tasks.md with [x] marks     │                                 │
│  │  - Logs execution times                │                                 │
│  │  - Reports failures with context       │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example session:**

```bash
$ aur spawn tasks.md --verbose

Loaded 6 tasks from tasks.md
Dependency graph:
  1 -> []
  2 -> []
  3 -> [1]
  4 -> [1, 2]
  5 -> [3, 4]
  6 -> [5]

Executing (max_concurrent=5)...

[1/6] Task 1: Setup Stripe SDK       [@full-stack-dev] RUNNING
[2/6] Task 2: Create payment models  [@full-stack-dev] RUNNING
[1/6] Task 1: Complete (23s)
[3/6] Task 3: Add API endpoints      [@full-stack-dev] RUNNING
[2/6] Task 2: Complete (31s)
[4/6] Task 4: Payment UI             [@ux-expert] RUNNING
...

Summary:
  Completed: 6/6
  Duration: 2m 14s
  Failures: 0
```

---

## 5. Memory Search Flow

**Use when:** Finding code, exploring codebase, retrieving specific chunks.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MEMORY SEARCH FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CLAUDE CODE                                                                 │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:search "authentication handler"  │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  HYBRID RETRIEVAL                      │                                 │
│  │                                        │                                 │
│  │  40% BM25 keyword matching             │                                 │
│  │  30% ACT-R activation (usage decay)    │                                 │
│  │  30% Git recency signals               │                                 │
│  │                                        │                                 │
│  │  (With ML: adds semantic similarity)   │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  RESULTS                               │                                 │
│  │                                        │                                 │
│  │  [1] src/auth/handler.py (0.92)        │                                 │
│  │      def authenticate_user(...)        │                                 │
│  │                                        │                                 │
│  │  [2] src/auth/middleware.py (0.85)     │                                 │
│  │      class AuthMiddleware(...)         │                                 │
│  │                                        │                                 │
│  │  [3] src/api/auth_routes.py (0.78)     │                                 │
│  │      @router.post("/login")            │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  /aur:get 1                            │                                 │
│  │  (Retrieves full content of result 1)  │                                 │
│  └────────────────────────────────────────┘                                 │
│                        │                                                     │
│                        v                                                     │
│  ┌────────────────────────────────────────┐                                 │
│  │  FULL CHUNK CONTENT                    │                                 │
│  │                                        │                                 │
│  │  File: src/auth/handler.py             │                                 │
│  │  Lines: 45-78                          │                                 │
│  │                                        │                                 │
│  │  def authenticate_user(               │                                 │
│  │      username: str,                    │                                 │
│  │      password: str                     │                                 │
│  │  ) -> Optional[User]:                  │                                 │
│  │      """Authenticate user..."""        │                                 │
│  │      ...                               │                                 │
│  └────────────────────────────────────────┘                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Example session:**

```bash
# Claude Code
/aur:search "payment validation"

Results:
  [1] src/payments/validator.py (0.94) - validate_payment_data()
  [2] src/checkout/forms.py (0.82) - PaymentForm
  [3] src/api/payment_routes.py (0.76) - @router.post("/pay")

/aur:get 1

# Returns full content of validate_payment_data() function
```

---

## Flow Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WHICH FLOW SHOULD I USE?                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  START                                                                       │
│    │                                                                         │
│    v                                                                         │
│  ┌─────────────────────────────────┐                                        │
│  │ Do you need to implement code? │                                        │
│  └─────────────────────────────────┘                                        │
│         │                    │                                               │
│        YES                  NO                                               │
│         │                    │                                               │
│         v                    v                                               │
│  ┌──────────────┐     ┌──────────────┐                                      │
│  │ Is it a      │     │ Need to find │                                      │
│  │ complex      │     │ specific     │                                      │
│  │ feature?     │     │ code?        │                                      │
│  └──────────────┘     └──────────────┘                                      │
│     │        │            │        │                                         │
│    YES      NO           YES      NO                                         │
│     │        │            │        │                                         │
│     v        v            v        v                                         │
│  ┌──────┐ ┌──────┐   ┌──────┐  ┌──────────────┐                             │
│  │OPTIMUM│ │REGULAR│  │MEMORY│  │ Understand   │                             │
│  │ PLAN │ │ PLAN │  │SEARCH│  │ something?   │                             │
│  └──────┘ └──────┘   └──────┘  └──────────────┘                             │
│                                    │        │                                │
│                                   YES      NO                                │
│                                    │        │                                │
│                                    v        v                                │
│                                ┌──────┐  ┌──────────┐                       │
│                                │ SOAR │  │ Just ask │                       │
│                                │RESEARCH│ │ Claude   │                       │
│                                └──────┘  └──────────┘                       │
│                                                                              │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                              │
│  OPTIMUM PLAN: aur goals -> /aur:plan goals.json -> /aur:implement          │
│  REGULAR PLAN: /aur:plan "prompt" -> /aur:implement                         │
│  MEMORY SEARCH: /aur:search -> /aur:get                                     │
│  SOAR RESEARCH: aur soar "question"                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference

| Scenario | Flow | Commands |
|----------|------|----------|
| New feature with unclear scope | Optimum Plan | `aur goals` -> `/aur:plan` -> `/aur:implement` |
| Simple, well-defined change | Regular Plan | `/aur:plan` -> `/aur:implement` |
| "How does X work?" | Research | `aur soar "question"` |
| "Where is the auth code?" | Memory Search | `/aur:search` -> `/aur:get` |
| Run a task list | Execution | `aur spawn tasks.md` |
| Save session for later | Checkpoint | `/aur:checkpoint` |

---

## See Also

- [Commands Reference](COMMANDS.md) - Full CLI documentation
- [Tools Guide](TOOLS_GUIDE.md) - Architecture and internals
- [README](../../README.md) - Project overview
