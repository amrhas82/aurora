# Store Hardening: Health Probes & Tiered Access-History Compaction

**Version**: 0.1
**Date**: 2026-04-13
**Status**: Change 1 implemented on `feat/store-integrity-checks` branch (pending verification & merge); Change 2 not yet started
**Scope**: `packages/core` (SQLite store, ACT-R activation) and `packages/cli` (memory_manager)
**Non-goals**: SOAR pipeline changes, retrieval-quality changes, schema migration beyond additive columns

---

## Executive Summary

Two independent, low-risk changes that harden the ACT-R memory layer against silent failures identified during a store-integrity audit. Both operate below SOAR and do not alter retrieval semantics.

1. **Store Integrity Checks** — a new `StoreIntegrityChecks` class plugged into the existing `aur doctor` flow. Detects FTS5 desync, orphan chunks, dangling ReasoningChunks, and activation orphans in <200ms. No new CLI surface — reuses the existing doctor harness and its `--fix` flag for mechanical repairs.
2. **Tiered Access-History Compaction** — bounds the unbounded JSON `access_history` column by collapsing old access records into time-bucketed records for *storage only*. The BLA decay formula is unchanged; we simply stop storing individual timestamps for old accesses that the decay already treats as negligible. Preserves BLA ranking accuracy to <0.001 error while keeping the per-chunk array at ≤200 entries regardless of chunk age.

Neither change touches SOAR, retrieval ranking, or embeddings. Both are additive — no breaking schema changes, no re-index required.

---

## Motivation

A store-integrity audit surfaced three silent-failure paths and one unbounded-growth path:

| Risk | Location | Current state | Failure mode |
|---|---|---|---|
| FTS5 desync | `store/sqlite.py` | DELETE+INSERT, no post-op check | Retrieval returns stale results |
| Orphan code chunks | `memory_manager.py:1596-1645` | Transaction cleanup, no verification | `file_path` not in `file_index`, queries return ghosts |
| Dangling ReasoningChunks | `chunks/reasoning_chunk.py` | **No invalidation logic at all** | SOAR retrieves reasoning patterns for deleted code |
| Unbounded `access_history` | `store/schema.py:34-43` | Append-only JSON array, no retention | **CRITICAL** — hot chunks accumulate 10K+ records, BLA recalculation becomes the bottleneck |

None of these produce exceptions. They degrade silently. The health-probe change makes them detectable; the compaction change eliminates the growth path.

---

## Change 1: Store Integrity Checks (in `aur doctor`)

### Goals

- Detect the four silent-failure classes above via the existing `aur doctor` harness
- Run cheaply enough to be part of every `aur doctor` invocation without meaningful slowdown
- Report actionable output — which chunk, which table, what's wrong
- **No new CLI**. Reuse the existing doctor infrastructure, its output formatting, and its `--fix` flag.

### Non-goals

- Cross-chunk semantic consistency (out of scope — ACT-R is append-only by design)
- Performance profiling (separate concern)
- A standalone `aur mem probe` command (explicitly rejected — `aur doctor` is the home)

### Where this lives

`aur doctor` (`packages/cli/src/aurora_cli/commands/doctor.py`) already composes six health-check classes imported from `aurora_cli.health_checks`:

- `InstallationChecks`
- `CoreSystemChecks`
- `CodeAnalysisChecks`
- `SearchRetrievalChecks`
- `ConfigurationChecks`
- `ToolIntegrationChecks`

This change adds a seventh: **`StoreIntegrityChecks`**. It follows the exact same interface as the other check classes (same constructor signature, same check-runner protocol) so doctor's output formatting, exit-code logic, and `--fix` plumbing apply automatically.

### API

```python
# packages/cli/src/aurora_cli/health_checks/store_integrity.py  (new file)

class StoreIntegrityChecks:
    """Integrity checks for the ACT-R store. Plugs into `aur doctor`."""

    def __init__(self, config: Config) -> None: ...

    def check_retrieval_roundtrip(self) -> CheckResult: ...
    def check_fts_consistency(self) -> CheckResult: ...
    def check_orphan_chunks(self) -> CheckResult: ...
    def check_dangling_reasoning(self) -> CheckResult: ...
    def check_activation_orphans(self) -> CheckResult: ...

    def run_all(self) -> list[CheckResult]: ...
    def run_fixes(self, results: list[CheckResult]) -> list[FixResult]: ...
```

`CheckResult` and `FixResult` are whatever the existing `health_checks` module already uses — this class conforms rather than inventing new types.

### Checks

Each check is a single SQL query; none require loading chunks into memory.

**1. Retrieval roundtrip** — pick the chunk with the highest `access_count` (guaranteed to exist, guaranteed to be real content), extract one keyword from its `keywords` array, run a hybrid retrieval with `limit=10`, assert the seed chunk appears in results.

Catches: FTS5 desync, HybridRetriever regressions, BM25 index corruption.

**2. FTS5 consistency**

```sql
SELECT
  (SELECT COUNT(*) FROM chunks WHERE type IN ('code', 'kb')) AS chunks_count,
  (SELECT COUNT(*) FROM chunks_fts) AS fts_count;
```

Counts must match. Mismatch means INSERT or DELETE on `chunks_fts` silently failed during a prior indexing run.

**3. Orphan chunks**

```sql
SELECT COUNT(*) FROM chunks
WHERE type = 'code'
  AND json_extract(content, '$.file') NOT IN (SELECT file_path FROM file_index);
```

Catches: partial `_cleanup_deleted_files()` failures where chunks survived but `file_index` was updated (or vice versa).

**4. Reasoning chunk growth (informational)**

Originally scoped as "dangling ReasoningChunks" — detect reasoning chunks that reference code chunks no longer in the store. **Detection deferred** in v0.1: ReasoningChunks store `subgoals` and `execution_order` as freeform dicts with no formal chunk_id reference schema (`packages/core/src/aurora_core/chunks/reasoning_chunk.py`), so any heuristic detector would be brittle. A real detector belongs in a follow-up change once SOAR defines the reference shape.

What v0.1 *does* check: reasoning-chunk **count**, with an informational warning above 10,000. SOAR's Record phase caches every successful query (confidence ≥ 0.5) with no retention, so an unbounded count is the symptom that surfaces first. The warning prompts the operator to check whether the Record phase is doing what they expect.

**5. Activation orphans**

```sql
SELECT COUNT(*) FROM activations
WHERE chunk_id NOT IN (SELECT id FROM chunks);
```

The FK has `ON DELETE CASCADE`, so this should always be zero. If it isn't, the FK constraint was bypassed (possible via `DELETE` with FKs disabled during a migration). Having the probe is cheap insurance.

### CLI

No new commands. Everything happens through existing doctor invocations:

```
aur doctor          # includes store integrity checks alongside the other six categories
aur doctor --fix    # auto-repairs the mechanical integrity failures (see Auto-repair scope below)
```

### Auto-repair scope (under existing `--fix` flag)

`aur doctor --fix` should mechanically repair the safe cases and leave the policy-laden ones alone:

| Failure | Auto-repairable? | Action |
|---|---|---|
| FTS5 desync | Yes | Rebuild `chunks_fts` from `chunks` |
| Activation orphans | Yes | DELETE orphans (FK CASCADE should prevent, but defensively) |
| Orphan code chunks | Yes | DELETE chunks whose `file_path` is no longer in `file_index` |
| Dangling ReasoningChunks | **No** | Report only — repair depends on SOAR staleness policy (future change) |
| Retrieval roundtrip failure | **No** | Report only — likely indicates a deeper issue needing investigation |

### Implementation sketch

- New file: `packages/cli/src/aurora_cli/health_checks/store_integrity.py` — the `StoreIntegrityChecks` class
- Modify: `packages/cli/src/aurora_cli/health_checks/__init__.py` — export `StoreIntegrityChecks`
- Modify: `packages/cli/src/aurora_cli/commands/doctor.py` — import `StoreIntegrityChecks`, add to the check list alongside the existing six categories
- No changes to `packages/core` — integrity checks query the existing store directly via the same interface the rest of the code uses

### Test plan

- Unit: synthetic corrupted store (insert orphan chunk, delete from FTS5 directly, insert reasoning chunk with a fake chunk_id reference), assert each check flags exactly what was corrupted
- Integration: full index → probe → assert `ok == True`; then delete a file, reindex, probe again, assert still `ok`
- Regression: probe a store of 50K chunks, assert `duration_ms < 200`

### Success criteria

- `aur doctor` with store integrity checks runs in <200ms of added overhead on a 50K-chunk store
- All four silent-failure classes produce a flagged report under the existing doctor output format
- Zero false positives on a freshly indexed Aurora self-index
- `aur doctor --fix` cleanly repairs the three mechanical failure cases without touching ReasoningChunks

---

## Change 2: Tiered Access-History Compaction

### What this is (and isn't)

**It isn't a change to ACT-R decay.** Aurora's BLA formula (`ln(Σ t_j^(-0.5))`) already weights accesses by age — an access from 1 hour ago contributes ~93× more than one from a year ago. The time-weighted decay works correctly today.

**It is a change to how raw access records are stored.** Today, every individual access timestamp is kept forever as an entry in a JSON column. A hot chunk accumulates thousands of records that the decay formula has already rendered nearly worthless. The compaction collapses those old records into time buckets for storage, while the BLA formula keeps reading them through the same `t^(-0.5)` math — a bucket of N accesses at a midpoint time `t` contributes `N · t^(-0.5)` to the sum, exactly as if you'd summed each access individually.

The change is safe *because* the decay already made old records nearly worthless. Bucketing them costs almost nothing in BLA accuracy but removes an unbounded storage growth path.

### Goals

- Bound `activations.access_history` JSON arrays to ≤200 entries regardless of chunk age
- Preserve BLA ranking accuracy — error must be below any threshold that affects retrieval order
- Operate transparently at the storage layer; ACT-R callers unchanged

### Non-goals

- **Change the BLA formula** — explicitly not touching decay math
- **Change decay rates** — `d=0.5` stays
- Eviction of whole chunks (only access records are compacted)
- Retention-policy configuration (v0.1 ships with fixed tiers; tunable in v0.2)

### The problem

Current schema (`store/schema.py:34-43`):

```sql
CREATE TABLE activations (
    chunk_id TEXT PRIMARY KEY,
    base_level REAL NOT NULL,
    last_access TIMESTAMP NOT NULL,
    access_count INTEGER DEFAULT 1,
    access_history JSON,   -- single-column JSON array, append-only
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
```

Each call to `record_access()` appends `{timestamp, context}`. No trimming.

Worst case: a chunk accessed 100×/day for 365 days = 36,500 JSON objects in a single TEXT column. `get_access_history()` loads the entire array, sorts DESC in Python, then slices. BLA recalculation walks the whole array. Both degrade as the array grows.

### Why naive truncation is wrong

Keeping only the most recent N accesses biases BLA toward chunks that happened to get a recent burst, and underweights chunks with long, moderate histories. ACT-R is specifically a *history-sensitive* model; you cannot drop the tail without replacing it with something.

### Why tiered compaction is safe — the math

ACT-R BLA (Anderson & Schooler 1991, as used in `activation/bla.py`):

$$
\text{BLA} = \ln\left(\sum_{j=1}^{n} t_j^{-d}\right)
$$

where `t_j` is seconds since the j-th access, `d` is the decay rate (Aurora uses `d=0.5`).

A single access contributes `t_j^{-0.5}` to the sum. Contribution by age:

| Access age | Single-access contribution | 100-access equivalent |
|---|---|---|
| 1 hour | 0.01667 | 1.667 |
| 1 day | 0.00340 | 0.340 |
| 1 week | 0.00129 | 0.129 |
| 1 month | 0.00062 | 0.062 |
| 6 months | 0.00025 | 0.025 |
| 1 year | 0.00018 | 0.018 |

**Key observation**: 100 accesses from a year ago contribute less to the sum than a single access from an hour ago. The decay function has already erased the information content of old records — compacting them into buckets loses almost nothing.

### The tiered scheme

| Tier | Age range | Representation | Per-record fidelity |
|---|---|---|---|
| 1 | 0–7 days | `{timestamp, context}` individual records | Full — exact timestamp, full context string |
| 2 | 7–30 days | `{hour_bucket, count}` | Collapsed — hourly granularity, no context |
| 3 | 30–180 days | `{day_bucket, count}` | Collapsed — daily granularity |
| 4 | 180+ days | `{period_start, period_end, count}` — single record per chunk | Aggregate only |

**BLA recalculation over buckets**: treat each bucket as `count` accesses placed at the bucket's midpoint time. The contribution becomes `count × (t_midpoint)^(-0.5)`.

**Bound on error**: The maximum BLA error introduced by replacing individual timestamps with a bucket midpoint is bounded by the difference between the bucket's edges. For a daily bucket 30 days old, the worst-case error in a single access contribution is:

$$
(30 \text{ days})^{-0.5} - (31 \text{ days})^{-0.5} \approx 0.00062 - 0.00060 = 2 \times 10^{-5}
$$

per access. Summed across the whole tier, the error stays below `0.001` in BLA units — an order of magnitude below any retrieval ranking threshold (Aurora's hybrid ranker uses BLA at ~30% weight with scores in the 0–10 range).

### When compaction runs

Lazy, on write:

```
record_access(chunk_id, ts, context):
    append new record to tier 1
    if len(access_history) > 200:
        compact(chunk_id)
```

`compact()` walks the array once, bucketing entries by age into their appropriate tier. The triggered-on-write approach means active chunks compact themselves and cold chunks never pay the cost.

A second entry point — `aur mem compact` — force-compacts all activations for administrative use (e.g., after importing historical data).

### Implementation sketch

- Modify: `packages/core/src/aurora_core/activation/bla.py`
  - `calculate_bla()` reads records as tagged unions: `{kind: "record", timestamp, context}` or `{kind: "bucket", midpoint, count}`
  - Sum becomes `Σ (record contribution) + Σ (count × bucket contribution)`
- Modify: `packages/core/src/aurora_core/store/sqlite.py`
  - `record_access()` triggers `_maybe_compact()` when array length crosses 200
  - New method `_maybe_compact(chunk_id)` — walks JSON array, re-buckets, writes back in one UPDATE
  - `get_access_history()` returns a tagged-union list; callers that need flat records expand buckets on demand
- Modify: `packages/core/src/aurora_core/store/schema.py`
  - No schema change — the JSON column already accommodates heterogeneous records
  - Add a comment documenting the tagged-union shape
- New: `packages/cli/src/aurora_cli/commands/mem_compact.py` — admin command

### Migration path

Existing `access_history` entries are all tier 1 (`{timestamp, context}` records). They remain valid under the new reader because the reader treats any record without a `kind` field as a tier-1 record. No migration script needed. Compaction happens lazily as chunks are next written to.

### Test plan

- Unit: build a synthetic history of 1000 accesses spanning 2 years, run compaction, assert:
  - Array length ≤ 200
  - BLA of compacted vs. uncompacted history differs by < 0.001
  - All tier boundaries correct
- Property-based: random access patterns, BLA error bound holds across 1000 trials
- Regression: import Aurora's own self-index history, run compaction, verify BLA-based ranking of top-100 queries is identical (within tolerance) before and after
- Performance: `record_access()` p99 latency must not regress more than 5% under a workload that triggers compaction

### Success criteria

- After `aur mem compact`, no `access_history` array exceeds 200 entries
- BLA ranking order for top-100 retrievals is preserved (Spearman ρ > 0.999 pre/post compaction on Aurora's own corpus)
- `record_access()` latency unchanged on the common path (length < 200), adds ≤5ms on the compaction trigger

---

## Shared concerns

### Risks

- **Probe false positives** on in-flight reindex. Mitigation: probe acquires a shared read lock; concurrent reindex is serialized.
- **Compaction during retrieval**. Mitigation: compaction happens inside the same transaction as the append, so `get_access_history()` either sees the pre- or post-compaction state, never a half-compacted one.
- **BLA formula drift**. If anyone changes the decay rate or formula, the error bound in the compaction design no longer holds. Mitigation: add an assertion in `bla.py` that the decay rate matches the value the compaction tiers were designed for; any change must explicitly update both.

### What this does not fix

- ReasoningChunk invalidation itself — the probe *detects* dangling ReasoningChunks but does not delete or repair them. Repair belongs in a follow-up change once we know how SOAR wants to handle pattern staleness.
- Concurrent indexing corruption — `aur mem index .` has no global lock. Out of scope here; separate concern.
- Token-level budgeting in SOAR RETRIEVE — deferred per user decision to pause SOAR investment.

### Rollout

1. Land `StoreIntegrityChecks` in `aur doctor` (Change 1) — zero risk, purely additive
2. Run `aur doctor --fix` against production stores, clean up any pre-existing corruption
3. Land compaction (Change 2) behind a feature flag (`AURORA_COMPACT_ACCESS_HISTORY=1`)
4. Enable compaction by default after one week of internal use
5. `aur doctor` then treats overlong access-history arrays as a check of its own (a signal that compaction isn't running, not a data-integrity failure)

---

## Open questions

- Should tier boundaries be configurable per-deployment? v0.1 hardcodes them; v0.2 can make them env-var tunable if a use case emerges.
- ~~Should the probe have a `--repair` mode?~~ Resolved — `aur doctor --fix` is the existing harness; `StoreIntegrityChecks` hooks into it, repairing the three mechanical cases (FTS5 rebuild, activation orphans, orphan code chunks) and leaving ReasoningChunk repair for a future SOAR-aware change.
- Should `get_access_history()` always return expanded records (for backward compatibility) or always return tagged unions (for correctness)? Propose: add a `raw: bool = False` kwarg, default to expanded for compatibility, tagged-union when explicitly requested.
