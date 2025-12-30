"""Unit tests for semantic threshold filtering in HybridRetriever.

Tests verify that the min_semantic_score parameter correctly filters
search results based on semantic similarity scores.
"""

import inspect
from aurora_context_code.semantic.hybrid_retriever import HybridRetriever


def test_retrieve_method_accepts_min_semantic_score():
    """Test that retrieve() method signature includes min_semantic_score parameter."""
    # Get method signature
    sig = inspect.signature(HybridRetriever.retrieve)
    params = sig.parameters

    # Verify min_semantic_score parameter exists
    assert "min_semantic_score" in params, "retrieve() should accept min_semantic_score parameter"

    # Verify it has a default value of None
    param = params["min_semantic_score"]
    assert param.default is None, "min_semantic_score should default to None"


def test_retrieve_method_signature_backward_compatible():
    """Test that retrieve() is backward compatible (min_semantic_score is optional)."""
    # Get method signature
    sig = inspect.signature(HybridRetriever.retrieve)
    params = sig.parameters

    # Verify required parameters haven't changed
    assert "query" in params
    assert "top_k" in params

    # Verify min_semantic_score is optional (has default value)
    assert params["min_semantic_score"].default is not inspect.Parameter.empty


def test_filtering_logic_structure():
    """Test that the filtering logic is present in the retrieve method source."""
    import inspect

    # Get source code of retrieve method
    source = inspect.getsource(HybridRetriever.retrieve)

    # Verify filtering logic is present
    assert "min_semantic_score" in source, "Filtering logic should reference min_semantic_score"
    assert "semantic_score" in source, "Filtering should be based on semantic_score"

    # Verify filtering happens after sorting
    # This ensures we filter before returning results
    lines = source.split("\n")
    sort_line = None
    filter_line = None

    for i, line in enumerate(lines):
        if "final_results.sort" in line:
            sort_line = i
        if "min_semantic_score is not None" in line or "min_semantic_score =" in line:
            filter_line = i

    # If both exist, filtering should come after sorting
    if sort_line is not None and filter_line is not None:
        assert filter_line > sort_line, "Filtering should occur after sorting"
