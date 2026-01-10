"""
Keyword-based prompt complexity assessment module.

A lightweight, LLM-free complexity classifier for routing prompts to
appropriate models based on lexical analysis and pattern matching.

Usage:
    from tests.keyword_assess import assess_prompt

    result = assess_prompt("implement user authentication")
    print(result.level)  # 'complex'
    print(result.score)  # 65
"""

from .complexity_assessor import (
    AssessmentResult,
    ComplexityAssessor,
    ComplexityLevel,
    assess_prompt,
)

__all__ = [
    "ComplexityAssessor",
    "AssessmentResult",
    "assess_prompt",
    "ComplexityLevel",
]
