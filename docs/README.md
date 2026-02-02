# Aurora Documentation

Welcome to the Aurora documentation. Aurora is a memory-first planning and multi-agent orchestration framework for AI coding assistants.

## Quick Start

1. **[3 Simple Steps](04-process/getting-started/3-SIMPLE-STEPS.md)** - Get started in 5 minutes
2. **[Quick Start Guide](04-process/getting-started/QUICK_START.md)** - Detailed setup instructions
3. **[CLI Usage Guide](02-features/cli/CLI_USAGE_GUIDE.md)** - Complete CLI reference

---

## Documentation Structure

```
docs/
├── 00-context/        # WHY - Vision, architecture, assumptions
├── 01-product/        # WHAT - Product requirements
├── 02-features/       # HOW - Feature documentation
├── 03-logs/           # MEMORY - Implementation history
└── 04-process/        # WORKFLOW - Development & usage guides
```

---

## 00-context: Project Context

Understanding Aurora's purpose and architecture.

| Document | Description |
|----------|-------------|
| [Vision](00-context/vision.md) | Purpose, goals, and boundaries |
| [System State](00-context/system-state.md) | Current architecture and implementation |
| [Assumptions](00-context/assumptions.md) | Constraints, decisions, and risks |

---

## 01-product: Product Requirements

| Document | Description |
|----------|-------------|
| [PRD](01-product/prd.md) | Core features and requirements |

---

## 02-features: Feature Documentation

### CLI Commands

| Document | Description |
|----------|-------------|
| [Commands Reference](02-features/cli/COMMANDS.md) | All `aur` commands |
| [CLI Usage Guide](02-features/cli/CLI_USAGE_GUIDE.md) | Detailed CLI usage |
| [aur goals](02-features/cli/aur-goals.md) | Goal decomposition command |
| [aur soar](02-features/cli/aur-soar.md) | SOAR pipeline command |
| [aur spawn](02-features/cli/aur-spawn.md) | Parallel execution command |

### Memory System

| Document | Description |
|----------|-------------|
| [ACT-R Activation](02-features/memory/ACTR_ACTIVATION.md) | Cognitive memory model |
| [Caching Guide](02-features/memory/CACHING_GUIDE.md) | Cache configuration |
| [ML Models](02-features/memory/ML_MODELS.md) | Embedding models |

### SOAR Pipeline

| Document | Description |
|----------|-------------|
| [SOAR Guide](02-features/soar/SOAR.md) | 9-phase pipeline usage |
| [SOAR Architecture](02-features/soar/SOAR_ARCHITECTURE.md) | Technical architecture |

### Agent System

| Document | Description |
|----------|-------------|
| [Tools Guide](02-features/agents/TOOLS_GUIDE.md) | Supported CLI tools |
| [Agent Integration](02-features/agents/AGENT_INTEGRATION.md) | Multi-agent patterns |

### Other Features

| Document | Description |
|----------|-------------|
| [Flows](02-features/FLOWS.md) | Workflow patterns |
| [Cost Tracking](02-features/COST_TRACKING_GUIDE.md) | LLM cost monitoring |
| [Early Detection](02-features/EARLY_DETECTION.md) | Issue detection |
| [Friction Detection](02-features/FRICTION_DETECTION.md) | UX friction tracking |

---

## 03-logs: Implementation History

| Document | Description |
|----------|-------------|
| [Implementation Log](03-logs/implementation-log.md) | Code change history |
| [Decisions Log](03-logs/decisions-log.md) | Architectural decisions |
| [Bug Log](03-logs/bug-log.md) | Bug tracking |
| [Validation Log](03-logs/validation-log.md) | Post-release observations |
| [Insights](03-logs/insights.md) | Learnings and patterns |

---

## 04-process: Development & Usage

### Getting Started

| Document | Description |
|----------|-------------|
| [3 Simple Steps](04-process/getting-started/3-SIMPLE-STEPS.md) | Quickest path to using Aurora |
| [Quick Start](04-process/getting-started/QUICK_START.md) | Complete setup guide |
| [Installation Verification](04-process/getting-started/INSTALLATION_VERIFICATION_GUIDE.md) | Verify your setup |
| [ML Install](04-process/getting-started/ML_INSTALL.md) | Optional ML features |

### Development

| Document | Description |
|----------|-------------|
| [Development Guide](04-process/development/development.md) | Dev environment setup |
| [Development Workflow](04-process/development/DEVELOPMENT-WORKFLOW.md) | Daily dev process |
| [Testing Guide](04-process/development/TESTING_GUIDE.md) | Test organization |
| [CLI Testing Guide](04-process/development/CLI_TESTING_GUIDE.md) | CLI-specific testing |
| [Spawn Testing Guide](04-process/development/SPAWN_TESTING_GUIDE.md) | Spawn testing |
| [Test Reference](04-process/development/TEST_REFERENCE.md) | Test patterns |
| [Code Review Checklist](04-process/development/CODE_REVIEW_CHECKLIST.md) | Review criteria |
| [Extension Guide](04-process/development/EXTENSION_GUIDE.md) | Adding custom features |
| [Prompt Engineering](04-process/development/PROMPT_ENGINEERING_GUIDE.md) | LLM prompt design |
| [Error Catalog](04-process/development/ERROR_CATALOG.md) | Error reference |
| [Pre-Push Validation](04-process/development/PRE_PUSH_VALIDATION.md) | Pre-commit checks |
| [Publishing](04-process/development/PUBLISHING.md) | Release process |

### Migration

| Document | Description |
|----------|-------------|
| [Migration Guide v0.3.0](04-process/development/MIGRATION_GUIDE_v0.3.0.md) | v0.3.0 upgrade |
| [Phase 4 Migration](04-process/development/PHASE4_MIGRATION_GUIDE.md) | Phase 4 changes |

### Troubleshooting

| Document | Description |
|----------|-------------|
| [Troubleshooting](04-process/troubleshooting/TROUBLESHOOTING.md) | Common issues |
| [CLI Troubleshooting](04-process/troubleshooting/CLI_TROUBLESHOOTING.md) | CLI-specific issues |

### Reference

| Document | Description |
|----------|-------------|
| [Config Reference](04-process/reference/CONFIG_REFERENCE.md) | Configuration options |
| [API Contracts](04-process/reference/API_CONTRACTS_v1.0.md) | Public API specs |
| [MCP Setup](04-process/reference/MCP_SETUP.md) | MCP integration |
| [MCP Deprecation](04-process/reference/MCP_DEPRECATION.md) | MCP migration notes |
| [Migration](04-process/reference/MIGRATION.md) | Version migration |

### Performance

| Document | Description |
|----------|-------------|
| [Performance Testing](04-process/PERFORMANCE_TESTING.md) | Benchmark guide |
| [Performance Quick Ref](04-process/PERFORMANCE_QUICK_REF.md) | Quick reference |
| [Performance Tuning](04-process/PERFORMANCE_TUNING.md) | Optimization guide |
| [Release](04-process/RELEASE.md) | Release process |

---

## Package Documentation

Each package has its own README:

- [`packages/cli/README.md`](../packages/cli/README.md) - CLI commands
- [`packages/core/README.md`](../packages/core/README.md) - Core models and store
- [`packages/soar/README.md`](../packages/soar/README.md) - SOAR pipeline
- [`packages/context-code/README.md`](../packages/context-code/README.md) - Code indexing
- [`packages/context-doc/README.md`](../packages/context-doc/README.md) - Document parsing
- [`packages/reasoning/README.md`](../packages/reasoning/README.md) - LLM clients
- [`packages/planning/README.md`](../packages/planning/README.md) - Plan generation
- [`packages/spawner/README.md`](../packages/spawner/README.md) - Parallel execution
- [`packages/implement/README.md`](../packages/implement/README.md) - Sequential execution
- [`packages/testing/README.md`](../packages/testing/README.md) - Test utilities

---

## Quick Reference

### Common Commands

```bash
# Initialize project
aur init

# Index codebase
aur mem index .

# Search memory
aur mem search "query"

# Ask questions
aur soar "how does X work?"

# Plan goals
aur goals "implement feature Y"

# Check setup
aur doctor
```

### Key Files

| File | Purpose |
|------|---------|
| `.aurora/config.json` | Project configuration |
| `.aurora/memory.db` | Memory database |
| `.aurora/plans/` | Generated plans |
| `~/.aurora/config.json` | Global configuration |

---

**Last Updated**: February 2026
