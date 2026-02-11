# Long-Term Memory Architecture

**Status:** DESIGN
**Updated:** 2026-02-11

---

## Problem

AI dev agents forget everything between sessions. Current mitigations (CLAUDE.md, .aurora/config) are manually maintained and project-scoped. Cross-project preferences, past decisions, and learned lessons are lost unless the user re-states them.

## Design Principles

1. **Three independent actions** — `/stash`, `/friction`, `/remember` — no coupling
2. **All project-local** — memory lives in `.claude/`, travels with the project
3. **No session-end hook** — there is no reliable session boundary
4. **No per-turn extraction** — 90% of dev turns are mechanical noise
5. **Curation > retrieval** — store less, store better, load everything
6. **No vector store** — the curated set is small enough to load as a preamble
7. **Portable** — plain markdown files, works with any agent
8. **JS runtime** — friction script in Node.js (guaranteed available with Claude Code)

## Architecture

```
ACTIONS (independent)          STORAGE (project-local)        RETRIEVAL
─────────────────────          ────────────────────────       ─────────

/stash                         .claude/stash/*.md
  (capture session,              (raw material,
   unchanged from today)          accumulates)
                                      │
/friction <path>                      │
  (analyze behavior,           .claude/friction/
   JS script, produces           antigen_review.md
   antigen_review)                    │
                                      │
/remember ────────────────────────────┤
  (consolidate all sources)           │
                                      ▼
                               .claude/memory/
                               ├── facts.md         ──┐
                               ├── episodes.md         ├──→ CLAUDE.md
                               └── preferences.md   ──┘    (project preamble)
```

### Key Separation

| Action | Job | Weight | Frequency |
|---|---|---|---|
| `/stash` | Capture session context | Light (haiku, one file) | Multiple times/day |
| `/friction` | Analyze behavioral signals | Medium (JS script) | Every 1-2 weeks |
| `/remember` | Consolidate → CLAUDE.md | Heavy (reads all, multiple LLM calls) | Weekly or on-demand |

Each action is independent. `/stash` and `/friction` produce raw material. `/remember` consumes it.

---

## User Types

Two paths to the same memory system:

| | Liteagents user | Aurora user |
|---|---|---|
| Capture sessions | `/stash` (skill/command) | `/stash` (same) |
| Analyze behavior | `/friction` (command, runs `friction.js`) | `aur friction` (CLI, runs `friction.py`) |
| Consolidate memory | `/remember` (command) | `/remember` (same) |
| Friction output | `.claude/friction/` | `.aurora/friction/` (legacy) or `.claude/friction/` |

Both produce the same output format. `/remember` checks both locations.

### Friction Script: JS vs Python

| | `friction.js` (liteagents) | `friction.py` (aurora) |
|---|---|---|
| Runtime | Node.js (guaranteed with Claude Code) | Python (may not be installed) |
| Invoked by | `/friction` command | `aur friction` CLI |
| Location | `.claude/scripts/friction.js` or bundled | `scripts/friction.py` |
| Output format | Same: `.claude/friction/` | Same: `.aurora/friction/` |
| Logic | Same 14 signals, same weights, same scoring | Original implementation |

The JS version is a port of the ~2000-line Python pipeline (`friction_analyze.py` + `antigen_extract.py`). No ML, no heavy deps — just file I/O, regex, JSON, and markdown generation. All doable in Node stdlib (`fs`, `path`, `readline`).

---

## Actions

### /stash — Capture session (unchanged)

What it does today. No changes needed.

```
1. User runs /stash at natural breakpoints
2. Haiku summarizes session context
3. Writes .claude/stash/<name>.md
4. Done. No extraction, no consolidation.
```

Stash files accumulate as raw material for `/remember`.

### /friction — Analyze behavior

Runs friction analysis via Node.js script. Takes session path as required argument.

```
1. User runs /friction <sessions-path>
   e.g. /friction ~/.claude/projects/-home-hamr-PycharmProjects-aurora/

2. Script (friction.js) analyzes Claude session JSONL files:
   - Reads session files from <path>
   - Detects 14 signal types (same as friction.py)
   - Scores sessions, identifies BAD/FRICTION/ROUGH/OK
   - Extracts antigen candidates from BAD sessions

3. Output writes to .claude/friction/ (project-local):
   - friction_analysis.json    per-session breakdown
   - friction_summary.json     aggregate stats + verdict
   - friction_raw.jsonl        raw signals
   - antigen_candidates.json   extracted patterns
   - antigen_review.md         human-readable review

4. Done. No memory consolidation yet.
```

### /remember — Consolidate into CLAUDE.md memory section

The heavy lift. Reads all sources, extracts what matters, updates project memory.

```
/remember pseudocode:

  # 1. Gather sources
  stashes = glob(".claude/stash/*.md")

  friction = find_first([
      ".claude/friction/antigen_review.md",    # liteagents output
      ".aurora/friction/antigen_review.md"     # aurora output (legacy)
  ])

  existing_facts = read(".claude/memory/facts.md")
  existing_episodes = read(".claude/memory/episodes.md")
  existing_prefs = read(".claude/memory/preferences.md")
  processed = read(".claude/memory/.processed")

  # 2. Extract facts + episodes from unprocessed stashes
  unprocessed = filter(stashes, not_in=processed)

  for stash in unprocessed:
      extraction = haiku.call(
          system = """Extract from this session stash:

          FACTS (atomic, one-line):
          - Stable preferences (tools, languages, style)
          - Decisions made ("chose X over Y because Z")
          - Corrections ("no, I meant...", "don't do that")
          - Explicit "remember this"

          EPISODE (3-5 bullet narrative):
          - What was the problem/goal?
          - What approaches were tried?
          - What was the outcome and lesson?

          SKIP: code details, file paths, errors, mechanical steps,
                LLM responses, one-off details""",
          content = stash.content
      )

      new_facts += extraction.facts
      new_episodes += extraction.episode

  # 3. Deduplicate facts against existing
  facts = haiku.call(
      system = """Merge these new facts with existing facts.
      Rules:
      - If a new fact UPDATES an old one, keep the new version
      - If a new fact CONTRADICTS an old one, keep the new version
      - If a new fact is already captured, skip it
      - Keep facts atomic, one line each""",
      existing = existing_facts,
      new = new_facts
  )
  write(".claude/memory/facts.md", facts)

  # 4. Append episodes (no dedup, append-only)
  append(".claude/memory/episodes.md", new_episodes)

  # 5. Distill friction into preferences (if friction output exists)
  if friction.exists:
      prefs = haiku.call(
          system = """From this friction/antigen review, extract BEHAVIORAL
          preferences. These are patterns the user DEMONSTRATED, not stated.

          Format each as:
          ## High Confidence
          - [pattern] (evidence: [count] observations)

          ## Medium Confidence
          - [pattern] (evidence: [count] observations)

          Promote existing medium → high if new evidence supports it.
          Demote if contradicted by recent behavior.""",
          friction_review = friction.content,
          existing_prefs = existing_prefs
      )
      write(".claude/memory/preferences.md", prefs)

  # 6. Generate memory section for CLAUDE.md
  memory_section = []
  memory_section += "<!-- MEMORY:START -->\n"
  memory_section += "# Project Memory (auto-generated by /remember)\n\n"
  memory_section += "## Facts\n"
  memory_section += read(".claude/memory/facts.md")
  memory_section += "\n## Preferences\n"
  memory_section += read_section(".claude/memory/preferences.md", "High Confidence")
  memory_section += "\n## Recent Episodes\n"
  memory_section += last_n_entries(".claude/memory/episodes.md", n=5)
  memory_section += "\n<!-- MEMORY:END -->"

  # Insert/replace in CLAUDE.md between MEMORY markers
  update_section("CLAUDE.md", "MEMORY:START", "MEMORY:END", memory_section)

  # 7. Mark stashes as processed
  append(".claude/memory/.processed", [s.path for s in unprocessed])

  # 8. Report
  print(f"Processed {len(unprocessed)} stashes")
  print(f"Facts: {count(facts)} ({count(new_facts)} new)")
  print(f"Episodes: {count(episodes)} ({count(new_episodes)} new)")
  print(f"Preferences: {count_high} high, {count_med} medium")
  print(f"CLAUDE.md memory section updated")
```

---

## Three Storage Files

### facts.md — What the user said

Atomic, one-line facts extracted from stash sessions. Deduplicated. Updated facts replace old versions.

```markdown
# Facts
- timezone: EST
- python projects: always use hatchling
- commit style: conventional commits, no co-author line
- preferred test runner: pytest with -x flag
- switched from setuptools to hatchling for cli package (2026-01)
```

**Source:** `/remember` extracts from stash files
**Content:** preferences stated, decisions made, corrections, explicit "remember this"
**Skips:** code details, errors, mechanical steps, LLM responses

### episodes.md — What happened and why

Timestamped narrative entries. Append-only. Records reasoning and trade-offs.

```markdown
## 2026-02-03 aurora/lsp-hook
- tried text fallback when LSP cold — caused noise from keyword extraction
- root cause: symbol extraction from arbitrary lines picks up keywords not symbols
- solution: only show count+risk when LSP works, text fallback only for 0 refs
- lesson: don't mix search strategies in same code path

## 2026-01-28 aurora/friction-pipeline
- explored 3 approaches to friction scoring: flat weights, decay, tier-based
- picked tier-based because it maps to confidence levels naturally
- key insight: gold signals (user_intervention) are 95% predictive alone
```

**Source:** `/remember` extracts from stash files
**Content:** debugging stories, architectural decisions, trade-off reasoning

### preferences.md — What the user does (not says)

Behavioral patterns inferred from friction analysis. Confidence-scored.

```markdown
# Preferences (behavioral, from friction analysis)

## High Confidence (loaded into CLAUDE.md)
- never add docstrings unless asked (rejected 12/15 times)
- prefer editing existing files over creating new (rejected new file 8/10)
- keep commit messages short, one line (rewrote 4/7 verbose ones)

## Medium Confidence (observing, not loaded)
- may prefer tabs over spaces (2 observations)

## Low Confidence (needs more data)
- possible preference for click over argparse (1 observation)
```

**Source:** `/remember` distills from friction output
**Promotion:** low → medium at 3 obs, medium → high at 5+ obs

---

## Retrieval: CLAUDE.md Project Preamble

No search. No vector store. No retrieval problem.

Memory is injected into the project's `CLAUDE.md` as a managed section (between `<!-- MEMORY:START -->` and `<!-- MEMORY:END -->` markers). Claude loads `CLAUDE.md` automatically every session.

### What Gets Loaded

```markdown
<!-- MEMORY:START -->
# Project Memory (auto-generated by /remember)

## Facts
- timezone: EST
- python: hatchling, pytest -x, make
- commit: conventional, no co-author

## Preferences
- never add docstrings unless asked
- prefer editing existing files over creating new
- keep commit messages short

## Recent Episodes
### 2026-02-03 aurora/lsp-hook
- tried text fallback when LSP cold — noise
- lesson: don't mix search strategies
<!-- MEMORY:END -->
```

### Why This Works

- **facts.md** — deduplicated, atomic, ~50-100 lines
- **preferences.md [high]** — only promoted patterns, ~10-20 lines
- **episodes.md** — only last 5 entries, ~25 lines
- **Total in CLAUDE.md:** ~100-150 lines, well within limits
- **No separate MEMORY.md** — everything in the file Claude already loads

---

## Why Not Per-Turn Extraction?

The Reddit article (RedisVL approach) runs an LLM on every turn to decide "is this worth remembering?" This works for chatbots where most turns are conversational.

Dev sessions are different:
- "Edit line 42 of foo.py" — not memorable
- "Run pytest" — not memorable
- 90%+ of turns are mechanical tool invocations

Per-turn extraction burns an LLM call per turn to store nothing.

## Why Not Session-End Hooks?

There is no reliable "session end" event in Claude Code:
- `/clear` — new session, no hook fires
- Close terminal — process killed, no hook
- Idle for hours — no timeout event

The only reliable triggers are explicit: `/stash`, `/friction`, `/remember`.

## Why Not Global Memory?

- Project-local memory moves with the project (git, clone, share)
- Cross-project preferences are rare (~15 lines) and stable
- Cross-project preferences belong in `~/.claude/MEMORY.md` (manually maintained, tiny)
- Project-specific context is 90% of what matters
- No "which project does this fact belong to?" problem

---

## Workflow

```
Day-to-day:
  /stash, /stash, /stash              accumulate raw material
  (natural breakpoints: feature done, bug solved, decision made)

Every 1-2 weeks:
  /friction <sessions-path>           analyze behavioral patterns
  (or: aur friction for aurora users)

When ready:
  /remember                           consolidate → CLAUDE.md
  (reads stashes + friction, extracts, dedupes, injects into CLAUDE.md)
```

Three independent actions. No dependencies between them. One output.

---

## File Locations

```
.claude/                          # All project-local
├── stash/                        # Raw session captures
│   ├── lsp-poc-complete.md
│   ├── headless-removal.md
│   └── ...
├── friction/                     # Friction analysis output
│   ├── friction_analysis.json
│   ├── friction_summary.json
│   ├── friction_raw.jsonl
│   ├── antigen_candidates.json
│   └── antigen_review.md
├── memory/                       # Consolidated memory
│   ├── facts.md
│   ├── episodes.md
│   ├── preferences.md
│   └── .processed
└── commands/
    ├── remember.md               # /remember command
    └── friction.md               # /friction command

CLAUDE.md                         # Project preamble (has MEMORY section)

~/.claude/MEMORY.md               # Global cross-project prefs (tiny, manual)
```

---

## Friction Script: JS Port

The `/friction` command runs `friction.js` — a Node.js port of the existing Python pipeline (~2000 lines across `friction_analyze.py` + `antigen_extract.py`).

### Why JS

- Node.js is guaranteed available (Claude Code requires it)
- Python is NOT guaranteed (Windows, minimal Linux)
- The script uses only: file I/O, regex, JSON, string matching
- No ML, no heavy deps — trivial port to Node stdlib

### Script Structure

```
.claude/scripts/
├── friction.js               # Main entry: analyze + extract
└── friction_config.json      # Signal weights (same as existing)
```

Or bundled as a single `friction.js` with embedded config.

### What It Does

```
Input:  Session JSONL files from <sessions-path>
Output: .claude/friction/ (analysis, summary, raw signals, antigens, review)

1. Read session JSONL files (fs.readFileSync, readline)
2. Extract 14 signal types per turn (regex, string match)
3. Score sessions (weighted accumulation, same config)
4. Classify quality (BAD/FRICTION/ROUGH/OK)
5. Aggregate stats (daily trends, best/worst)
6. Extract antigen candidates from BAD sessions
7. Write all output files
```

### Signals (same as Python, same weights)

| Signal | Weight | Detection |
|---|---|---|
| `user_intervention` | 10 | `/stash` in user message |
| `session_abandoned` | 10 | High friction at end, no resolution |
| `false_success` | 8 | LLM claimed success but tool failed |
| `no_resolution` | 8 | Errors without subsequent success |
| `interrupt_cascade` | 5 | Multiple ESC/Ctrl+C within 60s |
| `tool_loop` | 6 | Same tool called 3+ times identically |
| `rapid_exit` | 6 | <3 turns, ends with error |
| `user_curse` | 5 | Profanity detected |
| `request_interrupted` | 2.5 | User hit ESC/Ctrl+C |
| `exit_error` | 1 | Command failed (non-zero exit) |
| `repeated_question` | 1 | Same question asked twice |
| `long_silence` | 0.5 | >10 min gap |
| `user_negation` | 0.5 | "no", "didn't work" |
| `compaction` | 0.5 | Context overflow |

---

## Comparison to Alternatives

### vs. RedisVL per-turn approach (Reddit article)
- They: LLM on every turn, vector store, semantic search at query time
- We: LLM on `/remember` only, markdown files, full preamble load
- Why: dev sessions are 90% noise; their key insight (curate at write, not read) is correct but applied differently

### vs. Claude's built-in MEMORY.md
- We use CLAUDE.md (project-local) for project memory, MEMORY.md (global) for cross-project prefs
- Instead of manually editing, we generate from structured sources

### vs. Raw vector search over chat history
- Vector search can't judge value ("should this be stored?")
- Small curated set loaded fully beats large raw set searched imprecisely

---

## Open Questions

1. **Friction JS bundling** — single file with embedded config, or separate `friction.js` + `friction_config.json`?
2. **Episode pruning** — last N entries? Age-based? Or keep all and only load recent 5 into CLAUDE.md?
3. **CLAUDE.md section size** — if memory grows beyond ~150 lines, should `/remember` compress older facts?
4. **Stash gitignore** — should `.claude/stash/` and `.claude/memory/` be git-tracked or gitignored?
5. **Cross-project prefs** — keep `~/.claude/MEMORY.md` manual, or have `/remember` detect cross-project patterns?

---

## Related

- [FRICTION_DETECTION.md](../FRICTION_DETECTION.md) — friction pipeline (Python version, aurora users)
- [MEM_INDEXING.md](MEM_INDEXING.md) — code memory indexing (separate system)
- [ACTR_ACTIVATION.md](ACTR_ACTIVATION.md) — activation scoring (could inform episode relevance)
