# Goals-SOAR Integration Refactor Plan

## Problem
`aur goals` uses SOAR but has brittle adapter layer that transforms SOAR's clean format to Aurora's Pydantic format. This creates:
- Duplicate validation logic
- Fragile normalization (adding '@' prefix, 'sg-' prefix)
- Different UX between `aur soar` and `aur goals`

## Solution
Remove adapter layer, accept SOAR format natively, unify UX.

---

## Current State

### 1. SOAR Output Format (source of truth)
```json
{
  "subgoals_detailed": [
    {
      "agent": "full-stack-dev",           // NO @ prefix
      "ideal_agent": "performance-engineer", // NO @ prefix
      "match_quality": "excellent",
      "description": "..."
    }
  ],
  "decomposition": {
    "subgoals": [
      {
        "id": "1",                          // Numeric ID
        "depends_on": ["1", "2"]            // Numeric dependency IDs
      }
    ]
  }
}
```

### 2. Pydantic Models (packages/cli/src/aurora_cli/planning/models.py)
**Lines 159-179**: Validators REQUIRE '@' prefix:
```python
@field_validator("assigned_agent", "ideal_agent")
def validate_agent_format(cls, v: str) -> str:
    if not v:
        return v
    pattern = r"^@[a-z0-9][a-z0-9-]*$"
    if not re.match(pattern, v):
        raise ValueError(f"Agent must start with '@'. Got: {v}")
    return v
```

**Lines 140-157**: Validators REQUIRE 'sg-' prefix:
```python
@field_validator("id")
def validate_subgoal_id(cls, v: str) -> str:
    pattern = r"^sg-\d+$"
    if not re.match(pattern, v):
        raise ValueError(f"ID must be 'sg-N' format. Got: {v}")
    return v
```

### 3. Adapter Layer (packages/cli/src/aurora_cli/planning/core.py)
**Lines 1281-1299**: Normalization functions:
```python
def normalize_agent_name(agent: str) -> str:
    """Ensure agent name starts with '@'."""
    if not agent:
        return ""
    return agent if agent.startswith("@") else f"@{agent}"

def normalize_dependency_id(dep_id: str) -> str:
    """Ensure dependency ID starts with 'sg-'."""
    if not dep_id:
        return ""
    if dep_id.isdigit():
        return f"sg-{dep_id}"
    if dep_id.startswith("sg-"):
        return dep_id
    return f"sg-{dep_id}"
```

**Lines 1320-1330**: Usage in mapping:
```python
assigned_agent = normalize_agent_name(sg_detail.get("agent", ...))
ideal_agent = normalize_agent_name(sg_detail.get("ideal_agent", ...))
raw_dependencies = sg_data.get("depends_on", [])
dependencies = [normalize_dependency_id(dep) for dep in raw_dependencies]
```

### 4. Display Code (packages/cli/src/aurora_cli/commands/goals.py)
**Lines 281-325**: Custom goals display (table format, per-subgoal rendering)

---

## Changes Required

### Change 1: Relax Pydantic Validators
**File**: `packages/cli/src/aurora_cli/planning/models.py`

**Lines 159-179** - Agent validator:
- REMOVE strict '@' requirement
- ADD '@' prefix automatically if missing (coercion, not validation)

**Lines 140-157** - Subgoal ID validator:
- REMOVE strict 'sg-' requirement
- ADD 'sg-' prefix automatically if numeric (coercion, not validation)

**Lines 135-138** - Dependencies validator:
- ADD coercion for dependency IDs (numeric → 'sg-N')

### Change 2: Remove Adapter Layer
**File**: `packages/cli/src/aurora_cli/planning/core.py`

**Lines 1281-1299**: DELETE normalization functions entirely

**Lines 1320-1330**: UPDATE to use raw SOAR values:
```python
# BEFORE (with normalization)
assigned_agent = normalize_agent_name(sg_detail.get("agent", ...))
dependencies = [normalize_dependency_id(dep) for dep in raw_dependencies]

# AFTER (direct)
assigned_agent = sg_detail.get("agent", agent_info.get("agent_id", "full-stack-dev"))
dependencies = sg_data.get("depends_on", [])
```

### Change 3: Unify Display Until Divergence
**File**: `packages/cli/src/aurora_cli/commands/goals.py`

**Current flow** (lines 222-325):
```
1. create_plan() runs SOAR
2. goals command displays custom table
3. Opens editor
```

**New flow**:
```
1. create_plan() runs SOAR → SOAR displays phases 1-5
2. Divergence point: goals command takes over
3. Display goals-specific table (match quality)
4. Open editor
```

**Changes**:
- Let SOAR phases 1-5 display naturally (no suppression)
- At line 244 (after create_plan success), add goals-specific display
- Keep editor flow (lines 267-279)

### Change 4: Goals-Specific Display Format
**File**: `packages/cli/src/aurora_cli/commands/goals.py`

**NEW table format** (after SOAR phases complete):
```
                    Agent Assignments
┏━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ #  ┃ Subgoal           ┃ Agent            ┃ Match     ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 1  │ Analyze current…  │ @full-stack-dev  │ ✓ Excellent │
│ 2  │ Review budget…    │ @full-stack-dev  │ ✓ Excellent │
└────┴───────────────────┴──────────────────┴───────────┘

Summary: 5 subgoals • 5 excellent, 0 acceptable, 0 spawned
```

---

## Implementation Order

1. ✅ **Document current state** (this file)
2. ✅ **Relax Pydantic validators** (coerce instead of reject)
3. ✅ **Remove normalization functions** from `_decompose_with_soar`
4. ✅ **Update display** in goals command (reuse SOAR, add table at divergence)
5. ✅ **Test end-to-end** - 40 unit tests pass
6. **Commit clean break**

---

## Testing Checklist

- [ ] `aur goals "test goal" -t claude` works without validation errors
- [ ] Agents displayed without '@' in SOAR phases, with '@' in goals table
- [ ] Dependencies work with numeric IDs from SOAR
- [ ] Match quality table shows excellent/acceptable/insufficient
- [ ] Editor opens with goals.json
- [ ] goals.json has correct format for downstream consumers

---

## Files to Modify

1. `packages/cli/src/aurora_cli/planning/models.py` - Relax validators
2. `packages/cli/src/aurora_cli/planning/core.py` - Remove normalization
3. `packages/cli/src/aurora_cli/commands/goals.py` - Unify display

---

## Files to NOT Touch

- `packages/soar/*` - SOAR stays unchanged (source of truth)
- `packages/spawner/*` - No changes needed
