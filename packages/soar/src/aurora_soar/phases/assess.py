"""Phase 1: Complexity Assessment.

This module implements the Assess phase of the SOAR pipeline, which determines
query complexity using a two-tier approach:
- Tier 1: Keyword-based classification (96% accuracy on 101-prompt corpus)
- Tier 2: LLM-based verification (used for borderline cases)

Complexity Levels:
- SIMPLE: Single-step queries, direct lookups, definitions
- MEDIUM: Multi-step queries requiring reasoning, simple refactoring
- COMPLEX: Multi-agent coordination, deep analysis, system design
- CRITICAL: High-stakes queries requiring adversarial verification, security-critical
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from aurora_reasoning.llm_client import LLMClient


__all__ = ["assess_complexity", "ComplexityAssessor", "AssessmentResult", "ComplexityLevel"]


logger = logging.getLogger(__name__)


# ========== NEW IMPLEMENTATION: ComplexityLevel and AssessmentResult ==========


class ComplexityLevel(IntEnum):
    """Complexity levels with score thresholds."""

    SIMPLE = 1  # Score <= 11
    MEDIUM = 2  # Score 12-28
    COMPLEX = 3  # Score >= 29
    CRITICAL = 4  # High-stakes, overrides score-based classification


@dataclass
class AssessmentResult:
    """Result of complexity assessment."""

    level: Literal["simple", "medium", "complex", "critical"]
    score: int
    confidence: float  # 0.0-1.0
    signals: list[str] = field(default_factory=list)
    breakdown: dict[str, int | float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "confidence": round(self.confidence, 2),
            "signals": self.signals,
            "breakdown": self.breakdown,
        }

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ========== NEW IMPLEMENTATION: ComplexityAssessor Class ==========


class ComplexityAssessor:
    """Assesses prompt complexity using multi-dimensional lexical analysis.

    Dimensions analyzed:
    1. Lexical metrics (word count, sentence count, punctuation)
    2. Keyword categories (simple/medium/analysis/complex action verbs)
    3. Scope indicators (breadth of request)
    4. Constraint markers (conditions and requirements)
    5. Structural patterns (lists, sequences, conditionals)
    6. Domain complexity (technical jargon, cross-cutting concerns)

    Scoring Philosophy:
    - Simple prompts: Score 0-11 (lookup, display, trivial edits)
    - Medium prompts: Score 12-28 (analysis, moderate edits, bounded multi-step)
    - Complex prompts: Score 29+ (implementation, architecture, multi-system)
    """

    # ========== KEYWORD DICTIONARIES ==========

    # Simple action verbs - indicate lookup/display operations (penalize score)
    SIMPLE_VERBS = {
        "what",
        "show",
        "list",
        "get",
        "find",
        "print",
        "check",
        "read",
        "open",
        "run",
        "where",
        "which",
        "display",
        "view",
        "see",
        "tell",
        "give",
        "name",
        "count",
        "who",
        "when",
        "is",
    }

    # Medium action verbs - require moderate work (add score)
    MEDIUM_VERBS = {
        "add",
        "update",
        "fix",
        "write",
        "change",
        "modify",
        "remove",
        "delete",
        "improve",
        "enhance",
        "extend",
        "convert",
        "rename",
        "move",
        "test",
        "configure",
        "setup",
        "set",
        "enable",
        "disable",
    }

    # Analysis keywords - require understanding/reasoning (add score)
    ANALYSIS_VERBS = {
        "explain",
        "compare",
        "analyze",
        "debug",
        "understand",
        "investigate",
        "describe",
        "clarify",
        "elaborate",
        "why",
        "difference",
        "mean",
        "interpret",
        "evaluate",
        "assess",
        "review",
        "examine",
        "diagnose",
        "trace",
        "audit",
    }

    # Complex action keywords - require significant work (large score boost)
    COMPLEX_VERBS = {
        "implement",
        "design",
        "architect",
        "refactor",
        "integrate",
        "migrate",
        "build",
        "create",
        "develop",
        "construct",
        "engineer",
        "establish",
        "transform",
        "overhaul",
        "rewrite",
        "restructure",
        "optimize",
    }

    # Scope expansion keywords - broaden the request (significant boost)
    SCOPE_KEYWORDS = {
        "all",
        "every",
        "entire",
        "across",
        "comprehensive",
        "complete",
        "codebase",
        "project",
        "system",
        "application",
        "full",
        "whole",
        "everything",
        "throughout",
        "universal",
        "global",
    }

    # Constraint phrases - add conditions/requirements
    CONSTRAINT_PHRASES = [
        "without breaking",
        "without changing",
        "maintaining",
        "ensuring",
        "while also",
        "while keeping",
        "make sure",
        "must not",
        "should not",
        "backwards compatible",
        "backward compatible",
        "don't break",
        "keep existing",
        "preserve",
        "without affecting",
        "without modifying",
        "must work with",
        "keeping it",
        "while still",
    ]

    # Multi-step indicators - sequential operations
    SEQUENCE_MARKERS = [
        "first",
        "then",
        "after that",
        "finally",
        "next",
        "afterwards",
        "subsequently",
        "step by step",
        "following that",
        "once done",
        "before",
        "prior to",
        "and then",
    ]

    # Compound requirement markers
    COMPOUND_MARKERS = [
        "and also",
        "as well as",
        "additionally",
        "furthermore",
        "moreover",
        "in addition",
        "along with",
        "together with",
        "plus",
        "not only",
    ]

    # Technical domain keywords (cross-cutting concerns)
    TECHNICAL_DOMAINS = {
        "security",
        "performance",
        "scalability",
        "reliability",
        "testing",
        "authentication",
        "authorization",
        "caching",
        "logging",
        "monitoring",
        "database",
        "api",
        "frontend",
        "backend",
        "infrastructure",
        "deployment",
        "ci/cd",
        "docker",
        "kubernetes",
        "microservices",
        "distributed",
    }

    # Feature/system nouns that increase complexity when combined with action verbs
    COMPLEX_NOUNS = {
        "authentication",
        "authorization",
        "oauth",
        "jwt",
        "session",
        "sessions",
        "pipeline",
        "workflow",
        "notification",
        "notifications",
        "dashboard",
        "crud",
        "plugin",
        "framework",
        "websocket",
        "websockets",
        "realtime",
        "real-time",
        "rate-limit",
        "rate-limiting",
        "pagination",
        "search",
        "validation",
        "migration",
        "schema",
    }

    # Vague/unspecific words - indicate user doesn't know precise target (reduce score)
    VAGUE_WORDS = {
        "something",
        "somehow",
        "maybe",
        "general",
        "generally",
        "overall",
        "around",
        "stuff",
        "things",
        "better",
        "faster",
        "slower",
        "worse",
        "some",
        "any",
        "whatever",
        "somewhere",
    }

    # Question type patterns
    SIMPLE_QUESTION_PATTERNS = [
        r"^what is\b",
        r"^where is\b",
        r"^which\b",
        r"^who\b",
        r"^is there\b",
        r"^does it\b",
        r"^can i\b",
    ]

    COMPLEX_QUESTION_PATTERNS = [
        r"\bhow (?:can|should|would) (?:we|i|you)\b.*(?:implement|design|build)",
        r"\bwhat (?:is|are|\'s) the best (?:way|approach|practice|architecture)",
        r"\bhow to (?:properly|correctly|efficiently)\b",
        r"\bbest\s+architecture\b",
        r"\bdesign.*pattern\b",
        r"\barchitecture\s+for\b",
    ]

    # Score thresholds (calibrated from test corpus analysis)
    SIMPLE_THRESHOLD = 11
    MEDIUM_THRESHOLD = 28

    def __init__(self, debug: bool = False):
        self.debug = debug

    def assess(self, prompt: str) -> AssessmentResult:
        """Main assessment entry point.

        Args:
            prompt: The user prompt to assess

        Returns:
            AssessmentResult with level, score, confidence, and signals

        """
        if not prompt or not prompt.strip():
            return AssessmentResult(
                level="simple",
                score=0,
                confidence=1.0,
                signals=["empty_prompt"],
            )

        prompt = prompt.strip()
        prompt_lower = prompt.lower()

        # Check for critical keywords first (overrides score-based classification)
        is_critical = self._detect_critical(prompt_lower)
        if is_critical:
            return AssessmentResult(
                level="critical",
                score=100,  # High score to indicate urgency
                confidence=0.95,  # High confidence for keyword match
                signals=["critical_keyword_detected"],
                breakdown={"critical_override": True},
            )

        # Calculate all dimension scores
        breakdown: dict[str, int | float] = {}
        signals: list[str] = []

        # 1. Lexical metrics
        lexical_score, lexical_signals = self._score_lexical(prompt)
        breakdown["lexical"] = lexical_score
        signals.extend(lexical_signals)

        # 2. Keyword analysis
        keyword_score, keyword_signals = self._score_keywords(prompt_lower)
        breakdown["keywords"] = keyword_score
        signals.extend(keyword_signals)

        # 3. Scope analysis
        scope_score, scope_signals = self._score_scope(prompt_lower)
        breakdown["scope"] = scope_score
        signals.extend(scope_signals)

        # 4. Constraint analysis
        constraint_score, constraint_signals = self._score_constraints(prompt_lower)
        breakdown["constraints"] = constraint_score
        signals.extend(constraint_signals)

        # 5. Structural patterns
        structure_score, structure_signals = self._score_structure(prompt)
        breakdown["structure"] = structure_score
        signals.extend(structure_signals)

        # 6. Domain complexity
        domain_score, domain_signals = self._score_domain(prompt_lower)
        breakdown["domain"] = domain_score
        signals.extend(domain_signals)

        # 7. Question type analysis
        question_score, question_signals = self._score_question_type(prompt_lower)
        breakdown["question_type"] = question_score
        signals.extend(question_signals)

        # Calculate total score
        total_score = sum(breakdown.values())

        # Apply multipliers for compound complexity
        multiplier = self._calculate_multiplier(signals)
        final_score = int(total_score * multiplier)
        breakdown["multiplier"] = multiplier

        # Determine level
        level: Literal["simple", "medium", "complex", "critical"]
        if final_score <= self.SIMPLE_THRESHOLD:
            level = "simple"
        elif final_score <= self.MEDIUM_THRESHOLD:
            level = "medium"
        else:
            level = "complex"

        # Calculate confidence based on signal consistency
        confidence = self._calculate_confidence(breakdown, signals, level)

        return AssessmentResult(
            level=level,
            score=final_score,
            confidence=confidence,
            signals=signals,
            breakdown=breakdown,
        )

    def _detect_critical(self, prompt_lower: str) -> bool:
        """Check if prompt contains critical keywords requiring high-priority handling.

        Uses a tiered approach to avoid false positives:
        1. Tier 1 (always critical): emergency, outage, breach, vulnerability, exploit, corruption
        2. Tier 2 (critical with context): security/production/authentication with action verbs
        3. Tier 3 (compliance): gdpr, hipaa, pci, compliance

        Args:
            prompt_lower: Lowercase version of the prompt

        Returns:
            True if critical keywords detected, False otherwise

        """
        import re

        # Tier 1: Always critical - high-stakes incidents
        tier1_keywords = {
            "emergency",
            "outage",
            "breach",
            "vulnerability",
            "exploit",
            "corruption",
            "data loss",
            "incident",
            "penetration",
        }
        for keyword in tier1_keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, prompt_lower):
                return True

        # Tier 2: Critical only with action context (fix, patch, investigate, secure)
        tier2_keywords = {"security", "production", "authentication", "authorization"}
        critical_actions = {
            "fix",
            "patch",
            "investigate",
            "secure",
            "protect",
            "mitigate",
            "prevent",
            "respond",
            "handle",
        }

        has_tier2 = any(
            re.search(r"\b" + re.escape(k) + r"\b", prompt_lower) for k in tier2_keywords
        )
        has_action = any(
            re.search(r"\b" + re.escape(a) + r"\b", prompt_lower) for a in critical_actions
        )

        if has_tier2 and has_action:
            return True

        # Tier 3: Compliance keywords
        tier3_keywords = {"gdpr", "hipaa", "pci", "compliance", "regulation"}
        for keyword in tier3_keywords:
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, prompt_lower):
                return True

        # Financial/legal with payment/transaction
        financial_keywords = {"payment", "transaction", "billing", "financial"}
        security_context = {"encrypt", "secure", "protect", "audit"}

        has_financial = any(
            re.search(r"\b" + re.escape(k) + r"\b", prompt_lower) for k in financial_keywords
        )
        has_security = any(
            re.search(r"\b" + re.escape(k) + r"\b", prompt_lower) for k in security_context
        )

        if has_financial and has_security:
            return True

        return False

    def _score_lexical(self, prompt: str) -> tuple[int, list[str]]:
        """Score based on lexical metrics."""
        score = 0
        signals = []

        words = prompt.split()
        word_count = len(words)

        # Word count scoring (calibrated: short=simple, long=complex)
        if word_count <= 5:
            score += 0
        elif word_count <= 10:
            score += 5
        elif word_count <= 20:
            score += 10
        elif word_count <= 40:
            score += 15
        elif word_count <= 60:
            score += 20
        else:
            score += 25
            signals.append(f"long_prompt:{word_count}")

        # Sentence count (multiple sentences suggest compound task)
        sentences = len(re.findall(r"[.!?]+", prompt)) or 1
        if sentences > 2:
            score += (sentences - 2) * 5
            signals.append(f"multi_sentence:{sentences}")

        # Question marks (multiple questions = compound request)
        q_count = prompt.count("?")
        if q_count > 1:
            score += (q_count - 1) * 8
            signals.append(f"multi_question:{q_count}")

        # Comma density (indicates lists or complex structure)
        comma_count = prompt.count(",")
        if comma_count > 3:
            score += min((comma_count - 3) * 3, 15)
            signals.append(f"high_comma_density:{comma_count}")

        # Semicolons and colons (formal structure)
        semi_count = prompt.count(";") + prompt.count(":")
        if semi_count > 0:
            score += semi_count * 4
            signals.append(f"formal_punctuation:{semi_count}")

        return score, signals

    def _score_keywords(self, prompt_lower: str) -> tuple[int, list[str]]:
        """Score based on action verb keywords."""
        score = 0
        signals = []

        words = set(re.findall(r"\b\w+\b", prompt_lower))
        word_count = len(prompt_lower.split())

        # Simple verbs (reduce score - but only modestly)
        simple_matches = words & self.SIMPLE_VERBS
        if simple_matches:
            score -= min(len(simple_matches) * 3, 10)
            signals.append(f"simple_verbs:{list(simple_matches)[:3]}")

        # Vague words (reduce score - user doesn't know precise target)
        vague_matches = words & self.VAGUE_WORDS
        if vague_matches:
            score -= min(len(vague_matches) * 5, 15)
            signals.append(f"vague_words:{list(vague_matches)[:3]}")

        # Detect trivial edit patterns
        trivial_edit_patterns = [
            r"\b(?:fix|add|remove|delete|rename|update)\b.*\b(?:typo|console\.?log|comment|variable|version|line)\b",
            r"\b(?:fix|add|remove|delete)\s+(?:a|the|this)\s+\w+$",
            r"\bwrite\s+(?:a|the)\s+function\s+(?:that|to|which)\b",
        ]
        is_trivial_edit = any(re.search(p, prompt_lower) for p in trivial_edit_patterns)
        if is_trivial_edit and word_count <= 8:
            signals.append("trivial_edit_pattern")
        else:
            # Medium verbs (moderate score boost) - only if not trivial
            medium_matches = words & self.MEDIUM_VERBS
            if medium_matches:
                score += len(medium_matches) * 12
                signals.append(f"medium_verbs:{list(medium_matches)[:3]}")

        # Analysis verbs (cap to avoid over-classification)
        analysis_matches = words & self.ANALYSIS_VERBS
        if analysis_matches:
            analysis_score = min(len(analysis_matches) * 15, 20)
            score += analysis_score
            signals.append(f"analysis_verbs:{list(analysis_matches)[:3]}")

        # Complex verbs (large boost)
        complex_matches = words & self.COMPLEX_VERBS
        if complex_matches:
            score += len(complex_matches) * 25
            signals.append(f"complex_verbs:{list(complex_matches)[:3]}")

        # Integration patterns
        if re.search(r"\bintegrate\b.*\bwith\b", prompt_lower):
            score += 15
            signals.append("integration_pattern")

        # Complex nouns combined with action verbs
        complex_noun_matches = words & self.COMPLEX_NOUNS
        medium_matches = words & self.MEDIUM_VERBS
        if complex_noun_matches:
            if medium_matches or complex_matches:
                score += len(complex_noun_matches) * 10
                signals.append(f"complex_nouns:{list(complex_noun_matches)[:3]}")
            else:
                score += len(complex_noun_matches) * 5

        # "how does X work" pattern
        if re.search(r"\bhow does\b.*\bwork\b", prompt_lower):
            score += 10
            signals.append("how_does_work_pattern")

        # Complex feature patterns
        complex_feature_patterns = [
            r"\b(?:dark\s*mode|feature\s*flag|real-?time)\b",
            r"\b(?:end-?to-?end|full-?stack|cross-?cutting)\b",
        ]
        for pattern in complex_feature_patterns:
            if re.search(pattern, prompt_lower):
                score += 12
                signals.append("complex_feature_pattern")
                break

        # Open-ended optimization
        if re.search(r"\b(?:improve|optimize)\s+(?:performance|speed|efficiency)\b", prompt_lower):
            if not re.search(r"\b(?:this|the)\s+(?:function|method|query|loop)\b", prompt_lower):
                score += 15
                signals.append("open_ended_optimization")

        # Standards compliance
        if re.search(
            r"\bfollowing\s+\w+\s*(?:guidelines?|standards?|practices?|rules?)\b",
            prompt_lower,
        ):
            score += 10
            signals.append("standards_compliance")

        # Bounded scope detection (reduces complex verb impact)
        if complex_matches and re.search(
            r"\b(?:this|the|a)\s+(?:function|method|class|component|file)\b",
            prompt_lower,
        ):
            if word_count <= 8:
                score -= 10
                signals.append("bounded_scope")

        return score, signals

    def _score_scope(self, prompt_lower: str) -> tuple[int, list[str]]:
        """Score based on scope expansion indicators."""
        score = 0
        signals = []

        words = set(re.findall(r"\b\w+\b", prompt_lower))

        # Detect verbose simple patterns
        verbose_simple_patterns = [
            r"\b(?:i would like|can you|could you|please)\b.*\b(?:tell|show|give|what|where)\b",
            r"\b(?:tell|show|give) me\b.*\b(?:what|where|which|version)\b",
        ]
        is_verbose_simple = any(re.search(p, prompt_lower) for p in verbose_simple_patterns)

        # Scope expansion keywords
        scope_matches = words & self.SCOPE_KEYWORDS
        if scope_matches:
            if is_verbose_simple:
                score += len(scope_matches) * 4
                signals.append("verbose_simple_pattern")
            else:
                score += len(scope_matches) * 12
            signals.append(f"scope_expansion:{list(scope_matches)[:3]}")

        # File/path references
        file_refs = re.findall(r"[\w./]+\.\w{1,5}\b", prompt_lower)
        if len(file_refs) > 1:
            score += (len(file_refs) - 1) * 8
            signals.append(f"multi_file_ref:{len(file_refs)}")

        # Directory patterns
        dir_refs = re.findall(
            r"\b(?:src|lib|tests?|docs?|components?|modules?|packages?)/\w+",
            prompt_lower,
        )
        if dir_refs:
            score += len(dir_refs) * 5
            signals.append(f"dir_refs:{len(dir_refs)}")

        return score, signals

    def _score_constraints(self, prompt_lower: str) -> tuple[int, list[str]]:
        """Score based on constraint and requirement markers."""
        score = 0
        signals = []

        # Constraint phrases
        for phrase in self.CONSTRAINT_PHRASES:
            if phrase in prompt_lower:
                score += 12
                signals.append(f"constraint:{phrase}")

        # Compound requirement markers
        for marker in self.COMPOUND_MARKERS:
            if marker in prompt_lower:
                score += 10
                signals.append(f"compound:{marker}")

        # Sequence markers
        seq_count = 0
        for marker in self.SEQUENCE_MARKERS:
            if marker in prompt_lower:
                seq_count += 1
        if seq_count > 0:
            score += seq_count * 8
            signals.append(f"sequence_markers:{seq_count}")

        # Negative constraints
        negatives = len(
            re.findall(r"\b(?:don\'t|dont|do not|never|avoid|shouldn\'t|must not)\b", prompt_lower),
        )
        if negatives > 0:
            score += negatives * 6
            signals.append(f"negative_constraints:{negatives}")

        return score, signals

    def _score_structure(self, prompt: str) -> tuple[int, list[str]]:
        """Score based on structural patterns."""
        score = 0
        signals = []

        # Numbered lists
        numbered = len(re.findall(r"(?:^|\n)\s*\d+[.\)]\s", prompt))
        if numbered > 0:
            score += numbered * 10
            signals.append(f"numbered_list:{numbered}")

        # Bullet points
        bullets = len(re.findall(r"(?:^|\n)\s*[-*]\s", prompt))
        if bullets > 0:
            score += bullets * 8
            signals.append(f"bullet_list:{bullets}")

        # Code blocks
        code_blocks = len(re.findall(r"```[\s\S]*?```|`[^`]+`", prompt))
        if code_blocks > 0:
            score += code_blocks * 5
            signals.append(f"code_blocks:{code_blocks}")

        # Success criteria
        if re.search(
            r"\b(?:should|must|needs? to|has to)\s+(?:result|return|output|produce|work|be)\b",
            prompt.lower(),
        ):
            score += 8
            signals.append("success_criteria")

        # Conditional logic
        conditionals = len(
            re.findall(r"\bif\b.*\bthen\b|\bwhen\b.*\bshould\b|\bdepending on\b", prompt.lower()),
        )
        if conditionals > 0:
            score += conditionals * 10
            signals.append(f"conditionals:{conditionals}")

        return score, signals

    def _score_domain(self, prompt_lower: str) -> tuple[int, list[str]]:
        """Score based on technical domain complexity."""
        score = 0
        signals = []

        words = set(re.findall(r"\b\w+\b", prompt_lower))

        # Technical domain matches
        domain_matches = words & self.TECHNICAL_DOMAINS
        if len(domain_matches) > 1:
            score += len(domain_matches) * 8
            signals.append(f"multi_domain:{list(domain_matches)[:4]}")
        elif domain_matches:
            score += 5
            signals.append(f"technical_domain:{list(domain_matches)}")

        # Framework/library mentions
        frameworks = re.findall(
            r"\b(?:react|vue|angular|django|flask|fastapi|express|spring|rails)\b",
            prompt_lower,
        )
        if frameworks:
            score += len(set(frameworks)) * 5
            signals.append(f"frameworks:{frameworks}")

        return score, signals

    def _score_question_type(self, prompt_lower: str) -> tuple[int, list[str]]:
        """Score based on question pattern analysis."""
        score = 0
        signals = []

        # Simple question patterns
        for pattern in self.SIMPLE_QUESTION_PATTERNS:
            if re.search(pattern, prompt_lower):
                score -= 8
                signals.append("simple_question_pattern")
                break

        # Complex question patterns
        for pattern in self.COMPLEX_QUESTION_PATTERNS:
            if re.search(pattern, prompt_lower):
                score += 15
                signals.append("complex_question_pattern")
                break

        # "How to" without implementation verb
        if re.search(r"^how (?:to|do i|can i)\b", prompt_lower):
            if not any(v in prompt_lower for v in self.COMPLEX_VERBS):
                score += 8
                signals.append("how_to_pattern")

        return score, signals

    def _calculate_multiplier(self, signals: list[str]) -> float:
        """Calculate compound complexity multiplier."""
        multiplier = 1.0

        # Count complexity indicators
        complex_indicators = sum(
            1
            for s in signals
            if any(
                x in s
                for x in [
                    "complex_verbs",
                    "scope_expansion",
                    "constraint",
                    "multi_domain",
                    "sequence_markers",
                    "compound",
                    "numbered_list",
                ]
            )
        )

        # Count simplicity indicators
        simple_indicators = sum(
            1 for s in signals if any(x in s for x in ["simple_verbs", "simple_question"])
        )

        # Compound complexity
        if complex_indicators >= 3:
            multiplier += 0.2
        if complex_indicators >= 5:
            multiplier += 0.2

        # Simple signals with no complex signals reduce
        if simple_indicators > 0 and complex_indicators == 0:
            multiplier -= 0.1

        return max(0.7, min(1.5, multiplier))

    def _calculate_confidence(
        self, breakdown: dict[str, int | float], signals: list[str], level: str
    ) -> float:
        """Calculate confidence in the classification."""
        total = sum(v for k, v in breakdown.items() if k != "multiplier")

        # Distance from thresholds
        max_distance: float
        if level == "simple":
            distance = self.SIMPLE_THRESHOLD - total
            max_distance = float(self.SIMPLE_THRESHOLD)
        elif level == "medium":
            distance = min(total - self.SIMPLE_THRESHOLD, self.MEDIUM_THRESHOLD - total)
            max_distance = (self.MEDIUM_THRESHOLD - self.SIMPLE_THRESHOLD) / 2
        else:
            distance = total - self.MEDIUM_THRESHOLD
            max_distance = 30.0

        # Base confidence from distance
        base_confidence = min(0.5 + (distance / max_distance) * 0.4, 0.9)

        # Signal consistency bonus
        complex_signals = sum(1 for s in signals if "complex" in s or "scope" in s)
        simple_signals = sum(1 for s in signals if "simple" in s)

        if level == "complex" and complex_signals > simple_signals:
            base_confidence += 0.05
        elif level == "simple" and simple_signals > complex_signals:
            base_confidence += 0.05

        return min(0.95, max(0.5, base_confidence))


# ========== PRESERVED: CRITICAL_KEYWORDS from old implementation ==========

CRITICAL_KEYWORDS = {
    # Security and safety
    "security",
    "vulnerability",
    "authentication",
    "authorization",
    "encrypt",
    "secure",
    "protect",
    "audit",
    "compliance",
    "penetration",
    # High-stakes operations
    "production",
    "critical",
    "emergency",
    "incident",
    "outage",
    "data loss",
    "corruption",
    "breach",
    "exploit",
    # Financial/legal
    "payment",
    "transaction",
    "billing",
    "financial",
    "legal",
    "regulation",
    "gdpr",
    "hipaa",
    "pci",
}


# ========== ADAPTER: Wrap ComplexityAssessor for backward compatibility ==========


def _assess_tier1_keyword(query: str) -> tuple[str, float, float]:
    """Fast keyword-based complexity assessment using ComplexityAssessor.

    This function wraps the new ComplexityAssessor to maintain backward
    compatibility with the existing two-tier assessment interface.

    Args:
        query: User query string

    Returns:
        Tuple of (complexity_level, score, confidence):
            - complexity_level: "SIMPLE" | "MEDIUM" | "COMPLEX" | "CRITICAL"
            - score: 0.0-1.0 (normalized score)
            - confidence: 0.0-1.0 (how confident in classification)

    """
    # Create assessor and run assessment
    assessor = ComplexityAssessor()
    result = assessor.assess(query)

    # Convert lowercase level to uppercase for API compatibility
    complexity_level = result.level.upper()

    # Normalize score to 0.0-1.0 range (divide raw score by 100)
    # Raw scores typically range 0-50+, so we normalize conservatively
    normalized_score = min(result.score / 50.0, 1.0)

    # Use the assessor's confidence directly
    confidence = result.confidence

    logger.debug(
        f"ComplexityAssessor result: {complexity_level} "
        f"(raw_score={result.score}, normalized_score={normalized_score:.3f}, "
        f"confidence={confidence:.3f}, signals={result.signals[:3]})",
    )

    return (complexity_level, normalized_score, confidence)


# ========== PRESERVED: LLM Tier 2 and public API from old implementation ==========


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
        user_prompt = prompt_template.build_user_prompt(query=query, keyword_result=keyword_result)

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
            f"(confidence={confidence:.3f}, verification={recommended_verification})",
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


def assess_complexity(query: str, _llm_client: LLMClient | None = None) -> dict[str, Any]:
    """Assess query complexity using keyword-based classification.

    Uses ComplexityAssessor for multi-dimensional lexical analysis including:
    - Lexical metrics (word count, sentence count, punctuation)
    - Keyword categories (action verbs, scope indicators)
    - Structural patterns (lists, questions, conditionals)
    - Domain complexity (technical terms, cross-cutting concerns)

    LLM tier2 verification has been removed because:
    - LLM has no additional context beyond the query text
    - Keyword classifier achieved 96% accuracy on benchmark corpus
    - LLM tier2 was less accurate than keyword classifier in practice
    - Keyword scoring is transparent and debuggable

    Args:
        query: User query string
        _llm_client: Ignored (kept for API compatibility, reserved for future use)

    Returns:
        Dict with keys:
            - complexity: str (SIMPLE, MEDIUM, COMPLEX, CRITICAL)
            - confidence: float (0-1)
            - method: str (always "keyword")
            - reasoning: str (explanation of classification)
            - score: float (0-1, normalized complexity score)

    """
    # Use keyword classification only (LLM tier2 removed)
    # Rationale: LLM has no additional context and was less accurate than keyword classifier
    complexity_level, score, confidence = _assess_tier1_keyword(query)

    logger.info(
        f"Complexity assessment: {complexity_level} "
        f"(score={score:.3f}, confidence={confidence:.3f})",
    )

    return {
        "complexity": complexity_level,
        "confidence": confidence,
        "method": "keyword",
        "reasoning": f"Multi-dimensional keyword analysis: {complexity_level.lower()} complexity",
        "score": score,
    }
