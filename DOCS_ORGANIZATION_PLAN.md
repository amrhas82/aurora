# Documentation Organization Plan

## Current State Analysis

### Files in Root Directory (to be organized):
1. ACCEPTANCE_TEST_REPORT.md
2. CODE_REVIEW_CHECKLIST.md (duplicate with docs/)
3. CODE_REVIEW_REPORT.md
4. COVERAGE_ANALYSIS.md (NEW - just created)
5. DELIVERY_CHECKLIST.md
6. MEMORY_PROFILING_REPORT.md
7. PHASE1_ARCHIVE.md
8. PHASE1_VERIFICATION_REPORT.md
9. PHASE2_COMPLETION_SUMMARY.md
10. PHASE2_QUALITY_STATUS.md
11. PHASE3_READINESS_CHECKLIST.md
12. QUALITY_GATES_REPORT.md
13. RELEASE_NOTES_v0.2.0.md
14. RELEASE_NOTES_v1.0.0-phase1.md
15. RELEASE_NOTES_v1.0.0-phase3.md
16. TASK_*_COMPLETION_SUMMARY.md (multiple files)
17. TASK_STATUS_REPORT.md

### Files to Keep in Root:
- README.md (main project readme)
- .pytest_cache/README.md (pytest internal)

### Package READMEs (keep in place):
- packages/cli/README.md
- packages/context-code/README.md
- packages/core/README.md
- packages/reasoning/README.md
- packages/soar/README.md
- packages/testing/README.md

### Test Fixture Files (keep in place):
- tests/fixtures/headless/*.md

### Tasks Directory (keep in place):
- tasks/*.md (PRDs and task tracking)

## Proposed docs/ Structure

```
docs/
├── README.md (NEW - index of all documentation)
├── architecture/
│   ├── SOAR_ARCHITECTURE.md (existing)
│   ├── API_CONTRACTS_v1.0.md (existing)
│   └── AGENT_INTEGRATION.md (existing)
├── development/
│   ├── EXTENSION_GUIDE.md (existing)
│   ├── CODE_REVIEW_CHECKLIST.md (existing)
│   ├── PROMPT_ENGINEERING_GUIDE.md (existing)
│   ├── PROMPT_TEMPLATE_REVIEW.md (existing)
│   └── examples/
│       └── activation_usage.md (existing)
├── deployment/
│   ├── production-deployment.md (existing)
│   ├── headless-mode.md (existing)
│   └── troubleshooting-advanced.md (existing)
├── guides/
│   ├── TROUBLESHOOTING.md (existing)
│   ├── COST_TRACKING_GUIDE.md (existing)
│   └── performance-tuning.md (existing)
├── phases/
│   ├── phase1/
│   │   ├── PHASE1_ARCHIVE.md (move from root)
│   │   ├── PHASE1_VERIFICATION_REPORT.md (move from root)
│   │   └── RELEASE_NOTES_v1.0.0-phase1.md (move from root)
│   ├── phase2/
│   │   ├── PHASE2_COMPLETION_SUMMARY.md (move from root)
│   │   ├── PHASE2_QUALITY_STATUS.md (move from root)
│   │   ├── PHASE2_CONTRACTS.md (existing)
│   │   ├── PHASE2_MIGRATION_GUIDE.md (existing)
│   │   └── RELEASE_NOTES_v0.2.0.md (move from root)
│   └── phase3/
│       ├── PHASE3_READINESS_CHECKLIST.md (move from root)
│       ├── PHASE3_ARCHIVE_MANIFEST.md (existing)
│       ├── PHASE3_RETROSPECTIVE_TEMPLATE.md (existing)
│       ├── PHASE3_STAKEHOLDER_COMPLETION_REPORT.md (existing)
│       ├── RELEASE_NOTES_v1.0.0-phase3.md (move from root)
│       ├── phase3-acceptance-tests-verification.md (existing)
│       ├── phase3-delivery-verification-checklist.md (existing)
│       ├── phase3-functional-requirements-verification.md (existing)
│       ├── phase3-performance-metrics-verification.md (existing)
│       └── phase3-quality-gates-verification.md (existing)
├── reports/
│   ├── quality/
│   │   ├── CODE_REVIEW_REPORT.md (move from root)
│   │   ├── CODE_REVIEW_REPORT_v1.0.0-phase3.md (existing)
│   │   ├── QUALITY_GATES_REPORT.md (move from root)
│   │   ├── ACCEPTANCE_TEST_REPORT.md (move from root)
│   │   ├── DELIVERY_CHECKLIST.md (move from root)
│   │   └── VERIFICATION_CHECKPOINTS.md (existing)
│   ├── performance/
│   │   ├── MEMORY_PROFILING_REPORT.md (move from root)
│   │   ├── PERFORMANCE_PROFILING_REPORT.md (existing)
│   │   ├── VERIFICATION_CALIBRATION_REPORT.md (existing)
│   │   ├── embedding-benchmark-results.md (existing)
│   │   ├── hybrid-retrieval-precision-report.md (existing)
│   │   └── live-data-validation-checklist.md (existing)
│   ├── security/
│   │   ├── SECURITY_AUDIT_CHECKLIST.md (existing)
│   │   └── SECURITY_AUDIT_REPORT_v1.0.0-phase3.md (existing)
│   └── testing/
│       ├── COVERAGE_ANALYSIS.md (move from root - NEW)
│       └── actr-formula-validation.md (existing)
├── tasks/
│   ├── TASK_1.18_COMPLETION_SUMMARY.md (move from root)
│   ├── TASK_1.19_COMPLETION_SUMMARY.md (move from root)
│   ├── TASK_2.18_COMPLETION_SUMMARY.md (move from root)
│   ├── TASK_2.19_COMPLETION_SUMMARY.md (move from root)
│   ├── TASK_4_PROGRESS.md (move from root)
│   ├── TASK_5_COMPLETION_SUMMARY.md (move from root)
│   ├── TASK_COMPLETION_SUMMARY.md (move from root)
│   └── TASK_STATUS_REPORT.md (move from root)
├── agi-problem/ (existing - no changes)
└── actr-activation.md (existing)
```

## Migration Actions

### Create New Directories
1. docs/phases/phase1/
2. docs/phases/phase2/
3. docs/phases/phase3/
4. docs/reports/quality/
5. docs/reports/performance/ (exists - keep)
6. docs/reports/security/ (may need creation)
7. docs/reports/testing/
8. docs/tasks/
9. docs/architecture/
10. docs/development/
11. docs/deployment/
12. docs/guides/

### Move Files from Root to docs/
All moves with git to preserve history.

### Remove Duplicates
- CODE_REVIEW_CHECKLIST.md exists in both root and docs/ - keep docs/ version

### Create Master Index
- docs/README.md with navigation to all subdirectories
