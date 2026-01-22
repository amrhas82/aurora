"""Fuzzy matching utilities.

Provides Levenshtein distance and nearest match finding.
"""


def levenshtein(a: str, b: str) -> int:
    """Calculate Levenshtein distance between two strings.

    The Levenshtein distance is the minimum number of single-character
    edits (insertions, deletions, substitutions) needed to transform
    one string into another.

    Args:
        a: First string
        b: Second string

    Returns:
        Edit distance as integer

    """
    m = len(a)
    n = len(b)

    # Create distance matrix
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # Fill in the rest
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # deletion
                dp[i][j - 1] + 1,  # insertion
                dp[i - 1][j - 1] + cost,  # substitution
            )

    return dp[m][n]


def nearest_matches(input_str: str, candidates: list[str], max: int = 5) -> list[str]:
    """Find nearest matches to input string from candidates.

    Uses Levenshtein distance to rank candidates by similarity.

    Args:
        input_str: String to match against
        candidates: List of candidate strings
        max: Maximum number of results to return

    Returns:
        List of nearest matches, sorted by distance (closest first)

    """
    if not candidates:
        return []

    # Score each candidate
    scored = [(candidate, levenshtein(input_str, candidate)) for candidate in candidates]

    # Sort by distance
    scored.sort(key=lambda x: x[1])

    # Return top matches
    return [candidate for candidate, _ in scored[:max]]
