# SOAR Conversation Log

**Query ID**: soar-1768255550536
**Timestamp**: 2026-01-12T23:15:50.580528
**User Query**: what ae the differences between subagents in md file and in python scripts? how do companies solve stateless and multi-turn queries?

---

## Execution Summary

- **Duration**: 600042.308807373ms
- **Overall Score**: 0.93
- **Cached**: True
- **Cost**: $0.0212
- **Tokens Used**: 74 input + 1401 output

## Metadata

```json
{
  "query_id": "soar-1768255550536",
  "query": "what ae the differences between subagents in md file and in python scripts? how do companies solve stateless and multi-turn queries?",
  "total_duration_ms": 600042.308807373,
  "total_cost_usd": 0.021237,
  "tokens_used": {
    "input": 74,
    "output": 1401
  },
  "budget_status": {
    "period": "2026-01",
    "limit_usd": 10.0,
    "consumed_usd": 0.30488399999999993,
    "remaining_usd": 9.695116,
    "percent_consumed": 3.0488399999999993,
    "at_soft_limit": false,
    "at_hard_limit": false,
    "total_entries": 167
  },
  "phases": {
    "phase1_assess": {
      "complexity": "MEDIUM",
      "confidence": 0.8764705882352941,
      "method": "keyword",
      "reasoning": "Keyword-based classification with 87.6% confidence",
      "score": 0.36,
      "_timing_ms": 18.29075813293457,
      "_error": null
    },
    "phase2_retrieve": {
      "code_chunks": [],
      "reasoning_chunks": [],
      "total_retrieved": 0,
      "high_quality_count": 0,
      "retrieval_time_ms": 0.04076957702636719,
      "budget": 10,
      "budget_used": 0,
      "_timing_ms": 0.06389617919921875,
      "_error": null
    },
    "phase3_decompose": {
      "decomposition": {
        "goal": "Understand architectural differences between markdown-defined and Python-defined subagents, and industry approaches to stateless/multi-turn query handling",
        "subgoals": [
          {
            "description": "Analyze markdown-based subagent definitions in the codebase to understand structure and capabilities",
            "suggested_agent": "full-stack-dev",
            "is_critical": true,
            "depends_on": []
          },
          {
            "description": "Analyze Python-based subagent implementations to understand programmatic structure and runtime behavior",
            "suggested_agent": "full-stack-dev",
            "is_critical": true,
            "depends_on": []
          },
          {
            "description": "Compare and contrast the two approaches: flexibility, maintainability, execution model, and use cases",
            "suggested_agent": "holistic-architect",
            "is_critical": true,
            "depends_on": [
              0,
              1
            ]
          },
          {
            "description": "Research industry patterns for stateless query handling: session management, context serialization, state machines",
            "suggested_agent": "business-analyst",
            "is_critical": true,
            "depends_on": []
          },
          {
            "description": "Research industry patterns for multi-turn conversations: context windows, memory systems, conversation threading",
            "suggested_agent": "business-analyst",
            "is_critical": true,
            "depends_on": []
          },
          {
            "description": "Synthesize findings into architectural recommendations for Aurora's agent system",
            "suggested_agent": "holistic-architect",
            "is_critical": false,
            "depends_on": [
              2,
              3,
              4
            ]
          }
        ],
        "execution_order": [
          {
            "phase": 1,
            "parallelizable": [
              0,
              1,
              3,
              4
            ],
            "sequential": []
          },
          {
            "phase": 2,
            "parallelizable": [
              2
            ],
            "sequential": []
          },
          {
            "phase": 3,
            "parallelizable": [
              5
            ],
            "sequential": []
          }
        ],
        "expected_tools": [
          "code_reader",
          "file_search",
          "web_search",
          "documentation_reader"
        ]
      },
      "cached": false,
      "query_hash": "e94db0cdc159399346f4a9a18f9adbdde0279d49add0f429bdef20fd41dd934f",
      "timing_ms": 27348.56204499374,
      "subgoals_total": 6,
      "_timing_ms": 27350.932836532593,
      "_error": null
    },
    "phase4_verify": {
      "final_verdict": "PASS",
      "agent_assignments": [
        {
          "index": null,
          "agent_id": "full-stack-dev"
        },
        {
          "index": null,
          "agent_id": "full-stack-dev"
        },
        {
          "index": null,
          "agent_id": "holistic-architect"
        },
        {
          "index": null,
          "agent_id": "business-analyst"
        },
        {
          "index": null,
          "agent_id": "business-analyst"
        },
        {
          "index": null,
          "agent_id": "holistic-architect"
        }
      ],
      "issues": [],
      "_timing_ms": 0,
      "_error": null
    },
    "phase5_collect": {
      "agent_outputs": [
        {
          "subgoal_index": null,
          "agent_id": "full-stack-dev",
          "success": true,
          "summary": "Based on my analysis of the codebase, I can now provide comprehensive findings on the differences between MD-file and Python-script subagents, and how companies handle stateless vs multi-turn queries.\n\n## Key Findings\n\n### 1. MD File Subagents vs Python Script Subagents\n\n**MD File Subagents (Declarative Agents):**\n- **Location**: Stored in `~/.claude/agents/*.md` and similar directories across 20+ AI coding tools\n- **Structure**: YAML frontmatter + markdown body\n- **Discovery**: Scanned by `AgentScanner` (packages/cli/src/aurora_cli/agent_discovery/scanner.py:37)\n- **Metadata Model**: `AgentInfo` Pydantic model with fields:\n  - `id`: kebab-case identifier\n  - `role`: title\n  - `goal`: purpose description\n  - `category`: eng/qa/product/general\n  - `skills`: list of capabilities\n  - `when_to_use`: activation guidance\n  - `dependencies`: other agents this can invoke\n- **Use Case**: Documentation-driven agent definitions for Claude Code, consumed by orchestrator to route tasks\n- **Invocation**: Via @ mentions (`@qa-test-architect`) or role phrases (\"As ux-expert, ...\")\n- **State**: Stateless - each invocation is independent\n\n**Python Script Subagents (Programmatic Agents):**\n- **Location**: `packages/cli/src/aurora_cli/planning/agents.py`, `packages/soar/src/aurora_soar/`\n- **Structure**: `AgentRecommender` class with algorithmic matching logic\n- **Discovery**: Direct import and instantiation\n- **Metadata Model**: Same `AgentInfo` model, but loaded into runtime `AgentManifest`\n- **Key Classes**:\n  - `AgentRecommender`: Scores agents for subgoals via keyword matching + optional LLM fallback\n  - `AgentManifest`: In-memory registry with O(1) lookup by ID and category indexing\n- **Use Case**: Runtime agent selection and routing in SOAR pipeline\n- **Invocation**: Programmatic via `recommend_for_subgoal()`, `score_agent_for_subgoal()`\n- **State**: Maintains manifest cache, scores, and confidence metrics\n\n**Critical Differences:**\n\n| Aspect | MD Files | Python Scripts |\n|--------|----------|----------------|\n| **Nature** | Documentation/config | Executable code |\n| **Parsing** | YAML frontmatter \u2192 Pydantic | Direct Python imports |\n| **Storage** | Filesystem (20+ tool directories) | In-memory + JSON cache |\n| **Matching** | Manual routing by orchestrator | Algorithmic keyword + LLM scoring |\n| **State** | Stateless declarations | Stateful runtime (manifest, scores) |\n| **Extensibility** | Add .md file \u2192 auto-discovered | Code changes required |\n| **Performance** | Initial scan overhead | O(1) lookups after loading |\n\n### 2. How Companies Solve Stateless vs Multi-Turn Queries\n\nAurora uses a **hybrid approach** combining stateless execution with structured logging:\n\n**Stateless Execution (Primary):**\n```python\n# packages/soar/src/aurora_soar/orchestrator.py:65-100\nclass SOAROrchestrator:\n    \"\"\"7-phase SOAR pipeline - each query is independent\"\"\"\n    \n    # Each invocation creates fresh state\n    async def process_query(self, query: str):\n        # Phase 1-7 executed per query\n        # No persistent conversation state\n```\n\n**Multi-Turn Simulation via Conversation Logging:**\n```python\n# packages/core/src/aurora_core/logging/conversation_logger.py:27-105\nclass ConversationLogger:\n    \"\"\"Logs to .aurora/logs/conversations/YYYY/MM/\"\"\"\n    \n    def log_interaction(self, query, query_id, phase_data, execution_summary):\n        # Creates timestamped markdown files\n        # Format: keyword1-keyword2-YYYY-MM-DD.md\n```\n\n**Key Patterns:**\n\n1. **Stateless SOAR Pipeline**:\n   - Each query runs 4-7 phases independently\n   - SIMPLE queries: Assess \u2192 Retrieve \u2192 Synthesize \u2192 Respond (4 phases)\n   - COMPLEX queries: Full 7-phase pipeline with decomposition\n   - No conversation context carried between queries\n\n2. **Memory Substitutes Context**:\n   - ACT-R memory store retrieves relevant chunks (5-20 per query)\n   - Phase 2 (Retrieve) uses activation-based relevance\n   - Phase 7 (Record) caches reasoning patterns for future queries\n\n3. **Conversation Logs for Analysis**:\n   - Not used for multi-turn state\n   - Post-hoc analysis and debugging\n   - Structured phase data in JSON blocks\n\n4. **Agent Execution is Stateless**:\n```python\n# packages/soar/src/aurora_soar/phases/collect.py:79-148\nclass AgentOutput:\n    \"\"\"Single execution result - no conversation state\"\"\"\n    subgoal_index: int\n    agent_id: str\n    success: bool\n    summary: str\n    confidence: float  # 0-1 score\n```\n\n**Industry Patterns Aurora Implements:**\n\n1. **Stateless Microservices Pattern**: Each SOAR phase is stateless, orchestrator coordinates\n2. **Event Sourcing Lite**: Conversation logs capture all interactions for replay\n3. **Cached Reasoning**: Phase 7 stores lightweight patterns (keywords + truncated context)\n4. **Retry with Fallback**: Phase 5 (Collect) uses `spawn_with_retry_and_fallback()` for agent execution failures\n\n**What Aurora Does NOT Do:**\n\n- No session management or conversation IDs linking multiple queries\n- No explicit multi-turn dialog state (previous query context not passed forward)\n- No conversational memory beyond what's indexed in ACT-R store\n\nThe design philosophy: **Stateless execution with comprehensive memory retrieval** beats stateful conversation tracking for code-related queries, because relevant context is in the codebase, not in previous turns.\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 83254,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        },
        {
          "subgoal_index": null,
          "agent_id": "full-stack-dev",
          "success": true,
          "summary": "Perfect! Now I have enough information. Let me compile my findings:\n\n## Analysis: Markdown Subagents vs Python Agents & Industry Approaches to State Management\n\n### **Part 1: Subagents in MD Files vs Python Scripts**\n\n#### **Markdown-Defined Subagents (Claude Code Agent System)**\n\n**Location**: `~/.claude/agents/*.md`\n\n**Structure**:\n```yaml\n---\nid: agent-id\nrole: Agent Role\ngoal: Brief description of purpose\ncategory: eng/qa/product/general\nskills: [list of capabilities]\nwhen_to_use: Guidance on when to invoke\n---\n# Agent instructions follow...\n```\n\n**Characteristics**:\n- **Declarative metadata**: YAML frontmatter parsed by `AgentParser` (packages/cli/src/aurora_cli/agent_discovery/parser.py:49)\n- **Invocation model**: Used via Task tool in Claude Code, invoked as subprocesses\n- **Discovery**: Scanned by `ManifestManager` which builds cached JSON manifest (packages/cli/src/aurora_cli/agent_discovery/manifest.py)\n- **Validation**: Pydantic models enforce schema (AgentInfo, AgentCategory in models.py:39)\n- **State**: **Stateless** - Each invocation starts fresh with no memory\n- **Context**: Passed via prompt injection at invocation time\n- **Execution**: Claude SDK spawns subprocess with agent instructions loaded\n\n**Pros**:\n- Easy to author (markdown + frontmatter)\n- No code required\n- Discoverable via scanning\n- Version controllable\n\n**Cons**:\n- No persistent state\n- Limited to LLM capabilities\n- Can't maintain conversation context across turns\n- Expensive (each invocation = full LLM call)\n\n#### **Python-Defined Agents (Aurora Internal)**\n\n**Location**: `packages/cli/src/aurora_cli/planning/agents.py`, `packages/soar/src/aurora_soar/`\n\n**Structure**:\n```python\nclass AgentRecommender:\n    \"\"\"Recommends agents for subgoals based on capability matching\"\"\"\n    def __init__(self, manifest, config, llm_client):\n        self.manifest = manifest  # AgentManifest with indexes\n        self.llm_client = llm_client  # For fallback classification\n```\n\n**Characteristics**:\n- **Programmatic**: Full Python classes with state\n- **Hybrid retrieval**: Keyword matching (packages/cli/src/aurora_cli/planning/agents.py:450) + optional LLM classification (line 189)\n- **Scoring system**: Weighted overlap scoring (goal/when_to_use = 2x, capabilities = 1x) - line 494\n- **State management**: Can maintain instance state, caches manifest\n- **Integration**: Direct Python imports, synchronous/async methods\n- **Execution**: In-process, no subprocess overhead\n\n**Pros**:\n- Can maintain state across calls\n- Performance (in-process, no LLM needed for matching)\n- Complex logic (scoring, fallback, caching)\n- Type safety (Pydantic validation)\n\n**Cons**:\n- Requires code changes\n- Not discoverable by external tools\n- More complex to author\n\n### **Part 2: How Companies Solve Stateless vs Multi-Turn Queries**\n\nBased on the codebase analysis and market research (docs/archive/agi-problem/research/market-research/memory-learning-systems-analysis.md):\n\n#### **Aurora's Approach**\n\n**Stateless Design** (Current):\n```python\n# packages/soar/src/aurora_soar/orchestrator.py:65\nclass SOAROrchestrator:\n    \"\"\"7-phase reasoning pipeline\"\"\"\n    # Each query is independent\n    # State stored in .aurora/soar/state.json but reset per query\n```\n\n**Multi-Turn Handling**:\n1. **ConversationLogger** (packages/core/src/aurora_core/logging/conversation_logger.py:27) - Logs each interaction to markdown\n2. **Memory Store** - ACT-R activation-based retrieval (packages/core/src/aurora_core/store/sqlite.py)\n3. **Pattern Caching** - Record phase stores successful patterns (docs/guides/SOAR.md:127)\n4. **No session state** - Each SOAR invocation is independent\n\n**Limitations**:\n- No conversation history between invocations\n- Each query pays full reasoning cost\n- Can't build on previous turns contextually\n\n#### **Industry Solutions**\n\nFrom memory-learning-systems-analysis.md:\n\n**1. SuperMemory (Hierarchical Memory)**\n```\nWorking Memory \u2192 Short-Term \u2192 Long-Term \u2192 Semantic Memory\n```\n- **Stateless LLM** + **stateful memory layer**\n- Smart forgetting with decay functions\n- Recency bias for retrieval\n- **Problem**: Memory \u2260 Learning (stores facts, doesn't improve reasoning)\n\n**2. Mem0 (Multi-Tier Storage)**\n```\nMemory Extraction \u2192 Storage \u2192 Retrieval \u2192 Consolidation\n```\n- User-specific, interaction-specific, global knowledge tiers\n- LLM extracts what to remember\n- Memory consolidation merges redundant info\n- **Problem**: Curation, not learning\n\n**3. ACE Framework (Skillbook Pattern)**\n```\nAgent \u2192 Reflector \u2192 Skillbook Update \u2192 Next Invocation\n```\n- Stateless agent + persistent skillbook\n- Reflector agent analyzes performance\n- Updates skillbook with learnings\n- **Problem**: In-context learning via prompt engineering\n\n#### **Common Patterns**\n\nAll systems follow: **Stateless Compute + Stateful Storage**\n\n```\n\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510\n\u2502   Stateless Agent   \u2502 \u2190 Fresh invocation each time\n\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518\n           \u2502\n           \u2193\n\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510\n\u2502  Stateful Storage   \u2502 \u2190 Persists context/memory\n\u2502  - Vector DB        \u2502\n\u2502  - Session State    \u2502\n\u2502  - Conversation Log \u2502\n\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518\n```\n\n**Why Stateless?**\n1. **Scalability**: No server-side session state\n2. **Cost**: Pay per query, not per session\n3. **Simplicity**: No session management complexity\n4. **Token limits**: LLMs have context windows\n\n**How They Handle Multi-Turn**:\n1. **Context injection**: Retrieve relevant past interactions \u2192 inject into prompt\n2. **Session IDs**: Track related queries (Aurora uses query_id in ConversationLogger:56)\n3. **Memory retrieval**: BM25/semantic search over past interactions\n4. **Pattern matching**: Cache successful reasoning patterns\n\n**Performance Trade-offs**:\n- \u2705 Scales horizontally (no session affinity)\n- \u2705 No stale state issues\n- \u274c Every query pays retrieval cost\n- \u274c No true \"learning\" - just better context retrieval\n\n### **Key Insight**\n\nMD agents and Python agents solve different problems:\n- **MD agents** = User-facing personas for task orchestration (stateless by design)\n- **Python agents** = Internal systems for matching/routing/optimization (can be stateful)\n\nIndustry consensus: **Stateless execution + stateful memory** is the optimal pattern. True multi-turn learning remains unsolved - current systems do sophisticated context retrieval, not actual learning.\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 178953,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        },
        {
          "subgoal_index": null,
          "agent_id": "holistic-architect",
          "success": true,
          "summary": "## Findings: MD Files vs Python Scripts for Subagents\n\n### 1. **MD Files (Declarative Agents)**\n\n**Location**: `~/.claude/agents/*.md`\n\n**Structure**:\n- Frontmatter with metadata (name, description, model, color)\n- Instructions and role definition\n- Commands with `*` prefix\n- Workflow patterns and decision trees\n- Context injection rules\n\n**Examples**: orchestrator.md:12, qa-test-architect.md:1\n\n**Usage Pattern**:\n- Read by LLM at runtime as instructions\n- Defines persona, commands, and behavior\n- Human-readable prompts that shape LLM responses\n- Referenced via `@agent-id` or \"As agent-id, ...\"\n\n**Characteristics**:\n- Stateless by design - full instructions reloaded each invocation\n- No native multi-turn support - each call is independent\n- Context passed explicitly through selective injection (orchestrator.md:49-60)\n- Transformation model: agent adopts full persona from MD file (orchestrator.md:99-106)\n\n### 2. **Python Scripts (Programmatic Agents)**\n\n**Location**: `packages/*/src/**/agents.py`, `packages/soar/src/aurora_soar/agent_registry.py`\n\n**Structure**:\n- `AgentInfo` dataclass with id, name, description, capabilities, type (agent_registry.py:31-51)\n- `AgentRegistry` for registration and capability-based discovery (agent_registry.py:66-328)\n- `AgentRecommender` for matching agents to subgoals via keyword scoring (planning/agents.py:71-534)\n\n**Usage Pattern**:\n- Discovered and indexed via `ManifestManager` (commands/agents.py:75-113)\n- Scanned from directories configured in project\n- Used for agent selection, not execution\n- Metadata stored in `.aurora/cache/agent_manifest.json`\n\n**Characteristics**:\n- Python manages metadata and routing logic\n- Agent execution still goes through LLM (MD files or Claude Code Task tool)\n- Registry is stateless - agents rediscovered on refresh\n- No built-in multi-turn conversation management\n\n### 3. **Multi-Turn and Stateless Query Solutions**\n\n#### **Aurora's Approach (SOAR Orchestrator)**\n\n**File**: `packages/soar/src/aurora_soar/orchestrator.py:1-100`\n\n**Architecture**:\n- 7-phase pipeline: Assess \u2192 Retrieve \u2192 Decompose \u2192 Verify \u2192 Collect \u2192 Synthesize \u2192 Record \u2192 Respond\n- **Stateless phases**: Each phase is independent, receives explicit context\n- **Multi-turn via Python control**: POC at `src/aurora_mcp/multiturn_poc.py:14-137`\n- **Key insight**: \"Python controls the loop, makes separate API calls. Claude doesn't need to 'remember' - we FORCE it\" (multiturn_poc.py:18-19)\n\n**Method**:\n```python\n# Separate LLM calls per phase (multiturn_poc.py:44-135)\nphase1 = call_llm(\"Assess complexity...\")  # Call 1\nphase2 = call_llm(\"Decompose into subgoals...\")  # Call 2\nphase3 = call_llm(\"Verify subgoals...\")  # Call 3\nphase4 = call_llm(\"Collect findings...\")  # Call 4\nphase5 = call_llm(\"Synthesize...\")  # Call 5\nphase6 = call_llm(\"Respond...\")  # Call 6\n```\n\n**State Management**:\n- Context dictionary accumulates phase outputs (multiturn_poc.py:33, 58, 74, 90, 106, 122)\n- No LLM memory required - Python passes relevant context to each phase\n- ConversationLogger for persistence (orchestrator.py:40, 87)\n\n#### **Industry Solutions**\n\n**Common Patterns**:\n\n1. **External State Management**:\n   - Redis/database stores conversation history\n   - Each stateless LLM call receives conversation context\n   - Example: Langchain ConversationBufferMemory\n\n2. **Session Management**:\n   - Session IDs track conversation threads\n   - Backend retrieves and injects relevant history\n   - Token limits managed via summarization or truncation\n\n3. **Agentic Frameworks**:\n   - **AutoGPT/BabyAGI**: External task queue, stateless LLM execution\n   - **LangGraph**: State graphs with explicit context passing between nodes\n   - **Semantic Kernel**: Planner creates plan, executor runs stateless steps\n\n4. **MCP (Model Context Protocol)**:\n   - Tools control flow, make separate API calls per step\n   - Context injected programmatically, not via LLM memory\n   - Aurora's approach aligns with this pattern (multiturn_poc.py:1-164)\n\n### 4. **Key Differences Summary**\n\n| Aspect | MD Files | Python Scripts | Multi-Turn Solution |\n|--------|----------|----------------|---------------------|\n| **Purpose** | Define agent persona/instructions | Agent metadata/discovery | State orchestration |\n| **Execution** | Interpreted by LLM | Scanned/indexed, not executed | Python controls LLM calls |\n| **State** | Stateless (reloaded each call) | Stateless (registry refreshed) | Stateful via external context |\n| **Multi-turn** | No native support | N/A (not for execution) | Separate calls with context passing |\n| **Context** | Selective injection (orchestrator.md:49) | Keyword scoring (planning/agents.py:450-506) | Explicit accumulation (multiturn_poc.py:33) |\n| **Industry Pattern** | Prompt engineering | Service discovery | External orchestration layer |\n\n### 5. **Stateless Multi-Turn Solution Pattern**\n\n**Core principle**: LLMs are stateless functions. Multi-turn requires external state management.\n\n**Implementation**:\n1. **Orchestrator** (Python/backend) controls conversation flow\n2. **Phase isolation**: Each LLM call gets explicit, minimal context\n3. **State accumulation**: Backend stores phase outputs, injects into next phase\n4. **No LLM memory**: LLM doesn't \"remember\" - receives fresh instructions each time\n5. **Budget tracking**: External service monitors costs across calls (orchestrator.py:85, 99)\n\n**This is how companies solve stateless multi-turn**:\n- Claude Code Task tool: Python subprocess manages turns\n- Aurora SOAR: 7 separate LLM calls with context passing\n- Production systems: Session managers with Redis/DB + stateless LLM endpoints\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 244208,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        },
        {
          "subgoal_index": null,
          "agent_id": "business-analyst",
          "success": true,
          "summary": "# Differences Between Subagents in MD Files vs Python Scripts\n\n## 1. Markdown File Subagents (Claude Code)\n\n**Location**: `~/.claude/agents/*.md`\n\n**Nature**: \n- Prompt-based agents defined in markdown frontmatter\n- Used by Claude Code CLI (Anthropic's tool)\n- Stateless - each invocation is fresh\n- Loaded at runtime via Task tool\n\n**Structure**:\n```yaml\n---\nid: full-stack-dev\ngoal: \"Implement code and debug issues\"\nwhen_to_use: \"For code implementation, debugging, refactoring\"\ncapabilities: [\"python\", \"typescript\", \"testing\"]\ncategory: eng\n---\n# Agent instructions in markdown body\n```\n\n**Key Files**:\n- `/home/hamr/.claude/CLAUDE.md` - Registry of available agents\n- `packages/cli/src/aurora_cli/agent_discovery/scanner.py` - Scans for .md files across 20 AI tool directories\n- `packages/cli/src/aurora_cli/agent_discovery/manifest.py` - Caches agent metadata with 24hr refresh\n\n**How They Work**:\n1. Scanner discovers .md files from configured paths\n2. Parser extracts frontmatter (ID, capabilities, when_to_use)\n3. ManifestManager caches in `.aurora/cache/agent_manifest.json`\n4. Orchestrator matches tasks to agents via keyword scoring\n5. Claude Code launches subprocess with agent's prompt template\n\n**Statelessness**: Every Task tool call is independent. No conversation history persists between invocations.\n\n---\n\n## 2. Python Script Subagents (Aurora SOAR)\n\n**Location**: `packages/soar/src/aurora_soar/`\n\n**Nature**:\n- Functional pipeline phases, not discrete \"agents\"\n- Embedded in SOAR orchestrator\n- Stateful within a single query (via context dict)\n- Directly imported Python modules\n\n**Structure**:\n```python\n# packages/soar/src/aurora_soar/phases/decompose.py\ndef decompose_query(query: str, context: dict) -> dict:\n    \"\"\"Break query into subgoals\"\"\"\n    # Access context from previous phases\n    chunks = context.get(\"retrieved_chunks\", [])\n    # ...\n    return {\"subgoals\": [...]}\n```\n\n**Key Files**:\n- `packages/soar/src/aurora_soar/orchestrator.py` - Coordinates 7-phase pipeline\n- `packages/soar/src/aurora_soar/phases/` - assess, retrieve, decompose, verify, collect, synthesize, record, respond\n- `packages/cli/src/aurora_cli/planning/agents.py` - AgentRecommender matches subgoals to agents\n\n**How They Work**:\n1. Single `aur soar \"query\"` command enters orchestrator\n2. Phases execute sequentially: Assess \u2192 Retrieve \u2192 Decompose \u2192 Verify \u2192 Collect \u2192 Synthesize \u2192 Record \u2192 Respond\n3. Context dict passes state between phases\n4. Phase 5 (Collect) may invoke external agents via manifest lookup\n\n**Statefulness**: Context persists within single query execution. Lost between separate `aur soar` invocations.\n\n---\n\n## Key Differences\n\n| Aspect | MD Subagents | Python SOAR Phases |\n|--------|-------------|-------------------|\n| **Definition** | Markdown frontmatter + prompt | Python functions |\n| **Discovery** | Scanned from filesystem | Imported modules |\n| **Execution** | Subprocess via Task tool | Direct function call |\n| **State** | Stateless (each call fresh) | Context dict within query |\n| **Matching** | Keyword + LLM-based | Hardcoded phase sequence |\n| **Extensibility** | Add .md file to agents/ | Modify orchestrator code |\n| **Use Case** | Role-based workflows (PM, QA, Dev) | Query reasoning pipeline |\n\n---\n\n## How Companies Solve Stateless & Multi-Turn Queries\n\n### 1. **Session State Management**\n\n**Aurora's Approach**:\n```python\n# packages/soar/src/aurora_soar/orchestrator.py\nself._phase_metadata: dict[str, Any] = {}  # Per-query state\nself._session_cache = []  # MCP test shows session cache attempt\n```\n\n**Industry Solutions**:\n- **Langchain**: `ConversationBufferMemory`, `ConversationSummaryMemory`\n- **LlamaIndex**: `ChatMemoryBuffer` with sliding window\n- **Anthropic Claude API**: Pass full message history in `messages[]` array\n- **OpenAI Assistants API**: Thread-based conversation storage\n\n**Pattern**: Stateless HTTP APIs rely on client to send full history each request.\n\n### 2. **Multi-Turn Query Handling**\n\n**Aurora's POC** (`src/aurora_mcp/multiturn_poc.py`):\n```python\ndef run_multiturn_soar(query: str):\n    context = {\"query\": query, \"phases\": {}}\n    \n    # Phase 1: Assess (LLM call 1)\n    phase1 = call_llm(assess_prompt)\n    context[\"phases\"][\"assess\"] = phase1\n    \n    # Phase 2: Decompose (LLM call 2, uses phase1 results)\n    phase2 = call_llm(decompose_prompt + str(phase1))\n    context[\"phases\"][\"decompose\"] = phase2\n    \n    # ... 6 separate LLM calls, each sees previous results\n```\n\n**Key Insight**: Python controls the loop, makes separate API calls per phase. Claude doesn't need to \"remember\" phases - code enforces sequence.\n\n**Industry Patterns**:\n\n1. **ReAct Loop** (Reason-Act-Observe):\n   ```python\n   for step in range(max_steps):\n       thought = llm(prompt + history)\n       action = parse_action(thought)\n       observation = execute(action)\n       history.append((thought, action, observation))\n   ```\n\n2. **Chain-of-Thought with Backtracking**:\n   ```python\n   def solve(query, history=[]):\n       plan = llm_plan(query, history)\n       for step in plan:\n           result = execute_step(step)\n           if result.failed:\n               return solve(query, history + [result])  # Retry with failure context\n       return synthesize(history)\n   ```\n\n3. **Hierarchical Agent Systems** (AutoGPT, BabyAGI):\n   - **Master agent**: Decomposes goals\n   - **Worker agents**: Execute subgoals (stateless)\n   - **Memory system**: Stores intermediate results\n   - **Orchestrator**: Maintains conversation state\n\n4. **Streaming State Machines**:\n   ```python\n   class ConversationFSM:\n       state = \"initial\"\n       context = {}\n       \n       def handle(self, user_input):\n           if self.state == \"initial\":\n               self.state = \"gathering_requirements\"\n               self.context[\"requirements\"] = extract(user_input)\n           elif self.state == \"gathering_requirements\":\n               # ...\n   ```\n\n### 3. **Aurora-Specific Solutions**\n\n**Within-Query State** (works now):\n- `packages/soar/src/aurora_soar/orchestrator.py` maintains `context` dict\n- Phases share: retrieved chunks, decomposition, agent results\n\n**Cross-Query State** (limited):\n- `packages/core/src/aurora_core/store/sqlite.py` - ACT-R memory for facts\n- `packages/soar/src/aurora_soar/phases/record.py` - Caches reasoning patterns\n- `.aurora/cache/agent_manifest.json` - Agent capability cache\n\n**Multi-Turn Gaps**:\n1. No conversation ID tracking\n2. No `aur soar --continue <session-id>` command\n3. Each `aur soar` call starts fresh (doesn't see previous queries)\n4. MCP multi-turn test is marked as deprecated (PRD-0024)\n\n### 4. **Commercial AI Assistant Solutions**\n\n**Claude.ai Web UI**:\n- Backend maintains session state in database\n- Each API call includes full message history\n- Projects feature: Persistent knowledge base\n\n**GitHub Copilot Chat**:\n- VSCode extension maintains conversation buffer\n- Context: Open files + conversation history\n- Reset on workspace change\n\n**Cursor IDE**:\n- Thread-based conversations\n- Context: Git diff + open files + thread history\n- Composer mode: Multi-file editing with state\n\n**Windsurf/Codeium**:\n- Cascade mode: Multi-turn with plan persistence\n- State stored in `.windsurf/` directory\n- Resume interrupted tasks\n\n---\n\n## Recommendations for Multi-Turn in Aurora\n\nBased on codebase analysis:\n\n1. **Extend SOAR Orchestrator**:\n   ```python\n   class SOAROrchestrator:\n       def continue_conversation(self, session_id: str, follow_up: str):\n           # Load context from previous query\n           prev_context = self.store.get_conversation(session_id)\n           # Run phases with historical context\n           return self.run_with_context(follow_up, prev_context)\n   ```\n\n2. **Add Conversation Store**:\n   ```sql\n   CREATE TABLE conversations (\n       session_id TEXT PRIMARY KEY,\n       query_history TEXT,  -- JSON array\n       context_snapshot TEXT,  -- Serialized context\n       last_updated INTEGER\n   );\n   ```\n\n3. **CLI Command**:\n   ```bash\n   aur soar \"initial query\" --session-id abc123\n   aur soar \"follow-up\" --session-id abc123  # Resumes with history\n   ```\n\n4. **Reactivate MCP Multi-Turn** (currently dormant):\n   - `src/aurora_mcp/multiturn_poc.py` shows proof-of-concept\n   - `tests/integration/mcp/test_mcp_soar_multi_turn.py` has full test suite\n   - Both marked as deprecated (PRD-0024)\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 330173,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        },
        {
          "subgoal_index": null,
          "agent_id": "business-analyst",
          "success": true,
          "summary": "## Analysis: MD Files vs Python Scripts for Subagents\n\n### 1. MD File Subagents (Claude Code Agents)\n\n**Nature**: Markdown files in `~/.claude/agents/*.md` with YAML frontmatter\n- Store agent metadata (id, role, goal, capabilities)\n- Define behavior through natural language instructions\n- Invoked via `Task` tool with `subagent_type` parameter\n- Stateless - no persistence between invocations\n\n**Key characteristics**:\n```yaml\n---\nid: full-stack-dev\nrole: Expert Senior Software Engineer\ngoal: Implement stories and execute development tasks\ncategory: eng\ncapabilities: [coding, debugging, testing]\n---\n[Natural language instructions follow]\n```\n\n**Execution model**:\n- Each invocation starts fresh subprocess\n- No built-in multi-turn memory\n- Context passed explicitly via prompt\n- Agent ID resolution via keyword matching (AgentManifest)\n\n### 2. Python Script Subagents (Aurora Agents)\n\n**Nature**: Python classes in `packages/cli/src/aurora_cli/planning/agents.py`\n- Pydantic models (AgentInfo, AgentManifest)\n- Keyword-based capability matching\n- Score-based agent selection (0.0-1.0)\n- Integration with SOAR orchestrator\n\n**Key characteristics**:\n```python\nclass AgentInfo(BaseModel):\n    id: str  # kebab-case\n    role: str\n    goal: str\n    category: AgentCategory  # enum: eng/qa/product/general\n    skills: list[str]\n    when_to_use: str | None\n```\n\n**Execution model**:\n- Agents discovered and cached in AgentManifest\n- Keyword extraction from subgoals for matching\n- LLM fallback classification if keyword score < threshold\n- Stateless but manifest-based (scan `.aurora/cache/agent_manifest.json`)\n\n---\n\n## How Companies Solve Stateless/Multi-Turn Queries\n\n### Aurora's Approach (Hybrid)\n\n**Stateless Query Pattern** (`aur mem search`):\n- BM25 + semantic retrieval from indexed memory\n- No conversation state\n- Single-shot context retrieval\n\n**Multi-Turn Query Pattern** (`aur soar`):\n- 7-phase SOAR pipeline (assess \u2192 retrieve \u2192 decompose \u2192 verify \u2192 collect \u2192 synthesize \u2192 respond)\n- Session cache for context (`_session_cache` in MCP tools)\n- Phase-level state tracking (`_phase_metadata`)\n- Cost/token tracking across phases (`CostTracker`, `QueryMetrics`)\n\n**State Management**:\n```python\n# packages/soar/src/aurora_soar/orchestrator.py\nself._phase_metadata: dict[str, Any] = {}\nself._total_cost: float = 0.0\nself._token_usage: dict[str, int] = {\"input\": 0, \"output\": 0}\nself._query_id: str = \"\"\n```\n\n### Industry Patterns\n\n**1. Session-Based State (OpenAI Assistants, Claude Projects)**:\n- Persistent conversation threads\n- Vector store per thread\n- File attachments in context\n- State stored server-side\n\n**2. Agent Memory Systems (LangGraph, AutoGPT)**:\n- Working memory: Current conversation\n- Episodic memory: Past conversations indexed by similarity\n- Semantic memory: Learned facts/procedures\n- Often uses vector DBs (Chroma, Pinecone)\n\n**3. Stateless with Context Injection (Most APIs)**:\n- Pass full conversation history in each request\n- Token limits force truncation/summarization\n- No server-side persistence\n- Client manages state\n\n**4. Hybrid (Aurora's implementation)**:\n- ACT-R memory store (SQLite) for long-term memory\n- Session cache for active query context\n- Phase-based pipeline with intermediate state\n- Optional LLM features (can run fully local)\n\n### Aurora's Distinctive Features\n\n**Memory-First Design**:\n- `packages/core/src/aurora_core/store/sqlite.py` - persistent ACT-R memory\n- Chunks indexed with BM25 + optional embeddings\n- Activation-based retrieval (recency + frequency)\n\n**Stateless Phases with State Aggregation**:\n- Each SOAR phase is stateless function\n- Orchestrator aggregates phase outputs\n- Conversation logger for audit trail\n- No persistent session objects\n\n**Local-First Philosophy**:\n- Can run without LLM (keyword-based matching)\n- Optional embeddings (sentence-transformers)\n- Cost tracking to control cloud spending\n- Graceful degradation when offline\n\n### Comparison Table\n\n| Aspect | MD File Agents | Python Agents | Industry (OpenAI/Anthropic) |\n|--------|---------------|---------------|------------------------------|\n| State | None (subprocess) | Manifest cache | Persistent threads |\n| Multi-turn | Via prompt context | Session cache | Built-in conversation |\n| Agent discovery | Manual registration | Auto-scan + manifest | Curated library |\n| Capability matching | Natural language | Keyword + LLM fallback | Semantic |\n| Execution | Claude Code subprocess | Python async | API calls |\n| Memory | Conversation history | ACT-R store | Vector DB |\n| Cost model | Per-subprocess | Tracked across phases | Per-request |\n\n### Key Insight\n\n**Aurora bridges two paradigms**:\n1. **Claude Code agents** (MD files) - natural language personas for iterative dev tasks\n2. **Aurora agents** (Python) - capability-matched specialists for SOAR decomposition\n\n**Multi-turn solution**: Aurora doesn't maintain persistent sessions like ChatGPT. Instead:\n- Index codebase \u2192 persistent memory (ACT-R store)\n- Query \u2192 multi-phase pipeline with intermediate state\n- Each phase stateless \u2192 orchestrator aggregates\n- Session cache for active query only\n- Conversation logger for audit (not continuation)\n\nThis enables local-first operation while supporting multi-turn reasoning through memory retrieval rather than conversation threads.\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 410107,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        },
        {
          "subgoal_index": null,
          "agent_id": "holistic-architect",
          "success": true,
          "summary": "## Analysis: Differences Between MD Files and Python Scripts for Subagents\n\n### 1. MD Files (Claude Code Agents in ~/.claude/CLAUDE.md)\n\n**Purpose**: Human-readable specifications that Claude Code reads at runtime\n\n**Characteristics**:\n- **Stateless by design** - Each invocation starts fresh\n- **Natural language prompts** - Describe role, capabilities, when to use\n- **LLM-interpreted** - Claude reads instructions and adopts persona\n- **Runtime activation** - Mention \"@agent-id\" or \"As agent-id, ...\"\n- **Selective context injection** - Orchestrator passes minimal context\n- **No persistent state** - Each Task tool invocation is independent\n\n**Example Structure** (from CLAUDE.md):\n```markdown\n### Full Stack Developer (id: full-stack-dev)\n- When to use: Code implementation, debugging, refactoring\n- How to activate: Mention \"As full-stack-dev, ...\"\n```\n\n**Multi-turn handling**:\n- No conversation state between invocations\n- Orchestrator coordinates workflows with conditional user approval\n- Context passed explicitly per task via Task tool prompts\n\n### 2. Python Scripts (Aurora Agent System)\n\n**Purpose**: Programmatic agent registry with metadata and capability matching\n\n**Characteristics**:\n- **Stateful registry** - AgentManifest cached in JSON (packages/cli/src/aurora_cli/agent_discovery/manifest.py:1-150)\n- **Structured metadata** - AgentInfo dataclass with id, name, description, capabilities (packages/soar/src/aurora_soar/agent_registry.py:31-63)\n- **Keyword-based matching** - Score agents by capability overlap (packages/cli/src/aurora_cli/planning/agents.py:450-506)\n- **Programmatic discovery** - Scan .aurora/plans/*/agents.json files\n- **SOAR integration** - Used by orchestrator for agent assignment (packages/soar/src/aurora_soar/orchestrator.py:1-100)\n\n**Example Structure** (agents.json):\n```json\n{\n  \"plan_id\": \"0001-feature-name\",\n  \"subgoals\": [\n    {\n      \"id\": \"sg-1\",\n      \"description\": \"First subgoal\",\n      \"agent\": \"full-stack-dev\"\n    }\n  ]\n}\n```\n\n**Multi-turn handling**:\n- ConversationLogger tracks phase data per query (packages/core/src/aurora_core/logging/conversation_logger.py:27-352)\n- Each query_id logged with phase outputs but no shared state between queries\n- ACT-R memory store provides persistent context across sessions\n\n### Key Differences\n\n| Aspect | MD Files (Claude Code) | Python Scripts (Aurora) |\n|--------|----------------------|------------------------|\n| **Format** | Natural language | Structured JSON/dataclass |\n| **Activation** | Runtime text matching | Programmatic registry lookup |\n| **State** | Stateless invocations | Cached manifest + logged conversations |\n| **Matching** | LLM interpretation | Keyword scoring algorithm |\n| **Context** | Passed per invocation | Retrieved from memory store |\n| **Purpose** | Human instructions for LLM | Machine-readable metadata |\n\n## How Companies Solve Stateless/Multi-turn Queries\n\n### Aurora's Approach\n\n**1. Stateless Execution with Persistent Memory**:\n- Each SOAR query is stateless (no shared conversation state)\n- ConversationLogger persists phase data to .aurora/logs/conversations/YYYY/MM/ (packages/core/src/aurora_core/logging/conversation_logger.py:107-112)\n- ACT-R memory store provides retrieval across sessions\n- No session continuity - each query starts fresh\n\n**2. Agent Assignment**:\n- AgentRecommender scores agents by keyword overlap (packages/cli/src/aurora_cli/planning/agents.py:107-151)\n- Falls back to LLM classification if keyword matching fails (packages/cli/src/aurora_cli/planning/agents.py:153-188)\n- Uses cached AgentManifest for O(1) lookup (packages/cli/src/aurora_cli/agent_discovery/manifest.py:72-150)\n\n**3. Workflow Orchestration**:\n- Orchestrator coordinates 7-phase pipeline per query (packages/soar/src/aurora_soar/orchestrator.py:1-100)\n- Phase data logged but not carried between queries\n- User approval gates prevent runaway execution (.aurora/AGENTS.md:45-51)\n\n### Industry Patterns for Multi-turn State\n\n**1. Session Management**:\n- Session IDs track conversation threads\n- Session store (Redis, SQLite) persists context\n- Example: OpenAI Assistants API, LangChain ConversationBufferMemory\n\n**2. Message History**:\n- Append-only conversation logs\n- Recent messages included in context window\n- Example: Anthropic Conversations API, Vercel AI SDK\n\n**3. External Memory**:\n- Vector stores for semantic retrieval (Pinecone, Weaviate)\n- Knowledge graphs for structured relationships\n- RAG (Retrieval-Augmented Generation) patterns\n\n**4. Stateless with Context Injection**:\n- Each request is independent\n- Required context passed explicitly\n- Aurora's approach: orchestrator injects minimal context (.claude/CLAUDE.md:156-172)\n\n**5. Checkpointing**:\n- Save intermediate state to resume workflows\n- Example: LangGraph persistent checkpoints, Temporal workflow state\n\nAurora uses **Stateless + External Memory** (ACT-R store) + **Explicit Context Injection** (orchestrator passes minimal context per agent invocation). This avoids shared state complexity while enabling knowledge persistence across sessions.\n",
          "data": {},
          "confidence": 0.85,
          "execution_metadata": {
            "duration_ms": 494494,
            "exit_code": 0,
            "fallback": false,
            "retry_count": 0,
            "original_agent": null
          },
          "error": null
        }
      ],
      "execution_metadata": {
        "total_duration_ms": 494494,
        "total_subgoals": 6,
        "failed_subgoals": 0,
        "fallback_count": 0
      },
      "user_interactions": [],
      "fallback_agents": [],
      "_timing_ms": 0,
      "_error": null,
      "agents_executed": 6
    },
    "phase6_synthesize": {
      "answer": "## Differences Between MD-File and Python-Script Subagents\nThe codebase uses two complementary agent systems with fundamentally different roles:\n**Markdown Agents** (`~/.claude/agents/*.md`) are declarative, LLM-interpreted personas:\n- **Structure**: YAML frontmatter (id, role, goal, category, capabilities) + natural language instructions\n- **Purpose**: Runtime instructions for Claude Code to adopt specific personas (QA, full-stack-dev, orchestrator)\n- **Activation**: Mention `@agent-id` or \"As agent-id, ...\" in prompts\n- **State**: Completely stateless - each Task tool invocation starts fresh with full instructions reloaded\n- **Discovery**: Scanned by `AgentScanner` (Agent: full-stack-dev) from 20+ configured directories, cached in `.aurora/cache/agent_manifest.json`\n- **Execution**: Spawned as subprocesses via Claude Code SDK, with context injected through prompts\n- **Pros**: Easy to author, version-controllable, no code required\n- **Cons**: Expensive (full LLM call per invocation), no persistent state, subprocess overhead\n**Python Agents** (`packages/cli/src/aurora_cli/planning/agents.py`, `packages/soar/src/aurora_soar/`) are programmatic metadata registries:\n- **Structure**: `AgentInfo` Pydantic models with structured capability lists\n- **Purpose**: Enable algorithmic agent selection via keyword matching + optional LLM fallback (Agent: full-stack-dev)\n- **Matching**: Weighted overlap scoring (goal/when_to_use = 2x weight, capabilities = 1x) with 0.0-1.0 confidence\n- **Discovery**: `ManifestManager` scans project-specific `agents.json` files, maintains in-memory registry\n- **Execution**: In-process Python code - no subprocess overhead, but actual agent work still goes through LLM\n- **Pros**: Fast capability matching, can maintain instance state, type-safe validation\n- **Cons**: Requires code changes to extend, not directly consumable by external tools\n**Critical Insight** (Agent: holistic-architect): MD files define *what agents should do* (prompts), Python scripts define *which agent to choose* (metadata + routing logic). The systems solve different problems in Aurora's architecture.\n## How Companies Solve Stateless/Multi-Turn Queries\nAurora implements **stateless execution with persistent memory** - the industry-standard pattern for LLM systems (Agent: business-analyst):\n### Aurora's Architecture\n**Single-Query State Management**:\n- 7-phase SOAR pipeline (`packages/soar/src/aurora_soar/orchestrator.py`) - each phase is stateless with explicit context passing\n- Context dictionary accumulates outputs across phases (assess \u2192 retrieve \u2192 decompose \u2192 verify \u2192 collect \u2192 synthesize \u2192 respond)\n- Phase data logged to `.aurora/logs/conversations/YYYY/MM/` but NOT reused across queries (Agent: full-stack-dev)\n**POC Multi-Turn Pattern** (`src/aurora_mcp/multiturn_poc.py`):\n```python\n# Python controls the loop, makes separate API calls\nphase1 = call_llm(\"Assess complexity...\")  # Call 1\nphase2 = call_llm(\"Decompose\", previous=phase1)  # Call 2 with context\nphase3 = call_llm(\"Synthesize\", previous=[phase1, phase2])  # Call 3\n```\n**Key insight**: \"Claude doesn't need to 'remember' - we FORCE it\" through explicit context injection (Agent: business-analyst)\n**Cross-Session Memory**:\n- ACT-R memory store (`packages/core/src/aurora_core/store/sqlite.py`) provides activation-based retrieval (recency + frequency)\n- BM25 + optional semantic search retrieves 5-20 relevant chunks per query\n- No conversation threading - each `aur soar` invocation is independent\n### Industry Solutions\nAll major systems follow the same pattern: **Stateless LLM Compute + Stateful Storage Layer** (Agent: full-stack-dev)\n**Common Approaches**:\n1. **Session Management** (OpenAI Assistants, Claude Projects):\n- Backend stores conversation threads in database\n- Each API call includes full message history\n- Vector stores per thread for RAG\n2. **External Memory Systems** (Langchain, LlamaIndex):\n- `ConversationBufferMemory` appends messages to buffer\n- Recent N messages included in context window\n- Summarization when approaching token limits\n3. **Agentic Frameworks** (AutoGPT, LangGraph):\n- Task queue with persistent state\n- State graphs with explicit transitions\n- Checkpoint/resume capabilities\n4. **Context Injection** (Aurora's approach):\n- Python orchestrator controls multi-turn flow\n- Retrieves relevant context from memory store\n- Passes minimal, targeted context to each stateless LLM call\n- Agent: holistic-architect notes this avoids \"shared state complexity while enabling knowledge persistence\"\n**Why Stateless?**\n- Horizontal scalability (no session affinity required)\n- Cost efficiency (pay per query, not per session)\n- No stale state management complexity\n- Works within token limits\n**Performance Trade-offs** (Agent: full-stack-dev):\n- \u2705 Scales horizontally, no session affinity\n- \u2705 No state synchronization bugs\n- \u274c Every query pays retrieval cost\n- \u274c No true \"learning\" - sophisticated context retrieval, not adaptation\n### Aurora's Distinctive Design\nUnlike ChatGPT-style persistent sessions, Aurora uses **memory-first planning** (Agent: business-analyst):\n1. Index codebase once \u2192 persistent ACT-R store\n2. Query triggers multi-phase pipeline with intermediate state\n3. Each phase stateless \u2192 orchestrator aggregates\n4. Session cache only for active query\n5. Local-first operation (can run without LLM via keyword matching)\nThe philosophy: \"Stateless execution with comprehensive memory retrieval beats stateful conversation tracking for code-related queries, because relevant context is in the codebase, not in previous turns\" (Agent: full-stack-dev)",
      "confidence": 0.93,
      "traceability": [
        {
          "agent": "full-stack-dev",
          "subgoal_id": 0,
          "subgoal_description": "Analyze markdown-based subagent definitions in the codebase to understand structure and capabilities"
        },
        {
          "agent": "full-stack-dev",
          "subgoal_id": 1,
          "subgoal_description": "Analyze Python-based subagent implementations to understand programmatic structure and runtime behavior"
        },
        {
          "agent": "holistic-architect",
          "subgoal_id": 2,
          "subgoal_description": "Compare and contrast the two approaches: flexibility, maintainability, execution model, and use cases"
        },
        {
          "agent": "business-analyst",
          "subgoal_id": 3,
          "subgoal_description": "Research industry patterns for stateless query handling: session management, context serialization, state machines"
        },
        {
          "agent": "business-analyst",
          "subgoal_id": 4,
          "subgoal_description": "Research industry patterns for multi-turn conversations: context windows, memory systems, conversation threading"
        },
        {
          "agent": "holistic-architect",
          "subgoal_id": 5,
          "subgoal_description": "Synthesize findings into architectural recommendations for Aurora's agent system"
        }
      ],
      "metadata": {
        "retry_count": 0,
        "verification_score": 0.93,
        "coherence": 0.9,
        "completeness": 0.95,
        "factuality": 0.95,
        "subgoals_completed": 6,
        "subgoals_partial": 0,
        "subgoals_failed": 0,
        "total_files_modified": 0,
        "user_interactions_count": 0
      },
      "timing": {
        "duration_ms": 78121,
        "started_at": 1768256072.4310718,
        "completed_at": 1768256150.5528662,
        "input_tokens": 74,
        "output_tokens": 1401
      },
      "_timing_ms": 0,
      "_error": null
    },
    "phase7_record": {
      "cached": true,
      "reasoning_chunk_id": "summary_6fce4b4a967a4be3",
      "pattern_marked": true,
      "activation_update": 0.2,
      "timing": {
        "duration_ms": 0,
        "started_at": 1768256150.566705,
        "completed_at": 1768256150.5672956
      },
      "_timing_ms": 0,
      "_error": null
    },
    "phase8_respond": {
      "verbosity": "normal",
      "formatted": true
    }
  },
  "timestamp": 1768256150.5790293
}
```
