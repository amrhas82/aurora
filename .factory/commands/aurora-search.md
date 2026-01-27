---
name: Aurora: Search
description: Search indexed code ["query" --limit N --type function]
argument-hint: search query
category: Aurora
tags: [aurora, search, memory]
---
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.

**Usage**
Run `aur mem search "<query>"` to search indexed code.

**Argument Parsing**
User can provide search terms with optional flags in natural order:
- `/aur:search bm25 limit 5` → `aur mem search "bm25" --limit 5`
- `/aur:search "exact phrase" type function` → `aur mem search "exact phrase" --type function`
- `/aur:search authentication` → `aur mem search "authentication"`

Parse intelligently: detect `limit N`, `type X` as flags, rest as query terms.

**Examples**
```bash
# Basic search
aur mem search "authentication handler"

# Search with type filter
aur mem search "validate" --type function

# Search with more results
aur mem search "config" --limit 20

# Natural argument order
aur mem search "bm25" --limit 5
```

**Reference**
- Returns file paths and line numbers
- Uses hybrid BM25 + embedding search
- Shows match scores
- Type filters: function, class, module

**Output Format (MANDATORY - NEVER DEVIATE)**

Every response MUST follow this exact structure:

1. Execute `aur mem search` with parsed args
2. Display the **FULL TABLE** - never collapse with "... +N lines"
3. Create a simplified table showing ALL results (not just top 3):
   ```
   #  | File:Line           | Type | Name              | Score
   ---|---------------------|------|-------------------|------
   1  | memory.py:131       | code | MemoryManager     | 0.81
   2  | tools.py:789        | code | _handle_record    | 0.79
   3  | logs/query.md:1     | docs | Execution Summary | 0.58
   ...
   ```
4. Add exactly 2 sentences of guidance on where to look:
   - Sentence 1: Identify the most relevant result(s) and why
   - Sentence 2: Suggest what other results might provide useful context
5. Single line: `Next: /aur:get N`

NO additional explanations or questions beyond these 2 sentences.

$ARGUMENTS
<!-- AURORA:END -->
