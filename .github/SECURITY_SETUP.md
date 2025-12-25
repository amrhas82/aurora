# GitHub Security Configuration for AURORA

This document provides step-by-step instructions for securing the AURORA repository as a public repo.

## Overview

The security configuration ensures:
- Only approved contributors (owner + authorized CI/CD) can push to protected branches
- All changes go through pull requests with required reviews
- Automated quality checks must pass before merging
- No force pushes or deletions of protected branches
- Signed commits are enforced for authenticity

## Branch Protection Rules

### Main Branch Protection

Configure these settings for the `main` branch via GitHub Settings → Branches → Branch protection rules:

#### Required Settings (Critical)

1. **Require a pull request before merging**
   - ✅ Required number of approvals: 1
   - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ Require review from Code Owners (if CODEOWNERS file exists)

2. **Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging
   - Required checks (configure after CI/CD setup):
     - `quality-check` (lint, type-check, tests)
     - `test-suite` (full test run)
     - `security-scan` (if configured)

3. **Require signed commits**
   - ✅ Require signed commits for all commits to main
   - This ensures commit authenticity and non-repudiation

4. **Require linear history**
   - ✅ Prevent merge commits (require rebase or squash)
   - Keeps history clean and auditable

5. **Do not allow bypassing the above settings**
   - ✅ Include administrators (important for security)
   - Note: This means even you must follow the PR process

6. **Restrict who can push to matching branches**
   - ✅ Restrict pushes that create matching branches
   - Allowed actors:
     - Repository owner (amrhas82)
     - GitHub Actions (for automated releases)

7. **Force push and deletions**
   - ✅ Do not allow force pushes
   - ✅ Do not allow deletions

#### Optional (Recommended) Settings

8. **Require deployments to succeed**
   - Configure if using GitHub Deployments

9. **Lock branch**
   - ❌ Not recommended (would block all changes)

10. **Require conversation resolution before merging**
    - ✅ All review comments must be resolved

## Repository Security Settings

Configure via GitHub Settings → Security:

### 1. Code Security and Analysis

```
☑️ Dependency graph (automatic for public repos)
☑️ Dependabot alerts
☑️ Dependabot security updates
☑️ Grouped security updates
☑️ Code scanning (GitHub Advanced Security)
☑️ Secret scanning
☑️ Secret scanning push protection
```

### 2. Access Control

**Collaborators and Teams** (Settings → Collaborators):
- Owner: `amrhas82` (admin access)
- For CI/CD: Use GitHub Actions tokens (automatic)
- For Claude Code: Use personal access tokens (PATs) with minimal scope

**Deploy Keys** (Settings → Deploy keys):
- Only add if needed for specific deployment workflows
- Use read-only when possible

### 3. Required Workflows

Create `.github/workflows/required-checks.yml`:

```yaml
name: Required Quality Checks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run quality checks
        run: make quality-check

      - name: Run tests
        run: make test

      - name: Security scan
        run: |
          pip install bandit
          bandit -r packages/ -ll -f json -o bandit-report.json
          bandit -r packages/ -ll
```

## Claude Code Access Configuration

For Claude Code to interact with the repository:

### Option 1: Personal Access Token (Recommended)

1. **Create PAT** (Settings → Developer settings → Personal access tokens → Fine-grained tokens):
   - Repository access: Only `aurora`
   - Permissions:
     - Contents: Read and write
     - Pull requests: Read and write
     - Workflows: Read (if needed)
   - Expiration: 90 days (rotate regularly)

2. **Configure Git credential helper**:
   ```bash
   git config credential.helper store
   # Or use GitHub CLI:
   gh auth login
   ```

3. **Use in Claude Code**:
   - Claude Code uses local Git configuration
   - Authenticated via `gh` CLI or Git credentials
   - Works within branch protection rules (creates PRs)

### Option 2: GitHub Actions Bot

For automated operations:
- Use `GITHUB_TOKEN` (automatic, scoped per workflow)
- Configure as a repository secret if needed
- Has limited permissions by design

## CODEOWNERS File

Create `.github/CODEOWNERS` to require specific reviewers:

```
# Default owner for everything
* @amrhas82

# Critical configuration
/.github/ @amrhas82
/pyproject.toml @amrhas82
/setup.py @amrhas82

# Security-sensitive code
/packages/core/src/aurora_core/resilience/ @amrhas82
/packages/cli/src/aurora_cli/ @amrhas82

# MCP integration
/src/aurora/mcp/ @amrhas82
```

## Migration to Public Repository

Before making the repository public:

1. **Security Audit**:
   ```bash
   # Check for secrets
   git log --all --full-history --source --find-object=<object-id>

   # Scan for common secrets
   pip install detect-secrets
   detect-secrets scan --all-files

   # Review environment files
   find . -name ".env*" -o -name "*credentials*" -o -name "*secrets*"
   ```

2. **Remove sensitive data** (if found):
   ```bash
   # Use BFG Repo-Cleaner or git-filter-repo
   pip install git-filter-repo
   git filter-repo --path <sensitive-file> --invert-paths
   ```

3. **Update documentation**:
   - Ensure README.md is comprehensive
   - Add LICENSE file
   - Update CONTRIBUTING.md guidelines
   - Review all .md files for internal references

4. **Configure GitHub Actions secrets**:
   - `PYPI_API_TOKEN` (for releases)
   - `ANTHROPIC_API_KEY` (only for testing, if needed)
   - Any other service credentials

5. **Make repository public**:
   - Settings → General → Danger Zone → Change repository visibility
   - Confirm security settings are in place
   - Enable discussions (optional)

## Quick Setup Commands

```bash
# 1. Enable branch protection (via GitHub CLI)
gh api repos/amrhas82/aurora/branches/main/protection \
  --method PUT \
  --field required_status_checks[strict]=true \
  --field required_status_checks[contexts][]=quality-check \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[dismiss_stale_reviews]=true \
  --field enforce_admins=true \
  --field required_signatures=true \
  --field required_linear_history=true \
  --field allow_force_pushes=false \
  --field allow_deletions=false

# 2. Enable Dependabot
gh api repos/amrhas82/aurora/automated-security-fixes \
  --method PUT

# 3. Enable secret scanning
gh api repos/amrhas82/aurora/secret-scanning \
  --method PUT \
  --field enabled=true

# 4. Create CODEOWNERS file
mkdir -p .github
cat > .github/CODEOWNERS << 'EOF'
* @amrhas82
/.github/ @amrhas82
/pyproject.toml @amrhas82
EOF

# 5. Commit security configuration
git add .github/
git commit -m "chore: add GitHub security configuration"
git push origin main
```

## Workflow for Changes

With these settings in place:

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -S -m "feat: my feature"  # -S for signed commit
   ```

3. **Push to remote**:
   ```bash
   git push origin feature/my-feature
   ```

4. **Create pull request**:
   ```bash
   gh pr create --title "feat: my feature" --body "Description"
   ```

5. **Wait for checks** (automatic):
   - Quality checks run
   - Tests run
   - Security scans complete

6. **Review and merge**:
   - Review your own PR (or have collaborator review)
   - Merge via GitHub UI (squash or rebase)

## Emergency Access

If you need to bypass protection (emergency only):

1. Temporarily disable "Include administrators" in branch protection
2. Make critical fix
3. Re-enable protection immediately
4. Document in commit message why bypass was needed

## Monitoring

Regular security checks:

```bash
# Weekly: Review security alerts
gh api repos/amrhas82/aurora/dependabot/alerts

# Monthly: Audit access
gh api repos/amrhas82/aurora/collaborators

# Quarterly: Review branch protection
gh api repos/amrhas82/aurora/branches/main/protection
```

## References

- [GitHub Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Security Features](https://docs.github.com/en/code-security)
- [Signing Commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)
- [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
