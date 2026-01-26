# Aurora v0.10.0 Release TODO List

## Overview
Prepare Aurora v0.10.0 release with all changes since v0.9.4 (83 commits)

**Major Changes:**
- Epic 1: Memory Search Performance (Caching)
- Epic 2: Lazy BM25 Loading + Dual-Hybrid Fallback
- Planning System Refactor (R1-R9)
- Code Quality Improvements (ARG001-ARG005, type fixes, datetime deprecations)

**Version Bump:** 0.9.4 → 0.10.0 (minor version - new features, backward compatible)

---

## Pre-Release Tasks

### 1. Review and Categorize All Commits
- [ ] 1.1 Generate full commit list since v0.9.4
  - Command: `git log v0.9.4..HEAD --oneline --pretty=format:"%h %s" > /tmp/commits.txt`
  - Review all 83 commits
- [ ] 1.2 Categorize by type (feat, fix, refactor, docs, test, chore, perf)
- [ ] 1.3 Group by epic/feature area
  - Epic 1 (Caching)
  - Epic 2 (Lazy Loading + Dual-Hybrid)
  - Planning Refactor
  - Code Quality
  - Bug Fixes
- [ ] 1.4 Identify breaking changes (if any)
  - Review backward compatibility notes
  - Document migration steps if needed

### 2. Update CHANGELOG.md
- [ ] 2.1 Move "Unreleased" section to "[0.10.0] - YYYY-MM-DD"
- [ ] 2.2 Add new sections for v0.10.0:
  - [ ] **Added** - New features
    - Epic 1: Memory caching (HybridRetriever, ActivationEngine, QueryEmbedding, BM25 persistence)
    - Epic 2: Lazy BM25 loading, Dual-hybrid fallback
    - Planning: /aur:tasks skill, source_file field, agents.json schema docs
    - Planning: TDD hints in tasks.md template
  - [ ] **Changed** - Modifications
    - Planning: Slug-only plan folders (backward compatible with NNNN-slug)
    - Planning: Artifact generation order documented
    - Code quality: 4,425 safe formatting fixes
    - All datetime.utcnow() → datetime.now(timezone.utc)
  - [ ] **Fixed** - Bug fixes
    - Rate limit error handling
    - SOAR empty subgoals fallback
    - View command schema mismatch
    - Type-checking errors (Pyright clean)
    - Unused arguments (ARG001-ARG005 complete)
    - Configurator method signatures
  - [ ] **Removed** - Deletions
    - Spec generation from planning system (8 files → 5 files)
    - Non-existent command references (validate, --specs, --deltas-only)
  - [ ] **Performance**
    - Lazy BM25 loading: 150-250ms → 0ms startup improvement (99.9%)
    - Module-level retriever caching: 30-40% faster cold searches
    - Activation engine singleton: 40-50% faster warm searches
  - [ ] **Documentation**
    - 3-SIMPLE-STEPS.md guide created
    - PLAN_REFERENCES updated with schemas
- [ ] 2.3 Add migration notes section (if needed)
- [ ] 2.4 Add links to PRs/commits for major features
- [ ] 2.5 Review format against Keep a Changelog standard
- [ ] 2.6 Create new "## [Unreleased]" section at top

### 3. Update Version Files
- [ ] 3.1 Run version bump script
  - Command: `./scripts/bump-version.sh 0.10.0`
  - Updates: pyproject.toml, main.py
- [ ] 3.2 Verify version updated in:
  - [ ] pyproject.toml (all 9 packages)
  - [ ] packages/cli/src/aurora_cli/main.py
- [ ] 3.3 Check for any hardcoded version strings
  - Search: `grep -r "0\.9\.4" packages/ docs/`

### 4. Pre-commit Checks (NO SKIPPING)
- [ ] 4.1 Run full local CI
  - Command: `./scripts/run-local-ci.sh`
  - Verify all tests pass
- [ ] 4.2 Run pre-commit hooks manually
  - Command: `pre-commit run --all-files`
  - Fix any issues found
- [ ] 4.3 Verify specific checks:
  - [ ] Black formatting
  - [ ] isort import ordering
  - [ ] Flake8 linting
  - [ ] Bandit security
  - [ ] Pyright type checking (if configured)
  - [ ] Pytest markers
  - [ ] Import patterns
- [ ] 4.4 Run configurator tests
  - [ ] Test all 20 configurators generate correctly
  - Command: `pytest tests/unit/cli/configurators/ -v`
- [ ] 4.5 Run planning tests
  - Command: `pytest tests/unit/cli/planning/ -v`
  - Verify 74+ tests pass
- [ ] 4.6 Run memory search tests
  - Command: `pytest tests/unit/context_code/ -v`
  - Verify caching tests pass

### 5. Documentation Review
- [ ] 5.1 Review README.md for accuracy
  - [ ] Version references
  - [ ] Feature list includes new features
  - [ ] Installation instructions current
  - [ ] Links to 3-SIMPLE-STEPS.md work
- [ ] 5.2 Review CLAUDE.md
  - [ ] Reflects current structure
  - [ ] Command examples accurate
- [ ] 5.3 Review docs/guides/
  - [ ] COMMANDS.md current
  - [ ] TOOLS_GUIDE.md reflects 6 commands (tasks added)
  - [ ] 3-SIMPLE-STEPS.md accurate
- [ ] 5.4 Check for outdated references
  - [ ] No mentions of removed checkpoint commands
  - [ ] No mentions of spec files (removed)
  - [ ] No mentions of 8 files (should be 5)

### 6. Manual Testing
- [ ] 6.1 Test installation from wheel
  - [ ] `pip install --upgrade .`
  - [ ] Verify imports work
- [ ] 6.2 Test core workflows
  - [ ] `aur init` creates correct structure
  - [ ] `aur mem index .` works
  - [ ] `aur mem search "test"` returns results
  - [ ] `aur goals "test feature"` creates goals.json with source_file
- [ ] 6.3 Test planning workflow
  - [ ] `aur plan list` works
  - [ ] Plan folders use slug-only format (no NNNN prefix)
  - [ ] `aur plan view <id>` works without errors
- [ ] 6.4 Test configurators
  - [ ] `aur init --config --tools=claude,cursor` creates 6 commands each
  - [ ] /aur:tasks command file exists
  - [ ] No checkpoint command files

### 7. Commit Release Changes
- [ ] 7.1 Stage all changes
  - CHANGELOG.md
  - pyproject.toml (all packages)
  - main.py
  - Any documentation updates
- [ ] 7.2 Create release commit
  - Message: `chore: bump version to 0.10.0`
  - Include full change summary in commit body
- [ ] 7.3 Run pre-commit hooks on commit
  - Verify NO hooks are skipped
  - Fix any issues and recommit

---

## Release Execution

### 8. Run Release Script
- [ ] 8.1 Execute release script
  - Command: `./scripts/release.sh 0.10.0`
  - Script will:
    - Build distributions
    - Upload to PyPI
    - Create git tag v0.10.0
    - Push to remote
- [ ] 8.2 Monitor for errors during:
  - [ ] Build phase
  - [ ] Upload phase
  - [ ] Git operations
- [ ] 8.3 Verify tag created
  - Command: `git tag -l v0.10.0`

### 9. PyPI Verification
- [ ] 9.1 Check PyPI upload
  - URL: https://pypi.org/project/aurora-actr/
  - Verify version 0.10.0 visible
- [ ] 9.2 Test fresh installation
  - [ ] Create clean venv: `python -m venv test_venv`
  - [ ] Activate: `source test_venv/bin/activate`
  - [ ] Install: `pip install aurora-actr==0.10.0`
  - [ ] Verify: `aur --version` shows 0.10.0
  - [ ] Test basic command: `aur mem --help`
- [ ] 9.3 Test upgrade path
  - [ ] Install old version: `pip install aurora-actr==0.9.4`
  - [ ] Upgrade: `pip install --upgrade aurora-actr`
  - [ ] Verify upgraded to 0.10.0

### 10. GitHub Release
- [ ] 10.1 Create GitHub release
  - Tag: v0.10.0
  - Title: "Aurora v0.10.0 - Memory Performance & Planning Refactor"
- [ ] 10.2 Copy CHANGELOG entry to release notes
- [ ] 10.3 Add highlights section:
  - Performance improvements (99.9% startup reduction)
  - New /aur:tasks skill
  - Slug-only plan folders
  - Code quality improvements
- [ ] 10.4 Attach distributions (optional)
  - aurora_actr-0.10.0-py3-none-any.whl
  - aurora-actr-0.10.0.tar.gz

---

## Post-Release Tasks

### 11. Announce Release
- [ ] 11.1 Update project documentation links
- [ ] 11.2 Post release announcement (if applicable)
- [ ] 11.3 Update any external documentation

### 12. Monitor for Issues
- [ ] 12.1 Watch for installation issues
- [ ] 12.2 Monitor GitHub issues for bug reports
- [ ] 12.3 Check PyPI download stats

### 13. Cleanup
- [ ] 13.1 Delete feature branches (if any)
- [ ] 13.2 Archive old release notes
- [ ] 13.3 Update project board/tracker

---

## Rollback Plan (If Needed)

### Emergency Rollback
If critical issues discovered:
- [ ] A. Yank v0.10.0 from PyPI (keeps package visible but prevents new installs)
- [ ] B. Create hotfix branch from v0.9.4
- [ ] C. Apply fixes
- [ ] D. Release v0.10.1 with fixes
- [ ] E. Document issues in CHANGELOG

---

## Verification Checklist

Before marking complete, verify:
- [ ] ✓ Version is 0.10.0 in all files
- [ ] ✓ CHANGELOG.md has complete v0.10.0 entry
- [ ] ✓ All tests pass (make test)
- [ ] ✓ All pre-commit hooks pass (no skips)
- [ ] ✓ PyPI shows v0.10.0
- [ ] ✓ Fresh install works
- [ ] ✓ Git tag v0.10.0 exists
- [ ] ✓ Git tag pushed to remote
- [ ] ✓ GitHub release created
- [ ] ✓ Documentation updated

---

## Notes

**Breaking Changes:** None (all changes backward compatible)

**Migration Required:** None

**Deprecation Warnings:** None

**Known Issues:** None

**Next Version:** 0.10.1 (patch) or 0.11.0 (next minor)
