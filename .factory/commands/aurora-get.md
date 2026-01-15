---
name: Aurora: Get
description: Retrieve search result [N] from last search
argument-hint: chunk index number
category: Aurora
tags: [aurora, search, memory]
---
<!-- AURORA:START -->
**Guardrails**
- Favor straightforward, minimal implementations first and add complexity only when requested or clearly required.
- Keep changes tightly scoped to the requested outcome.
- Refer to `.aurora/AGENTS.md` if you need additional Aurora conventions or clarifications.

**Usage**
Run `aur mem get <N>` to retrieve the full content of search result N from the last search.

**Examples**
```bash
# Get first result from last search
aur mem get 1

# Get third result
aur mem get 3
```

**Note:** The output includes detailed score breakdown (Hybrid, BM25, Semantic, Activation). For access count details, see the Activation score.

**Workflow**
1. Run `/aur:search <query>` to search
2. Review the numbered results
3. Run `/aur:get <N>` to see full content of result N

**Output**
- Full code content (not truncated)
- File path and line numbers
- Detailed score breakdown (Hybrid, BM25, Semantic, Activation)
- Syntax highlighting

**Notes**
- Results cached for 10 minutes after search
- Index is 1-based (first result = 1)
- Returns error if no previous search or index out of range

**Output Format (MANDATORY - NEVER DEVIATE)**

Every response MUST follow this exact structure:

1. Execute `aur mem get N`
2. Display the content box
3. One sentence: what this is and what it does (include file:line reference from the header)
4. If not code implementation: note the file type (e.g., "log file", "docs", "config")
5. Optional: If relevant to other search results, add: "See also: result #X (relationship)"

NO additional explanations, suggestions, or questions.

$ARGUMENTS
<!-- AURORA:END -->
