# bare-agent Evaluation — Round 5 (v0.2.2, resilience features)

> Round 1: stale v0.1.0 (deleted). Round 2: v0.2.0, 3 workarounds needed. Round 3: DX/UX feedback. Round 4: v0.2.1, all workarounds eliminated. **Round 5: v0.2.2, resilience features (stepRetry, jitter, CircuitBreaker, Fallback, typed errors).**

## What Was Built

`aur soar2` — an experimental SOAR pipeline that replaces Aurora's ~2400-line Python orchestrator with bare-agent for the core DECOMPOSE → COLLECT → SYNTHESIZE phases. Python handles ASSESS, RETRIEVE, RECORD, RESPOND.

**Result**: Working end-to-end. SIMPLE and MEDIUM queries produce comparable output quality to the original SOAR. Wave parallelism works (verified: independent steps start concurrently).

### Integration code (how bare-agent was consumed)

| File | Lines | What it does |
|------|-------|-------------|
| [`packages/cli/src/aurora_cli/bareagent/soar_agent.js`](../packages/cli/src/aurora_cli/bareagent/soar_agent.js) | 273 | Main Node.js orchestrator — wires Planner, runPlan, Loop, StateMachine, Stream, CLIPipe, JsonlTransport. This is the primary bare-agent consumer. |
| [`packages/cli/src/aurora_cli/bareagent/bridge.py`](../packages/cli/src/aurora_cli/bareagent/bridge.py) | ~130 | Python↔Node.js subprocess bridge — spawns soar_agent.js, sends JSONL on stdin, yields parsed events from stdout |
| [`packages/cli/src/aurora_cli/commands/soar2.py`](../packages/cli/src/aurora_cli/commands/soar2.py) | ~280 | CLI command — Python phases (ASSESS, RETRIEVE, RECORD, RESPOND) + terminal UX, maps JSONL events to Rich console output |
| [`packages/cli/src/aurora_cli/bareagent/__init__.py`](../packages/cli/src/aurora_cli/bareagent/__init__.py) | 1 | Package init |

**Key sections in `soar_agent.js`** (the bare-agent consumer):

| Lines | What | bare-agent components used |
|-------|------|---------------------------|
| 34–45 | `makeProvider()` — CLIPipe with native `systemPromptFlag` (v0.2.1) | `CLIPipe` |
| 52–56 | Component wiring — provider, retry, stream (JsonlTransport), state machine | `Retry`, `Stream`, `JsonlTransport`, `StateMachine` |
| 68–88 | SIMPLE path — skip Planner, direct `Loop.run()` | `Loop` |
| 93–117 | MEDIUM/COMPLEX — Planner with retry | `Planner`, `Retry` |
| 136–183 | Step execution via `runPlan` with `onWaveStart` + callbacks (v0.2.1) | `runPlan`, `StateMachine`, `Loop`, `Retry`, `Stream` |
| 203–237 | Synthesis — final `Loop.run()` with all step outputs | `Loop` |

---

## Components Used

| bare-agent Component | Used For | Verdict |
|---|---|---|
| `CLIPipe` (provider) | Spawn `claude --print` for LLM calls | Works natively with `systemPromptFlag` (v0.2.1) |
| `Planner` | Decompose query into step DAG | Works well for MEDIUM/COMPLEX |
| `runPlan` | Wave-parallel DAG execution | Excellent — replaced 50 lines of custom code |
| `StateMachine` | Track step lifecycle | Works, event hooks useful for debugging |
| `Retry` | Wrap Planner and Loop calls | Works, 2 attempts with exponential backoff |
| `Stream` | Emit JSONL events to Python bridge | Works with `JsonlTransport` from `bare-agent/transports` (v0.2.1) |
| `Loop` | Execute each step (single-round LLM call) | Works, retry integration is seamless |
| `Planner` + `runPlan` together | Full plan-then-execute pipeline | Clean separation of concerns, `onWaveStart` callback added (v0.2.1) |

**Not used**: `Scheduler` (time-triggered, not relevant), `Checkpoint` (no human-in-the-loop needed), `Memory` (Aurora has its own store).

---

## Was It Helpful?

**Yes.** Concrete evidence:

### What bare-agent saved me from writing

| What | Without bare-agent | With bare-agent |
|---|---|---|
| Wave executor with dep tracking | ~50 lines custom JS, 3 bugs found during testing (null state handling, blocked step detection, parallel execution) | `runPlan(steps, fn, { stateMachine, onStepStart, onStepDone, onStepFail })` — one function call, dependency failure propagation included |
| Step state tracking | ~25 lines custom `StepStateMachine` class, no events | `StateMachine` with `EventEmitter`, `onTransition()` hooks, persistence option |
| Retry logic | Nothing (steps failed permanently in v1) | `Retry` integrated into `Loop` — wraps both provider calls and tool executions |
| LLM call wrapper | ~80 lines custom `CLIPipeProvider` with spawn/pipe/error handling | `CLIPipe` — handles spawn failures, timeouts (SIGTERM+SIGKILL grace), empty output |
| Event streaming | ~3 lines `emit()` helper, no subscriber pattern | `Stream` with transport pluggability and subscriber pattern |

### Line count comparison

| | Round 1 (stale pkg, everything custom) | Round 2 (v0.2.0) | Round 4 (v0.2.1) |
|---|---|---|---|
| `soar_agent.js` | 250 lines | 195 lines | 173 lines |
| `cli_pipe_provider.js` | 80 lines | 0 (deleted, using CLIPipe) | 0 |
| Custom `executeWaves` | 45 lines | 0 (using runPlan) | 0 |
| Custom `StepStateMachine` | 20 lines | 0 (using StateMachine) | 0 |
| `makeProvider()` wrapper | — | 30 lines (system prompt workaround) | 6 lines (just CLIPipe constructor) |
| Inline transport | — | 3 lines | 0 (using JsonlTransport) |
| **Total custom JS** | **~395 lines** | **~195 lines** | **~173 lines** |

That's a **56% reduction** from Round 1. The remaining 173 lines are 100% domain logic (prompts, JSONL protocol, SIMPLE vs COMPLEX path routing) — zero framework plumbing.

### What I didn't have to debug

The biggest value wasn't line count — it was bugs I didn't have to find:

1. `runPlan` handles dependency failure propagation correctly (if s1 fails, s2 that depends on s1 is auto-failed with a clear message). My custom version missed this initially.
2. `StateMachine` validates transition legality (can't go from `done` back to `running`). My custom version was a dumb state bag.
3. `Retry` handles both provider errors and tool errors with the same backoff policy. I had no retry at all in Round 1.
4. `CLIPipe` has timeout handling with SIGTERM→SIGKILL grace period. My version had no timeout.

---

## What I Had to Work Around

### 1. CLIPipe system prompt handling — FIXED in v0.2.1

**Problem**: `CLIPipe._formatPrompt()` flattens all messages to `Role: content` plaintext. When passed to `claude --print`, the LLM can't distinguish system instructions from user content.

**v0.2.0 workaround**: Wrapped `CLIPipe` in a `makeProvider()` function (~30 lines) that manually separated system/user messages.

**v0.2.1 fix**: `systemPromptFlag` option on CLIPipe. System messages are extracted and passed via the specified CLI flag. Workaround deleted — `makeProvider()` is now 6 lines:

```js
// Before (v0.2.0): 30-line wrapper
// After (v0.2.1): native support
new CLIPipe({
  command: 'claude',
  args: ['--print', '--model', 'sonnet'],
  systemPromptFlag: '--system-prompt',
})
```

### 2. SIMPLE query path — Planner is wrong tool

**Problem**: For simple queries ("What is SOAR?"), the Planner sends the query to the LLM with a system prompt asking for JSON steps. But the LLM answers the question directly instead of planning — even with forceful system prompts. This isn't a bare-agent bug; it's a fundamental mismatch: you don't plan a simple lookup.

**Workaround**: Skip the Planner entirely for SIMPLE complexity. Use `Loop.run()` directly for a single-shot answer. This is what the original SOAR does too (`_execute_simple_path()`).

**Recommendation**: Not a bare-agent issue. Application-level concern. The Planner is for queries that need decomposition.

### 3. JSON synthesis prompt fragility

**Problem**: Initially asked the LLM to return the synthesized answer as JSON (`{"answer": "markdown...", "confidence": 0.85}`). Long markdown answers with newlines and quotes break JSON serialization — the LLM produces unterminated strings.

**Workaround**: Changed synthesis to ask for plain markdown with a trailing `CONFIDENCE: 0.XX` line. Parse the confidence with a regex.

**Recommendation**: Not a bare-agent issue. General LLM prompt engineering. But `Planner` handles this well internally (strips markdown fences, has regex fallback). A similar utility for "ask LLM for structured output" could be useful — or just document the pattern.

### 4. JsonlTransport not exported — FIXED in v0.2.1

**v0.2.0**: `require('bare-agent/src/transport-jsonl')` failed with `ERR_PACKAGE_PATH_NOT_EXPORTED`. Worked around with inline 3-line transport.

**v0.2.1**: `require('bare-agent/transports')` exports `JsonlTransport`. Inline hack deleted. Bonus: `JsonlTransport` adds `ts` timestamps to events automatically.

---

## What bare-agent Got Right

### 1. runPlan is the standout

`runPlan` is the single most valuable component for this use case. It takes a Planner DAG and executes it with:
- Wave parallelism via `Promise.all()`
- Dependency failure propagation
- Concurrency limiting
- Callbacks for start/done/fail
- StateMachine integration (optional)
- Input validation (duplicate IDs, unknown deps)

I went from a buggy 50-line custom implementation to a single function call. This is exactly what a framework should provide.

### 2. Composability works

Every component is independently useful:
- Used `Loop` without `Checkpoint` or `Memory`
- Used `StateMachine` without file persistence
- Used `Stream` with a custom transport (not `JsonlTransport`)
- Used `Retry` through `Loop` (didn't call it directly)
- Used `Planner` output as input to `runPlan` — clean handoff

No component forced me to use another component. This is the right design.

### 3. CLIPipe as a provider concept

The idea of CLI pipe as a first-class provider is genuinely differentiating. No other framework offers "use your existing CLI tool as the LLM backend." For Aurora, this means:
- No API keys needed
- Works with claude, cursor, windsurf, or any CLI tool
- The tool handles auth, context, capabilities
- Same code works regardless of which tool the user has

### 4. Planner DAG format

The `{id, action, dependsOn}` step format is simple and sufficient. Planner validates `dependsOn` references, strips invalid ones, handles markdown fences in LLM output. The format maps directly to `runPlan` input — no transformation needed.

---

## What's Missing or Could Improve

### ~~Priority 1: CLIPipe system prompt support~~ — SHIPPED in v0.2.1

### ~~Priority 2: Export JsonlTransport~~ — SHIPPED in v0.2.1

### Priority 1 (remaining): Loop.run() error behavior

`Loop.run()` catches provider errors and returns `{ text: '', error: 'message' }` instead of throwing. This means callers must check `result.error` manually — easy to miss (I did miss it initially, got empty answers silently). Consider: throw by default, offer a `throwOnError: false` option for callers who want the current behavior.

### Nice to have: Validate before run

`loop.validate()` exists and is useful, but I didn't use it because the SIMPLE path tells me immediately if claude works (the first Loop.run() either succeeds or fails). Validate is more useful for startup health checks in long-running services. For CLI tools it's less critical.

---

## Comparison: Original SOAR vs SOAR2 (bare-agent)

| Aspect | Original SOAR (Python) | SOAR2 (bare-agent) |
|---|---|---|
| Total code | ~2400 lines across 8 files | ~760 lines (195 JS + 280 Python command + 130 bridge + 60 init/wiring) |
| Decomposition | Custom LLM prompt + JSON parse + cache + retry | `Planner.plan()` — one call |
| Step execution | Custom `spawn_parallel_tracked` with circuit breakers | `runPlan()` with wave parallelism |
| State tracking | Custom tracking dict | `StateMachine` with EventEmitter |
| Retry | Custom retry logic per phase | `Retry` integrated into `Loop` |
| Streaming | Custom progress callbacks | `Stream` + JSONL transport |
| Agent routing | 3-tier matching (excellent/acceptable/spawned) | None — CLI tool handles everything |
| Verification | Devil's advocate pass, score thresholds | None |
| Caching | Query hash → cached decomposition | None |
| Early detection | Stall monitoring, progress polling | None |
| Output quality | High | Comparable (for SIMPLE/MEDIUM) |

### What SOAR2 gains
- **50% less code** to maintain
- **Faster to iterate** — change a prompt, not a phase class
- **Wave parallelism out of the box** via `runPlan`
- **Node.js ecosystem** available for future tooling

### What SOAR2 loses
- **No verification** — bad plans execute without validation
- **No caching** — same query re-plans every time
- **No agent routing** — can't match subgoals to specialized agents
- **No early detection** — stalled LLM calls hang until timeout
- **No circuit breakers** — cascading failures aren't prevented

These are all application-level concerns, not framework gaps. bare-agent correctly leaves them to the consumer.

---

## Verdict

**bare-agent v0.2.1 is production-ready for this use case.** All three workarounds from v0.2.0 have been eliminated. Zero custom framework plumbing remains — `soar_agent.js` is now 100% domain logic (prompts, JSONL protocol, complexity routing).

The `makeProvider()` wrapper went from 30 lines to 6 lines (just CLIPipe constructor + env cleanup). The inline transport hack is gone. Wave boundaries are now visible in the UX via `onWaveStart`.

**No remaining framework gaps.** The only open item is `Loop.run()` error-not-throw behavior (documented in gotchas, manageable with `if (result.error)` check).

---

## Developer Experience (Round 3 feedback)

### Was it easy to figure out the framework?

**No, not initially.** The actual learning path:

1. `npm install bare-agent@0.1.0` → empty module → built everything from scratch (wasted Round 1)
2. After being told the package was updated to v0.2.0, I had an agent read every source file in `node_modules/bare-agent/src/` to extract exact API signatures
3. Ran `node -e` snippets to test edge cases (StateMachine returning `null` for unknown IDs, transition validation, etc.)
4. Discovered `CLIPipe._formatPrompt()` behavior only after watching the Planner fail in production

**What I actually relied on**: JSDoc blocks in the source files. Those have exact signatures, parameter types, return shapes, and throw conditions. That's what I built from.

### Was bareagent.context.md helpful?

**Round 2 (v0.2.0)**: Didn't have it during integration. Read it after. Verdict: useful as a map, not as a build guide. Missing signatures, return types, edge cases.

**Round 4 (v0.2.1)**: The updated context.md is a **significant improvement**. It now includes:
- Component selection guide (table mapping goals to components)
- 3 integration recipes with copy-pasteable code
- 11 gotchas section covering all the edge cases I hit
- Provider options with `systemPromptFlag` documented
- `loop.validate()` health check example
- Checkpoint and Scheduler wiring examples

**What's now covered that I previously had to discover by reading source**:
- `runPlan` options: `onWaveStart`, `onStepStart`, `onStepDone`, `onStepFail`, `concurrency`, `stateMachine` — all in Recipe 1
- `Loop.run()` returns `{error}` instead of throwing — gotcha #8
- `StateMachine.getStatus()` returns null — gotcha #9
- `Planner` expects JSON array — gotcha #10
- `JsonlTransport` import path — gotcha #11
- `CLIPipe._formatPrompt()` flattens messages — gotcha #7

**Estimated time savings if I had this on Day 1**: ~45 minutes of the ~65 minutes I spent on framework friction. The recipes alone would have prevented most wrong assumptions.

### What documentation would have saved me time

**Estimated time savings: ~45 minutes** (out of ~65 min framework friction).

1. **CLIPipe `_formatPrompt()` behavior** (~30 min saved). If context.md said: _"CLIPipe concatenates all messages as `Role: content` plaintext. If your CLI tool has a `--system-prompt` flag, system messages will be mixed into the prompt body — you'll need a wrapper to pass them separately."_ — I would have written `makeProvider()` immediately instead of debugging why Planner answered queries instead of planning.

2. **`Loop.run()` returns `{error}` instead of throwing** (~15 min saved). If context.md said: _"`Loop.run()` never throws on provider errors. Check `result.error` — it will be a string if the provider failed. `result.text` will be empty."_ — I wouldn't have silently gotten empty answers and had to add console.log to diagnose.

3. **`StateMachine.getStatus()` returns `null` for unregistered IDs** (~10 min saved). One line: _"Returns `null` if the task ID hasn't been registered yet."_

4. **`Planner` output format** (~5 min saved). _"Planner expects the LLM to return a JSON array `[{id, action, dependsOn}]`, not `{steps: [...]}`."_

**Pattern**: Every issue above is a **behavioral edge case** — not a missing feature, but unexpected behavior at the boundary. These are the hardest to discover by reading JSDoc (which documents the happy path). A "Gotchas" or "Common mistakes" section per component would eliminate most of this friction.

### What the ideal context.md looks like (for AI agents)

```markdown
## CLIPipe

### Quick start
\`\`\`js
const { CLIPipe } = require('bare-agent/providers');
const pipe = new CLIPipe({ command: 'claude', args: ['--print'], timeout: 60000 });
const result = await pipe.generate([{ role: 'user', content: 'Hello' }]);
console.log(result.text);
\`\`\`

### Gotchas
- `_formatPrompt()` flattens all messages to plaintext. System messages are NOT passed via a separate flag.
- If your CLI tool supports `--system-prompt`, wrap CLIPipe to separate system/user messages.
- Timeout uses SIGTERM → SIGKILL with 5s grace period.
- Empty stdout returns `{ text: '' }`, NOT an error.

## Loop

### Quick start
\`\`\`js
const loop = new Loop({ provider, maxRounds: 1, retry, stream });
const result = await loop.run([{ role: 'user', content: 'prompt' }]);
if (result.error) throw new Error(result.error);  // ← MUST CHECK, doesn't throw
\`\`\`

### Gotchas
- `run()` catches errors and returns `{ text: '', error: 'message' }` — does NOT throw.
- `validate()` checks provider connectivity — useful for startup health checks.
```

This format — **quick start + gotchas per component** — is what an AI agent (or a developer) needs. The current context.md describes what components *are* but not how they *behave at the edges*.

### Things that cost debugging time

| Issue | Time spent | How I found it |
|---|---|---|
| CLIPipe flattens system prompt into text | ~30 min | Planner kept answering instead of planning. Traced through `_formatPrompt()` source. |
| `Loop.run()` returns `{error}` silently | ~15 min | Got empty answers. Added `console.log(result)` to see the error field. |
| `StateMachine.getStatus()` returns `null` not `{status:'pending'}` | ~10 min | Wave executor skipped all steps. Wrote `node -e` test to check. |
| `JsonlTransport` not in exports map | ~5 min | `ERR_PACKAGE_PATH_NOT_EXPORTED` at runtime. Made inline transport. |
| Planner expects JSON array, not `{steps:[]}` | ~5 min | `[Planner] expected JSON array` error at runtime. Checked `planner.js:69`. |

Total: ~65 minutes on framework friction, out of ~2 hours total integration. The rest was prompt engineering and Python bridge code.

---

## UX Gaps — Framework vs Consumer Responsibility

### Observed issues in `aur soar2` output:

1. **No spinner during LLM calls** — user sees `→ s1: ...` then silence for 30-60 seconds
2. **No wave headers** — parallel steps show as individual lines, no `[Wave 1: s1, s2]` grouping
3. **Action text truncated** — step descriptions cut at ~60 chars
4. **No streaming during step execution** — all output arrives at once when step completes

### Whose responsibility?

| Issue | Owner | Reasoning |
|---|---|---|
| Spinner | **Consumer** (soar2.py) | Different consumers want different UX — CLI spinner, web progress bar, log line, silent. bare-agent's `Stream` emits `loop:start`/`loop:done` events that the consumer can map to any UX. |
| Wave headers | **Shared** | Consumer can infer waves from callback timing, but `runPlan` knows the wave boundaries explicitly. **Suggestion: add `onWaveStart(waveNumber, steps)` callback to `runPlan`** — the framework has this information, the consumer doesn't without tracking it. |
| Action truncation | **Consumer** (soar2.py) | Terminal width, wrapping policy, verbosity level are consumer decisions. bare-agent correctly passes full action text. |
| Mid-step streaming | **CLIPipe gap** | `CLIPipe` reads all stdout then returns — no token-level streaming. This is hard to solve generically (CLI tools stream differently), but a `streaming: true` option that yields chunks from `child.stdout` would enable consumers who want it. |

### Recommendation for bare-agent

One addition to `runPlan`:
```js
// Before each Promise.all() wave:
options.onWaveStart?.(waveNumber, readySteps);
```

This is the one piece of information the framework has that the consumer can't easily derive. Everything else (spinners, truncation, formatting) is correctly left to the consumer.

One addition to `CLIPipe`:
```js
// Option for streaming stdout chunks instead of buffering:
new CLIPipe({ command: 'claude', args: ['--print'], streaming: true })
// generate() would yield chunks or accept an onChunk callback
```

This is harder to design well (different tools stream differently) but would enable real-time progress for long LLM calls.

---

## Recipes — What I Actually Built (copy-pasteable patterns)

These are the three patterns I ended up using. If these had been in context.md, integration would have taken ~1 hour instead of ~2.

### Recipe 1: Planner → runPlan with wave callbacks (the main use case)

```js
// From soar_agent.js:93-183 (v0.2.1)
const { Planner, StateMachine, Retry, Stream, Loop, runPlan } = require('bare-agent');
const { CLIPipe } = require('bare-agent/providers');
const { JsonlTransport } = require('bare-agent/transports');

const provider = new CLIPipe({
  command: 'claude',
  args: ['--print', '--model', 'sonnet'],
  systemPromptFlag: '--system-prompt',
  timeout: 120000,
});
const retry = new Retry({ maxAttempts: 2, backoff: 'exponential', timeout: 120000 });
const sm = new StateMachine();
const stream = new Stream({ transport: new JsonlTransport() });

// 1. Plan
const planner = new Planner({ provider, prompt: 'Your system prompt...' });
const steps = await retry.call(() => planner.plan(query));
// steps = [{id: 's1', action: '...', dependsOn: []}, {id: 's2', action: '...', dependsOn: ['s1']}]

// 2. Execute with wave parallelism
const stepResults = {};
const results = await runPlan(steps, async (step) => {
  const priorContext = (step.dependsOn || [])
    .filter(id => stepResults[id])
    .map(id => `[${id}]: ${stepResults[id]}`).join('\n');

  const loop = new Loop({ provider, maxRounds: 1, retry, stream });
  const result = await loop.run([{ role: 'user', content: `${step.action}\n${priorContext}` }]);
  if (result.error) throw new Error(result.error);  // ← MUST CHECK
  stepResults[step.id] = result.text;
  return result.text;
}, {
  stateMachine: sm,
  onWaveStart: (num, wave) => console.log(`[Wave ${num}]: ${wave.map(s => s.id).join(', ')}`),
  onStepStart: (step) => console.log(`→ ${step.id}: ${step.action}`),
  onStepDone: (step) => console.log(`✓ ${step.id} complete`),
  onStepFail: (step, err) => console.error(`✗ ${step.id}: ${err.message}`),
});
// results = [{id: 's1', status: 'done', result: '...'}, {id: 's2', status: 'done', result: '...'}]
```

### Recipe 2: Loop + CLIPipe (minimal single-shot LLM call)

```js
// From soar_agent.js:68-88 (SIMPLE path, v0.2.1)
const { Loop, Retry } = require('bare-agent');
const { CLIPipe } = require('bare-agent/providers');

const provider = new CLIPipe({
  command: 'claude',
  args: ['--print', '--model', 'sonnet'],
  systemPromptFlag: '--system-prompt',
  timeout: 120000,
});
const retry = new Retry({ maxAttempts: 2, backoff: 'exponential', timeout: 120000 });
const loop = new Loop({ provider, maxRounds: 1, retry });

const result = await loop.run([{ role: 'user', content: 'What is SOAR?' }]);
if (result.error) throw new Error(result.error);
console.log(result.text);
```

### Recipe 3: Stream + JsonlTransport (event forwarding)

```js
// From soar_agent.js:55 (v0.2.1 — was 3-line inline hack in v0.2.0)
const { Stream } = require('bare-agent');
const { JsonlTransport } = require('bare-agent/transports');

const stream = new Stream({ transport: new JsonlTransport() });

// Emit events — JsonlTransport writes JSON + newline to stdout, adds timestamps
stream.emit({ type: 'step:start', data: { id: 's1', action: 'Research topic' } });
// stdout: {"type":"step:start","data":{"id":"s1","action":"Research topic"},"ts":"2026-02-20T21:24:12.915Z"}

// Subscribe for in-process handling
stream.subscribe((event) => {
  if (event.type === 'step:fail') console.error(`Failed: ${event.data.id}`);
});
```

---

## Updated Verdict (Round 4 — v0.2.1)

bare-agent v0.2.1 is **production-ready** with **zero workarounds needed**.

**Framework completeness**: 9/10. All three gaps from v0.2.0 are fixed. The only remaining item is `Loop.run()` error-not-throw behavior (documented, manageable). Up from 8/10.

**Developer experience**: 8/10. The updated `bareagent.context.md` now includes recipes, gotchas, and component selection guide. This is a massive improvement — the three recipes alone would have saved ~45 minutes of the original integration. Up from 5/10.

**Unique value**: CLIPipe + runPlan together. No other lightweight framework offers "plan a DAG with an LLM, execute it in parallel waves via CLI pipe." That's the pitch.

**Ship list status**:
1. ~~`CLIPipe` `systemPromptFlag` option~~ — SHIPPED v0.2.1
2. ~~`runPlan` `onWaveStart` callback~~ — SHIPPED v0.2.1
3. ~~Export `JsonlTransport`~~ — SHIPPED v0.2.1
4. ~~Integration recipes in context.md~~ — SHIPPED (3 recipes + gotchas section)
5. Document `Loop.run()` error-not-throw behavior — SHIPPED (gotcha #8 in context.md)

**All 5 items shipped.** Nothing remaining on the adoption-blocking list.

### What changed in the consumer code (soar_agent.js)

| v0.2.0 | v0.2.1 | Lines saved |
|---|---|---|
| 30-line `makeProvider()` wrapper separating system/user messages | 6-line `makeProvider()` — just `new CLIPipe({ systemPromptFlag })` | -24 |
| 3-line inline transport `{ write(e) { ... } }` | `new JsonlTransport()` from `bare-agent/transports` | -2 (+ timestamps for free) |
| No wave visibility — consumer inferred from callback timing | `onWaveStart(num, steps)` → emits `wave:start` event → `[Wave 1: s1, s2]` in terminal | +5 (net new, but it's feature not plumbing) |

---

## v0.2.2 — Resilience Features

bare-agent v0.2.2 shipped four new capabilities: CircuitBreaker, Fallback provider, step-level retry in runPlan, and jitter on Retry. Plus typed error classes.

### What was applied to SOAR2

**1. `stepRetry` in `runPlan`** — applied, fixes real gap.

Previously, a transient CLI timeout killed a step permanently. That step's entire dependency chain auto-failed via `runPlan`'s propagation — which is correct behavior, but harsh when the failure was a 1-second network blip. Now:

```js
const planResults = await runPlan(steps, executeFn, {
  stepRetry: new Retry({ maxAttempts: 2, backoff: 'exponential', jitter: 'full' }),
  // ...callbacks
});
```

Each step gets 2 attempts before being marked failed. Zero code change to `executeFn` — `runPlan` wraps it automatically. This is exactly how framework-level retry should work: the consumer doesn't change, the framework handles it.

**2. `jitter: 'full'` on Retry** — applied, prevents thundering herd.

SOAR2 runs parallel wave steps (e.g., s1, s2, s3 in Wave 1) hitting the same CLI tool. Without jitter, if all three fail and retry, they retry at identical intervals — hammering the tool simultaneously. Full jitter randomizes delay within `[0, calculatedDelay]`:

```js
const retry = new Retry({ maxAttempts: 2, backoff: 'exponential', jitter: 'full', timeout: 120000 });
```

Applied to both the global `retry` (used by Planner, Loop) and the `stepRetry` in runPlan.

### What was NOT applied (and why)

**3. `CircuitBreaker` + `Fallback`** — skipped, not needed yet.

CircuitBreaker tracks failure counts across calls and opens the circuit after a threshold. This matters for:
- Long-running services making repeated LLM calls over minutes/hours
- Batch processing where you want to fail fast after N failures instead of retrying each one

SOAR2 is a single CLI invocation — one Node.js process per query, 3-5 LLM calls total, then exit. There's no persistent state to trip a circuit. If we ever make SOAR2 a long-running daemon (e.g., serving multiple queries), CircuitBreaker becomes essential.

`Fallback` provider needs a second provider to fall back to. SOAR2 uses one CLI tool (claude/cursor). Adding `--fallback-tool` support would be the trigger to wire Fallback in — it's a clean fit:

```js
// Future: if we add --fallback-tool
const cb = new CircuitBreaker({ threshold: 3, resetAfter: 30000 });
const provider = new Fallback([
  cb.wrapProvider(makeProvider('claude', model), 'claude'),
  cb.wrapProvider(makeProvider('cursor', model), 'cursor'),
], {
  onFallback: (err, from, to) => log(`Falling back from provider ${from} to ${to}: ${err.message}`),
});
```

**4. Typed errors** (`ProviderError`, `CircuitOpenError`, etc.) — skipped, CLIPipe doesn't emit them yet.

`CLIPipe` throws plain `Error` with string messages like `[CLIPipeProvider] timed out after 120000ms`. The typed error hierarchy exists (`ProviderError` with `.retryable`, `.status`) but CLIPipe hasn't adopted it. When it does, Retry could make smarter decisions:

```js
// Future: when CLIPipe throws ProviderError
catch (err) {
  if (err instanceof ProviderError && err.retryable) retry();
  else fail();
}
```

Currently all CLIPipe errors are retried equally. This is fine for SOAR2 (all failures are worth retrying — timeouts, spawn failures, empty output), but typed errors would matter for API providers where 400 (bad request, don't retry) differs from 429 (rate limited, do retry).

### Gap coverage update

The evaluation originally listed these gaps under "What SOAR2 loses":

| Gap | v0.2.0 | v0.2.2 |
|---|---|---|
| No circuit breakers | Not addressed | **Available** (`CircuitBreaker`) — not needed for single-run CLI, ready for daemon mode |
| No fallback providers | Not addressed | **Available** (`Fallback`) — needs `--fallback-tool` feature to be useful |
| Failed step kills branch | Steps failed permanently | **Fixed** (`stepRetry`) — transient failures auto-retry |
| No jitter on retry | Retries land simultaneously | **Fixed** (`jitter: 'full'`) — randomized delay |
| String-based error matching | `err.message.includes(...)` | **Available** (typed errors) — waiting for CLIPipe adoption |

---

## Honest Judgment — Component-Level Value Assessment

| Component | Value to me | Could I write it myself? | Would I get it right? |
|-----------|------------|-------------------------|----------------------|
| `runPlan` | **High** — the standout | 50+ lines, took 3 attempts in Round 1 | No. Dependency failure propagation, concurrent wave limiting, input validation — I missed all three in my custom version. |
| `CLIPipe` | **High** — unique concept | 40+ lines for spawn/pipe/timeout | Eventually, but the SIGTERM→SIGKILL grace period and empty-output detection are the kind of things you only add after hitting them in production. |
| `Planner` | **Medium** — convenient | 20 lines (prompt + JSON.parse) | The 20-line version works until the LLM wraps output in markdown fences or returns `{steps:[]}` instead of `[...]`. Planner handles both. |
| `Retry` | **Medium** — small but correct | 10 lines for basic retry | Basic retry yes. Exponential backoff with jitter, timeout per attempt, and clean integration with Loop — that's where hand-rolled versions diverge. |
| `Loop` | **Medium** — mixed | 15 lines for single-round | Yes for single-round. The think/act/observe multi-round with tool calling is harder. I only used single-round, so the value was marginal for my use case. |
| `StateMachine` | **Low** — used for debugging only | 15 lines | Yes. I used `onTransition` for stderr logging. Wouldn't use it in production for this use case. |
| `Stream` | **Low** — thin wrapper | 3 lines | Yes. `transport.write(event)` with a subscriber list. The transport pluggability is nice in theory but I used one transport. |

---

## Devil's Advocate — Why NOT Just Write It Yourself?

This is the hard question. My initial instinct was "I could write Planner in 20 lines, Stream in 3 lines, StateMachine in 15 lines — why import a library?" Here's why that instinct is wrong:

### The "I could write it in 20 lines" trap

**The 20-line version works on the happy path.** Then reality hits:

| What you write | What you discover you needed |
|---|---|
| `JSON.parse(llmOutput)` | LLM wraps output in ` ```json ``` `. Now you need fence stripping. LLM returns `{steps:[...]}` not `[...]`. Now you need unwrapping. Your 1-line parse is now 15 lines with 3 fallbacks. |
| `child_process.spawn()` with stdout collection | Process hangs forever. Now you need timeout. Timeout kills with SIGTERM but process ignores it. Now you need SIGKILL fallback. Process produces no output. Now you need empty-output detection. Your 5-line spawn is now 30 lines. |
| `Promise.all(steps.map(execute))` | Step 2 depends on step 1. Now you need dependency resolution. Step 1 fails — step 2 should auto-fail, not hang. Now you need failure propagation. Two steps have the same ID. Now you need input validation. Your 1-line parallel executor is now 50 lines. |
| `if (error) retry()` | First retry fires immediately, hammering a rate-limited API. Now you need backoff. Backoff is predictable, causing thundering herd. Now you need jitter. Your 3-line retry is now 15 lines. |

**Each of these is a real bug I either hit or would have hit.** The 20-line version is a prototype. The 50-line version is production code. bare-agent gives you the 50-line version in a tested, maintained package.

### The real cost of "rolling your own"

It's not the initial writing — it's the **ongoing maintenance burden**:

1. **You wrote 200 lines of orchestration plumbing.** Now you need to maintain 200 lines of orchestration plumbing. Every edge case is your bug to find.
2. **You don't write tests for plumbing.** Nobody writes tests for their hand-rolled retry logic or their custom state machine. bare-agent's tests catch regressions you never would.
3. **Context switching cost.** When debugging a failed plan execution, you're now debugging both your domain logic AND your plumbing simultaneously. With bare-agent, if `runPlan` works (and it does), the bug is in your `executeFn` — always.
4. **Knowledge transfer.** A new developer reads `runPlan(steps, fn, { onWaveStart })` and knows what it does. They read your 50-line custom `executeWaves()` and need to understand your specific implementation.

### The LangChain comparison — why 1500 lines matters

The real competitor isn't "write it yourself" — it's heavyweight frameworks:

| | bare-agent | LangChain | LlamaIndex | CrewAI |
|---|---|---|---|---|
| Total code | ~1500 lines | ~50,000+ lines | ~40,000+ lines | ~15,000+ lines |
| Dependencies | 0 required | 20+ packages | 15+ packages | 10+ packages |
| Time to read entire source | 30 minutes | Never | Never | A few hours |
| Understand what happens on LLM call | Read `CLIPipe._spawn()` — 40 lines | Good luck tracing through 8 abstraction layers | Similar | Somewhat traceable |
| Vendor lock-in | None — swap providers freely | Deeply embedded | Deeply embedded | Moderate |
| "Magic" behavior | None | Significant | Significant | Some |
| Debug a failed step | Read the error, check your `executeFn` | Which of the 12 middleware layers failed? | Which retriever/synthesizer/callback failed? | Which agent/task/crew boundary failed? |

**bare-agent occupies the only empty quadrant**: lightweight enough to understand completely, complete enough to not reinvent wheels. Everything else is either "do it yourself" (left) or "massive framework" (right). There's nothing in the middle.

The honest comparison:
- **LangChain** solves problems you don't have yet, and creates problems you didn't expect. You import it for one feature and get 50,000 lines of opinions about how your code should work.
- **bare-agent** solves the 5 problems every agent needs (LLM call, plan, execute, retry, observe) and stays out of the way. You import `runPlan` and get `runPlan`. Not a philosophy.

### When you SHOULD roll your own

bare-agent isn't the right choice when:
- You need exactly one component (e.g., just retry). Copy the pattern, don't add a dependency.
- You need deep customization of the LLM call loop (streaming, function calling with complex routing). `Loop` is opinionated about think/act/observe — if your loop is fundamentally different, you'll fight it.
- Your language isn't JavaScript. bare-agent is Node.js only. Python has its own ecosystem.

### When you SHOULD use bare-agent

- You're building a CLI agent or tool that pipes to LLM CLI tools → `CLIPipe` is the only game in town
- You need plan-then-execute with dependency-aware parallelism → `runPlan` saves real bugs
- You want to understand your entire stack → 1500 lines, 30 minutes to read
- You're an AI agent building another AI agent → the context.md + recipes format is designed for this

---

## Final Verdict (Round 5 — v0.2.2)

**bare-agent is the right tool at the right size.** It's not a framework — it's a toolkit. The distinction matters: a framework tells you how to structure your application; a toolkit gives you components to use however you want.

**Framework completeness**: 9.5/10. v0.2.1 eliminated all workarounds. v0.2.2 adds resilience primitives (CircuitBreaker, Fallback, stepRetry, jitter, typed errors) that close the gap between "works in demos" and "works in production." The 0.5 deduction is for CLIPipe not yet throwing typed errors — when it does, the error hierarchy becomes actionable.

**Developer experience**: 8/10. The updated context.md with recipes + gotchas is what every library should ship. The component selection guide answers "what do I use for X?" immediately.

**Unique positioning**: The only lightweight, zero-dependency agent orchestration library that treats CLI tools as first-class LLM providers. This matters because:
- Most developers already have `claude` or `cursor` installed
- API keys are a friction point for adoption
- CLI tools handle auth, context, and capabilities — bare-agent just pipes to them

**The 80/20 argument**: `runPlan` + `CLIPipe` deliver 80% of the value in ~300 lines. The other components (Loop, Planner, StateMachine, Stream, Retry, Scheduler, Checkpoint, Memory, CircuitBreaker, Fallback) fill out the toolkit so you never need to leave the ecosystem for common patterns. That's the right ratio — two killer features, supporting components that earn their import when you need them.

**Version progression** (from this integration):

| Version | Status | Key change |
|---------|--------|-----------|
| v0.2.0 | Usable with 3 workarounds | Core components work, composability proven |
| v0.2.1 | Production-ready, zero workarounds | `systemPromptFlag`, `onWaveStart`, transports export |
| v0.2.2 | Production-hardened | `stepRetry`, `jitter`, CircuitBreaker, Fallback, typed errors |

**What I'd tell another developer**: "Use it. Read the source once (30 min), use the recipes, check the gotchas. You'll have a working agent pipeline in under an hour. The alternative is either writing 200 lines of plumbing that you'll debug for a week, or importing LangChain and spending a week understanding the abstractions."
