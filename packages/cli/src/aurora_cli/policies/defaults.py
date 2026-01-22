"""Default policy configurations."""

from __future__ import annotations


DEFAULT_POLICIES_YAML = """# Aurora Policies Configuration
# This file defines policies for execution control and safety

# Budget policies
budget:
  monthly_limit_usd: 100.0
  warn_at_percent: 80
  hard_limit_action: reject  # reject | warn

# Agent recovery policies
agent_recovery:
  timeout_seconds: 300  # 5 minutes - LLMs need time to think
  max_retries: 2
  fallback_to_llm: true

# Destructive operation policies
destructive:
  file_delete:
    action: prompt           # prompt | allow | deny
    max_files: 5             # Prompt if deleting more than N files

  git_force_push:
    action: deny             # Never allow force push

  git_push_main:
    action: prompt           # Prompt before pushing to main/master

  drop_table:
    action: deny             # Never allow DROP TABLE

  truncate:
    action: prompt           # Prompt before TRUNCATE

# Safety policies
safety:
  auto_branch: true          # Create feature branch before changes
  branch_prefix: "aurora/"   # Branch naming: aurora/goal-slug

  max_files_modified: 20     # Anomaly if exceeds
  max_lines_changed: 1000    # Anomaly if exceeds

  protected_paths:           # Never modify these
    - ".git/"
    - "node_modules/"
    - "vendor/"
    - ".env"
    - "*.pem"
    - "*.key"

# Anomaly detection
anomalies:
  scope_multiplier: 3        # Alert if scope > 3x expected
  unexpected_file_types:     # Alert if modifying these
    - "*.sql"
    - "*.sh"
    - "Dockerfile"
"""


def get_default_policies_yaml() -> str:
    """Get default policies YAML configuration.

    Returns:
        Default policies configuration as YAML string

    """
    return DEFAULT_POLICIES_YAML
