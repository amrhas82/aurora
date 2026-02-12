#!/bin/bash
# Script to configure GitHub security settings for AURORA repository
# Usage: ./scripts/setup-github-security.sh

set -e

REPO="hamr0/aurora"
BRANCH="main"

echo "🔒 Configuring GitHub Security for $REPO"
echo "================================================"

# Check if gh CLI is authenticated
if ! gh auth status &>/dev/null; then
    echo "❌ Error: GitHub CLI is not authenticated"
    echo "Run: gh auth login"
    exit 1
fi

echo "✓ GitHub CLI authenticated"

# Function to enable branch protection
setup_branch_protection() {
    echo ""
    echo "📋 Setting up branch protection for $BRANCH..."

    # Note: GitHub CLI doesn't have a direct command for all protection settings
    # We need to use the API directly
    gh api repos/$REPO/branches/$BRANCH/protection \
        --method PUT \
        --field required_status_checks[strict]=true \
        --field required_status_checks[contexts][]=quality-check \
        --field required_status_checks[contexts][]=test-suite \
        --field required_status_checks[contexts][]=security-scan \
        --field required_pull_request_reviews[required_approving_review_count]=1 \
        --field required_pull_request_reviews[dismiss_stale_reviews]=true \
        --field required_pull_request_reviews[require_code_owner_reviews]=true \
        --field enforce_admins=true \
        --field required_linear_history=true \
        --field allow_force_pushes=false \
        --field allow_deletions=false \
        --field restrictions=null \
        2>&1 || {
            echo "⚠️  Warning: Could not set all branch protection rules via API"
            echo "Please configure manually via: https://github.com/$REPO/settings/branches"
        }

    echo "✓ Branch protection configured (verify at GitHub web interface)"
}

# Function to enable security features
enable_security_features() {
    echo ""
    echo "🛡️  Enabling security features..."

    # Enable vulnerability alerts
    gh api repos/$REPO/vulnerability-alerts \
        --method PUT \
        2>&1 && echo "✓ Vulnerability alerts enabled" || echo "⚠️  Could not enable vulnerability alerts"

    # Enable automated security fixes (Dependabot)
    gh api repos/$REPO/automated-security-fixes \
        --method PUT \
        2>&1 && echo "✓ Dependabot security updates enabled" || echo "⚠️  Could not enable Dependabot"

    # Note: Secret scanning and code scanning require GitHub Advanced Security
    # For public repos, these are free
    echo "ℹ️  Note: Enable Secret Scanning and Code Scanning manually at:"
    echo "   https://github.com/$REPO/settings/security_analysis"
}

# Function to check current settings
check_current_settings() {
    echo ""
    echo "🔍 Current repository settings:"

    echo ""
    echo "Branch protection for $BRANCH:"
    gh api repos/$REPO/branches/$BRANCH/protection \
        --jq '{
            required_status_checks: .required_status_checks.contexts,
            required_reviews: .required_pull_request_reviews.required_approving_review_count,
            enforce_admins: .enforce_admins.enabled,
            linear_history: .required_linear_history.enabled
        }' 2>&1 || echo "No branch protection currently configured"

    echo ""
    echo "Repository visibility:"
    gh api repos/$REPO --jq '.visibility'

    echo ""
    echo "Security features:"
    gh api repos/$REPO --jq '{
        has_vulnerability_alerts: .has_vulnerability_alerts,
        has_automated_security_fixes: .has_automated_security_fixes
    }'
}

# Function to pre-flight checks
pre_flight_checks() {
    echo ""
    echo "🔍 Running pre-flight security checks..."

    # Check for .env files
    echo ""
    echo "Checking for environment files..."
    if find . -name ".env*" -not -path "./venv/*" -not -path "./.venv/*" 2>/dev/null | grep -q .; then
        echo "⚠️  WARNING: Found .env files:"
        find . -name ".env*" -not -path "./venv/*" -not -path "./.venv/*"
        echo "   Ensure these are in .gitignore before making repo public!"
    else
        echo "✓ No .env files found"
    fi

    # Check for potential secrets in recent commits
    echo ""
    echo "Checking for common secret patterns in recent commits..."
    if git log --all --oneline -n 100 | grep -iE "(password|secret|token|key|api)" | head -5; then
        echo "⚠️  WARNING: Found potential secret-related commits"
        echo "   Review commit history before making repo public"
    else
        echo "✓ No obvious secret patterns in recent commits"
    fi

    # Check .gitignore
    echo ""
    echo "Checking .gitignore..."
    if grep -qE "\.env|secrets|credentials" .gitignore 2>/dev/null; then
        echo "✓ .gitignore includes common secret patterns"
    else
        echo "⚠️  WARNING: .gitignore may not exclude all sensitive files"
    fi
}

# Main execution
main() {
    echo ""
    read -p "Do you want to run pre-flight security checks? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pre_flight_checks
    fi

    echo ""
    read -p "Do you want to check current repository settings? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        check_current_settings
    fi

    echo ""
    read -p "Do you want to configure branch protection rules? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_branch_protection
    fi

    echo ""
    read -p "Do you want to enable security features? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        enable_security_features
    fi

    echo ""
    echo "================================================"
    echo "✅ Security setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Review settings at: https://github.com/$REPO/settings"
    echo "2. Enable Secret Scanning: https://github.com/$REPO/settings/security_analysis"
    echo "3. Configure required status checks after first workflow run"
    echo "4. Consider enabling Discussions for community engagement"
    echo "5. Add LICENSE file if not present"
    echo ""
    echo "To make repository public:"
    echo "https://github.com/$REPO/settings (scroll to Danger Zone)"
}

main
