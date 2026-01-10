# AURORA - Knowledge Base

Complete documentation index for AURORA project.

Last Updated: 2025-12-25 | Version: v0.2.0

---

## Getting Started

- **docs/MCP_SETUP.md** - Claude Code CLI integration via MCP (7 tools, no API key required)
- **docs/cli/QUICK_START.md** - 5-minute CLI setup guide (requires API key for queries)
- **docs/cli/CLI_USAGE_GUIDE.md** - Comprehensive command reference
- **docs/INSTALLATION_VERIFICATION_GUIDE.md** - Installation health checks

### MCP Tools vs CLI Commands

| Tool/Command | API Key? | Usage Context |
|--------------|----------|---------------|
| 7 MCP Tools | NO | Inside Claude Code CLI |
| `aur query` | YES | Standalone CLI |
| `aur mem` commands | NO | Standalone CLI |
| `aur headless` | YES | Standalone CLI |

## Architecture

- **docs/reference/SOAR_ARCHITECTURE.md** - 9-phase orchestration pipeline
- **docs/reference/API_CONTRACTS_v1.0.md** - API reference and contracts
- **docs/reference/AGENT_INTEGRATION.md** - Agent formats and execution
- **docs/actr-activation.md** - ACT-R memory activation scoring details
- **docs/CI_ARCHITECTURE.md** - CI/CD pipeline design

### BM25 Tri-Hybrid Memory Search (v0.3.0)

**Architecture**: Two-stage retrieval system combining BM25 lexical matching with semantic and activation-based ranking.

**Stage 1: BM25 Filtering**
- Code-aware tokenization (CamelCase, snake_case, dot notation, acronyms)
- Okapi BM25 scoring (k1=1.5, b=0.75)
- Filters top-100 candidates from corpus
- Optimized for exact identifier matches

**Stage 2: Tri-Hybrid Re-ranking**
- **BM25 (30%)**: Term frequency / inverse document frequency
- **Semantic (40%)**: Embedding similarity via sentence-transformers
- **Activation (30%)**: ACT-R cognitive model (frequency + recency)
- Final top-K results returned to user

**CLI Features**:
- `aur mem search "query"` - Default tri-hybrid search
- `aur mem search "query" --show-scores` - Show score breakdown
- `aur mem search "query" --type function` - Filter by element type

**Performance Targets**:
- Simple queries: <2s latency
- Complex queries: <10s latency
- Memory usage: <100MB for 10K chunks

**Implementation Files**:
- `packages/context-code/src/aurora_context_code/semantic/bm25_scorer.py` - BM25 implementation
- `packages/context-code/src/aurora_context_code/semantic/hybrid_retriever.py` - Staged retrieval
- `packages/context-code/src/aurora_context_code/knowledge_parser.py` - Markdown chunk parser
- `tests/unit/test_bm25_tokenizer.py` - 15 BM25 unit tests
- `tests/integration/test_e2e_search_quality.py` - MRR validation (target: ≥0.85)

## Development

### Testing & Quality

- **docs/development/TESTING.md** - Comprehensive testing guide (philosophy, test pyramid, principles, anti-patterns, DI examples)
- **docs/development/TEST_REFERENCE.md** - Complete test catalog (2,369 tests, coverage matrix, test statistics)
- **docs/development/TESTING_TECHNICAL_DEBT.md** - Coverage gap analysis (81.06% vs 85% target, prioritized recommendations)
- **docs/CLI_TESTING_GUIDE.md** - CLI-specific testing guide
- **docs/CLI_TEST_RESULTS.md** - CLI test results and analysis

**Test Suite Overview**:
- **Total Tests**: 2,369 (1,810 unit, 500 integration, 59 E2E)
- **Coverage**: 81.06% (Core: 86.8%, SOAR: 94%, Context-Code: 89.25%)
- **Quality Gates**: ✅ DI pattern, ✅ Real components, ✅ Python 3.10-3.13
- **Execution Time**: ~2-3 minutes (full suite)

### Extension & Migration

- **docs/development/EXTENSION_GUIDE.md** - Extending AURORA with new features
- **docs/development/PROMPT_ENGINEERING_GUIDE.md** - Template design patterns
- **docs/development/PHASE4_MIGRATION_GUIDE.md** - Upgrade guide
- **docs/development/CODE_REVIEW_CHECKLIST.md** - Quality gate checklist

## CLI Reference

- **docs/cli/CLI_USAGE_GUIDE.md** - Complete CLI command reference
  - **[Retrieval Quality Handling](cli/CLI_USAGE_GUIDE.md#retrieval-quality-handling)** - Interactive prompts for weak/missing context
  - **[Agent Discovery](cli/CLI_USAGE_GUIDE.md#agent-discovery)** - Multi-source agent discovery (`aur agents list/search/show/refresh`)
- **docs/cli/QUICK_START.md** - Quick start for CLI users
- **docs/cli/ERROR_CATALOG.md** - Error messages and solutions

### Agent Discovery (v0.3.0)

**Purpose**: Discover and manage AI coding assistant agents from multiple sources.

**Supported Sources**:
- `~/.claude/agents/` - Claude Code CLI agents
- `~/.config/ampcode/agents/` - AMP Code agents
- `~/.config/droid/agent/` - Droid agents
- `~/.config/opencode/agent/` - OpenCode agents

**CLI Commands**:
- `aur agents list` - List all agents grouped by category
- `aur agents search "keyword"` - Search agents by keyword
- `aur agents show <agent-id>` - Display full agent details
- `aur agents refresh` - Force regenerate manifest

**Features**:
- Field aliasing: `name`→`id`, `description`→`goal` (backward compatible)
- Auto-refresh based on configurable interval (default: 24 hours)
- Fuzzy suggestions when agent not found
- Graceful degradation for malformed files
- Manifest caching for performance (~37ms discovery)

**Implementation Files**:
- `packages/cli/src/aurora_cli/agent_discovery/models.py` - AgentInfo, AgentManifest Pydantic models
- `packages/cli/src/aurora_cli/agent_discovery/scanner.py` - Multi-source file discovery
- `packages/cli/src/aurora_cli/agent_discovery/parser.py` - Frontmatter parsing with validation
- `packages/cli/src/aurora_cli/agent_discovery/manifest.py` - Manifest generation and caching
- `packages/cli/src/aurora_cli/commands/agents.py` - CLI commands

## Troubleshooting

- **docs/TROUBLESHOOTING.md** - Common issues and solutions
- **docs/improvement-areas.md** - Known limitations and improvement areas
- **docs/TECHNICAL_DEBT.md** - Technical debt tracking
- **docs/ISSUES_TESTING.md** - Testing issues documentation
- **docs/USER_TESTING_SUMMARY.md** - User testing feedback

## Project Management

- **docs/COMPREHENSIVE_FIX_PLAN.md** - Ongoing fix plan
- **docs/MCP_INTEGRATION_PLAN.md** - MCP integration roadmap
- **docs/PRD_INPUT_CLI_FIXES_MCP.md** - PRD for CLI and MCP improvements
- **docs/PRD_QUESTIONS.md** - Open questions for PRDs
- **docs/PUBLISHING.md** - PyPI publishing guide

## Performance

- **docs/performance/** - Performance benchmarking documentation

## Examples

- **docs/examples/** - Usage examples and code samples

## Release History

### Phase 2 (Current - v0.2.0)
- **docs/phases/phase2/RELEASE_NOTES_v0.2.0.md** - Latest release notes
- **docs/phases/phase2/** - Phase 2 documentation

### Phase 1 (Historical)
- **docs/phases/phase1/** - Phase 1 archives

### Phase 3 (Historical)
- **docs/phases/phase3/** - Phase 3 archives
- **docs/phases/phase3/CODE_REVIEW_REPORT_v1.0.0-phase3.md** - Phase 3 code review
- **docs/phases/phase3/SECURITY_AUDIT_REPORT_v1.0.0-phase3.md** - Security audit
- **docs/phases/phase3/PHASE3_ARCHIVE_MANIFEST.md** - Phase 3 archive manifest

## Research Archives

Advanced research and exploration (historical, not required for development):

- **docs/agi-problem/aurora/** - AURORA framework research
- **docs/agi-problem/research/** - Cognitive architecture research
- **docs/agi-problem/research/soar_act-r/** - SOAR/ACT-R integration research
- **docs/agi-problem/archive/** - Archived research materials

## Project Status

- **docs/project-status/** - Current project status tracking

---

**Navigation Tips**:
- Start with docs/MCP_SETUP.md for Claude Code CLI integration
- Read docs/cli/QUICK_START.md for standalone CLI usage
- Reference docs/TROUBLESHOOTING.md when issues arise
- Check docs/reference/SOAR_ARCHITECTURE.md for system design
- Review docs/improvement-areas.md for known limitations
