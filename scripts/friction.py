#!/usr/bin/env python3
"""Friction analysis pipeline - analyze sessions and extract antigens.

Usage:
    python friction.py <sessions-directory>
    python friction.py ~/.claude/projects/-home-hamr-PycharmProjects-aurora/

Outputs (all in .aurora/friction/):
    friction_analysis.json   - Per-session analysis
    friction_summary.json    - Aggregate stats
    friction_raw.jsonl       - Raw signals
    antigen_candidates.json  - Antigen candidates
    antigen_review.md        - Human review file
"""

import sys
from pathlib import Path

# Import from sibling scripts
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from antigen_extract import main as extract_main
from friction_analyze import main as analyze_main


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    sessions_dir = Path(sys.argv[1])

    if not sessions_dir.exists():
        print(f"Error: {sessions_dir} does not exist")
        return 1

    print("=" * 60)
    print(" FRICTION ANALYSIS PIPELINE")
    print("=" * 60)

    # Step 1: Analyze sessions
    print("\n[1/2] Analyzing sessions...\n")
    analyze_main()  # Continue even if INCONCLUSIVE - may still have BAD sessions

    # Check if analysis produced output
    analysis_file = Path(".aurora/friction/friction_analysis.json")
    if not analysis_file.exists():
        print("\nNo analysis output. Check session directory.")
        return 1

    # Step 2: Extract antigens
    print("\n" + "=" * 60)
    print("\n[2/2] Extracting antigens from BAD sessions...\n")
    extract_main()

    # Final summary
    print("\n" + "=" * 60)
    print(" DONE")
    print("=" * 60)

    review_file = Path(".aurora/friction/antigen_review.md")
    if review_file.exists():
        print("\nReview your antigens:")
        print(f"  cat {review_file}")
        print("\nOr feed to LLM:")
        print(f'  cat {review_file} | claude "write CLAUDE.md rules to prevent these patterns"')

    return 0


if __name__ == "__main__":
    sys.exit(main())
