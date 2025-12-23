# Live Data Validation Checklist

**Purpose**: Track items that require real-world production data to validate properly. These are metrics, targets, or assumptions that cannot be fully validated during development due to MVP constraints, synthetic benchmarks, or lack of representative data.

**When to Use**: After deployment to production or when you have access to real user queries, large codebases, and actual usage patterns.

**Status**: 🟡 Pre-Production (awaiting live deployment)

---

## 1. Retrieval Precision (≥85% Target)

**Current Status**:
- **MVP Baseline**: 36% precision on synthetic benchmarks
- **Improvement vs Keyword-Only**: +16% absolute (+80% relative)
- **Target**: ≥85% precision on common query types

**Why Live Data Needed**:
- Current benchmarks use synthetic queries and hand-labeled ground truth
- Real user queries have different distribution (intent, specificity, domain vocabulary)
- Precision can only be properly evaluated with actual developer queries in real codebases

**What to Measure After Deployment**:
1. **User feedback on retrieval quality**:
   - Track "helpful" vs "not helpful" ratings on retrieved chunks
   - Measure click-through rate on search results
   - Collect explicit precision feedback from users

2. **Query type distribution**:
   - What types of queries do users actually ask? (architectural, debugging, feature location, etc.)
   - Are benchmark queries representative of real usage?

3. **Precision by query type**:
   - Calculate precision@5 for each query category
   - Identify which types work well (>70%) vs poorly (<40%)

4. **Failure analysis**:
   - Collect false positives (irrelevant chunks ranked high)
   - Collect false negatives (relevant chunks ranked low)
   - Identify patterns in failures

**How to Re-Measure**:
```bash
# After collecting 100+ real queries with user feedback:
pytest tests/performance/test_live_precision.py --real-queries --min-samples=100

# Generate precision report by query type:
python scripts/analyze_precision.py --input=logs/user_queries.jsonl --output=docs/performance/live-precision-report.md
```

**Re-Evaluation Triggers**:
- ✓ After 100 user queries with feedback (initial validation)
- ✓ After 1,000 queries (statistically significant)
- ✓ After major model/algorithm changes
- ✓ Monthly review for first 6 months post-launch

**Short-Term Improvements to Test** (see Task 2.18):
- Optimize activation/semantic weight ratio (currently 60/40)
- Tune activation thresholds based on real query difficulty
- Add query intent classifier (architectural vs debugging vs feature location)
- Implement query expansion for sparse queries

**Long-Term Improvements to Test** (beyond MVP):
- Fine-tune embedding model on codebase-specific corpus
- Larger embedding model (384d → 768d)
- Advanced reranking with cross-encoders
- User feedback loop (learn from corrections)

**Documentation References**:
- Baseline: `/home/hamr/PycharmProjects/aurora/docs/performance/hybrid-retrieval-precision-report.md`
- Task: `/home/hamr/PycharmProjects/aurora/tasks/tasks-0004-prd-aurora-advanced-features.md` (Task 2.18)
- Completion Summary: `/home/hamr/PycharmProjects/aurora/TASK_2.18_COMPLETION_SUMMARY.md`

---

## 2. Query Latency at Scale (p95 <500ms for 10K chunks)

**Current Status**:
- **MVP Target**: <500ms p95 latency for 10K chunks
- **Tested**: Synthetic benchmarks with controlled chunk counts
- **Unknown**: Real-world latency distribution with concurrent users

**Why Live Data Needed**:
- Production has cache warming, concurrent queries, database contention
- Real codebases have different chunk size distributions
- Network latency, disk I/O, and resource contention vary by deployment

**What to Measure After Deployment**:
1. **Latency percentiles** (p50, p90, p95, p99):
   - Overall query latency
   - Breakdown by component (embedding, activation calculation, retrieval)

2. **Cache hit rates**:
   - Hot cache effectiveness
   - Persistent cache effectiveness
   - Activation cache effectiveness

3. **Scaling characteristics**:
   - Latency vs chunk count (5K, 10K, 20K, 50K chunks)
   - Latency vs concurrent users (1, 5, 10, 50 users)

4. **Resource utilization**:
   - CPU usage during queries
   - Memory footprint (verify <100MB target)
   - Disk I/O patterns

**How to Re-Measure**:
```bash
# Run production performance monitoring:
python scripts/monitor_latency.py --duration=24h --output=logs/latency_report.json

# Analyze latency distribution:
python scripts/analyze_latency.py --input=logs/latency_report.json --percentiles=50,90,95,99
```

**Re-Evaluation Triggers**:
- ✓ After 24 hours of production traffic (initial baseline)
- ✓ After 1 week (identify daily patterns)
- ✓ After major optimization changes
- ✓ When chunk count exceeds 10K (validate scaling)

---

## 3. Headless Mode Success Rate (≥80% goal completion)

**Current Status**:
- **MVP Target**: ≥80% goal completion rate
- **Tested**: Unit tests with mocked LLM responses
- **Unknown**: Real autonomous task success in production

**Why Live Data Needed**:
- Success depends on LLM capabilities (GPT-4, Claude, etc.)
- Real tasks have varied complexity and ambiguity
- Autonomous execution has unpredictable edge cases

**What to Measure After Deployment**:
1. **Goal completion rate**:
   - Percentage of headless runs that reach "DONE" status
   - Success vs failure vs timeout vs budget-exceeded

2. **Iteration efficiency**:
   - Average iterations to completion
   - Budget usage per task type

3. **Failure analysis**:
   - Why did it fail? (unclear goal, LLM hallucination, missing context, Git conflicts)
   - Which task types succeed vs fail?

4. **Scratchpad quality**:
   - Are termination decisions correct?
   - Are intermediate observations useful?

**How to Re-Measure**:
```bash
# Collect headless run logs for 50+ runs:
pytest tests/integration/test_headless_real_tasks.py --collect-only

# Analyze success rate:
python scripts/analyze_headless.py --input=logs/headless_runs.jsonl --output=docs/performance/headless-success-report.md
```

**Re-Evaluation Triggers**:
- ✓ After 50 real headless runs (initial validation)
- ✓ After 200 runs (statistically significant)
- ✓ After LLM model upgrades
- ✓ After prompt engineering changes

---

## 4. Error Recovery Rate (≥95% for transient failures)

**Current Status**:
- **MVP Target**: ≥95% recovery rate for transient failures
- **Tested**: Fault injection tests (mocked timeouts, locks)
- **Unknown**: Real failure modes in production

**Why Live Data Needed**:
- Production has different failure modes (network flakiness, API rate limits, database deadlocks)
- Retry strategy effectiveness varies by deployment environment
- Real failures have correlated failure patterns (cascading failures)

**What to Measure After Deployment**:
1. **Recovery success rate**:
   - Percentage of transient failures that recover after retry
   - Recovery time distribution

2. **Failure type distribution**:
   - LLM API timeouts
   - Database lock contention
   - Network errors
   - Rate limit violations

3. **Retry strategy effectiveness**:
   - Average retries before success
   - Backoff timing adequacy
   - Cost of retries (LLM tokens, latency)

**How to Re-Measure**:
```bash
# Analyze error logs for 1 week:
python scripts/analyze_errors.py --input=logs/errors.log --window=7d --output=docs/performance/error-recovery-report.md
```

**Re-Evaluation Triggers**:
- ✓ After 1 week of production traffic
- ✓ After infrastructure changes (new LLM provider, database tuning)
- ✓ Monthly review for first 3 months

---

## 5. Embedding Model Quality (Domain Adaptation)

**Current Status**:
- **Model**: `all-MiniLM-L6-v2` (general-purpose, 384 dimensions)
- **Tested**: Generic code similarity benchmarks
- **Unknown**: Performance on domain-specific codebases (React, Django, embedded systems, etc.)

**Why Live Data Needed**:
- Embedding quality depends on domain-specific vocabulary and patterns
- Different tech stacks have different terminology (e.g., "component" in React vs "component" in Angular)
- Code similarity varies by language paradigm (OOP vs functional vs declarative)

**What to Measure After Deployment**:
1. **Semantic similarity quality**:
   - Do similar code chunks have high cosine similarity?
   - Do unrelated chunks have low similarity?

2. **Domain-specific performance**:
   - How well does it work for frontend vs backend vs infrastructure code?
   - Language-specific performance (Python, TypeScript, Rust, etc.)

3. **Embedding drift**:
   - Does model performance degrade with newer libraries/frameworks?

**How to Re-Measure**:
```bash
# Collect user feedback on semantic search quality:
python scripts/analyze_semantic_quality.py --input=logs/user_feedback.jsonl --output=docs/performance/semantic-quality-report.md

# Compare embeddings for known similar/dissimilar pairs:
pytest tests/integration/test_semantic_quality.py --real-codebase
```

**Re-Evaluation Triggers**:
- ✓ After deployment to 5 different codebase types (diversity check)
- ✓ After 6 months (check for framework evolution)
- ✓ When considering model upgrade (compare against baseline)

---

## 6. Cache Effectiveness (≥30% hit rate after 1000 queries)

**Current Status**:
- **MVP Target**: ≥30% cache hit rate after 1000 queries
- **Tested**: Synthetic query patterns with repeated queries
- **Unknown**: Real user query patterns and repetition rates

**Why Live Data Needed**:
- Cache hit rate depends on query uniqueness distribution
- Real users may repeat queries or have team-wide common queries
- Cache eviction strategy depends on working set size

**What to Measure After Deployment**:
1. **Cache hit rates** (hot cache, persistent cache, activation cache):
   - Overall hit rate
   - Hit rate by cache tier
   - Hit rate over time (first hour vs first day vs first week)

2. **Query repetition patterns**:
   - Percentage of exact duplicate queries
   - Percentage of semantically similar queries
   - Team-wide vs individual query patterns

3. **Cache efficiency**:
   - Memory usage vs hit rate tradeoff
   - Eviction policy effectiveness (LRU, TTL)

**How to Re-Measure**:
```bash
# Monitor cache metrics for 1 week:
python scripts/monitor_cache.py --duration=7d --output=logs/cache_metrics.json

# Analyze cache effectiveness:
python scripts/analyze_cache.py --input=logs/cache_metrics.json --output=docs/performance/cache-effectiveness-report.md
```

**Re-Evaluation Triggers**:
- ✓ After 1,000 queries (initial target)
- ✓ After 10,000 queries (mature cache)
- ✓ After cache configuration changes
- ✓ Monthly review for first 3 months

---

## 7. Memory Footprint (<100MB for 10K chunks)

**Current Status**:
- **MVP Target**: <100MB memory footprint for 10K chunks
- **Tested**: Profiling with synthetic chunk datasets
- **Unknown**: Real-world memory usage with production workloads

**Why Live Data Needed**:
- Real chunks have varied sizes (small config files vs large module files)
- Embeddings stored in memory have actual dimensionality and precision
- Graph cache and activation cache sizes depend on relationship density

**What to Measure After Deployment**:
1. **Memory usage distribution**:
   - Baseline memory (process start)
   - Memory after chunk loading
   - Memory after cache warming
   - Peak memory during high concurrency

2. **Memory breakdown**:
   - Chunk storage
   - Embedding vectors
   - Graph cache
   - Activation cache
   - Other data structures

3. **Memory scaling**:
   - Memory vs chunk count (5K, 10K, 20K, 50K)
   - Memory vs concurrent queries

**How to Re-Measure**:
```bash
# Profile memory usage for 24 hours:
python scripts/profile_memory.py --duration=24h --output=logs/memory_profile.json

# Analyze memory footprint:
python scripts/analyze_memory.py --input=logs/memory_profile.json --output=docs/performance/memory-footprint-report.md
```

**Re-Evaluation Triggers**:
- ✓ After deployment with 10K+ chunk codebase
- ✓ After 24 hours of production traffic
- ✓ After memory optimization changes
- ✓ When memory usage exceeds 80MB (early warning)

---

## How to Add New Items

When you identify something that needs live data validation:

1. **Add a new section** following the template above:
   - Section number and descriptive title
   - Current status (baseline metrics, tested conditions, unknowns)
   - Why live data is needed
   - What to measure after deployment
   - How to re-measure (specific commands/scripts)
   - Re-evaluation triggers (timing and conditions)

2. **Update the status** at the top of the document:
   - 🔴 No live data yet
   - 🟡 Pre-production (awaiting deployment)
   - 🟢 Initial validation complete
   - ✅ Long-term validation complete

3. **Link to relevant documentation**:
   - Original PRD or task file
   - Baseline benchmark reports
   - Implementation files

4. **Create tracking scripts** if they don't exist:
   - Add to `/home/hamr/PycharmProjects/aurora/scripts/`
   - Document in `/home/hamr/PycharmProjects/aurora/docs/scripts/`

---

## Status Summary

| Item | Target | MVP Baseline | Status | Next Validation |
|------|--------|--------------|--------|-----------------|
| Retrieval Precision | ≥85% | 36% | 🟡 Pre-Production | After 100 real queries |
| Query Latency (p95) | <500ms | Synthetic only | 🟡 Pre-Production | After 24h production |
| Headless Success Rate | ≥80% | Unit tests only | 🟡 Pre-Production | After 50 real runs |
| Error Recovery Rate | ≥95% | Fault injection only | 🟡 Pre-Production | After 1 week production |
| Embedding Quality | Domain-adapted | General-purpose | 🟡 Pre-Production | After 5 codebases |
| Cache Hit Rate | ≥30% | Synthetic only | 🟡 Pre-Production | After 1,000 queries |
| Memory Footprint | <100MB | Profiling only | 🟡 Pre-Production | After 10K chunks |

---

## Next Steps

1. **Before deployment**:
   - Review this checklist with the team
   - Ensure monitoring/logging infrastructure is in place
   - Create placeholder scripts in `/home/hamr/PycharmProjects/aurora/scripts/`

2. **After deployment**:
   - Schedule initial validation (100 queries, 24h traffic, etc.)
   - Run re-measurement scripts according to triggers
   - Update this document with live metrics

3. **Continuous improvement**:
   - Review validation results monthly for first 6 months
   - Identify optimization opportunities based on live data
   - Update MVP targets based on real-world feasibility

---

**Document Version**: 1.0
**Created**: December 23, 2025
**Last Updated**: December 23, 2025
**Owned By**: Aurora Development Team
**Review Cycle**: Monthly (first 6 months), Quarterly (after 6 months)
