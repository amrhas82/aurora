"""SOAR Pipeline Phases.

This module contains the 9-phase SOAR orchestration pipeline:

Phase 1: Assess - Complexity assessment using keyword and LLM-based classification
Phase 2: Retrieve - Context retrieval from ACT-R memory
Phase 3: Decompose - Query decomposition into subgoals
Phase 4: Verify - Decomposition verification with retry loop
Phase 5: Route - Agent routing and capability matching
Phase 6: Collect - Agent execution with parallel support
Phase 7: Synthesize - Result synthesis and traceability
Phase 8: Record - ACT-R pattern caching
Phase 9: Respond - Response formatting and verbosity control

Each phase is implemented as a separate module for testability and maintainability.
"""

from __future__ import annotations


__all__ = [
    "assess",
    "retrieve",
    "decompose",
    "verify",
    "route",
    "collect",
    "synthesize",
    "record",
    "respond",
]
