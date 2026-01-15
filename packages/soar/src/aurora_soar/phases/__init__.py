"""SOAR Pipeline Phases.

This module contains the simplified 7-phase SOAR orchestration pipeline:

Phase 1: Assess - Complexity assessment using keyword and LLM-based classification
Phase 2: Retrieve - Context retrieval from ACT-R memory
Phase 3: Decompose - Query decomposition into subgoals
Phase 4: Verify - Decomposition verification + agent assignment (combined with routing)
Phase 5: Collect - Agent execution with parallel support and retry/fallback
Phase 6: Synthesize - Result synthesis and traceability
Phase 7: Record - ACT-R pattern caching (lightweight)
Phase 8: Respond - Response formatting and verbosity control

Key simplifications:
- Phase 4 (Verify) now includes agent assignment using verify_lite
- Route phase removed (functionality integrated into verify)
- Record phase uses lightweight caching for improved performance

Each phase is implemented as a separate module for testability and maintainability.
"""

from __future__ import annotations


__all__ = [
    "assess",
    "retrieve",
    "decompose",
    "verify",
    "collect",
    "synthesize",
    "record",
    "respond",
]
