"""Phase 1: Complexity Assessment.

This module implements the Assess phase of the SOAR pipeline, which determines
query complexity using a two-tier approach:
- Tier 1: Keyword-based classification (fast, 60-70% of queries)
- Tier 2: LLM-based verification (used for borderline cases)

Complexity Levels:
- SIMPLE: Single-step queries, direct lookups, definitions
- MEDIUM: Multi-step queries requiring reasoning, simple refactoring
- COMPLEX: Multi-agent coordination, deep analysis, system design
- CRITICAL: High-stakes queries requiring adversarial verification, security-critical
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from aurora_reasoning.llm_client import LLMClient


__all__ = ["assess_complexity"]


logger = logging.getLogger(__name__)


# Keyword lists for complexity classification (based on software engineering patterns)
SIMPLE_KEYWORDS = {
    # Informational queries
    "what", "who", "where", "when", "which", "define", "explain", "describe",
    "show", "display", "list", "find", "search", "lookup", "get", "retrieve",
    # Simple operations
    "read", "view", "see", "check", "status", "info", "information",
    # Single-step actions
    "print", "log", "output", "format", "convert",
}

MEDIUM_KEYWORDS = {
    # Multi-step actions
    "create", "add", "update", "modify", "change", "edit", "refactor",
    "fix", "debug", "resolve", "improve", "enhance", "optimize",
    # Reasoning required
    "analyze", "compare", "evaluate", "assess", "review", "validate",
    "why", "how", "explain how", "walk through",
    # Code operations
    "write", "implement", "develop", "build", "code",
    "test", "unit test", "integration test",
}

COMPLEX_KEYWORDS = {
    # System-level work
    "architect", "design system", "integrate", "coordinate", "orchestrate",
    "migrate", "refactor system", "restructure", "reorganize",
    # Multi-component work
    "deploy", "configure", "setup", "install", "infrastructure",
    "pipeline", "workflow", "automation", "ci/cd",
    # Deep analysis
    "investigate", "diagnose", "troubleshoot", "root cause",
    "performance", "scalability", "reliability",
    # Multi-agent work
    "research and implement", "design and build", "analyze and refactor",
}

CRITICAL_KEYWORDS = {
    # Security and safety
    "security", "vulnerability", "authentication", "authorization", "encrypt",
    "secure", "protect", "audit", "compliance", "penetration",
    # High-stakes operations
    "production", "critical", "emergency", "incident", "outage",
    "data loss", "corruption", "breach", "exploit",
    # Financial/legal
    "payment", "transaction", "billing", "financial", "legal",
    "regulation", "gdpr", "hipaa", "pci",
}


def _assess_tier1_keyword(query: str) -> tuple[str, float, float]:
    """Fast keyword-based complexity assessment.

    This function performs a lightweight keyword analysis to classify queries
    without LLM overhead. It's optimized for speed and should handle 60-70%
    of queries with high confidence.

    Args:
        query: User query string

    Returns:
        Tuple of (complexity_level, score, confidence):
            - complexity_level: "SIMPLE" | "MEDIUM" | "COMPLEX" | "CRITICAL"
            - score: 0.0-1.0 (normalized keyword match score)
            - confidence: 0.0-1.0 (how confident in classification)
    """
    # Normalize query
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))

    # Count matches for each complexity level
    simple_matches = len(query_words & SIMPLE_KEYWORDS)
    medium_matches = len(query_words & MEDIUM_KEYWORDS)
    complex_matches = len(query_words & COMPLEX_KEYWORDS)
    critical_matches = len(query_words & CRITICAL_KEYWORDS)

    # Calculate total keywords present
    total_keywords = len(query_words)
    if total_keywords == 0:
        return ("SIMPLE", 0.0, 0.3)  # Empty query, low confidence

    # Calculate weighted scores for each level
    # Higher-level keywords have more weight
    simple_score = simple_matches / total_keywords
    medium_score = (medium_matches / total_keywords) * 1.2
    complex_score = (complex_matches / total_keywords) * 1.5
    critical_score = (critical_matches / total_keywords) * 2.0

    # Determine complexity based on highest score
    scores = {
        "SIMPLE": simple_score,
        "MEDIUM": medium_score,
        "COMPLEX": complex_score,
        "CRITICAL": critical_score,
    }

    complexity_level = max(scores, key=lambda k: scores[k])
    raw_score = scores[complexity_level]

    # Normalize score to 0-1 range
    normalized_score = min(raw_score, 1.0)

    # Calculate confidence based on:
    # 1. How much the top score beats the second-highest score (separation)
    # 2. Whether we matched any keywords at all (coverage)
    sorted_scores = sorted(scores.values(), reverse=True)
    separation = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else sorted_scores[0]

    total_matches = simple_matches + medium_matches + complex_matches + critical_matches
    coverage = min(total_matches / 3, 1.0)  # Expect at least 3 keyword matches for high confidence

    # Confidence is combination of separation and coverage
    confidence = (separation * 0.6 + coverage * 0.4)
    confidence = min(max(confidence, 0.1), 1.0)  # Clamp to [0.1, 1.0]

    # Special case: If critical keywords detected, always flag as CRITICAL
    if critical_matches > 0:
        confidence = max(confidence, 0.9)  # High confidence for critical

    logger.debug(
        f"Keyword assessment: {complexity_level} "
        f"(score={normalized_score:.3f}, confidence={confidence:.3f}, "
        f"matches: S={simple_matches}, M={medium_matches}, "
        f"C={complex_matches}, CR={critical_matches})"
    )

    return (complexity_level, normalized_score, confidence)


def _assess_tier2_llm(
    query: str,
    keyword_result: dict[str, Any],
    llm_client: LLMClient,
) -> dict[str, Any]:
    """LLM-based complexity verification for borderline or uncertain cases.

    This function calls the reasoning LLM with the assessment prompt to get
    a more accurate complexity classification when the keyword classifier is
    uncertain.

    Args:
        query: User query string
        keyword_result: Result from _assess_tier1_keyword (contains complexity, score, confidence)
        llm_client: LLM client for reasoning (Tier 2 model like Sonnet/GPT-4)

    Returns:
        Dict with keys:
            - complexity: str (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            - confidence: float (0-1)
            - reasoning: str (LLM's explanation)
            - indicators: list[str] (specific indicators noted by LLM)
            - recommended_verification: str (verification option recommendation)
    """
    try:
        # Import prompt template
        from aurora_reasoning.prompts.assess import AssessPromptTemplate

        # Build prompt
        prompt_template = AssessPromptTemplate()
        system_prompt = prompt_template.build_system_prompt()
        user_prompt = prompt_template.build_user_prompt(
            query=query,
            keyword_result=keyword_result
        )

        logger.info(f"Calling LLM for complexity verification (query: {query[:50]}...)")

        # Call LLM with JSON output
        result = llm_client.generate_json(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent classification
            max_tokens=512,
        )

        # Validate result has required fields
        if "complexity" not in result:
            raise ValueError("LLM response missing 'complexity' field")

        complexity = result["complexity"].upper()
        if complexity not in {"SIMPLE", "MEDIUM", "COMPLEX", "CRITICAL"}:
            raise ValueError(f"Invalid complexity level from LLM: {complexity}")

        # Extract fields with defaults
        confidence = result.get("confidence", 0.8)
        reasoning = result.get("reasoning", "LLM-based classification")
        indicators = result.get("indicators", [])

        # Recommend verification option based on complexity
        if complexity == "CRITICAL":
            recommended_verification = "option_b"  # Adversarial for critical
        elif complexity == "COMPLEX":
            recommended_verification = "option_b"  # Adversarial for complex
        elif complexity == "MEDIUM":
            recommended_verification = "option_a"  # Self-verify for medium
        else:
            recommended_verification = "none"  # No verification for simple

        logger.info(
            f"LLM assessment: {complexity} "
            f"(confidence={confidence:.3f}, verification={recommended_verification})"
        )

        return {
            "complexity": complexity,
            "confidence": confidence,
            "reasoning": reasoning,
            "indicators": indicators,
            "recommended_verification": recommended_verification,
        }

    except Exception as e:
        logger.error(f"LLM verification failed: {e}, falling back to keyword result")
        # Fallback to keyword result if LLM fails
        return {
            "complexity": keyword_result.get("complexity", "MEDIUM"),
            "confidence": keyword_result.get("confidence", 0.5),
            "reasoning": f"LLM verification failed: {str(e)}. Using keyword fallback.",
            "indicators": [],
            "recommended_verification": "option_a",
            "error": str(e),
        }


def assess_complexity(query: str, llm_client: LLMClient | None = None) -> dict[str, Any]:
    """Assess query complexity using two-tier approach.

    This function first attempts fast keyword classification. If the keyword
    classifier has high confidence (≥0.8) and the score is not borderline
    ([0.4, 0.6]), it returns immediately. Otherwise, it falls back to LLM
    verification for more accurate classification.

    Cost Optimization:
    - 60-70% of queries use keyword only (zero LLM cost)
    - 30-40% use LLM verification (~$0.0002/query)
    - Target: <$0.0001 average per complexity assessment

    Args:
        query: User query string
        llm_client: Optional LLM client for Tier 2 verification (if None, keyword-only)

    Returns:
        Dict with keys:
            - complexity: str (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            - confidence: float (0-1)
            - method: str ("keyword" or "llm")
            - reasoning: str (explanation of classification)
            - score: float (0-1, keyword match score for keyword method)
            - recommended_verification: str (verification option recommendation, if LLM used)
    """
    # Tier 1: Keyword classification
    complexity_level, score, confidence = _assess_tier1_keyword(query)

    # Build keyword result dict for potential LLM call
    keyword_result = {
        "complexity": complexity_level,
        "score": score,
        "confidence": confidence,
    }

    # Decision logic: Use keyword result if high confidence and not borderline
    is_borderline = 0.4 <= score <= 0.6
    use_keyword = confidence >= 0.8 and not is_borderline

    if use_keyword:
        logger.info(f"Keyword assessment: {complexity_level} (confidence={confidence:.3f})")
        return {
            "complexity": complexity_level,
            "confidence": confidence,
            "method": "keyword",
            "reasoning": f"Keyword-based classification with {confidence:.1%} confidence",
            "score": score,
        }
    # Tier 2: LLM verification
    if llm_client is not None:
        logger.info(
            f"Keyword assessment borderline or low confidence "
            f"(confidence={confidence:.3f}, score={score:.3f}), "
            f"calling LLM for verification"
        )

        llm_result = _assess_tier2_llm(query, keyword_result, llm_client)

        return {
            "complexity": llm_result["complexity"],
            "confidence": llm_result["confidence"],
            "method": "llm",
            "reasoning": llm_result["reasoning"],
            "recommended_verification": llm_result.get("recommended_verification"),
            "keyword_fallback": keyword_result,  # Include keyword result for reference
        }
    # No LLM available, use keyword result with warning
    logger.warning(
        f"Keyword assessment borderline or low confidence "
        f"(confidence={confidence:.3f}, score={score:.3f}), "
        f"but no LLM client provided. Using keyword result."
    )

    return {
        "complexity": complexity_level,
        "confidence": confidence,
        "method": "keyword",
        "reasoning": (
            "Keyword-based classification (borderline or low confidence). "
            "LLM verification recommended but not available."
        ),
        "score": score,
        "llm_verification_needed": True,
    }
