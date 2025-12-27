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

- **docs/architecture/SOAR_ARCHITECTURE.md** - 9-phase orchestration pipeline
- **docs/architecture/API_CONTRACTS_v1.0.md** - API reference and contracts
- **docs/architecture/AGENT_INTEGRATION.md** - Agent formats and execution
- **docs/actr-activation.md** - ACT-R memory activation scoring details
- **docs/CI_ARCHITECTURE.md** - CI/CD pipeline design

## Development

### Testing & Quality

- **docs/development/TESTING.md** - Comprehensive testing guide (philosophy, test pyramid, principles, anti-patterns, DI examples)
- **docs/development/TEST_REFERENCE.md** - Complete test catalog (2,369 tests, coverage matrix, test statistics)
- **docs/development/TECHNICAL_DEBT_COVERAGE.md** - Coverage gap analysis (81.06% vs 85% target, prioritized recommendations)
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
- **docs/cli/QUICK_START.md** - Quick start for CLI users
- **docs/cli/ERROR_CATALOG.md** - Error messages and solutions

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
- Check docs/architecture/SOAR_ARCHITECTURE.md for system design
- Review docs/improvement-areas.md for known limitations
