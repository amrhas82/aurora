# AURORA-Context Documentation Index

**Last Updated**: December 12, 2025

---

## SINGLE SOURCE OF TRUTH

**Official Specification (v2.0)**:
📄 `/home/hamr/Documents/PycharmProjects/OneNote/smol/agi-problem/tasks/0001-prd-aurora-context.md`

This is the **COMPLETE TECHNICAL SPECIFICATION** - everything needed for implementation:
- ✓ Executive summary and problem analysis
- ✓ Complete architecture (SOAR orchestrator, ACT-R memory, verification system)
- ✓ All 6 LLM prompt specifications (JSON format)
- ✓ Implementation details (repository structure, logging, metrics)
- ✓ Success metrics and phase roadmap
- ✓ Consolidated from AURORA-MVP-Correction.md
- ✓ All clarifications (SQLite+JSON, pyactr usage scope)

**Status**: Ready for implementation ✅

---

## TEST SAMPLES

**JSON Prompt Test Suite**:
📄 `/home/hamr/Documents/PycharmProjects/OneNote/smol/agi-problem/aurora/JSON-PROMPT-TESTS.md`

Contains **6 end-to-end test prompts** using practical scenario (agentic AI market research):
1. ✓ Complexity Assessment Test
2. ✓ Decomposition Test
3. ✓ Decomposition Verification Test
4. ✓ Agent Output Verification Test
5. ✓ Synthesis Verification Test
6. ✓ Retry Feedback Test

Each test includes:
- Complete JSON prompt structure
- Expected output sample
- Validation checklist
- Common issues to watch for

**Purpose**: Validate LLM JSON format compatibility before implementation

---

## SUPPORTING DOCUMENTS (Reference Only)

These documents provided context but are now fully integrated into the official spec:

**AURORA-MVP-Correction.md** (143K, 2700 lines)
- Original correction document with Parts 1-26
- All content now merged into official spec
- Keep for historical reference

**AURORA-Framework-PRD.md** (62K)
- Original PRD (pre-verification layer)
- Superseded by v2.0 spec

**AURORA-Framework-SPECS.md** (50K)
- Technical specs including assessment prompt
- Content now in v2.0 spec

---

## WHAT TO USE FOR IMPLEMENTATION

**Start Here**:
1. Read `/tasks/0001-prd-aurora-context.md` (official spec v2.0)
2. Use `/aurora/JSON-PROMPT-TESTS.md` to test LLM compatibility

**Do NOT use**:
- Old PRD files (v1.0 or earlier)
- Correction document directly (already merged)
- Any files in `/Documents/smol/agi-problem/aurora/` (duplicates, removed)

---

## QUICK REFERENCE

### Architecture Decisions

**Storage**: SQLite + JSON
- SQLite database with JSON stored IN columns (not separate files)
- Path: `~/.aurora/memory.db`
- Tables: chunks, activations, relationships

**pyactr Library Usage**:
- ✓ USE: Activation formulas (base_level_learning, decay functions)
- ✗ BUILD: SQLite integration, retrieval logic, spreading activation

**Memory Identifiers**:
- `code:*` - Code chunks (functions/classes)
- `reas:*` - Reasoning patterns (decompositions)
- `know:*` - Knowledge chunks (Phase 2)

**Complexity Routing**:
- SIMPLE → Direct LLM (no decomposition)
- MEDIUM → Option A (self-verify)
- COMPLEX → Option B (adversarial)
- CRITICAL → Option C (deep reasoning, Phase 2)
- Escalation: 2x fail → escalate to next level

**Scoring Thresholds**:
- >= 0.8: CACHE (learn from success)
- >= 0.7: PASS (proceed)
- 0.5-0.7: RETRY (max 2 retries)
- < 0.5: FAIL (reject)

### Repository Structure

```
aurora-context/
├── packages/
│   ├── core/              # ACT-R activation engine, chunks, store
│   ├── soar/              # SOAR orchestrator (9 phases)
│   ├── reasoning/         # Decomposition, verification, synthesis
│   ├── context-code/      # cAST parser, git integration
│   ├── context-reasoning/ # Pattern retrieval
│   ├── mcp-server/        # MCP integration
│   └── cli/               # Command-line interface
```

### Installation Options

```bash
# Full install
pip install aurora-context[all]

# MCP server only
pip install aurora-context[mcp]

# Core library only
pip install aurora-context-core
```

---

## VERSION HISTORY

**v2.0 (2025-12-12)**:
- Complete consolidation (single source of truth)
- All 6 LLM prompts added
- SQLite+JSON and pyactr clarified
- SOAR orchestrator, agent registry, logging/metrics
- Ready for implementation

**v1.0 (2025-12-12)**:
- Initial PRD (incomplete)

---

## QUESTIONS?

- **Architecture questions**: See Section 3-7 in official spec
- **Implementation questions**: See Section 9 in official spec
- **Prompt formats**: See Section 8 in official spec
- **Testing**: See JSON-PROMPT-TESTS.md

---

**Ready to build! 🚀**
