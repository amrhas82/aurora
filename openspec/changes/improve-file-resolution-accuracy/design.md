# Design: Improve File Resolution Accuracy in aur goals

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         aur goals Command                            │
│  (packages/cli/src/aurora_cli/planning/decompose.py)                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Goal Decomposer                                 │
│  Creates subgoals from user goal                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   FilePathResolver (Enhanced)                        │
│  packages/cli/src/aurora_cli/planning/memory.py                     │
│                                                                       │
│  - resolve_for_subgoal(subgoal, limit=5) → list[FileResolution]     │
│  - _extract_keywords(subgoal) → list[str]                           │
│  - _classify_change_type(subgoal) → ChangeType                      │
└─────────────┬───────────────────────────┬────────────────────────────┘
              │                           │
              │                           │
    ┌─────────▼─────────┐       ┌─────────▼──────────┐
    │ MemoryRetriever   │       │ StructuralAnalyzer │
    │   (Existing)      │       │      (New)         │
    │                   │       │                    │
    │ - Semantic search │       │ - Import tracking  │
    │ - BM25 + embeddings│      │ - Call graphs      │
    │ - Keyword matching│       │ - Dependency map   │
    └─────────┬─────────┘       └─────────┬──────────┘
              │                           │
              │                           │
              └───────────┬───────────────┘
                          │
                          ▼
              ┌───────────────────────────┐
              │   MultiFactorScorer       │
              │         (New)             │
              │                           │
              │ - Combine scores:         │
              │   • Semantic (40%)        │
              │   • Structural (30%)      │
              │   • Recency (20%)         │
              │   • Type relevance (10%)  │
              │ - Filter by threshold     │
              │ - Explain scores          │
              └───────────┬───────────────┘
                          │
                          ▼
              ┌───────────────────────────┐
              │  list[FileResolution]     │
              │  (confidence > 0.6)       │
              └───────────────────────────┘
```

## Component Specifications

### 1. FilePathResolver (Enhanced)

**Location**: `packages/cli/src/aurora_cli/planning/memory.py`

**Current Implementation**:
```python
class FilePathResolver:
    def __init__(self, retriever: MemoryRetriever):
        self.retriever = retriever

    def resolve_for_subgoal(self, subgoal: Subgoal, limit: int = 5) -> list[FileResolution]:
        # Current: simple keyword search
        chunks = self.retriever.retrieve(subgoal.description, limit=limit)
        return [FileResolution(path=c.file_path, confidence=c.score) for c in chunks]
```

**Enhanced Implementation**:
```python
from aurora_cli.planning.structural import StructuralAnalyzer
from aurora_cli.planning.change_types import ChangeTypeClassifier
from aurora_cli.planning.scoring import MultiFactorScorer

class FilePathResolver:
    def __init__(
        self,
        retriever: MemoryRetriever,
        structural_analyzer: StructuralAnalyzer | None = None,
        change_classifier: ChangeTypeClassifier | None = None,
        scorer: MultiFactorScorer | None = None
    ):
        self.retriever = retriever
        self.structural = structural_analyzer or StructuralAnalyzer(retriever.store)
        self.classifier = change_classifier or ChangeTypeClassifier()
        self.scorer = scorer or MultiFactorScorer()

    def resolve_for_subgoal(
        self,
        subgoal: Subgoal,
        goal_context: str = "",
        limit: int = 5
    ) -> list[FileResolution]:
        """
        Resolve files for subgoal using multi-factor analysis.

        Args:
            subgoal: Subgoal to resolve files for
            goal_context: Parent goal description for additional context
            limit: Maximum files to return

        Returns:
            List of FileResolution with confidence > 0.6, ranked by relevance
        """
        # 1. Classify change type
        change_type = self.classifier.classify(subgoal, goal_context)

        # 2. Semantic search with enhanced keywords
        keywords = self._extract_keywords(subgoal, goal_context)
        query = " ".join(keywords)
        semantic_results = self.retriever.retrieve(query, limit=limit * 3)

        # 3. Structural analysis
        structural_results = self.structural.find_related_files(
            seed_files=[r.file_path for r in semantic_results[:3]],
            change_type=change_type
        )

        # 4. Combine and score
        all_candidates = self._merge_candidates(semantic_results, structural_results)
        scored = self.scorer.score(
            candidates=all_candidates,
            subgoal=subgoal,
            change_type=change_type
        )

        # 5. Filter and rank
        filtered = [r for r in scored if r.confidence >= 0.6]
        return sorted(filtered, key=lambda r: r.confidence, reverse=True)[:limit]

    def _extract_keywords(self, subgoal: Subgoal, context: str) -> list[str]:
        """Extract keywords from subgoal + context."""
        # Combine subgoal description with goal context
        text = f"{subgoal.description} {context}"

        # Extract key terms (nouns, verbs, technical terms)
        # Use simple heuristics for v1
        words = text.lower().split()

        # Filter stopwords, keep technical terms
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        return keywords

    def _merge_candidates(
        self,
        semantic: list[MemoryChunk],
        structural: list[tuple[Path, float]]
    ) -> dict[Path, CandidateFile]:
        """Merge semantic and structural results."""
        candidates = {}

        # Add semantic results
        for chunk in semantic:
            path = Path(chunk.file_path)
            if path not in candidates:
                candidates[path] = CandidateFile(
                    path=path,
                    semantic_score=chunk.score,
                    structural_score=0.0,
                    recency_score=0.0
                )

        # Add structural results
        for path, score in structural:
            if path not in candidates:
                candidates[path] = CandidateFile(
                    path=path,
                    semantic_score=0.0,
                    structural_score=score,
                    recency_score=0.0
                )
            else:
                candidates[path].structural_score = score

        return candidates
```

### 2. StructuralAnalyzer (New)

**Location**: `packages/cli/src/aurora_cli/planning/structural.py`

**Purpose**: Analyze code structure to find related files beyond semantic search

**Implementation**:
```python
from pathlib import Path
from dataclasses import dataclass
from aurora_core.store import SQLiteStore
from aurora_cli.planning.change_types import ChangeType

@dataclass
class ImportRelation:
    """Represents import relationship between files."""
    source: Path
    target: Path
    import_type: str  # "direct" | "transitive"

@dataclass
class DependencyGraph:
    """File dependency graph."""
    nodes: set[Path]
    edges: list[ImportRelation]

    def get_importers(self, file: Path) -> list[Path]:
        """Files that import this file."""
        return [e.source for e in self.edges if e.target == file]

    def get_imports(self, file: Path) -> list[Path]:
        """Files imported by this file."""
        return [e.target for e in self.edges if e.source == file]

class StructuralAnalyzer:
    """Analyzes code structure to find related files."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self._graph_cache: DependencyGraph | None = None

    def find_related_files(
        self,
        seed_files: list[Path],
        change_type: ChangeType,
        max_depth: int = 2
    ) -> list[tuple[Path, float]]:
        """
        Find files related to seed files based on change type.

        Args:
            seed_files: Starting files from semantic search
            change_type: Type of change being made
            max_depth: How many hops to traverse

        Returns:
            List of (file_path, structural_score) tuples
        """
        graph = self._get_dependency_graph()
        related = set()

        for seed in seed_files:
            if change_type == ChangeType.ADD_FEATURE:
                # Find similar existing features (same directory, similar names)
                related.update(self._find_similar_features(seed, graph))

            elif change_type == ChangeType.REFACTOR:
                # Find callers and callees
                related.update(self._find_callers_and_callees(seed, graph, max_depth))

            elif change_type == ChangeType.BUG_FIX:
                # Focus on direct dependencies
                related.update(self._find_direct_dependencies(seed, graph))

            elif change_type == ChangeType.TEST:
                # Prioritize test files
                related.update(self._find_test_files(seed, graph))

        # Score by distance from seed files
        scored = []
        for file in related:
            distance = self._min_distance_to_seeds(file, seed_files, graph)
            score = max(0.0, 1.0 - (distance / max_depth))
            scored.append((file, score))

        return sorted(scored, key=lambda x: x[1], reverse=True)

    def _get_dependency_graph(self) -> DependencyGraph:
        """Build or retrieve cached dependency graph."""
        if self._graph_cache:
            return self._graph_cache

        # Query indexed metadata for import information
        # Assumes tree-sitter indexing captures import statements
        edges = []

        # Query chunks for import patterns
        # This is simplified - actual implementation would parse chunk metadata
        conn = self.store._get_connection()
        cursor = conn.execute("""
            SELECT file_path, content
            FROM chunks
            WHERE content LIKE '%import %' OR content LIKE '%from %'
        """)

        import_map = {}
        for row in cursor:
            file_path = Path(row[0])
            content = row[1]

            # Parse imports (simplified - use tree-sitter in production)
            imports = self._parse_imports(content)
            import_map[file_path] = imports

        # Build edges
        for source, targets in import_map.items():
            for target in targets:
                edges.append(ImportRelation(source, target, "direct"))

        nodes = set(import_map.keys())
        self._graph_cache = DependencyGraph(nodes, edges)
        return self._graph_cache

    def _parse_imports(self, content: str) -> list[Path]:
        """Parse import statements from code content."""
        # Simplified implementation
        # Production would use tree-sitter AST parsing
        imports = []
        for line in content.split("\n"):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                # Extract module name and resolve to file path
                # This is placeholder logic
                pass
        return imports

    def _find_similar_features(self, seed: Path, graph: DependencyGraph) -> set[Path]:
        """Find files in same directory or with similar names."""
        similar = set()

        # Same directory
        for node in graph.nodes:
            if node.parent == seed.parent and node != seed:
                similar.add(node)

        # Similar names (e.g., user_auth.py and user_profile.py)
        seed_stem = seed.stem.split("_")[0]  # "user" from "user_auth"
        for node in graph.nodes:
            if node.stem.startswith(seed_stem) and node != seed:
                similar.add(node)

        return similar

    def _find_callers_and_callees(
        self,
        seed: Path,
        graph: DependencyGraph,
        max_depth: int
    ) -> set[Path]:
        """Find files that call or are called by seed (BFS)."""
        related = set()
        visited = {seed}
        queue = [(seed, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            # Files that import current
            for importer in graph.get_importers(current):
                if importer not in visited:
                    related.add(importer)
                    visited.add(importer)
                    queue.append((importer, depth + 1))

            # Files imported by current
            for imported in graph.get_imports(current):
                if imported not in visited:
                    related.add(imported)
                    visited.add(imported)
                    queue.append((imported, depth + 1))

        return related

    def _find_direct_dependencies(self, seed: Path, graph: DependencyGraph) -> set[Path]:
        """Find files directly imported by seed."""
        return set(graph.get_imports(seed))

    def _find_test_files(self, seed: Path, graph: DependencyGraph) -> set[Path]:
        """Find test files related to seed."""
        test_files = set()

        for node in graph.nodes:
            # Test file naming conventions
            if "test_" in node.name or "_test" in node.name or "/tests/" in str(node):
                # Check if test file relates to seed
                if seed.stem in node.stem or seed.parent == node.parent.parent:
                    test_files.add(node)

        return test_files

    def _min_distance_to_seeds(
        self,
        target: Path,
        seeds: list[Path],
        graph: DependencyGraph
    ) -> int:
        """Calculate minimum graph distance from target to any seed file."""
        # BFS to find shortest path
        if target in seeds:
            return 0

        visited = {target}
        queue = [(target, 0)]

        while queue:
            current, depth = queue.pop(0)

            # Check neighbors
            neighbors = set(graph.get_importers(current)) | set(graph.get_imports(current))
            for neighbor in neighbors:
                if neighbor in seeds:
                    return depth + 1

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return 999  # No path found
```

### 3. ChangeTypeClassifier (New)

**Location**: `packages/cli/src/aurora_cli/planning/change_types.py`

**Purpose**: Classify subgoals by change type for type-specific file filtering

**Implementation**:
```python
from enum import Enum
from dataclasses import dataclass

class ChangeType(Enum):
    """Types of code changes."""
    ADD_FEATURE = "add_feature"
    REFACTOR = "refactor"
    BUG_FIX = "bug_fix"
    TEST = "test"
    DOCUMENTATION = "documentation"
    UNKNOWN = "unknown"

@dataclass
class ChangeTypePattern:
    """Pattern for detecting change type."""
    keywords: list[str]
    type: ChangeType
    weight: float = 1.0

class ChangeTypeClassifier:
    """Classifies subgoals by change type."""

    PATTERNS = [
        # Add feature patterns
        ChangeTypePattern(["add", "create", "implement", "new", "feature"], ChangeType.ADD_FEATURE, 1.0),
        ChangeTypePattern(["build", "develop", "introduce"], ChangeType.ADD_FEATURE, 0.8),

        # Refactor patterns
        ChangeTypePattern(["refactor", "restructure", "reorganize", "cleanup"], ChangeType.REFACTOR, 1.0),
        ChangeTypePattern(["improve", "optimize", "simplify"], ChangeType.REFACTOR, 0.7),

        # Bug fix patterns
        ChangeTypePattern(["fix", "bug", "error", "issue", "crash"], ChangeType.BUG_FIX, 1.0),
        ChangeTypePattern(["resolve", "patch", "correct"], ChangeType.BUG_FIX, 0.8),

        # Test patterns
        ChangeTypePattern(["test", "testing", "coverage", "unittest"], ChangeType.TEST, 1.0),
        ChangeTypePattern(["verify", "validate", "check"], ChangeType.TEST, 0.6),

        # Documentation patterns
        ChangeTypePattern(["document", "docs", "readme", "comment"], ChangeType.DOCUMENTATION, 1.0),
    ]

    def classify(self, subgoal: "Subgoal", goal_context: str = "") -> ChangeType:
        """
        Classify subgoal by change type.

        Args:
            subgoal: Subgoal to classify
            goal_context: Parent goal description

        Returns:
            ChangeType enum value
        """
        text = f"{subgoal.description} {goal_context}".lower()

        # Score each type
        type_scores = {t: 0.0 for t in ChangeType}

        for pattern in self.PATTERNS:
            for keyword in pattern.keywords:
                if keyword in text:
                    type_scores[pattern.type] += pattern.weight

        # Return highest scoring type
        max_score = max(type_scores.values())
        if max_score == 0:
            return ChangeType.UNKNOWN

        for change_type, score in type_scores.items():
            if score == max_score:
                return change_type

        return ChangeType.UNKNOWN
```

### 4. MultiFactorScorer (New)

**Location**: `packages/cli/src/aurora_cli/planning/scoring.py`

**Purpose**: Combine multiple scoring factors with configurable weights

**Implementation**:
```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from aurora_cli.planning.change_types import ChangeType

@dataclass
class CandidateFile:
    """File candidate with component scores."""
    path: Path
    semantic_score: float  # 0.0-1.0
    structural_score: float  # 0.0-1.0
    recency_score: float  # 0.0-1.0

@dataclass
class ScoredResolution:
    """File resolution with confidence and explanation."""
    path: Path
    confidence: float
    explanation: str

class MultiFactorScorer:
    """Combines multiple scoring factors."""

    def __init__(
        self,
        semantic_weight: float = 0.4,
        structural_weight: float = 0.3,
        recency_weight: float = 0.2,
        type_relevance_weight: float = 0.1
    ):
        self.semantic_w = semantic_weight
        self.structural_w = structural_weight
        self.recency_w = recency_weight
        self.type_w = type_relevance_weight

    def score(
        self,
        candidates: dict[Path, CandidateFile],
        subgoal: "Subgoal",
        change_type: ChangeType
    ) -> list[ScoredResolution]:
        """
        Score candidates using multi-factor algorithm.

        Args:
            candidates: Files to score with component scores
            subgoal: Subgoal for context
            change_type: Type of change for relevance filtering

        Returns:
            List of scored resolutions with explanations
        """
        scored = []

        for path, candidate in candidates.items():
            # Calculate type relevance
            type_score = self._type_relevance(path, change_type)

            # Calculate recency (already in candidate or compute)
            if candidate.recency_score == 0.0:
                candidate.recency_score = self._recency_score(path)

            # Weighted combination
            confidence = (
                self.semantic_w * candidate.semantic_score +
                self.structural_w * candidate.structural_score +
                self.recency_w * candidate.recency_score +
                self.type_w * type_score
            )

            # Build explanation
            explanation = self._explain_score(
                semantic=candidate.semantic_score,
                structural=candidate.structural_score,
                recency=candidate.recency_score,
                type_rel=type_score
            )

            scored.append(ScoredResolution(path, confidence, explanation))

        return scored

    def _type_relevance(self, path: Path, change_type: ChangeType) -> float:
        """Score based on file type relevance to change type."""
        if change_type == ChangeType.TEST:
            # Prioritize test files
            if "test" in path.name or "/tests/" in str(path):
                return 1.0
            return 0.3  # Non-test files less relevant

        elif change_type == ChangeType.DOCUMENTATION:
            # Prioritize docs
            if path.suffix in [".md", ".rst", ".txt"]:
                return 1.0
            return 0.2

        elif change_type == ChangeType.BUG_FIX:
            # Penalize test files unless fixing tests
            if "test" in path.name:
                return 0.5
            return 1.0

        else:
            # Default: no penalty
            return 1.0

    def _recency_score(self, path: Path) -> float:
        """Score based on file modification recency."""
        try:
            mtime = path.stat().st_mtime
            age_days = (datetime.now().timestamp() - mtime) / 86400

            # Decay function: 1.0 for recent, 0.0 for old (>180 days)
            if age_days <= 7:
                return 1.0
            elif age_days <= 30:
                return 0.8
            elif age_days <= 90:
                return 0.5
            elif age_days <= 180:
                return 0.3
            else:
                return 0.1
        except (OSError, FileNotFoundError):
            return 0.5  # Unknown, neutral score

    def _explain_score(
        self,
        semantic: float,
        structural: float,
        recency: float,
        type_rel: float
    ) -> str:
        """Generate human-readable score explanation."""
        factors = []

        if semantic > 0.7:
            factors.append(f"strong keyword match ({semantic:.2f})")
        elif semantic > 0.4:
            factors.append(f"moderate keyword match ({semantic:.2f})")

        if structural > 0.5:
            factors.append(f"structurally related ({structural:.2f})")

        if recency > 0.7:
            factors.append("recently modified")

        if type_rel < 0.5:
            factors.append("lower type relevance")

        return "; ".join(factors) if factors else "general relevance"
```

## Integration Points

### 1. Modify Goal Decomposer

**File**: `packages/cli/src/aurora_cli/planning/decompose.py`

**Change**: Pass goal context to FilePathResolver

```python
def decompose_goal_with_files(goal: str, retriever: MemoryRetriever) -> Goals:
    # Existing decomposition logic...
    subgoals = decomposer.decompose(goal)

    # Enhanced file resolution
    resolver = FilePathResolver(retriever)  # Now uses enhanced version

    for subgoal in subgoals:
        # Pass goal context for better keyword extraction
        files = resolver.resolve_for_subgoal(subgoal, goal_context=goal)
        subgoal.related_files = files

    return Goals(goal=goal, subgoals=subgoals)
```

### 2. Update Goals Model

**File**: `packages/cli/src/aurora_cli/planning/models.py`

**Change**: Add explanation to FileResolution

```python
@dataclass
class FileResolution:
    """Resolved file path with confidence score."""
    path: Path
    confidence: float
    explanation: str = ""  # New field for score breakdown
```

## Configuration

**File**: `packages/cli/src/aurora_cli/config.py`

Add configuration for file resolution:

```python
@dataclass
class FileResolutionConfig:
    """Configuration for file path resolution."""
    min_confidence: float = 0.6
    max_files_per_subgoal: int = 5
    enable_structural_analysis: bool = True
    semantic_weight: float = 0.4
    structural_weight: float = 0.3
    recency_weight: float = 0.2
    type_relevance_weight: float = 0.1
```

## Performance Considerations

### Caching Strategy

**Dependency Graph Cache**:
- Build once per `aur goals` invocation
- Invalidate if memory index changes
- Store in `StructuralAnalyzer._graph_cache`

**Recency Scores**:
- Cache file mtimes for session
- Batch file stat calls

### Lazy Loading

- Only build dependency graph if structural analysis enabled
- Skip structural analysis for DOCUMENTATION change type

### Query Optimization

- Retrieve 3x limit from memory for filtering
- Filter by confidence threshold before sorting
- Use set operations for graph traversal

## Backward Compatibility

- New components are optional dependencies of FilePathResolver
- Default behavior unchanged if not initialized
- Confidence threshold configurable (default 0.6, can lower to 0.3)
- `resolve_for_subgoal` signature backward compatible (goal_context optional)

## Testing Strategy

### Unit Tests

- `test_change_type_classifier.py` - Pattern matching accuracy
- `test_structural_analyzer.py` - Graph construction, traversal
- `test_multi_factor_scorer.py` - Score calculation, weighting
- `test_file_path_resolver.py` - Integration of all components

### Integration Tests

- `test_file_resolution_e2e.py` - Full workflow with real codebase
- `test_resolution_accuracy.py` - Compare against ground truth

### Benchmark Suite

Create 20 test cases with known correct file resolutions:

```python
BENCHMARK_CASES = [
    {
        "goal": "Add OAuth2 authentication",
        "subgoal": "Implement OAuth2 token validation",
        "expected_files": [
            "packages/core/src/auth/oauth.py",
            "packages/core/src/auth/tokens.py"
        ]
    },
    # ... 19 more cases
]
```

Measure:
- Recall: % of expected files found
- Precision: % of returned files in expected set
- Confidence distribution

## Error Handling

- Missing dependency graph → fall back to semantic-only
- Parse errors in imports → skip that file in graph
- File not found → remove from candidates
- Low confidence for all files → return best effort with warning

## User-Visible Changes

### Verbose Output

```bash
$ aur goals "Add OAuth2 authentication" --verbose

Resolving files for: "Implement OAuth2 token validation"
  Change type: add_feature
  Semantic candidates: 12 files
  Structural candidates: 5 files
  After scoring: 3 files (confidence > 0.6)

Files resolved:
  [0.85] packages/core/src/auth/oauth.py
         strong keyword match (0.92); structurally related (0.78); recently modified
  [0.72] packages/core/src/auth/tokens.py
         moderate keyword match (0.65); structurally related (0.88)
  [0.68] packages/api/src/routes/auth.py
         strong keyword match (0.78); general relevance
```

### Goals JSON

```json
{
  "subgoals": [
    {
      "id": "sg-1",
      "title": "Implement OAuth2 token validation",
      "files": [
        {
          "path": "packages/core/src/auth/oauth.py",
          "confidence": 0.85,
          "explanation": "strong keyword match (0.92); structurally related (0.78)"
        }
      ]
    }
  ]
}
```
