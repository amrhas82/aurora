# Aurora Architecture Documentation

## SOAR Orchestration: Dual Approach Design

Aurora implements SOAR (Search, Observe, Act, Record) query processing using **two coexisting orchestration approaches**, each serving distinct use cases. This design was clarified during PRD-0024 (MCP Tool Deprecation) to prevent accidental deletion of critical infrastructure.

### 1. Bash Orchestration (Terminal Command)

**Command**: `aur soar "your question"`

**Architecture**:
- Implemented in: `scripts/soar-query.sh`
- Orchestration: Shell script coordinates 5 separate Claude CLI invocations
- Phase execution: Bash script manages state between phases
- Output: Formatted terminal output with progress indicators

**Use Case**:
- Interactive terminal usage
- Manual query execution
- Development and testing
- User-facing command-line interface

**Characteristics**:
- Simple bash-based coordination
- Direct CLI tool invocations
- Human-readable progress output
- No Python library dependencies for execution

### 2. Python Orchestration (Library/Programmatic)

**Class**: `SOAROrchestrator` in `packages/soar/src/aurora_soar/orchestrator.py`

**Architecture**:
- Phase handlers: 9 Python modules in `packages/soar/src/aurora_soar/phases/`
  - `assess.py` - Phase 1: Complexity Assessment
  - `retrieve.py` - Phase 2: Context Retrieval
  - `decompose.py` - Phase 3: Query Decomposition
  - `verify.py` - Phase 4: Decomposition Verification
  - `route.py` - Phase 5: Agent Routing
  - `collect.py` - Phase 6: Agent Execution
  - `synthesize.py` - Phase 7: Result Synthesis
  - `record.py` - Phase 8: ACT-R Pattern Caching
  - `respond.py` - Phase 9: Response Formatting
- Orchestration: Python class manages phase transitions and data flow
- Phase execution: Direct Python function calls
- Output: Structured Python objects and JSON

**Use Case**:
- Programmatic integration
- Library embedding in other Python applications
- Fine-grained control over phase execution
- Testing and benchmarking with direct phase access

**Characteristics**:
- Full Python API
- Programmatic control over each phase
- Structured data flow between phases
- Importable as Python library

### Why Both Approaches Coexist

**DO NOT DELETE phase handlers** - they are actively used by `SOAROrchestrator` for:
1. Programmatic/library integration use cases
2. Direct testing of individual SOAR phases
3. Future programmatic query APIs
4. Fine-grained phase benchmarking

The bash orchestration (`aur soar`) provides a simpler user experience for terminal users, while the Python orchestration (`SOAROrchestrator`) enables programmatic integration and testing.

### MCP Tool Deprecation Context (PRD-0024)

During MCP tool deprecation, we removed 3 MCP tools:
- `aurora_query` → replaced by `aur soar` terminal command
- `aurora_search` → replaced by `/aur:search` slash command
- `aurora_get` → replaced by `/aur:get` slash command

**Critical**: The phase handler files in `packages/soar/src/aurora_soar/phases/` were preserved because:
1. They serve the Python `SOAROrchestrator` library use case
2. They enable programmatic SOAR integration
3. They support direct phase-level testing
4. They may be used by future programmatic APIs

The bash orchestration (`aur soar`) and Python orchestration (`SOAROrchestrator`) serve **different purposes** and both remain valid approaches.

### Decision Matrix: Which Orchestration to Use?

| Use Case | Recommended Approach | Reason |
|----------|---------------------|--------|
| Terminal user queries | `aur soar "question"` | Simple, formatted output |
| Programmatic integration | `SOAROrchestrator` | Python API, structured data |
| Testing individual phases | `SOAROrchestrator` + phase handlers | Direct phase access |
| CI/CD pipeline | `aur soar` or both | Depends on testing needs |
| Library embedding | `SOAROrchestrator` | Importable Python library |
| Interactive development | `aur soar "question"` | Fast, human-readable |

### Related Documentation

- **PRD-0024**: MCP Tool Deprecation and slash command migration
- **MCP_DEPRECATION.md**: Rationale for deprecating MCP tools
- **MIGRATION.md**: User guide for migrating from MCP tools
- **TESTING.md**: Test classification and phase handler testing strategy

---

**Last Updated**: PRD-0024 (January 2026)
**Maintainers**: Aurora Core Team
