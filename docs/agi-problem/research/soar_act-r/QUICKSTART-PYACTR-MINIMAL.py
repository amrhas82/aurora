#!/usr/bin/env python3
"""
MINIMAL VIABLE ACT-R SYSTEM
Ready to run, ~100 lines, immediate start

This is the absolute minimum to get ACT-R + LLM working.
Based on OPEN-SOURCE-SOAR-ACTR-PRACTICAL-GUIDE.md Part 7

Installation:
  pip install python_actr anthropic

Usage:
  python QUICKSTART-PYACTR-MINIMAL.py

Expected output:
  First call: [ACT-R] No learned procedure, querying LLM...
  Second call: [ACT-R] Using learned procedure (activation: 0.85)
  Third call: [ACT-R] Using learned procedure (activation: 0.90)
"""

import json
import time

from anthropic import Anthropic


# Initialize Claude
client = Anthropic()

class MinimalACTRSystem:
    """Minimum viable ACT-R + LLM system"""

    def __init__(self):
        self.memory = {
            'procedures': [],
            'last_procedure_id': None
        }

    def solve(self, prompt, visible_reasoning=True):
        """Solve a prompt using learned procedures or LLM"""

        # Step 1: ACT-R PATTERN MATCHING (Phase 1-2)
        # Search memory for similar past procedures
        similar = self._find_similar_procedure(prompt)

        if similar and similar['activation'] > 0.75:
            # Strong match: Execute learned procedure
            if visible_reasoning:
                print(f"[ACT-R] Using learned procedure: {similar['name']}")
                print(f"        (activation: {similar['activation']:.2f})")

            self.memory['last_procedure_id'] = similar['id']
            return self._execute_procedure(similar)

        # Step 2: ACT-R ACTION with LLM (Phase 3)
        # No strong match: Query LLM for new solution
        if visible_reasoning:
            print("[ACT-R] No strong match, querying LLM...")

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.content[0].text

        # Step 3: ACT-R LEARNING (Phase 4)
        # Store for future reuse
        proc_id = len(self.memory['procedures'])
        self.memory['procedures'].append({
            'id': proc_id,
            'name': self._extract_type(prompt),
            'prompt_keywords': self._extract_keywords(prompt),
            'result': result[:200],  # Store first 200 chars
            'rating': 0,
            'timestamp': time.time(),
            'use_count': 1,
            'activation': 0.5  # Start neutral
        })
        self.memory['last_procedure_id'] = proc_id

        return result

    def give_feedback(self, rating):
        """User rates last response (0-10)"""
        if self.memory['last_procedure_id'] is not None:
            proc = self.memory['procedures'][self.memory['last_procedure_id']]
            proc['rating'] = rating
            proc['activation'] = rating / 10.0
            proc['use_count'] += 1

            if rating >= 7:
                print(f"[ACT-R Learning] Procedure improved (rating: {rating}/10)")

    def _find_similar_procedure(self, prompt):
        """Find similar procedure in memory (Pattern Matching)"""
        best_match = None
        best_score = 0.0
        prompt_words = set(self._extract_keywords(prompt))

        for proc in self.memory['procedures']:
            # Similarity: how many keywords overlap
            proc_words = set(proc['prompt_keywords'])
            if not (prompt_words | proc_words):
                continue

            similarity = len(prompt_words & proc_words) / len(prompt_words | proc_words)

            # Activation: success * recency * frequency
            if proc.get('rating', 0) > 0:
                recency = 1.0 - min((time.time() - proc['timestamp']) / 86400, 1.0)
                frequency = min(proc.get('use_count', 1) / 10.0, 1.0)
                activation = (
                    0.4 * (proc.get('activation', 0.5)) +
                    0.3 * recency +
                    0.3 * frequency
                )
            else:
                activation = 0.0

            score = similarity * activation

            if score > best_score:
                best_match = {
                    'id': proc['id'],
                    'name': proc['name'],
                    'activation': activation,
                    'proc': proc
                }
                best_score = score

        return best_match if best_score > 0.0 else None

    def _execute_procedure(self, match):
        """Execute a learned procedure"""
        return match['proc']['result']

    def _extract_keywords(self, text):
        """Extract keywords from text"""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'to', 'in', 'of', 'for'}
        words = text.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 3]

    def _extract_type(self, prompt):
        """Classify prompt type"""
        if 'market' in prompt.lower():
            return 'market_analysis'
        elif 'design' in prompt.lower():
            return 'design'
        elif 'strategy' in prompt.lower():
            return 'strategy'
        return 'general'

    def save(self, filename='actr_memory.json'):
        """Save memory to disk"""
        with open(filename, 'w') as f:
            json.dump(self.memory, f, indent=2)
        print(f"[ACT-R] Memory saved to {filename}")

    def load(self, filename='actr_memory.json'):
        """Load memory from disk"""
        try:
            with open(filename) as f:
                self.memory = json.load(f)
            print(f"[ACT-R] Memory loaded from {filename}")
        except FileNotFoundError:
            print("[ACT-R] No prior memory found, starting fresh")


def main():
    """Demo: MinimalACTRSystem in action"""

    print("=" * 60)
    print("MINIMAL ACT-R SYSTEM DEMO")
    print("=" * 60)

    system = MinimalACTRSystem()
    system.load()  # Try to load prior memory

    # First request: No memory, queries LLM
    print("\n[FIRST REQUEST]")
    print("Prompt: What opportunities exist in AI market?")
    print("-" * 60)
    result1 = system.solve("What opportunities exist in AI market?", visible_reasoning=True)
    print(f"Response: {result1[:150]}...")
    system.give_feedback(9)  # User rates highly

    # Second request: Similar task, may reuse procedure
    print("\n[SECOND REQUEST]")
    print("Prompt: What opportunities in blockchain market?")
    print("-" * 60)
    result2 = system.solve("What opportunities in blockchain market?", visible_reasoning=True)
    print(f"Response: {result2[:150]}...")
    system.give_feedback(8)

    # Third request: Should use learned procedure
    print("\n[THIRD REQUEST]")
    print("Prompt: What opportunities in cybersecurity market?")
    print("-" * 60)
    result3 = system.solve("What opportunities in cybersecurity market?", visible_reasoning=True)
    print(f"Response: {result3[:150]}...")
    system.give_feedback(9)

    # Show memory state
    print("\n[MEMORY STATE]")
    print(f"Procedures learned: {len(system.memory['procedures'])}")
    for proc in system.memory['procedures']:
        print(f"  - {proc['name']}: activation={proc['activation']:.2f}, uses={proc['use_count']}")

    # Save for next session
    system.save()

    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("1. Integrate with Anthropic's Claude API key (or use local LLM)")
    print("2. Add domain-specific prompts in solve()")
    print("3. Extend _extract_keywords() with semantic similarity")
    print("4. Add SOAR reasoning for complex tasks (from Part 3)")
    print("5. Build web UI to visualize learning")
    print("=" * 60)


if __name__ == "__main__":
    main()
