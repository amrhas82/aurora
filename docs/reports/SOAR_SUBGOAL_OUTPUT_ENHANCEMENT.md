# SOAR Subgoal Output Enhancement

## Summary

Modified the SOAR orchestrator to capture and format subgoal decomposition data in the output, providing users with detailed visibility into how queries are broken down and executed.

## Changes Made

### 1. Enhanced Subgoal Capture in Orchestrator
**File**: `packages/soar/src/aurora_soar/orchestrator.py`

#### Phase 4 Verification Enhancement (lines 314-350)
- Extended `subgoal_details` structure to include:
  - `description`: Full subgoal description
  - `agent`: Assigned agent ID
  - `is_critical`: Critical flag
  - `depends_on`: List of dependency indices
- Added `subgoals_detailed` to `phase4_result` metadata
- Ensures detailed subgoal data is available for output formatting

#### Phase 4 Retry Enhancement (lines 372-394)
- Applied same enhancement to retry path
- Ensures consistent subgoal data capture even after decomposition retries

### 2. Enhanced Response Formatting
**File**: `packages/soar/src/aurora_soar/phases/respond.py`

#### Helper Function (lines 338-359)
Added `_extract_subgoal_breakdown()` function:
- Extracts subgoal breakdown from phase metadata
- Handles both primary and retry verification phases
- Returns empty list if data unavailable (graceful degradation)

#### NORMAL Verbosity Enhancement (lines 174-183)
Added "SUBGOAL BREAKDOWN" section displaying:
- Numbered subgoals (1, 2, 3...)
- Truncated descriptions (70 chars max)
- Critical markers `[CRITICAL]`
- Assigned agent names
- Dependencies in parenthetical format

Example output:
```
--------------------------------------------------------------------------------
SUBGOAL BREAKDOWN:
  1. Analyze current aur soar output format [CRITICAL]
     Agent: code-developer
  2. Locate SOAR orchestrator code [CRITICAL]
     Agent: code-developer
  3. Design output format for breakdown [CRITICAL] (depends on: 1, 2)
     Agent: system-architect
```

#### VERBOSE Verbosity Enhancement (lines 251-263)
Added "SUBGOAL DECOMPOSITION" section with full details:
- Complete descriptions (no truncation)
- Critical markers
- Assigned agent names
- Dependency lists formatted as "Subgoals X, Y, Z"

Example output:
```
================================================================================
SUBGOAL DECOMPOSITION
================================================================================

1. Analyze current aur soar output format and identify where subgoal decomposition information is missing [CRITICAL]
   Assigned Agent: code-developer

2. Design output format for subgoal breakdown that includes goal hierarchy, agent assignments, and dependencies [CRITICAL]
   Assigned Agent: system-architect
   Dependencies: Subgoals 1, 2
```

## Data Flow

```
Phase 3: Decompose
  └─> DecompositionResult with subgoals[]
       ├─> description
       ├─> is_critical
       └─> depends_on[]

Phase 4: Verify
  └─> Build subgoal_details[] from subgoals + agent_assignments
       ├─> index (1-based)
       ├─> description
       ├─> agent (assigned agent ID)
       ├─> is_critical
       └─> depends_on[]
  └─> Store in phase4_result["subgoals_detailed"]

Phase 8: Respond
  └─> Extract from phase_metadata["phases"]["phase4_verify"]["subgoals_detailed"]
  └─> Format according to verbosity level
       ├─> NORMAL: Compact breakdown with truncation
       └─> VERBOSE: Full breakdown with complete details
```

## Benefits

1. **Transparency**: Users see exactly how queries are decomposed into subgoals
2. **Agent Visibility**: Clear view of which agents are assigned to each subgoal
3. **Dependency Tracking**: Understand execution order and dependencies
4. **Critical Indicators**: Identify high-priority subgoals at a glance
5. **Debugging Support**: Easier to diagnose decomposition issues

## Compatibility

- Changes are backward compatible
- Gracefully handles missing subgoal data (returns empty list)
- Works with existing QUIET and JSON verbosity modes (metadata available in raw data)
- No breaking changes to external APIs

## Testing Recommendations

1. Run SOAR with NORMAL verbosity: `aur soar "test query" --verbosity normal`
2. Run SOAR with VERBOSE verbosity: `aur soar "test query" --verbosity verbose`
3. Verify subgoal breakdown section appears in output
4. Test with retry scenarios (decomposition failure → retry → success)
5. Test with queries that generate dependencies
6. Test with critical and non-critical subgoals
