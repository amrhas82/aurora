"""POC: Multi-turn MCP tool that controls the conversation loop.

This tool makes SEPARATE API calls for each phase, controlling the flow
from Python - not relying on Claude to "follow instructions".
"""

import json
import os

import anthropic


def run_multiturn_soar(query: str, api_key: str | None = None) -> dict:
    """Run a multi-turn SOAR query with separate LLM calls per phase.

    The KEY insight: Python controls the loop, makes separate API calls.
    Claude doesn't need to "remember" to follow phases - we FORCE it.

    Args:
        query: User question
        api_key: Anthropic API key (or from env)

    Returns:
        Dict with all phase outputs and final answer
    """
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "No API key provided. Set ANTHROPIC_API_KEY or pass api_key."}

    client = anthropic.Anthropic(api_key=api_key)
    context = {"query": query, "phases": {}}

    def call_llm(prompt: str, max_tokens: int = 1000) -> str:
        """Make a single LLM call."""
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    # ===== PHASE 1: ASSESS (LLM call 1) =====
    phase1_prompt = f"""Assess the complexity of this query. Output JSON only.

Query: {query}

Output format:
{{"complexity": "SIMPLE|MEDIUM|COMPLEX", "reasoning": "brief explanation"}}"""

    phase1_raw = call_llm(phase1_prompt, max_tokens=200)
    try:
        # Extract JSON from response
        phase1 = json.loads(phase1_raw.strip().strip("```json").strip("```"))
    except:
        phase1 = {"complexity": "MEDIUM", "reasoning": phase1_raw}
    context["phases"]["assess"] = phase1

    # ===== PHASE 2: DECOMPOSE (LLM call 2) =====
    phase2_prompt = f"""Break this query into 2-4 subgoals. Output JSON only.

Query: {query}
Complexity: {phase1.get('complexity', 'MEDIUM')}

Output format:
{{"subgoals": ["subgoal 1", "subgoal 2", ...]}}"""

    phase2_raw = call_llm(phase2_prompt, max_tokens=300)
    try:
        phase2 = json.loads(phase2_raw.strip().strip("```json").strip("```"))
    except:
        phase2 = {"subgoals": [phase2_raw]}
    context["phases"]["decompose"] = phase2

    # ===== PHASE 3: VERIFY (LLM call 3) =====
    phase3_prompt = f"""Verify if these subgoals completely cover the query. Output JSON only.

Query: {query}
Subgoals: {json.dumps(phase2.get('subgoals', []))}

Output format:
{{"verdict": "PASS|FAIL", "missing": "what's missing if FAIL, or null"}}"""

    phase3_raw = call_llm(phase3_prompt, max_tokens=200)
    try:
        phase3 = json.loads(phase3_raw.strip().strip("```json").strip("```"))
    except:
        phase3 = {"verdict": "PASS", "missing": None}
    context["phases"]["verify"] = phase3

    # ===== PHASE 4: COLLECT (LLM call 4) =====
    phase4_prompt = f"""Answer each subgoal. Output JSON only.

Query: {query}
Subgoals: {json.dumps(phase2.get('subgoals', []))}

Output format:
{{"findings": [{{"subgoal": "...", "answer": "..."}}, ...]}}"""

    phase4_raw = call_llm(phase4_prompt, max_tokens=1500)
    try:
        phase4 = json.loads(phase4_raw.strip().strip("```json").strip("```"))
    except:
        phase4 = {"findings": [{"subgoal": "all", "answer": phase4_raw}]}
    context["phases"]["collect"] = phase4

    # ===== PHASE 5: SYNTHESIZE (LLM call 5) =====
    phase5_prompt = f"""Synthesize findings into a coherent answer. Output JSON only.

Query: {query}
Findings: {json.dumps(phase4.get('findings', []))}

Output format:
{{"synthesis": "comprehensive answer combining all findings"}}"""

    phase5_raw = call_llm(phase5_prompt, max_tokens=1000)
    try:
        phase5 = json.loads(phase5_raw.strip().strip("```json").strip("```"))
    except:
        phase5 = {"synthesis": phase5_raw}
    context["phases"]["synthesize"] = phase5

    # ===== PHASE 6: RESPOND (LLM call 6) =====
    phase6_prompt = f"""Format the final answer for the user. Be clear and actionable.

Query: {query}
Synthesis: {phase5.get('synthesis', '')}

Output the final answer directly (not JSON)."""

    final_answer = call_llm(phase6_prompt, max_tokens=1000)
    context["phases"]["respond"] = {"answer": final_answer}
    context["final_answer"] = final_answer

    return context


# For testing directly
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python multiturn_poc.py 'your question'")
        sys.exit(1)

    query = sys.argv[1]
    print(f"Query: {query}\n")
    print("=" * 60)

    result = run_multiturn_soar(query)

    if "error" in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    for phase_name, phase_data in result.get("phases", {}).items():
        print(f"\n## {phase_name.upper()}")
        print(json.dumps(phase_data, indent=2))

    print("\n" + "=" * 60)
    print("\n## FINAL ANSWER\n")
    print(result.get("final_answer", "No answer"))
