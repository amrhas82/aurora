# AURORA Framework PRD - Content Index

**File**: `/home/hamr/tasks/AURORA-Framework-PRD.md` (3043 lines)

## Complete Table of Contents

### 1. Executive Summary (p.1)
- Problem Statement: Three critical limitations in current AI agent systems
- Solution: Five-layer AURORA framework
- Key Features: SOAR, ACT-R, File Persistence, Pluggable LLM, Metrics, CLI-First
- Target Users

### 2. Architecture Deep Dive (p.2-25)
**Five-Layer System**:
- **LAYER 1**: Assessment & Discovery
  - Query assessment (complexity analysis)
  - Agent registry & discovery (global + local)
  - Semantic matching algorithm
  - Agent registry JSON schema

- **LAYER 2**: ACT-R Learning & Memory (COMPLETE IMPLEMENTATION)
  - Activation equation: Base_Level + Spreading + Boosts - Decay
  - Full formula with all components explained
  - Example calculation shown
  - Utility learning system
  - Memory persistence (in-memory + disk)
  - ACT-R store JSON schema

- **LAYER 3**: SOAR Problem-Space Reasoner (COMPLETE)
  - SOAR cycle: Elaboration → Decision → Application
  - Impasse detection (4 types: Conflict, Constraint, No-Change, Insufficient-Info)
  - Preference semantics (absolute, partial, context)
  - Preference score calculation
  - Chunking mechanism (learning from solved problems)

- **LAYER 4**: SOAR-Assist Orchestration
  - Orchestration state machine (11 phases)
  - Multi-turn conversation management
  - Context threading across agents
  - **Task File Writing** (CRITICAL FEATURE)
    - Permanent reference files for every task
    - Complete file schema with all metadata
    - Directory structure: ~/.aurora/tasks/YYYY/MM/DD/
  - Feedback synthesis (implicit + explicit → LLM synthesis)

- **LAYER 5**: LLM Integration Layer
  - LLM provider abstraction (Claude, GPT-4, others)
  - Configuration & selection
  - Synthesis & fallback chains
  - Always guarantee response

### 3. Agent Discovery & Registry System (p.26-28)
- Discovery protocol (3 phases: global, local, runtime matching)
- Agent metadata structure (with AURORA augmentation)
- Registry JSON schema with activation/utility tracking

### 4. Multi-Turn Conversation Management (p.28-31)
- Stateful session management with persistence
- WorkingMemory class for context threading
- Session recovery & resumption

### 5. CLI Interface Specification (p.31-36)
**Core Commands** (all implemented):
- `aurora "<query>"` - Basic invocation
- `aurora --interactive` - Multi-turn REPL
- `aurora --verbose` - Show reasoning
- `aurora stats agent <id>` - Agent metrics
- `aurora stats learning --days 7` - Learning velocity
- `aurora stats satisfaction` - User satisfaction
- `aurora task list` - Task history
- `aurora task show <task_id>` - Task details

**Output Format**: Examples for all command types

### 6. File Structure & Persistence (p.36-40)
- Complete directory tree: ~/.aurora/
  - config/ - Configuration files
  - agents/ - Agent registry
  - memory/ - ACT-R persistent store
  - sessions/ - Multi-turn conversation state
  - tasks/ - Task execution logs (dated hierarchy)
  - logs/ - System logging
- Configuration file examples
- Aurora.json schema with all ACT-R parameters

### 7. Full ACT-R Learning System Details (p.40-48)
**Complete Activation Calculation**:
- Base_Level formula: ln(Σ(t_i^-d))
- Spreading activation: Σ(S_j × w_j)
- Context boosts (domain, recency, success, relevance)
- Decay formula: k × ln(t)
- Example calculations with real numbers
- Complete Python implementation (not pseudocode)

**Utility Learning**:
- Bayesian update mechanism
- Domain-specific utility tracking
- Success/failure recording
- Cost and time penalties
- Python implementation with Bayesian weighting

### 8. Fallback & Graceful Degradation (p.48-52)
- Complete fallback chain (5-level: Full AURORA → Partial Orchestration → Primary LLM → Fallback LLM → SOAR-Assist)
- ALWAYS return response guarantee
- Error tracking and logging
- Confidence scoring for each fallback level

### 9. Success Metrics & Queryable Statistics (p.52-68)
**Metrics Architecture** (Production-Ready):
- User Satisfaction Metrics
  - Explicit satisfaction tracking (1-5 scale)
  - Thank you signals
  - Follow-up quality scoring
  - Solution reuse tracking
  - NPS calculation

- System Efficiency Metrics
  - Per-agent invocation tracking
  - Response time monitoring
  - Cost tracking
  - Agent efficiency dashboard

- Learning Velocity Metrics
  - Pattern discovery tracking
  - ACT-R activation changes
  - Learning acceleration detection

- System Health Metrics
  - Task completion rates
  - Success rates
  - Fallback usage frequency

**CLI Commands** (with pseudocode):
- `aurora stats agent <id>`
- `aurora stats learning --days 7`
- `aurora stats satisfaction`
- `aurora task list [filters]`
- `aurora task show <task_id>`

### 10. Execution Flows (p.68-92)
**Three Complete Scenarios with Full Walkthrough**:

1. **Simple Query Flow** (No decomposition needed)
   - "What is the capital of France?"
   - Direct LLM invocation, minimal overhead

2. **Complex Query Flow** (Full AURORA pipeline)
   - "Create market analysis for AI tools"
   - Complete walkthrough of all 8 phases
   - SOAR impasse detection and resolution
   - Agent orchestration with dependency management
   - Synthesis and feedback gathering
   - Task file creation

3. **Medium Query Flow** (Adaptive feedback)
   - "Should we use Python or Rust?"
   - Shows SOAR insufficient-info impasse
   - Adaptive feedback questions to user
   - Re-evaluation with user constraints
   - Learning from clarifications

### 11. Declarative States (p.92-94)
- Full state tree showing all AURORA phases
- Visible to user in --verbose mode
- Examples of state progression

### 12. Implementation Pseudocode (p.94-110)
**4 Complete Implementations**:

1. **Main AURORA Orchestration Loop** (100+ lines)
   - Full state machine implementation
   - SOAR reasoning with elaboration/decision
   - Impasse detection and handling
   - Agent orchestration with dependency tracking
   - Synthesis and feedback collection
   - Task file writing

2. **ACT-R Activation Calculation** (30+ lines)
   - All 4 components (base-level, spreading, boosts, decay)
   - Realistic parameter values
   - Clamping and normalization

3. **SOAR Decision Cycle** (20+ lines)
   - Rule matching and firing
   - Operator proposal and evaluation
   - Preference semantics
   - Impasse diagnosis

4. **Task File Writing** (50+ lines)
   - Complete task file structure
   - All metadata collected
   - Disk persistence
   - Dated directory organization

### 13. Testing Strategy & Validation (p.110-115)
**3 Test Categories**:
- Unit Tests (ACT-R activation, SOAR impasse detection, utility learning)
- Integration Tests (Full orchestration, agent discovery, multi-turn)
- Success Metrics with Targets:
  - System success rate > 90%
  - Avg response time < 8s
  - Agent utility improvement +5% per week
  - User NPS > 40
  - Fallback usage < 10%
  - Learning velocity 3+ patterns/week

### 14. Known Limitations & Future Work (p.115-118)
**Phase 1 Limitations**:
- No RAG integration
- No multi-agent collaboration patterns
- No GUI dashboard
- CLI-only

**Phase 2: RAG Integration** (Planned)
- External knowledge base search on impasse
- Vector DB for chunk storage

**Phase 3: Multi-Agent Collaboration** (Planned)
- Parallel execution patterns
- Voting/consensus mechanisms
- Debate patterns
- Hierarchical delegation

### 15. Declarative Schema Summary (p.118-123)
**3 Key JSON Schemas**:
- Agent Registry Entry
- Task Execution File
- ACT-R Memory Chunk

---

## Key Highlights

### Addresses All 10 Scope Answers
1. ✓ Full AURORA framework (not phased)
2. ✓ Full SOAR with impasse detection, chunking, preference semantics
3. ✓ Internal agents + local discovery (expandable)
4. ✓ Pluggable LLM (Claude, GPT-4, others)
5. ✓ Full ACT-R (activation equations, utility learning, decay)
6. ✓ Hybrid stateful persistence with disk serialization
7. ✓ Fallback always available (SOAR-Assist + LLM)
8. ✓ Hybrid adaptive feedback (implicit + explicit)
9. ✓ All metrics equally important with queryable stats
10. ✓ CLI-optimized for agent-to-agent communication

### Critical Innovations
- **Task File Writing**: Every orchestration creates permanent reference file
- **LLM Synthesis Feedback**: Feedback synthesized by LLM for clarity
- **Queryable Metrics**: CLI commands to assess system usefulness
- **Full ACT-R**: Complete activation equations with example calculations
- **SOAR Impasse Handling**: Recursive problem decomposition when stuck

### Production-Ready Elements
- Complete JSON schemas for all data structures
- Full Python/pseudocode implementations (not simplified)
- Real parameter values (decay=0.5, etc.)
- Example calculations with numbers
- Integration points clearly marked
- Error handling and fallbacks specified
- Testing strategy with success criteria
- CLI command specifications

---

## File Statistics
- **Total Lines**: 3043
- **Sections**: 16 major
- **JSON Schemas**: 3
- **Pseudocode Implementations**: 4
- **Execution Flow Scenarios**: 3
- **CLI Commands Specified**: 10+
- **Architectural Diagrams**: 3
- **Tables**: 5+

## Ready for Handoff
This PRD is complete and ready for:
1. Development team implementation
2. Architecture review
3. Task breakdown via `2-generate-tasks` agent
4. Iterative implementation starting with Layer 1

---

**Created**: 2025-12-08
**Status**: PRODUCTION-READY SPECIFICATION
**Next Step**: Invoke `2-generate-tasks` agent to create detailed task breakdown
