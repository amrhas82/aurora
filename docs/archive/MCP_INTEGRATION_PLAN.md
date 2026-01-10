# AURORA MCP Integration Plan

**Date**: December 24, 2025
**Purpose**: Enable AURORA to work with Claude via MCP (Model Context Protocol) instead of requiring direct API keys

---

## Problem Statement

**Current Limitation**:
- AURORA requires `ANTHROPIC_API_KEY` environment variable
- Users must have paid Anthropic API account
- Cannot use Claude Pro subscription (web-only)
- Cannot leverage existing MCP servers

**User Feedback**:
> "we don't have mcp and that's a big issue without api keys"

---

## What is MCP (Model Context Protocol)?

MCP is Anthropic's protocol that allows applications to:
1. **Expose tools** to Claude via standardized server interface
2. **Provide context** (files, databases, APIs) to Claude
3. **Enable integrations** without direct API access

### MCP Architecture:
```
┌─────────────┐      MCP Protocol      ┌──────────────┐
│ Claude.app  │◄────────────────────────┤ MCP Server   │
│ (Desktop)   │                         │ (Your code)  │
└─────────────┘                         └──────────────┘
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │   Resources  │
                                        │  (AURORA DB) │
                                        └──────────────┘
```

**Key Point**: MCP runs in Claude Desktop app, giving Claude access to your tools/data WITHOUT you needing API keys.

---

## Two Possible MCP Approaches for AURORA

### Approach A: AURORA as MCP Server (RECOMMENDED)

**Concept**: Create an MCP server that exposes AURORA's capabilities as tools for Claude Desktop

```python
# Example MCP server for AURORA
class AuroraMCPServer:
    """MCP server exposing AURORA memory and search capabilities."""

    @mcp_tool()
    def search_codebase(self, query: str, limit: int = 10) -> list[dict]:
        """Search indexed codebase using AURORA's hybrid retrieval."""
        # Use MemoryManager.search()
        pass

    @mcp_tool()
    def index_directory(self, path: str) -> dict:
        """Index a directory into AURORA memory."""
        # Use MemoryManager.index_path()
        pass

    @mcp_tool()
    def get_memory_stats(self) -> dict:
        """Get statistics about indexed memory."""
        # Use MemoryManager.get_stats()
        pass

    @mcp_resource()
    def get_code_context(self, file_path: str) -> str:
        """Provide code context from indexed files."""
        pass
```

**Benefits**:
- ✓ Works with Claude Desktop (no API key needed)
- ✓ Leverages AURORA's memory/search strengths
- ✓ Users can chat with Claude about their indexed codebase
- ✓ Natural integration with Claude's workflow

**User Experience**:
```
User in Claude Desktop:
> "Search my codebase for authentication code"

Claude calls: search_codebase("authentication")
→ AURORA returns relevant code chunks
Claude responds with context-aware answer
```

**Implementation**: Medium complexity (1-2 days)

---

### Approach B: AURORA Uses External MCP for LLM

**Concept**: AURORA calls Claude via MCP client instead of Anthropic API

```python
# Instead of:
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
response = client.messages.create(...)

# Use MCP client:
mcp_client = MCPClient("claude-mcp-server")
response = mcp_client.call_tool("chat", {"prompt": "..."})
```

**Problem**: This doesn't actually solve the API key issue because:
- MCP servers typically still need API keys internally
- MCP is for tools/resources, not for being an LLM provider
- Would be going against MCP's intended use

**Recommendation**: DON'T DO THIS - Use Approach A instead

---

## Recommended Implementation: AURORA MCP Server

### Phase 1: Core MCP Server (MVP)

**Goal**: Let Claude Desktop users search their indexed AURORA codebase

**Features**:
1. **Tool**: `aurora_search` - Search indexed code
2. **Tool**: `aurora_index` - Index a directory
3. **Tool**: `aurora_stats` - Get memory statistics
4. **Resource**: `aurora://file/{path}` - Access indexed file content

**File Structure**:
```
packages/mcp/
├── pyproject.toml
├── src/aurora_mcp/
│   ├── __init__.py
│   ├── server.py         # Main MCP server
│   ├── tools.py          # Tool implementations
│   └── resources.py      # Resource providers
└── tests/
    └── test_server.py
```

**Dependencies**:
```toml
[dependencies]
mcp = "^0.1.0"  # Anthropic's MCP SDK
aurora-core = "*"
aurora-context-code = "*"
aurora-cli = "*"
```

**Installation**:
```bash
# Install AURORA MCP server
pip install aurora-mcp

# Configure in Claude Desktop settings
# ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "aurora": {
      "command": "aurora-mcp",
      "args": ["--db-path", "/path/to/aurora.db"]
    }
  }
}
```

**User Workflow**:
```bash
# 1. Index your codebase (one-time setup)
aur mem index ~/my-project

# 2. Start Claude Desktop (MCP server auto-starts)

# 3. Chat with Claude:
User: "Search my project for authentication code"
Claude: [Uses aurora_search tool] "I found 5 authentication-related functions..."

User: "Show me the LoginHandler class"
Claude: [Uses aurora://file resource] "Here's the LoginHandler class..."
```

---

### Phase 2: Advanced Features (Future)

1. **Activation-based Retrieval**
   - Tool: `aurora_activate` - Spread activation from query
   - Returns most relevant chunks based on ACT-R spreading

2. **SOAR Pipeline Integration**
   - Tool: `aurora_soar` - Run full SOAR pipeline
   - Executes decompose → assess → route → collect → synthesize

3. **Relationship Exploration**
   - Tool: `aurora_related` - Find related code chunks
   - Uses dependency graph traversal

4. **Real-time Indexing**
   - Resource subscription for file changes
   - Auto-index on file modifications

---

## Alternative: Use Existing LLM MCP Servers

If you don't want to use Anthropic API but have other LLM access:

### Option 1: Use OpenAI via MCP
```bash
# Install OpenAI MCP server
pip install openai-mcp

# Configure AURORA to use MCP-provided LLM
export AURORA_LLM_PROVIDER=mcp
export AURORA_MCP_SERVER=openai-mcp
```

### Option 2: Use Local LLM via MCP
```bash
# Use ollama or llamacpp via MCP
pip install local-llm-mcp

# Configure AURORA
export AURORA_LLM_PROVIDER=mcp
export AURORA_MCP_SERVER=local-llm-mcp
export AURORA_MCP_MODEL=mistral
```

**Implementation Complexity**: Medium-High
- Need to abstract LLM interface
- Support multiple providers
- Handle different response formats

---

## Immediate Next Steps

### Decision Required:

**Question 1**: Which approach do you want?
- [ ] A. Create AURORA MCP server (recommended - lets Claude Desktop access AURORA)
- [ ] B. Support calling LLMs via MCP (lets AURORA use other LLM providers)
- [ ] C. Both (do A first, then B later)

**Question 2**: Priority level?
- [ ] Critical - Can't use AURORA without it
- [ ] High - Would be very useful
- [ ] Medium - Nice to have
- [ ] Low - Future enhancement

**Question 3**: Current blocker?
- Do you have Claude Desktop installed?
- Do you have any API access (Anthropic, OpenAI, etc.)?
- Are you trying to use AURORA completely free (local LLM only)?

---

## Implementation Estimate

### Approach A: AURORA as MCP Server (RECOMMENDED)

**Effort**: 2-3 days
- Day 1: MCP server scaffold, basic tools
- Day 2: Resource providers, testing
- Day 3: Documentation, examples

**PRD Tasks**:
1. Create `packages/mcp/` package structure
2. Implement MCP server with search/index tools
3. Add resource provider for code files
4. Write Claude Desktop configuration guide
5. Create example workflows
6. Add integration tests

**Dependencies**:
- Must fix memory indexing first (critical bug)
- Need MCP SDK (`pip install mcp`)

---

### Approach B: Support External LLM MCPs

**Effort**: 3-5 days
- Day 1-2: Abstract LLM interface
- Day 2-3: MCP client integration
- Day 3-4: Support multiple providers
- Day 4-5: Testing, documentation

**Complexity**: Higher (more architectural changes)

---

## Questions for User

1. **What do you mean by "we don't have mcp"?**
   - You want to create an MCP server for AURORA?
   - You want to use AURORA with a different LLM via MCP?
   - You want to avoid API keys entirely?

2. **Do you have Claude Desktop installed?**
   - If yes → Approach A makes sense
   - If no → Need to understand your setup

3. **What's your current LLM access?**
   - Anthropic API (paid)
   - OpenAI API (paid)
   - Local LLM (Ollama, etc.)
   - None (want completely free solution)

4. **What's the primary use case?**
   - Search your code from Claude Desktop
   - Run AURORA without paid API
   - Both

---

## Recommendation

**Phase 1 (Immediate)**:
1. Fix memory indexing (critical bug blocking everything)
2. Clarify your MCP requirements
3. Choose Approach A or B

**Phase 2 (After bug fix)**:
1. Implement chosen MCP approach
2. Test with your use case
3. Document and iterate

**Phase 3 (Future)**:
1. Add advanced SOAR features to MCP
2. Support multiple LLM providers
3. Real-time indexing via MCP subscriptions

---

## Example PRD Outline: AURORA MCP Server

```markdown
# PRD: AURORA MCP Server Integration

## Objective
Enable Claude Desktop users to search and interact with AURORA-indexed codebases without requiring Anthropic API keys.

## Success Criteria
- Users can install and configure AURORA MCP server
- Claude Desktop can search indexed code via aurora_search tool
- Users can chat with Claude about their codebase

## Tasks
1. Package setup (mcp package, dependencies)
2. MCP server implementation (FastMCP or MCP SDK)
3. Tool: aurora_search (hybrid retrieval)
4. Tool: aurora_index (index directories)
5. Tool: aurora_stats (memory statistics)
6. Resource: aurora://file/{path} (code access)
7. Claude Desktop config generator
8. Documentation and examples
9. Integration tests
10. User guide

## Non-goals
- Full SOAR pipeline via MCP (Phase 2)
- Supporting other LLM providers (separate PRD)
```

**Ready to create this PRD if you choose Approach A!**
