# Headless Mode Test Fixtures

This directory contains test fixtures for the Aurora SOAR headless mode components.

## Prompt Fixtures

### `prompt.md`
A comprehensive, valid prompt file demonstrating all required sections with realistic content.
- Contains Goal, Success Criteria, Constraints, and Context sections
- 10 success criteria items
- 8 constraint items
- Realistic authentication system implementation scenario

### `prompt_minimal.md`
A minimal valid prompt file with only required fields.
- Contains Goal, Success Criteria, and empty Constraints sections
- Useful for testing minimal input handling

### `prompt_invalid_missing_goal.md`
An invalid prompt file missing the required Goal section.
- Used for testing validation error handling
- Should trigger PromptValidationError

### `prompt_invalid_empty_criteria.md`
An invalid prompt file with empty Success Criteria section.
- Used for testing validation of list items
- Should trigger PromptValidationError

## Scratchpad Fixtures

### `scratchpad.md`
A realistic in-progress scratchpad with multiple iterations.
- Status: IN_PROGRESS
- 5 completed iterations showing typical workflow
- Total cost: $2.45
- Demonstrates Planning, Implementation, and Testing phases

### `scratchpad_empty.md`
An empty scratchpad for a task that hasn't started yet.
- Status: PENDING
- 0 iterations
- Total cost: $0.00
- Useful for testing initialization

### `scratchpad_completed.md`
A completed scratchpad showing successful task completion.
- Status: COMPLETED
- 3 iterations with success termination signal
- Total cost: $1.25
- Demonstrates full workflow from planning to verification

### `scratchpad_budget_exceeded.md`
A scratchpad showing budget constraint violation.
- Status: TERMINATED
- 8 iterations with budget exceeded termination
- Total cost: $5.50 (exceeded $5.00 budget)
- Demonstrates constraint enforcement

## Usage in Tests

These fixtures can be used in unit tests by referencing their paths:

```python
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "headless"

def test_load_valid_prompt():
    loader = PromptLoader(FIXTURES_DIR / "prompt.md")
    data = loader.load()
    assert data.goal.startswith("Implement a user authentication")

def test_load_invalid_prompt():
    loader = PromptLoader(FIXTURES_DIR / "prompt_invalid_missing_goal.md")
    with pytest.raises(PromptValidationError):
        loader.load()
```

## Maintenance

When updating these fixtures:
1. Ensure valid fixtures remain valid according to current schema
2. Update invalid fixtures if validation rules change
3. Keep content realistic and representative of actual use cases
4. Document any breaking changes in this README
