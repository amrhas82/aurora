# Spec: Change Type Classification

## ADDED Requirements

### Requirement: ChangeType Enum

The system SHALL define a ChangeType enum to categorize different types of code changes.

**Enum Values**:
- ADD_FEATURE: New functionality
- REFACTOR: Code restructuring
- BUG_FIX: Error correction
- TEST: Testing changes
- DOCUMENTATION: Documentation updates
- UNKNOWN: Cannot determine type

#### Scenario: Enum used for classification
- **WHEN** classifying a subgoal
- **THEN** return one of the defined ChangeType values

---

### Requirement: Keyword-Based Classification

The system SHALL classify subgoals using keyword pattern matching against change type patterns.

**Interface**:
```python
def classify(subgoal: Subgoal, goal_context: str = "") -> ChangeType:
    """Returns ChangeType based on keyword analysis."""
```

#### Scenario: ADD_FEATURE detected from keywords
- **WHEN** subgoal description contains "add", "create", or "implement"
- **THEN** classify as ADD_FEATURE
- **AND** return ChangeType.ADD_FEATURE

#### Scenario: REFACTOR detected from keywords
- **WHEN** subgoal description contains "refactor", "restructure", or "optimize"
- **THEN** classify as REFACTOR
- **AND** return ChangeType.REFACTOR

#### Scenario: BUG_FIX detected from keywords
- **WHEN** subgoal description contains "fix", "bug", or "error"
- **THEN** classify as BUG_FIX
- **AND** return ChangeType.BUG_FIX

#### Scenario: TEST detected from keywords
- **WHEN** subgoal description contains "test", "testing", or "coverage"
- **THEN** classify as TEST
- **AND** return ChangeType.TEST

#### Scenario: DOCUMENTATION detected from keywords
- **WHEN** subgoal description contains "document", "docs", or "readme"
- **THEN** classify as DOCUMENTATION
- **AND** return ChangeType.DOCUMENTATION

#### Scenario: UNKNOWN for no keyword match
- **WHEN** no keywords match any pattern
- **THEN** return ChangeType.UNKNOWN

---

### Requirement: Context-Enhanced Classification

The system SHALL use both subgoal description and goal context for improved classification accuracy.

#### Scenario: Context improves classification
- **WHEN** subgoal is "Implement validation logic"
- **AND** goal_context is "Add new feature"
- **THEN** "add" keyword from context contributes
- **AND** classify as ADD_FEATURE

#### Scenario: Classification without context
- **WHEN** goal_context is empty
- **AND** subgoal is "Implement authentication"
- **THEN** use only subgoal description
- **AND** "implement" keyword matches ADD_FEATURE

---

### Requirement: Weighted Pattern Matching

The system SHALL score each change type using weighted keyword patterns and return highest-scoring type.

**Pattern Structure**:
```python
@dataclass
class ChangeTypePattern:
    keywords: list[str]
    type: ChangeType
    weight: float
```

#### Scenario: Multiple patterns contribute to score
- **WHEN** subgoal contains both "add" (weight 1.0) and "implement" (weight 1.0)
- **THEN** ADD_FEATURE score is 2.0
- **AND** return ADD_FEATURE if highest

#### Scenario: Strong vs weak keyword matches
- **WHEN** "refactor" keyword (weight 1.0) matches
- **AND** "improve" keyword (weight 0.7) also matches
- **THEN** REFACTOR score is 1.7
- **AND** return REFACTOR if highest

---

### Requirement: Type-Specific File Filters

The system SHALL apply change type-specific filtering strategies for file resolution.

#### Scenario: ADD_FEATURE filter strategy
- **WHEN** change_type is ADD_FEATURE
- **THEN** prioritize files in same directory
- **AND** boost recently modified files
- **AND** penalize test files

#### Scenario: REFACTOR filter strategy
- **WHEN** change_type is REFACTOR
- **THEN** prioritize callers and callees
- **AND** include all files in module
- **AND** boost high-coupling files

#### Scenario: BUG_FIX filter strategy
- **WHEN** change_type is BUG_FIX
- **THEN** prioritize direct dependencies
- **AND** include files with similar error patterns
- **AND** penalize test files

#### Scenario: TEST filter strategy
- **WHEN** change_type is TEST
- **THEN** prioritize test files matching patterns
- **AND** include source files being tested
- **AND** penalize non-test files

#### Scenario: DOCUMENTATION filter strategy
- **WHEN** change_type is DOCUMENTATION
- **THEN** prioritize .md, .rst, .txt files
- **AND** include source files with docstrings
- **AND** penalize implementation files

---

### Requirement: Classification Performance

The system SHALL classify subgoals with minimal performance overhead.

#### Scenario: Classification time target
- **WHEN** classifying a subgoal
- **THEN** complete in <5ms

#### Scenario: Memory usage minimal
- **WHEN** pattern database loaded
- **THEN** memory overhead is <1KB

---

### Requirement: Classification Accuracy

The system SHALL achieve target classification accuracy on benchmark test set.

#### Scenario: Accuracy benchmark
- **WHEN** classifying 20 sample subgoals with ground truth
- **THEN** achieve >85% classification accuracy

#### Scenario: UNKNOWN rate threshold
- **WHEN** classifying diverse subgoals
- **THEN** UNKNOWN rate is <20%
- **AND** most subgoals are classifiable

---

### Requirement: Custom Pattern Support

The system SHALL allow users to define custom classification patterns.

**Configuration**:
```python
@dataclass
class ChangeTypeConfig:
    custom_patterns: list[ChangeTypePattern]
    default_unknown_type: ChangeType
```

#### Scenario: Custom patterns added
- **WHEN** user defines pattern for ["security", "audit"] → BUG_FIX
- **THEN** "Add security audit" classifies as BUG_FIX
- **AND** custom patterns supplement built-in patterns

#### Scenario: Default UNKNOWN type configurable
- **WHEN** classification returns UNKNOWN
- **AND** default_unknown_type is ADD_FEATURE
- **THEN** treat UNKNOWN as ADD_FEATURE for file resolution

---

### Requirement: Error Handling

The system SHALL handle edge cases in classification gracefully.

#### Scenario: Empty input handling
- **WHEN** subgoal description is empty
- **THEN** return ChangeType.UNKNOWN

#### Scenario: Special character normalization
- **WHEN** text contains "bug-fix" (hyphenated)
- **THEN** normalize to "bug fix"
- **AND** match "bug" and "fix" keywords

#### Scenario: Case insensitivity
- **WHEN** text contains "ADD FEATURE" (uppercase)
- **THEN** normalize to lowercase
- **AND** match "add" keyword
