# Spec: Structural Analysis for File Resolution

## ADDED Requirements

### Requirement: Dependency Graph Construction

The system SHALL build a dependency graph from import relationships to track file connections.

**Data Model**:
```python
@dataclass
class ImportRelation:
    source: Path
    target: Path
    import_type: str  # "direct" | "transitive"

@dataclass
class DependencyGraph:
    nodes: set[Path]
    edges: list[ImportRelation]
```

#### Scenario: Graph built from memory chunks
- **WHEN** StructuralAnalyzer initializes
- **THEN** query memory store for chunks with import statements
- **AND** parse imports to build edge list
- **AND** cache graph for session duration

#### Scenario: Import parsing from code content
- **WHEN** chunk contains "import X" or "from X import Y"
- **THEN** extract module name using regex
- **AND** resolve module to file path
- **AND** create ImportRelation edge

---

### Requirement: Related File Discovery

The system SHALL find files related to seed files based on change type using graph traversal.

**Interface**:
```python
def find_related_files(
    seed_files: list[Path],
    change_type: ChangeType,
    max_depth: int = 2
) -> list[tuple[Path, float]]:
    """Returns (file_path, structural_score) tuples."""
```

#### Scenario: ADD_FEATURE finds similar features
- **WHEN** change_type is ADD_FEATURE
- **AND** seed files are ["auth/oauth.py"]
- **THEN** return files in same directory
- **AND** return files with similar naming patterns
- **AND** score 1.0 for same directory, 0.8 for similar names

#### Scenario: REFACTOR finds callers and callees
- **WHEN** change_type is REFACTOR
- **AND** seed files are ["auth/oauth.py"]
- **THEN** perform BFS traversal up to max_depth
- **AND** follow import edges in both directions
- **AND** score as 1.0 - (distance / max_depth)

#### Scenario: BUG_FIX finds direct dependencies
- **WHEN** change_type is BUG_FIX
- **AND** seed files are ["auth/oauth.py"]
- **THEN** return only directly imported files
- **AND** score all as 1.0

#### Scenario: TEST finds test files
- **WHEN** change_type is TEST
- **AND** seed files are ["auth/oauth.py"]
- **THEN** return files matching test patterns
- **AND** patterns include "test_*.py", "*_test.py", "tests/"
- **AND** score 1.0 for related test files

---

### Requirement: Graph Traversal

The system SHALL traverse the dependency graph using BFS to find connected files within max_depth hops.

#### Scenario: BFS traversal finds connected files
- **WHEN** traversing from seed file "auth/oauth.py" with max_depth=2
- **AND** graph has edges: oauth.py → tokens.py → crypto.py
- **THEN** find tokens.py (distance 1) and crypto.py (distance 2)
- **AND** do not traverse beyond depth 2

#### Scenario: Bidirectional traversal
- **WHEN** traversing in both directions (importers and imports)
- **AND** api/routes.py imports auth/oauth.py
- **THEN** find both upstream (routes.py) and downstream (tokens.py) files

---

### Requirement: Distance-Based Scoring

The system SHALL score files based on graph distance from nearest seed file.

**Formula**: `structural_score = max(0.0, 1.0 - (distance / max_depth))`

#### Scenario: Seed file scores 1.0
- **WHEN** file is in seed_files
- **THEN** distance is 0
- **AND** score is 1.0

#### Scenario: Direct neighbor scores based on depth
- **WHEN** file is 1 hop from seed
- **AND** max_depth is 2
- **THEN** distance is 1
- **AND** score is 0.5

#### Scenario: At boundary scores 0.0
- **WHEN** file is max_depth hops from seed
- **THEN** score is 0.0

---

### Requirement: Graph Caching

The system SHALL cache dependency graphs for session duration to avoid rebuilding.

#### Scenario: Cache hit on subsequent calls
- **WHEN** graph built once per session
- **AND** resolve_for_subgoal called multiple times
- **THEN** reuse cached graph
- **AND** avoid re-parsing imports

#### Scenario: Cache invalidation on index change
- **WHEN** memory index timestamp changes
- **THEN** invalidate cached graph
- **AND** rebuild on next request

---

### Requirement: Error Handling

The system SHALL handle missing imports and parse errors gracefully.

#### Scenario: Missing import target
- **WHEN** import cannot be resolved to file path
- **THEN** skip that edge
- **AND** log warning in debug mode
- **AND** continue with remaining edges

#### Scenario: Parse error in chunk
- **WHEN** chunk content cannot be parsed for imports
- **THEN** skip that chunk
- **AND** continue with remaining chunks

#### Scenario: Empty graph fallback
- **WHEN** no imports found in codebase
- **THEN** return empty related files list
- **AND** fall back to semantic search only

---

### Requirement: Performance Targets

The system SHALL meet performance targets for graph construction and traversal.

#### Scenario: Graph construction time
- **WHEN** codebase has 5000 files
- **THEN** graph construction completes in <200ms

#### Scenario: Traversal time per subgoal
- **WHEN** max_depth is 2
- **AND** processing single subgoal
- **THEN** traversal completes in <50ms

#### Scenario: Memory usage
- **WHEN** graph cached in memory
- **THEN** overhead is <50MB for typical codebase
