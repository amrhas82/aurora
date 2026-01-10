# AURORA CLI - Issues & Testing Tracker

**Date**: December 24, 2025
**Status**: TESTING PHASE - Collecting issues before batch fixes

## Testing Strategy

1. **Discovery Phase**: Test all CLI functionality and document every issue
2. **Categorization**: Group issues by severity and component
3. **Batch Fixes**: Fix related issues together, not one-by-one
4. **Verification**: Test fixes comprehensively before moving to next batch

---

## Known Issues from Testing

### CRITICAL - Indexing Completely Broken

**Component**: `aurora_cli.memory_manager.MemoryManager`

**Issues Found**:
1. ✅ FIXED: `EmbeddingProvider.embed()` doesn't exist → should be `.embed_chunk()`
2. ✅ FIXED: `chunk.chunk_id` doesn't exist → should be `chunk.id`
3. ❌ OPEN: `memory_store.add_chunk()` doesn't exist → should use `save_chunk(chunk)`
   - Store API: `save_chunk(chunk: Chunk)` - takes Chunk object
   - Current code: Calls `add_chunk(chunk_id, content, embedding, metadata)` with params
   - **Fix needed**: Refactor to set `chunk.embeddings` and call `memory_store.save_chunk(chunk)`

**Test Case**:
```bash
# Remove old DB
rm -f aurora.db

# Try to index packages
PYTHONPATH=/home/hamr/PycharmProjects/aurora/packages/cli/src:$PYTHONPATH python3 -c "
from pathlib import Path
from aurora_core.store import SQLiteStore
from aurora_cli.memory_manager import MemoryManager

db_path = Path.cwd() / 'aurora.db'
memory_store = SQLiteStore(str(db_path))
manager = MemoryManager(memory_store)

stats = manager.index_path(Path('packages'))
print(f'Indexed: {stats.files_indexed} files, {stats.chunks_created} chunks')
"
```

**Current Result**: `AttributeError: 'SQLiteStore' object has no attribute 'add_chunk'`
**Expected Result**: Should index ~85 Python files successfully

---

### CRITICAL - MCP Integration Missing

**Component**: MCP server / API key alternatives

**User Report**:
> "we also don't have mcp and that's a big issue without api keys"

**Questions to Clarify**:
1. What MCP functionality do you need?
2. Were you expecting to use AURORA through MCP without API keys?
3. Is this about:
   - a. Creating an MCP server for AURORA?
   - b. Using an existing MCP server for embeddings/LLM?
   - c. Alternative to Anthropic API?

**Current State**:
- AURORA requires ANTHROPIC_API_KEY for LLM operations
- No MCP server implementation exists
- No alternative embedding providers configured

**Needed Info**:
- [ ] What MCP use case do you have in mind?
- [ ] Should we create an MCP server for AURORA?
- [ ] Do you want to use a different LLM provider via MCP?

---

## Untested Components

### CLI Commands

**Status**: Need systematic testing of all commands

- [ ] `aur --help` - Does it show all commands?
- [ ] `aur init` - Does it create config correctly?
- [ ] `aur init` (indexing) - Does it index files? (KNOWN BROKEN)
- [ ] `aur mem index .` - Does it work? (KNOWN BROKEN)
- [ ] `aur mem search "query"` - Does search work?
- [ ] `aur mem stats` - Does it show stats?
- [ ] `aur query "question"` - Does it work without memory?
- [ ] `aur query "question"` - Does it work with memory?
- [ ] `aur query --dry-run "question"` - Does dry-run work?
- [ ] `aur query --force-aurora "question"` - Does force mode work?
- [ ] `aur query --force-direct "question"` - Does direct mode work?
- [ ] `aur query --show-reasoning "question"` - Does reasoning display work?
- [ ] `aur --headless prompt.md` - Does headless mode work?

### Configuration System

**Status**: Need to verify precedence and validation

- [ ] Does config file get created with correct permissions (0600)?
- [ ] Does API key precedence work? (CLI > ENV > Config > None)
- [ ] Does config validation catch invalid values?
- [ ] Can users override config with env vars?

### Error Handling

**Status**: Need to verify error messages are helpful

- [ ] Missing API key error - Is message clear?
- [ ] Invalid API key error - Is message clear?
- [ ] Database locked error - Does retry work?
- [ ] Permission error - Is message actionable?
- [ ] Network error - Is message helpful?

---

## Testing Plan

### Phase 1: Discovery (CURRENT)
- [ ] Create this issues document
- [ ] Get user feedback on priorities
- [ ] Understand MCP requirements
- [ ] Test all CLI commands systematically
- [ ] Document every issue found

### Phase 2: Categorization
- [ ] Group issues by component
- [ ] Assign severity (Critical/High/Medium/Low)
- [ ] Identify dependencies between fixes
- [ ] Create fix batches

### Phase 3: Batch Fixes
- [ ] Batch 1: Indexing (memory_manager.py fixes)
- [ ] Batch 2: MCP integration (TBD based on requirements)
- [ ] Batch 3: CLI UX improvements
- [ ] Batch 4: Error handling improvements

### Phase 4: Verification
- [ ] Test each batch comprehensively
- [ ] Update smoke tests
- [ ] Create integration tests
- [ ] Document what works

---

## User Feedback Needed

### Questions:
1. **MCP**: What MCP functionality do you need? Should we build an MCP server?
2. **Priority**: What's most important to fix first?
3. **API Keys**: Do you have access to Anthropic API, or need alternatives?
4. **Use Case**: What are you trying to accomplish with AURORA?

### Testing Help:
- Which commands should we test together?
- What workflows are most important to you?
- Any specific error messages you've seen?

---

## Notes

- **Approach Change**: Stop fixing issues one-by-one, collect them all first
- **Test Coverage**: Current tests (159 passing) didn't catch these API mismatches
- **Root Cause**: Tests mock the Store, so real SQLiteStore issues weren't detected
- **Need**: Integration tests that use real SQLiteStore, not mocks
