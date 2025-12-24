# Aurora Documentation Index

Welcome to the Aurora documentation. This directory contains comprehensive documentation for the Aurora project, organized by topic and phase.

## Quick Navigation

- [Architecture](#architecture) - System design and technical architecture
- [Development](#development) - Developer guides and best practices
- [Deployment](#deployment) - Production deployment and operations
- [Guides](#guides) - User guides and troubleshooting
- [Reports](#reports) - Quality, performance, security, and testing reports
- [Phases](#phases) - Phase-specific documentation and retrospectives
- [Tasks](#tasks) - Task completion reports and status tracking
- [AGI Problem](#agi-problem) - Research and design documentation
- [Examples](#examples) - Usage examples and code samples

---

## Architecture

Technical architecture, API contracts, and system design documentation.

**Location:** `/docs/architecture/`

- [SOAR Architecture](./architecture/SOAR_ARCHITECTURE.md) - Core SOAR-based cognitive architecture
- [API Contracts v1.0](./architecture/API_CONTRACTS_v1.0.md) - Public API specifications and contracts
- [Agent Integration](./architecture/AGENT_INTEGRATION.md) - Multi-agent integration patterns

---

## Development

Developer guides, code review checklists, and development best practices.

**Location:** `/docs/development/`

- [Testing Guide](./development/TESTING.md) - **NEW** - Comprehensive testing documentation
- [Extension Guide](./development/EXTENSION_GUIDE.md) - How to extend Aurora with custom functionality
- [Code Review Checklist](./development/CODE_REVIEW_CHECKLIST.md) - Quality gates and review criteria
- [Prompt Engineering Guide](./development/PROMPT_ENGINEERING_GUIDE.md) - Best practices for prompt design
- [Prompt Template Review](./development/PROMPT_TEMPLATE_REVIEW.md) - Analysis of prompt templates
- [Phase 4 Migration Guide](./development/PHASE4_MIGRATION_GUIDE.md) - Migration guide for Phase 4 features

### Examples
- [Activation Usage](./examples/activation_usage.md) - How to use ACT-R activation mechanisms

---

## Deployment

Production deployment guides, operational procedures, and troubleshooting.

**Location:** `/docs/deployment/`

- [Production Deployment](./deployment/production-deployment.md) - Production deployment procedures
- [Headless Mode](./deployment/headless-mode.md) - Running Aurora in headless mode
- [Advanced Troubleshooting](./deployment/troubleshooting-advanced.md) - Advanced debugging techniques

---

## Guides

User guides, troubleshooting resources, and operational guidance.

**Location:** `/docs/guides/`

- [Troubleshooting](./guides/TROUBLESHOOTING.md) - Common issues and solutions
- [Cost Tracking Guide](./guides/COST_TRACKING_GUIDE.md) - How to track and optimize LLM costs
- [Performance Tuning](./guides/performance-tuning.md) - Performance optimization techniques

---

## Reports

### Quality Reports

Code reviews, quality gates, acceptance testing, and delivery verification.

**Location:** `/docs/reports/quality/`

- [Code Review Report](./reports/quality/CODE_REVIEW_REPORT.md) - General code review findings
- [Code Review Report Phase 3](./reports/quality/CODE_REVIEW_REPORT_v1.0.0-phase3.md) - Phase 3 code review
- [Quality Gates Report](./reports/quality/QUALITY_GATES_REPORT.md) - Quality gate metrics and status
- [Acceptance Test Report](./reports/quality/ACCEPTANCE_TEST_REPORT.md) - Acceptance testing results
- [Delivery Checklist](./reports/quality/DELIVERY_CHECKLIST.md) - Pre-delivery verification checklist
- [Verification Checkpoints](./reports/quality/VERIFICATION_CHECKPOINTS.md) - Quality verification checkpoints

### Performance Reports

Performance profiling, benchmarking, and optimization analysis.

**Location:** `/docs/performance/`

- [Memory Profiling Report](./performance/MEMORY_PROFILING_REPORT.md) - Memory usage analysis and optimization
- [Performance Profiling Report](./performance/PERFORMANCE_PROFILING_REPORT.md) - Performance benchmarks
- [Verification Calibration Report](./performance/VERIFICATION_CALIBRATION_REPORT.md) - Verification system calibration
- [Embedding Benchmark Results](./performance/embedding-benchmark-results.md) - Embedding model benchmarks
- [Hybrid Retrieval Precision Report](./performance/hybrid-retrieval-precision-report.md) - Retrieval accuracy metrics
- [Live Data Validation Checklist](./performance/live-data-validation-checklist.md) - Production data validation

### Security Reports

Security audits, vulnerability assessments, and compliance.

**Location:** `/docs/reports/security/`

- [Security Audit Checklist](./reports/security/SECURITY_AUDIT_CHECKLIST.md) - Security review checklist
- [Security Audit Report Phase 3](./reports/security/SECURITY_AUDIT_REPORT_v1.0.0-phase3.md) - Phase 3 security audit

### Testing Reports

Test coverage analysis, validation reports, and test documentation.

**Location:** `/docs/reports/testing/`

- [Coverage Analysis](./reports/testing/COVERAGE_ANALYSIS.md) - **NEW** - Comprehensive coverage metrics explanation
- [ACT-R Formula Validation](./reports/testing/actr-formula-validation.md) - ACT-R formula correctness validation

---

## Phases

Phase-specific documentation, retrospectives, and migration guides organized by development phase.

### Phase 1 - Foundation

**Location:** `/docs/phases/phase1/`

- [Phase 1 Archive](./phases/phase1/PHASE1_ARCHIVE.md) - Archived Phase 1 documentation
- [Phase 1 Verification Report](./phases/phase1/PHASE1_VERIFICATION_REPORT.md) - Phase 1 completion verification
- [Release Notes v1.0.0-phase1](./phases/phase1/RELEASE_NOTES_v1.0.0-phase1.md) - Phase 1 release notes

### Phase 2 - Core Features

**Location:** `/docs/phases/phase2/`

- [Phase 2 Completion Summary](./phases/phase2/PHASE2_COMPLETION_SUMMARY.md) - Phase 2 completion report
- [Phase 2 Quality Status](./phases/phase2/PHASE2_QUALITY_STATUS.md) - Quality metrics and status
- [Phase 2 Contracts](./phases/phase2/PHASE2_CONTRACTS.md) - API contracts introduced in Phase 2
- [Phase 2 Migration Guide](./phases/phase2/PHASE2_MIGRATION_GUIDE.md) - Migration from Phase 1 to Phase 2
- [Release Notes v0.2.0](./phases/phase2/RELEASE_NOTES_v0.2.0.md) - Phase 2 release notes

### Phase 3 - Production Readiness

**Location:** `/docs/phases/phase3/`

- [Phase 3 Readiness Checklist](./phases/phase3/PHASE3_READINESS_CHECKLIST.md) - Production readiness criteria
- [Phase 3 Archive Manifest](./phases/phase3/PHASE3_ARCHIVE_MANIFEST.md) - Archived artifacts manifest
- [Phase 3 Retrospective Template](./phases/phase3/PHASE3_RETROSPECTIVE_TEMPLATE.md) - Retrospective template
- [Phase 3 Stakeholder Completion Report](./phases/phase3/PHASE3_STAKEHOLDER_COMPLETION_REPORT.md) - Executive summary
- [Release Notes v1.0.0-phase3](./phases/phase3/RELEASE_NOTES_v1.0.0-phase3.md) - Phase 3 release notes
- [Acceptance Tests Verification](./phases/phase3/phase3-acceptance-tests-verification.md) - Acceptance test results
- [Delivery Verification Checklist](./phases/phase3/phase3-delivery-verification-checklist.md) - Delivery checklist
- [Functional Requirements Verification](./phases/phase3/phase3-functional-requirements-verification.md) - Requirements traceability
- [Performance Metrics Verification](./phases/phase3/phase3-performance-metrics-verification.md) - Performance validation
- [Quality Gates Verification](./phases/phase3/phase3-quality-gates-verification.md) - Quality gate metrics

---

## Tasks

Task completion summaries, progress reports, and status tracking.

**Location:** `/docs/tasks/`

- [Task 1.18 Completion Summary](./tasks/TASK_1.18_COMPLETION_SUMMARY.md)
- [Task 1.19 Completion Summary](./tasks/TASK_1.19_COMPLETION_SUMMARY.md)
- [Task 2.18 Completion Summary](./tasks/TASK_2.18_COMPLETION_SUMMARY.md)
- [Task 2.19 Completion Summary](./tasks/TASK_2.19_COMPLETION_SUMMARY.md)
- [Task 4 Progress](./tasks/TASK_4_PROGRESS.md)
- [Task 5 Completion Summary](./tasks/TASK_5_COMPLETION_SUMMARY.md)
- [Task Completion Summary](./tasks/TASK_COMPLETION_SUMMARY.md) - General task completion template
- [Task Status Report](./tasks/TASK_STATUS_REPORT.md) - Current task status

---

## AGI Problem

Research documentation, market analysis, and foundational design work for Aurora's cognitive architecture.

**Location:** `/docs/agi-problem/`

### Key Entry Points
- [START HERE](./agi-problem/START-HERE.md) - Master navigation document
- [Session Completion Summary](./agi-problem/SESSION-COMPLETION-SUMMARY.md) - Latest research session summary
- [MD Index](./agi-problem/MD-INDEX.md) - Complete markdown file index

### Aurora Documentation
- [Aurora Framework PRD](./agi-problem/aurora/AURORA-Framework-PRD.md) - Product requirements
- [Aurora Unified Specs](./agi-problem/aurora/AURORA_UNIFIED_SPECS_TRUTH.md) - Definitive specifications
- [Aurora Executive Summary](./agi-problem/aurora/AURORA_EXECUTIVE_SUMMARY.md) - High-level overview

### Research
- [Core Research](./agi-problem/research/core-research/) - Fundamental architecture research
- [Market Research](./agi-problem/research/market-research/) - Competitive analysis
- [SOAR & ACT-R](./agi-problem/research/soar_act-r/) - Cognitive architecture research

### Archive
- [Archive](./agi-problem/archive/) - Historical documents and outdated approaches

---

## Examples

Code examples and usage demonstrations.

**Location:** `/docs/examples/`

- [Activation Usage](./examples/activation_usage.md) - ACT-R activation examples

---

## Additional Resources

### Package Documentation
Each package has its own README with specific documentation:
- [CLI Package](../packages/cli/README.md)
- [Context-Code Package](../packages/context-code/README.md)
- [Core Package](../packages/core/README.md)
- [Reasoning Package](../packages/reasoning/README.md)
- [SOAR Package](../packages/soar/README.md)
- [Testing Package](../packages/testing/README.md)

### Test Documentation
- [Test Fixtures](../tests/fixtures/headless/README.md) - Headless mode test fixtures

### Task Tracking
- [Tasks Directory](../tasks/) - Active PRDs and task tracking documents

---

## ACT-R Cognitive Model

Core cognitive modeling documentation:

**Location:** `/docs/`

- [ACT-R Activation](./actr-activation.md) - ACT-R activation mechanisms explained

---

## Document Organization

All documentation follows this structure:

```
docs/
├── README.md (this file)
├── architecture/          # System design
├── development/          # Developer guides
├── deployment/           # Operations
├── guides/               # User guides
├── reports/
│   ├── quality/          # Quality reports
│   ├── security/         # Security audits
│   └── testing/          # Test reports
├── performance/          # Performance analysis
├── phases/
│   ├── phase1/           # Foundation phase
│   ├── phase2/           # Core features
│   └── phase3/           # Production readiness
├── tasks/                # Task tracking
├── agi-problem/          # Research docs
├── examples/             # Code examples
└── actr-activation.md    # Core cognitive model
```

---

## Getting Started

### For Developers
1. Start with [Architecture](#architecture) to understand the system
2. Read [Development](#development) guides for best practices
3. Review [Examples](#examples) for code samples

### For Operators
1. Read [Deployment](#deployment) guides for production setup
2. Review [Guides](#guides) for operational procedures
3. Check [Troubleshooting](./guides/TROUBLESHOOTING.md) for common issues

### For Researchers
1. Start at [AGI Problem START HERE](./agi-problem/START-HERE.md)
2. Review [Aurora Framework PRD](./agi-problem/aurora/AURORA-Framework-PRD.md)
3. Explore [Research](./agi-problem/research/) documentation

### For Project Managers
1. Review [Phases](#phases) for project history
2. Check [Reports](#reports) for quality metrics
3. Review [Tasks](#tasks) for progress tracking

---

## Contributing

When adding new documentation:
1. Place it in the appropriate subdirectory
2. Update this index with a link
3. Follow naming conventions (UPPERCASE for major docs, lowercase for guides)
4. Include clear headers and navigation

---

**Last Updated:** December 24, 2025
**Version:** 1.0.0
**Maintainer:** Aurora Development Team
