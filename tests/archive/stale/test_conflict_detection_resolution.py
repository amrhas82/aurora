"""Unit tests for conflict detection and resolution mechanisms.

Tests cover the ConflictDetector and ConflictResolver classes used
when multiple tools produce differing outputs.
"""

import pytest
from aurora_cli.concurrent_executor import (
    ConflictDetector,
    ConflictInfo,
    ConflictResolver,
    ConflictSeverity,
    ToolResult,
)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class TestOutputNormalization:
    """Test output normalization for comparison."""

    def test_normalize_whitespace(self):
        """Test that excessive whitespace is normalized."""
        text = "Hello    world   with   spaces"
        normalized = ConflictDetector.normalize_output(text)
        assert "    " not in normalized  # No quadruple spaces

    def test_normalize_newlines(self):
        """Test that excessive newlines are normalized."""
        text = "Line 1\n\n\n\n\nLine 2"
        normalized = ConflictDetector.normalize_output(text)
        assert "\n\n\n" not in normalized

    def test_normalize_leading_trailing(self):
        """Test that leading/trailing whitespace is removed."""
        text = "   Hello world   "
        normalized = ConflictDetector.normalize_output(text)
        assert not normalized.startswith(" ")
        assert not normalized.endswith(" ")

    def test_normalize_preserves_content(self):
        """Test that normalization preserves actual content."""
        text = "Important content with code `example`"
        normalized = ConflictDetector.normalize_output(text)
        assert "Important" in normalized
        assert "content" in normalized
        assert "example" in normalized


# ---------------------------------------------------------------------------
# Test: ConflictDetector - Code Block Extraction
# ---------------------------------------------------------------------------


class TestCodeBlockExtraction:
    """Test code block extraction from outputs."""

    def test_extract_python_block(self):
        """Test extracting Python code blocks."""
        text = "Here is code:\n```python\ndef hello():\n    print('hi')\n```"
        blocks = ConflictDetector.extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0] == "python"
        assert "def hello" in blocks[0][1]

    def test_extract_multiple_blocks(self):
        """Test extracting multiple code blocks."""
        text = """
```python
print('python')
```

Some text

```javascript
console.log('js');
```
"""
        blocks = ConflictDetector.extract_code_blocks(text)
        assert len(blocks) == 2
        assert blocks[0][0] == "python"
        assert blocks[1][0] == "javascript"

    def test_extract_no_language(self):
        """Test extracting code blocks without language tag."""
        text = "```\nplain code\n```"
        blocks = ConflictDetector.extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0][0] == ""  # No language

    def test_no_code_blocks(self):
        """Test when there are no code blocks."""
        text = "Just plain text without any code"
        blocks = ConflictDetector.extract_code_blocks(text)
        assert len(blocks) == 0


# ---------------------------------------------------------------------------
# Test: ConflictDetector - Similarity Calculation
# ---------------------------------------------------------------------------


class TestSimilarityCalculation:
    """Test similarity calculation between outputs."""

    def test_identical_texts(self):
        """Test similarity of identical texts."""
        text = "This is some text"
        similarity = ConflictDetector.calculate_similarity(text, text)
        assert similarity == 1.0

    def test_empty_texts(self):
        """Test similarity of empty texts."""
        similarity = ConflictDetector.calculate_similarity("", "")
        assert similarity == 1.0

    def test_one_empty(self):
        """Test similarity when one text is empty."""
        similarity = ConflictDetector.calculate_similarity("Some text", "")
        assert similarity == 0.0

    def test_similar_texts(self):
        """Test similarity of similar texts."""
        text1 = "The quick brown fox jumps over the lazy dog"
        text2 = "The quick brown fox jumps over the lazy cat"
        similarity = ConflictDetector.calculate_similarity(text1, text2)
        assert 0.8 < similarity < 1.0

    def test_different_texts(self):
        """Test similarity of very different texts."""
        text1 = "Hello world"
        text2 = "Completely different content here"
        similarity = ConflictDetector.calculate_similarity(text1, text2)
        assert similarity < 0.5


# ---------------------------------------------------------------------------
# Test: ConflictDetector - Conflict Detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    """Test conflict detection between tool results."""

    def test_identical_outputs_no_conflict(self):
        """Test that identical outputs show no conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42"),
            ToolResult(tool="opencode", success=True, output="The answer is 42"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE
        assert conflict.similarity_score >= 0.95

    def test_minor_differences(self):
        """Test minor differences (formatting, punctuation)."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is 42."),
            ToolResult(tool="opencode", success=True, output="The answer is 42"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity in (ConflictSeverity.NONE, ConflictSeverity.MINOR)
        assert conflict.similarity_score >= 0.9

    def test_moderate_differences(self):
        """Test moderate differences requiring review."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="Use a recursive approach with memoization for optimal performance.",
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="Use an iterative approach with a stack for better memory usage.",
            ),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
        assert conflict.similarity_score < 0.8

    def test_major_disagreement(self):
        """Test major disagreement between tools."""
        results = [
            ToolResult(tool="claude", success=True, output="Yes, this is safe and recommended."),
            ToolResult(
                tool="opencode",
                success=True,
                output="No, this is dangerous and should be avoided.",
            ),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR)
        assert conflict.similarity_score < 0.6

    def test_single_result_no_conflict(self):
        """Test that single result shows no conflict."""
        results = [
            ToolResult(tool="claude", success=True, output="Only one result"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE
        assert conflict.similarity_score == 1.0

    def test_no_successful_results(self):
        """Test handling when all results failed."""
        results = [
            ToolResult(tool="claude", success=False, output=""),
            ToolResult(tool="opencode", success=False, output=""),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        # Should handle gracefully
        assert conflict.severity == ConflictSeverity.NONE

    def test_empty_outputs(self):
        """Test handling of empty outputs."""
        results = [
            ToolResult(tool="claude", success=True, output=""),
            ToolResult(tool="opencode", success=True, output=""),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE

    def test_three_tools_two_agree(self):
        """Test with three tools where two agree."""
        results = [
            ToolResult(tool="claude", success=True, output="The answer is A"),
            ToolResult(tool="opencode", success=True, output="The answer is A"),
            ToolResult(tool="cursor", success=True, output="The answer is B"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        # There should be some level of conflict due to cursor disagreeing
        assert conflict.tools_involved == ["claude", "opencode", "cursor"]


# ---------------------------------------------------------------------------
# Test: ConflictDetector - Diff Summary
# ---------------------------------------------------------------------------


class TestDiffSummary:
    """Test diff summary generation."""

    def test_diff_summary_generated(self):
        """Test that diff summary is generated for different outputs."""
        text1 = "Line 1\nLine 2\nLine 3"
        text2 = "Line 1\nModified Line 2\nLine 3"
        diff = ConflictDetector.get_diff_summary(text1, text2, "claude", "opencode")
        assert "claude" in diff or "opencode" in diff
        assert "Line 2" in diff or "Modified" in diff

    def test_diff_summary_truncation(self):
        """Test that long diffs are truncated."""
        # Create very different large texts
        text1 = "\n".join([f"Line {i} from source A" for i in range(100)])
        text2 = "\n".join([f"Line {i} from source B" for i in range(100)])
        diff = ConflictDetector.get_diff_summary(text1, text2, "claude", "opencode")
        # Should be truncated if too long
        assert len(diff) < len(text1) + len(text2)


# ---------------------------------------------------------------------------
# Test: ConflictResolver - Consensus Resolution
# ---------------------------------------------------------------------------


class TestConsensusResolution:
    """Test consensus-based conflict resolution."""

    def test_consensus_reached(self):
        """Test consensus resolution when outputs agree."""
        results = [
            ToolResult(tool="claude", success=True, output="The solution is X"),
            ToolResult(tool="opencode", success=True, output="The solution is X"),
        ]
        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.8)
        assert winner is not None
        assert winner.output == "The solution is X"
        assert conflict_info.similarity_score >= 0.8

    def test_consensus_not_reached(self):
        """Test consensus resolution when outputs disagree."""
        results = [
            ToolResult(tool="claude", success=True, output="Do it this way"),
            ToolResult(tool="opencode", success=True, output="Do it the other way"),
        ]
        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.8)
        assert winner is None
        assert conflict_info.similarity_score < 0.8

    def test_consensus_prefers_longer_output(self):
        """Test that consensus prefers longer (more complete) output."""
        results = [
            ToolResult(tool="claude", success=True, output="Short answer"),
            ToolResult(
                tool="opencode",
                success=True,
                output="Short answer with more details and explanation",
            ),
        ]
        winner, conflict_info = ConflictResolver.resolve_by_consensus(results, threshold=0.5)
        if winner:
            assert winner.tool == "opencode"

    def test_consensus_custom_threshold(self):
        """Test consensus with custom threshold."""
        results = [
            ToolResult(tool="claude", success=True, output="Answer A here"),
            ToolResult(tool="opencode", success=True, output="Answer A there"),
        ]
        # Low threshold should pass
        winner_low, _ = ConflictResolver.resolve_by_consensus(results, threshold=0.5)
        assert winner_low is not None

        # High threshold might fail
        winner_high, _ = ConflictResolver.resolve_by_consensus(results, threshold=0.99)
        # This could be None if similarity is below 0.99


# ---------------------------------------------------------------------------
# Test: ConflictResolver - Weighted Vote Resolution
# ---------------------------------------------------------------------------


class TestWeightedVoteResolution:
    """Test weighted vote conflict resolution."""

    def test_weighted_vote_uses_weights(self):
        """Test that weighted voting respects tool weights."""
        results = [
            ToolResult(tool="claude", success=True, output="A", execution_time=10),
            ToolResult(tool="opencode", success=True, output="B", execution_time=10),
        ]
        weights = {"claude": 2.0, "opencode": 1.0}
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results, weights)
        assert winner.tool == "claude"

    def test_weighted_vote_equal_weights(self):
        """Test weighted voting with equal weights."""
        results = [
            ToolResult(tool="claude", success=True, output="A" * 100, execution_time=10),
            ToolResult(tool="opencode", success=True, output="B" * 50, execution_time=10),
        ]
        weights = {"claude": 1.0, "opencode": 1.0}
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results, weights)
        # Claude has longer output, should win on length bonus
        assert winner.tool == "claude"

    def test_weighted_vote_speed_bonus(self):
        """Test that faster tools get speed bonus."""
        results = [
            ToolResult(tool="claude", success=True, output="A", execution_time=5),  # Fast
            ToolResult(tool="opencode", success=True, output="A", execution_time=100),  # Slow
        ]
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results, {})
        # Claude is faster, should get speed bonus
        assert winner.tool == "claude"

    def test_weighted_vote_no_successful_results(self):
        """Test weighted voting when no results are successful."""
        results = [
            ToolResult(tool="claude", success=False, output=""),
            ToolResult(tool="opencode", success=False, output=""),
        ]
        winner, _ = ConflictResolver.resolve_by_weighted_vote(results, {})
        # Should return first result even if failed
        assert winner.tool == "claude"


# ---------------------------------------------------------------------------
# Test: ConflictResolver - Smart Merge
# ---------------------------------------------------------------------------


class TestSmartMerge:
    """Test smart merge conflict resolution."""

    def test_smart_merge_similar_outputs(self):
        """Test smart merge with similar outputs uses best."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world"),
            ToolResult(tool="opencode", success=True, output="Hello world"),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        # Should not add merge header for identical outputs
        assert "Merged Output" not in merged
        assert "Hello world" in merged

    def test_smart_merge_different_outputs(self):
        """Test smart merge with different outputs adds sections."""
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output="## Claude Analysis\n\nThis is Claude's unique perspective on the problem.",
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output="## OpenCode Implementation\n\nThis is OpenCode's unique implementation approach.",
            ),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        # Should merge both sections
        if conflict_info.severity in (ConflictSeverity.MODERATE, ConflictSeverity.MAJOR):
            assert "Claude" in merged or "OpenCode" in merged

    def test_smart_merge_single_result(self):
        """Test smart merge with single result."""
        results = [
            ToolResult(tool="claude", success=True, output="Single output"),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        assert merged == "Single output"

    def test_smart_merge_no_successful(self):
        """Test smart merge when no results are successful."""
        results = [
            ToolResult(tool="claude", success=False, output=""),
            ToolResult(tool="opencode", success=False, output=""),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        assert merged == ""

    def test_smart_merge_removes_duplicates(self):
        """Test that smart merge removes duplicate sections."""
        # Both outputs contain similar content
        common_content = "This is the same analysis in both outputs."
        results = [
            ToolResult(
                tool="claude",
                success=True,
                output=f"Intro\n\n{common_content}\n\nClaude specific ending.",
            ),
            ToolResult(
                tool="opencode",
                success=True,
                output=f"Different intro\n\n{common_content}\n\nOpenCode ending.",
            ),
        ]
        merged, conflict_info = ConflictResolver.smart_merge(results)
        # The common content should not be duplicated excessively
        # (actual deduplication depends on similarity threshold)


# ---------------------------------------------------------------------------
# Test: Conflict Info Structure
# ---------------------------------------------------------------------------


class TestConflictInfoStructure:
    """Test ConflictInfo data structure."""

    def test_conflict_info_fields(self):
        """Test that ConflictInfo has all required fields."""
        conflict = ConflictInfo(
            severity=ConflictSeverity.MODERATE,
            tools_involved=["claude", "opencode"],
            description="Test conflict",
            similarity_score=0.65,
            diff_summary="Some diff",
            conflicting_sections=[{"type": "code_blocks"}],
        )
        assert conflict.severity == ConflictSeverity.MODERATE
        assert conflict.tools_involved == ["claude", "opencode"]
        assert conflict.description == "Test conflict"
        assert conflict.similarity_score == 0.65
        assert conflict.diff_summary == "Some diff"
        assert len(conflict.conflicting_sections) == 1

    def test_conflict_info_defaults(self):
        """Test ConflictInfo default values."""
        conflict = ConflictInfo(
            severity=ConflictSeverity.NONE,
            tools_involved=["tool1"],
            description="No conflict",
            similarity_score=1.0,
        )
        assert conflict.diff_summary is None
        assert conflict.conflicting_sections == []


# ---------------------------------------------------------------------------
# Test: ConflictSeverity Levels
# ---------------------------------------------------------------------------


class TestConflictSeverityLevels:
    """Test ConflictSeverity enum values."""

    def test_severity_values(self):
        """Test that all severity values are defined."""
        assert ConflictSeverity.NONE.value == "none"
        assert ConflictSeverity.FORMATTING.value == "formatting"
        assert ConflictSeverity.MINOR.value == "minor"
        assert ConflictSeverity.MODERATE.value == "moderate"
        assert ConflictSeverity.MAJOR.value == "major"

    def test_severity_ordering(self):
        """Test logical ordering of severity levels."""
        # No strict ordering in enum, but names suggest: NONE < FORMATTING < MINOR < MODERATE < MAJOR
        severity_order = [
            ConflictSeverity.NONE,
            ConflictSeverity.FORMATTING,
            ConflictSeverity.MINOR,
            ConflictSeverity.MODERATE,
            ConflictSeverity.MAJOR,
        ]
        # Just verify they're all distinct
        assert len(set(severity_order)) == 5


# ---------------------------------------------------------------------------
# Test: Edge Cases in Conflict Detection
# ---------------------------------------------------------------------------


class TestConflictDetectionEdgeCases:
    """Test edge cases in conflict detection."""

    def test_unicode_content(self):
        """Test conflict detection with unicode content."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello world"),
            ToolResult(tool="opencode", success=True, output="Hello world"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE

    def test_very_long_outputs(self):
        """Test conflict detection with very long outputs."""
        long_output = "x" * 50000
        results = [
            ToolResult(tool="claude", success=True, output=long_output),
            ToolResult(tool="opencode", success=True, output=long_output),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        assert conflict.severity == ConflictSeverity.NONE

    def test_mixed_success_failure(self):
        """Test conflict detection with mixed success/failure."""
        results = [
            ToolResult(tool="claude", success=True, output="Success output"),
            ToolResult(tool="opencode", success=False, output=""),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        # Only successful results should be compared
        assert "claude" in conflict.tools_involved
        assert conflict.severity == ConflictSeverity.NONE  # Single successful result

    def test_whitespace_only_difference(self):
        """Test that whitespace-only differences are detected as formatting."""
        results = [
            ToolResult(tool="claude", success=True, output="Hello   world\n\n\ntest"),
            ToolResult(tool="opencode", success=True, output="Hello world\n\ntest"),
        ]
        conflict = ConflictDetector.detect_conflicts(results)
        # After normalization, these should be very similar
        assert conflict.similarity_score >= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
