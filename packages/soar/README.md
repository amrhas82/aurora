# aurora-soar

Agent registry and orchestration for AURORA framework.

This package provides agent discovery, registration, and management capabilities, along with a 9-phase SOAR (Sense, Organize, Act, Respond) pipeline for adaptive reasoning with retrieval quality assessment.

## Features

- **9-Phase SOAR Pipeline**: Assess → Retrieve → Decompose → Verify → Route → Collect → Synthesize → Record → Respond
- **Agent Registry**: Dynamic agent discovery and routing based on capabilities
- **Retrieval Quality Assessment**: Automatic evaluation of retrieved context quality with user guidance
- **Headless Orchestration**: Multi-turn reasoning workflows without user interaction
- **ACT-R Integration**: Cognitive architecture with activation-based memory retrieval

## Retrieval Quality Assessment

The SOAR pipeline includes intelligent retrieval quality assessment in Phase 4 (Verify) that guides users when retrieved context is weak or missing:

### Quality Levels

- **NONE**: No indexed context available → proceeds with LLM general knowledge
- **WEAK**: Low groundedness (<0.7) or few high-quality chunks (<3) → prompts user (CLI) or auto-continues (MCP)
- **GOOD**: High groundedness (≥0.7) and sufficient chunks (≥3) → proceeds automatically

### Interactive Mode Example (CLI)

```python
from aurora_soar.phases.verify import verify_decomposition

result = verify_decomposition(
    query="Explain the authentication flow",
    decomposition=decomp,
    verification_option="self",
    interactive_mode=True,  # Enable user prompts
    retrieval_context={
        "high_quality_count": 2,  # Only 2 chunks with activation ≥ 0.3
        "total_chunks": 5
    }
)

# If quality is WEAK, user sees:
# ⚠ Warning: Retrieved context quality is weak
#   Groundedness: 0.62 (target: ≥0.7)
#   High-quality chunks: 2 (target: ≥3)
#
# Options:
#   1. Start anew - Clear weak matches, use general knowledge
#   2. Start over - Rephrase query for better matches
#   3. Continue - Proceed with weak matches (results may be generic)

print(result.retrieval_quality)  # "WEAK"
print(result.verdict)  # "PASS" or "RETRY" or "FAIL"
```

### Non-Interactive Mode (MCP, Headless, Automation)

```python
result = verify_decomposition(
    query="Explain the authentication flow",
    decomposition=decomp,
    verification_option="self",
    interactive_mode=False,  # No prompts, auto-continues
    retrieval_context={
        "high_quality_count": 2,
        "total_chunks": 5
    }
)

# No user prompt shown, automatically continues
# Quality metadata included in result for client-side handling
print(result.retrieval_quality)  # "WEAK"
```

### VerifyPhaseResult Schema

```python
@dataclass
class VerifyPhaseResult:
    completeness: float  # 0.0-1.0
    consistency: float   # 0.0-1.0
    groundedness: float  # 0.0-1.0
    routability: float   # 0.0-1.0
    overall_score: float # Weighted average
    verdict: str         # "PASS" | "RETRY" | "FAIL"
    issues: List[str]    # Problems identified
    suggestions: List[str]  # Improvements
    retrieval_quality: str  # "NONE" | "WEAK" | "GOOD" (added in v0.2.1)
```

## Documentation

- **Full Architecture**: [docs/architecture/SOAR_ARCHITECTURE.md](../../docs/architecture/SOAR_ARCHITECTURE.md)
- **CLI Usage**: [docs/cli/CLI_USAGE_GUIDE.md](../../docs/cli/CLI_USAGE_GUIDE.md) - See "Retrieval Quality Handling" section
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md) - See "Weak Match Warnings" section
