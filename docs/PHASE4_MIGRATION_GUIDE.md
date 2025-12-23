# AURORA Phase 4+ Migration Guide

**Document Version**: 1.0
**Target Audience**: Phase 4+ Developers, Contributors, Maintainers
**Effective Date**: December 23, 2025
**Phase 3 Version**: v1.0.0-phase3

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Phase 3 Architecture Overview](#2-phase-3-architecture-overview)
3. [Stable APIs & Contracts](#3-stable-apis--contracts)
4. [Extension Points](#4-extension-points)
5. [Development Environment Setup](#5-development-environment-setup)
6. [Adding New Features](#6-adding-new-features)
7. [Performance Considerations](#7-performance-considerations)
8. [Testing Requirements](#8-testing-requirements)
9. [Security Guidelines](#9-security-guidelines)
10. [Documentation Standards](#10-documentation-standards)
11. [Release Process](#11-release-process)
12. [Common Migration Patterns](#12-common-migration-patterns)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Introduction

### 1.1 Purpose

This guide helps Phase 4+ developers understand the AURORA Phase 3 codebase, stable APIs, extension points, and best practices for adding new features without breaking existing functionality.

### 1.2 Scope

**Phase 3 Deliverables** (Complete):
- ACT-R activation engine with full formulas
- Semantic embeddings with hybrid retrieval
- Headless reasoning mode with autonomous execution
- Performance optimization (multi-tier caching, parallel execution)
- Production hardening (retry logic, metrics, rate limiting, alerting)
- Memory commands and auto-escalation

**Phase 4+ Goals** (Future):
- Advanced retrieval (re-ranking, query expansion, domain adaptation)
- Collaborative agents (multi-agent coordination, role specialization)
- Learning & adaptation (feedback loops, preference learning)
- Production scaling (distributed caching, horizontal scaling)
- Security hardening (sandboxing, secrets management, audit logging)

### 1.3 Prerequisites

- Familiarity with Python 3.9+
- Understanding of cognitive architectures (ACT-R)
- Experience with machine learning (embeddings, semantic similarity)
- Knowledge of distributed systems (for scaling features)
- Security best practices

---

## 2. Phase 3 Architecture Overview

### 2.1 Package Structure

```
aurora/
├── packages/
│   ├── core/                    # Core activation engine, optimization, resilience
│   │   ├── src/aurora_core/
│   │   │   ├── activation/      # ACT-R formulas (BLA, spreading, context, decay)
│   │   │   ├── optimization/    # Query optimizer, cache manager, parallel executor
│   │   │   ├── resilience/      # Retry handler, metrics, rate limiter, alerting
│   │   │   └── store/           # Chunk storage interface (SQLite, Memory)
│   │   └── tests/
│   ├── context-code/            # Semantic embeddings and hybrid retrieval
│   │   ├── src/aurora_context_code/
│   │   │   └── semantic/        # Embedding provider, hybrid retriever
│   │   └── tests/
│   ├── soar/                    # SOAR orchestration and headless mode
│   │   ├── src/aurora_soar/
│   │   │   └── headless/        # Git enforcer, prompt loader, scratchpad, orchestrator
│   │   └── tests/
│   └── cli/                     # Command-line interface
│       ├── src/aurora_cli/
│       │   ├── commands/        # Memory command, headless command
│       │   └── escalation.py    # Auto-escalation handler
│       └── tests/
├── docs/                        # Comprehensive documentation
├── tests/                       # Integration and performance tests
└── tasks/                       # Project management
```

### 2.2 Dependency Graph

```
cli → soar, context-code, core
soar → core
context-code → core
core → (external dependencies only)
```

**Design Principle**: Core package has no internal dependencies, enabling independent evolution of higher-level packages.

### 2.3 Key Design Patterns

1. **Factory Pattern**: `ActivationEngine.create_preset("default")`
2. **Strategy Pattern**: Pluggable activation formulas
3. **Builder Pattern**: Configuration classes (ActivationConfig, HybridConfig)
4. **Facade Pattern**: HeadlessOrchestrator simplifies complex interactions
5. **Repository Pattern**: ChunkStore interface abstracts storage
6. **Observer Pattern**: MetricsCollector for real-time monitoring

---

## 3. Stable APIs & Contracts

### 3.1 Guaranteed Stable APIs (v1.x)

All public APIs in `docs/API_CONTRACTS_v1.0.md` are guaranteed stable within v1.x:

**Core Activation**:
- `ActivationEngine.__init__()`, `calculate_activation()`, `create_preset()`
- `ActivationRetriever.retrieve()`
- All activation formula classes (BLA, Spreading, Context, Decay)

**Semantic Context**:
- `EmbeddingProvider.__init__()`, `embed_chunk()`, `embed_query()`
- `HybridRetriever.retrieve()`
- `cosine_similarity()`

**Headless Mode**:
- `HeadlessOrchestrator.__init__()`, `run()`
- `HeadlessResult` dataclass
- CLI commands: `aur mem`, `aur headless`

**Resilience**:
- `RetryHandler.execute_with_retry()`
- `MetricsCollector.record_query()`, `get_metrics()`
- `RateLimiter.wait_if_needed()`
- `Alerting` class

### 3.2 Breaking Changes Policy

**Within v1.x** (Minor/Patch):
- ✅ Add new optional parameters (backward compatible)
- ✅ Add new methods to classes
- ✅ Add new classes/modules
- ✅ Enhance internal implementation
- ❌ Change required parameter signatures
- ❌ Remove or rename public APIs
- ❌ Change return types

**In v2.0+** (Major):
- ✅ All breaking changes allowed with:
  - 6-month deprecation warning period
  - Clear migration guide
  - Automated migration tools (if feasible)

---

## 4. Extension Points

### 4.1 Adding New Activation Formulas

**Use Case**: Custom activation calculation (e.g., topic-specific weighting)

**Extension Point**: `ActivationEngine` accepts custom formula components

**Example**:
```python
from aurora_core.activation import ActivationEngine, ActivationConfig

class TopicActivation:
    """Custom topic-based activation boost."""

    def calculate(self, chunk_keywords: Set[str], topic: str) -> float:
        if topic in chunk_keywords:
            return 2.0  # Strong boost
        return 0.0

# Use in engine
config = ActivationConfig(...)
engine = ActivationEngine(config)

# Add custom component (Phase 4 feature - requires engine enhancement)
# engine.register_component("topic_boost", TopicActivation())
```

**Migration Path**: Phase 4 will add `register_component()` method to ActivationEngine (backward compatible).

### 4.2 Adding New Embedding Models

**Use Case**: Domain-specific embeddings (CodeBERT, GraphCodeBERT)

**Extension Point**: `EmbeddingProvider` can be subclassed

**Example**:
```python
from aurora_context_code.semantic import EmbeddingProvider

class CodeBERTProvider(EmbeddingProvider):
    """CodeBERT-based embeddings for code."""

    def __init__(self):
        super().__init__(model_name="microsoft/codebert-base")

    def embed_chunk(self, name, docstring=None, signature=None):
        # Custom preprocessing for code
        code_text = self._format_for_codebert(name, docstring, signature)
        return self.model.encode(code_text, normalize_embeddings=True)

# Use in retriever
provider = CodeBERTProvider()
retriever = HybridRetriever(store, engine, provider)
```

**Migration Path**: Phase 4 will add provider registry for easy switching.

### 4.3 Adding New Retrieval Strategies

**Use Case**: Re-ranking, query expansion, diversification

**Extension Point**: `HybridRetriever` can be subclassed or wrapped

**Example**:
```python
from aurora_context_code.semantic import HybridRetriever

class ReRankingRetriever:
    """Re-ranks hybrid results using cross-encoder."""

    def __init__(self, hybrid_retriever, cross_encoder):
        self.hybrid_retriever = hybrid_retriever
        self.cross_encoder = cross_encoder

    def retrieve(self, query, top_k=10):
        # Get initial candidates (top 100)
        candidates = self.hybrid_retriever.retrieve(query, top_k=100)

        # Re-rank with cross-encoder
        scores = self.cross_encoder.predict([(query, c.context) for c in candidates])
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)

        return [c for c, _ in ranked[:top_k]]

# Use in application
retriever = ReRankingRetriever(hybrid_retriever, cross_encoder_model)
```

**Migration Path**: Phase 4 will add first-class re-ranking support to HybridRetriever.

### 4.4 Adding New Headless Termination Conditions

**Use Case**: Custom goal completion detection (e.g., code coverage threshold)

**Extension Point**: `HeadlessOrchestrator` can be extended with custom evaluators

**Example**:
```python
from aurora_soar.headless import HeadlessOrchestrator

class CoverageAwareOrchestrator(HeadlessOrchestrator):
    """Terminates when code coverage exceeds threshold."""

    def _check_coverage_goal(self) -> bool:
        coverage = self._run_coverage_tool()
        if coverage >= self.config.coverage_threshold:
            self.scratchpad.append(f"Coverage goal met: {coverage}%")
            return True
        return False

    def _should_terminate(self) -> Tuple[bool, str]:
        # Check coverage first
        if self._check_coverage_goal():
            return True, "COVERAGE_GOAL_ACHIEVED"

        # Fall back to parent logic
        return super()._should_terminate()
```

**Migration Path**: Phase 4 will add plugin system for custom termination conditions.

### 4.5 Adding New Metrics & Alerts

**Use Case**: Domain-specific metrics (e.g., semantic drift, query diversity)

**Extension Point**: `MetricsCollector` and `Alerting` can be extended

**Example**:
```python
from aurora_core.resilience import MetricsCollector, Alerting, AlertRule, AlertSeverity

class SemanticDriftMetrics(MetricsCollector):
    """Tracks semantic drift in query embeddings."""

    def __init__(self):
        super().__init__()
        self.query_embeddings = []

    def record_query_embedding(self, embedding):
        self.query_embeddings.append(embedding)
        if len(self.query_embeddings) > 100:
            self.query_embeddings.pop(0)

    def get_drift_score(self):
        if len(self.query_embeddings) < 10:
            return 0.0
        # Calculate mean pairwise distance
        return self._calculate_drift(self.query_embeddings)

# Add alert rule
alerting = Alerting()
alerting.add_rule(AlertRule(
    name="semantic_drift_alert",
    condition=lambda metrics: metrics.get_drift_score() > 0.5,
    severity=AlertSeverity.MEDIUM,
    message="Semantic drift detected: query patterns changing significantly"
))
```

**Migration Path**: Phase 4 will formalize metrics extension API.

---

## 5. Development Environment Setup

### 5.1 Prerequisites

```bash
# Python 3.9+ required
python --version  # Should be ≥3.9

# Git for version control
git --version

# Virtual environment recommended
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

### 5.2 Installation

```bash
# Clone repository
git clone https://github.com/your-org/aurora.git
cd aurora

# Install in development mode (all packages)
pip install -e packages/core
pip install -e packages/context-code
pip install -e packages/soar
pip install -e packages/cli

# Install development dependencies
pip install -r requirements-dev.txt  # pytest, mypy, ruff, bandit, etc.
```

### 5.3 Verification

```bash
# Run test suite (should pass 1,824 tests)
pytest

# Run type checking
mypy packages/*/src --strict

# Run linting
ruff check packages/

# Run security scan
bandit -r packages/ -ll

# Check CLI
aur --version  # Should show v1.0.0-phase3
```

---

## 6. Adding New Features

### 6.1 Feature Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write Tests First** (TDD)
   ```bash
   # Create test file
   touch tests/unit/core/test_your_feature.py

   # Write failing tests
   pytest tests/unit/core/test_your_feature.py  # Should fail
   ```

3. **Implement Feature**
   ```bash
   # Add implementation
   vim packages/core/src/aurora_core/your_feature.py

   # Run tests until passing
   pytest tests/unit/core/test_your_feature.py
   ```

4. **Integration Tests**
   ```bash
   # Add integration test
   touch tests/integration/test_your_feature_integration.py

   # Verify end-to-end
   pytest tests/integration/test_your_feature_integration.py
   ```

5. **Documentation**
   ```bash
   # Add docstrings to all public APIs
   # Update docs/
   # Add examples to docs/examples/
   ```

6. **Quality Gates**
   ```bash
   # All must pass before PR
   pytest --cov  # Coverage ≥85%
   mypy packages/*/src --strict  # Type safety
   ruff check packages/  # Linting
   bandit -r packages/ -ll  # Security
   ```

7. **Pull Request**
   - Create PR with clear description
   - Link to relevant issues
   - Request 2+ reviewers
   - Address feedback

### 6.2 Backward Compatibility Checklist

Before submitting PR for v1.x:
- [ ] No changes to required parameter signatures
- [ ] No removal of public APIs
- [ ] No changes to return types
- [ ] All new parameters are optional with defaults
- [ ] Existing tests still pass
- [ ] API contracts documentation updated
- [ ] Migration guide updated (if needed)
- [ ] Deprecation warnings added (if deprecating anything)

### 6.3 Adding Configuration Options

**Pattern**: Add to configuration schema with sensible defaults

**Example**:
```python
# packages/core/src/aurora_core/config.py

@dataclass
class RetrievalConfig:
    activation_threshold: float = 0.3
    batch_size: int = 100
    # Add new option (backward compatible)
    enable_caching: bool = True  # Default maintains existing behavior
```

**YAML Config**:
```yaml
# config.yaml (optional user override)
retrieval:
  activation_threshold: 0.3
  batch_size: 100
  enable_caching: true  # New option
```

---

## 7. Performance Considerations

### 7.1 Performance Targets (Must Maintain)

| Metric | Target | Current |
|--------|--------|---------|
| 100 chunks retrieval | <100ms | ~80ms |
| 1K chunks retrieval | <200ms | ~150ms |
| 10K chunks (p95) | <500ms | ~420ms |
| Query embedding | <50ms | ~45ms |
| Cache hit rate | ≥30% | 34% |
| Memory (10K chunks) | <100MB | ~85MB |

**Rule**: New features must not regress these targets by more than 10%.

### 7.2 Profiling Before Optimization

```python
# Use cProfile for CPU profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
retriever.retrieve(query, top_k=10)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### 7.3 Caching Strategy

**Multi-Tier Cache** (existing):
1. **Hot Cache** (in-memory LRU, 1000 chunks)
2. **Persistent Cache** (SQLite, all chunks)
3. **Activation Scores** (10-min TTL)

**Adding New Cache Tier**:
```python
from aurora_core.optimization import CacheManager

class DistributedCacheManager(CacheManager):
    """Adds Redis tier for distributed caching."""

    def __init__(self, store, redis_client):
        super().__init__(store)
        self.redis = redis_client

    def get_chunk(self, chunk_id):
        # Check Redis before hot cache
        cached = self.redis.get(f"chunk:{chunk_id}")
        if cached:
            return json.loads(cached)

        # Fall back to parent logic
        return super().get_chunk(chunk_id)
```

---

## 8. Testing Requirements

### 8.1 Test Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Overall | ≥85% | 88.41% |
| activation/ | ≥85% | ~90%+ |
| headless/ | ≥80% | ~95%+ |
| resilience/ | ≥80% | 96.19% |
| semantic/ | ≥80% | ~92% |

**Rule**: New features must have ≥85% coverage before merge.

### 8.2 Test Types

**Unit Tests** (test individual components):
```python
def test_new_formula_returns_positive_for_high_activation():
    formula = YourNewFormula()
    score = formula.calculate(access_count=100, recency_hours=1)
    assert score > 0
```

**Integration Tests** (test component interactions):
```python
def test_new_retrieval_strategy_integrates_with_hybrid_retriever():
    retriever = HybridRetriever(store, engine, provider)
    strategy = YourNewStrategy()
    results = strategy.retrieve_with_hybrid(retriever, query="test")
    assert len(results) > 0
```

**Performance Tests** (benchmark critical paths):
```python
@pytest.mark.performance
def test_new_feature_meets_latency_target(benchmark):
    def retrieve():
        return retriever.retrieve(query="test", top_k=10)

    result = benchmark(retrieve)
    assert result.stats['mean'] < 0.5  # <500ms
```

### 8.3 Test Fixtures

**Reuse Existing Fixtures**:
```python
# tests/conftest.py has shared fixtures
def test_with_existing_fixture(memory_store, activation_engine):
    retriever = ActivationRetriever(memory_store, activation_engine)
    results = retriever.retrieve("test", top_k=5)
    assert len(results) <= 5
```

**Add New Fixtures**:
```python
# tests/fixtures/your_feature/
# Add test data files, mock objects, sample configurations
```

---

## 9. Security Guidelines

### 9.1 Security Checklist (Required for All PRs)

- [ ] Input validation on all public APIs
- [ ] No SQL string concatenation (use parameterized queries)
- [ ] No shell=True in subprocess calls
- [ ] Path validation to prevent directory traversal
- [ ] No hardcoded secrets or API keys
- [ ] Error messages don't leak sensitive data
- [ ] Logging doesn't include sensitive data
- [ ] Rate limiting for resource-intensive operations
- [ ] Budget limits for cost-intensive operations

### 9.2 Common Security Pitfalls

**BAD** (SQL Injection):
```python
cursor.execute(f"SELECT * FROM chunks WHERE id = '{chunk_id}'")
```

**GOOD**:
```python
cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
```

**BAD** (Command Injection):
```python
subprocess.run(f"git checkout {branch}", shell=True)
```

**GOOD**:
```python
subprocess.run(["git", "checkout", branch], check=True)
```

### 9.3 Secrets Management

**BAD**:
```python
API_KEY = "sk-1234567890"  # Hardcoded
```

**GOOD**:
```python
import os
API_KEY = os.environ.get("AURORA_API_KEY")
if not API_KEY:
    raise ValueError("AURORA_API_KEY environment variable required")
```

---

## 10. Documentation Standards

### 10.1 Docstring Format

**All public APIs must have docstrings** following this format:

```python
def your_function(param1: str, param2: int = 10) -> List[str]:
    """
    Brief one-line description.

    Detailed description explaining what the function does,
    any important behavior, and edge cases.

    Parameters:
        param1: Description of param1
        param2: Description of param2 (default: 10)

    Returns:
        Description of return value

    Contract:
        - Behavioral guarantee 1
        - Behavioral guarantee 2
        - Stability promise (if part of public API)

    Raises:
        ValueError: When param1 is empty
        RuntimeError: When operation fails

    Example:
        >>> result = your_function("test", param2=20)
        >>> print(len(result))
        5
    """
```

### 10.2 Documentation Updates (Required)

For each feature, update:
1. **Docstrings**: All public APIs
2. **User Guide**: `docs/` directory (if user-facing)
3. **Examples**: `docs/examples/` directory
4. **API Contracts**: `docs/API_CONTRACTS_v1.0.md` (if public API)
5. **Migration Guide**: This document (if breaking change or major feature)
6. **README**: Update feature list and examples
7. **Release Notes**: Add to next release notes draft

---

## 11. Release Process

### 11.1 Versioning (Semantic Versioning)

**Format**: MAJOR.MINOR.PATCH

- **MAJOR** (v1→v2): Breaking changes to public APIs
- **MINOR** (v1.0→v1.1): New features, backward compatible
- **PATCH** (v1.0.0→v1.0.1): Bug fixes, backward compatible

### 11.2 Release Checklist

**Pre-Release**:
- [ ] All tests passing (1,824+ tests)
- [ ] Coverage ≥85%
- [ ] Quality gates pass (mypy, ruff, bandit)
- [ ] Documentation updated
- [ ] API contracts reviewed
- [ ] Security audit completed
- [ ] Performance benchmarks met

**Release**:
- [ ] Update version in `pyproject.toml` (all packages)
- [ ] Create release notes in `RELEASE_NOTES_vX.Y.Z.md`
- [ ] Git tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] Push tag: `git push origin vX.Y.Z`
- [ ] Build distributions: `python -m build`
- [ ] Publish to PyPI (if applicable)
- [ ] GitHub release with notes

**Post-Release**:
- [ ] Announce on communication channels
- [ ] Update documentation site (if applicable)
- [ ] Create v(X.Y+1).0 milestone for next minor version

---

## 12. Common Migration Patterns

### 12.1 Migrating from Phase 2 to Phase 3

**No Breaking Changes** - Phase 3 is fully backward compatible.

**New Features to Adopt** (Optional):
1. **Activation-Based Retrieval**: Replace keyword-only with activation-based
2. **Hybrid Retrieval**: Use semantic embeddings for better precision
3. **Headless Mode**: Enable autonomous experimentation
4. **Resilience Features**: Add retry logic, metrics, alerting

**Example Migration**:
```python
# Phase 2 (keyword-only retrieval)
results = store.search_chunks(query="parse JSON", top_k=10)

# Phase 3 (activation-based)
from aurora_core.activation import ActivationEngine, ActivationRetriever
engine = ActivationEngine()
retriever = ActivationRetriever(store, engine)
results = retriever.retrieve(query="parse JSON", top_k=10)

# Phase 3 (hybrid with semantics)
from aurora_context_code.semantic import HybridRetriever, EmbeddingProvider
provider = EmbeddingProvider()
retriever = HybridRetriever(store, engine, provider)
results = retriever.retrieve(query="parse JSON", top_k=10)
```

### 12.2 Adding Multi-Tenant Support (Phase 4 Feature)

**Current**: Single-user local CLI
**Future**: Multi-tenant service with authentication

**Extension Points**:
1. Add `user_id` parameter to ChunkStore methods
2. Add authentication middleware to CLI
3. Add authorization checks in retrieval logic
4. Add tenant isolation in database

**Example**:
```python
# Phase 4 extension (backward compatible)
class MultiTenantStore(ChunkStore):
    def get_chunks(self, user_id: str, query: str) -> List[Dict]:
        # Add user_id filter
        return self.conn.execute(
            "SELECT * FROM chunks WHERE user_id = ? AND ...",
            (user_id, ...)
        )
```

### 12.3 Adding Distributed Caching (Phase 4 Feature)

**Current**: In-memory hot cache + SQLite persistent cache
**Future**: Redis/Memcached for distributed caching

**Extension Point**: Subclass `CacheManager`

**Example**:
```python
from aurora_core.optimization import CacheManager
import redis

class RedisCacheManager(CacheManager):
    def __init__(self, store, redis_url):
        super().__init__(store)
        self.redis = redis.from_url(redis_url)

    def get_chunk(self, chunk_id):
        # Try Redis first
        cached = self.redis.get(f"chunk:{chunk_id}")
        if cached:
            return json.loads(cached)

        # Fall back to parent (hot cache + SQLite)
        chunk = super().get_chunk(chunk_id)
        if chunk:
            # Populate Redis
            self.redis.setex(f"chunk:{chunk_id}", 600, json.dumps(chunk))
        return chunk
```

---

## 13. Troubleshooting

### 13.1 Common Issues

**Issue**: Tests fail after adding new feature
**Solution**: Check for API signature changes, update tests, verify fixtures

**Issue**: Performance regression after adding feature
**Solution**: Profile with cProfile, optimize hot paths, add caching

**Issue**: MyPy type errors
**Solution**: Add type hints to all new code, use `Optional[T]` for nullable types

**Issue**: Ruff linting errors
**Solution**: Run `ruff check --fix packages/` to auto-fix style issues

### 13.2 Getting Help

- **Documentation**: Read `docs/` directory thoroughly
- **Examples**: Check `docs/examples/` for usage patterns
- **Tests**: Look at existing tests for patterns
- **API Contracts**: Review `docs/API_CONTRACTS_v1.0.md` for stable APIs
- **GitHub Issues**: Search for similar issues
- **Code Review**: Request review from maintainers

### 13.3 Debugging Tips

**Enable Debug Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Use Explain Mode**:
```python
# Activation retrieval with explain
results = retriever.retrieve(query="test", explain=True)
for result in results:
    print(result.breakdown)  # Shows activation components
```

**Profile Performance**:
```python
import cProfile
profiler = cProfile.Profile()
profiler.enable()
# ... your code ...
profiler.disable()
profiler.print_stats(sort='cumulative')
```

---

## Appendix A: Phase 4 Feature Roadmap

### Planned Features (v1.1.0 - v2.0.0)

1. **Advanced Retrieval** (v1.1.0)
   - Re-ranking with cross-encoders
   - Query expansion (synonyms, related terms)
   - Domain adaptation (fine-tuned embeddings)

2. **Collaborative Agents** (v1.2.0)
   - Multi-agent coordination
   - Role specialization (planner, executor, reviewer)
   - Shared memory and context

3. **Learning & Adaptation** (v1.3.0)
   - User feedback loops
   - Preference learning
   - Adaptive activation formulas

4. **Production Scaling** (v1.4.0)
   - Distributed caching (Redis)
   - Horizontal scaling (load balancing)
   - Monitoring and observability

5. **Security Hardening** (v2.0.0 - breaking changes)
   - Authentication & authorization (RBAC)
   - Sandboxing for untrusted code
   - Secrets management (Vault integration)
   - Audit logging

---

## Appendix B: Code Examples

### Example 1: Custom Activation Formula

```python
from aurora_core.activation import ActivationEngine, ActivationConfig

class ProjectActivityBoost:
    """Boosts activation for chunks in active projects."""

    def __init__(self, active_projects: Set[str]):
        self.active_projects = active_projects

    def calculate(self, chunk_project: str) -> float:
        return 3.0 if chunk_project in self.active_projects else 0.0

# Usage (Phase 4 - requires engine enhancement)
# engine.register_component("project_boost", ProjectActivityBoost({"project-a"}))
```

### Example 2: Custom Embedding Provider

```python
from aurora_context_code.semantic import EmbeddingProvider
from transformers import AutoModel, AutoTokenizer

class GraphCodeBERTProvider(EmbeddingProvider):
    """GraphCodeBERT embeddings for code structure."""

    def __init__(self):
        self.model = AutoModel.from_pretrained("microsoft/graphcodebert-base")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/graphcodebert-base")

    def embed_chunk(self, name, docstring=None, signature=None):
        code = f"{signature}\n{docstring}" if signature and docstring else name
        inputs = self.tokenizer(code, return_tensors="pt", truncation=True, max_length=512)
        outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().detach().numpy()
        return embedding / np.linalg.norm(embedding)  # L2 normalize
```

### Example 3: Custom Metrics

```python
from aurora_core.resilience import MetricsCollector

class QueryDiversityMetrics(MetricsCollector):
    """Tracks query diversity (unique vs repeated queries)."""

    def __init__(self):
        super().__init__()
        self.query_hashes = set()

    def record_query(self, success, latency_ms, cache_hit=False, query_hash=None):
        super().record_query(success, latency_ms, cache_hit)
        if query_hash:
            self.query_hashes.add(query_hash)

    def get_diversity_score(self):
        total_queries = self._counters['total_queries']
        unique_queries = len(self.query_hashes)
        return unique_queries / total_queries if total_queries > 0 else 0.0
```

---

## Appendix C: Glossary

- **ACT-R**: Adaptive Control of Thought-Rational (cognitive architecture)
- **BLA**: Base-Level Activation (frequency and recency)
- **Spreading Activation**: Relationship-based activation propagation
- **Context Boost**: Keyword overlap scoring
- **Decay Penalty**: Time-based forgetting
- **Hybrid Retrieval**: Activation + semantic similarity
- **Headless Mode**: Autonomous goal-driven execution
- **Chunk**: Unit of stored knowledge (function, class, variable)
- **SOAR**: State Operator And Result (cognitive architecture)
- **LRU**: Least Recently Used (cache eviction policy)
- **p95**: 95th percentile (performance metric)

---

**Document Version**: 1.0
**Last Updated**: December 23, 2025
**Next Review**: v1.1.0 release (Q1 2026)

---

**END OF PHASE 4 MIGRATION GUIDE**
