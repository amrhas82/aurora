"""Unit tests for type abbreviation mapping.

Tests the _get_type_abbreviation() helper function in memory.py
that maps full type names to abbreviated forms for display.
"""


def _get_type_abbreviation(element_type: str) -> str:
    """Get abbreviated type name for display.

    This is a test stub - will be implemented in memory.py.

    Args:
        element_type: Full type name (e.g., "function", "knowledge")

    Returns:
        Abbreviated type (e.g., "func", "know")

    """
    # This is just a stub for testing - real implementation will be in memory.py
    raise NotImplementedError("Stub - implement in memory.py")


def test_get_type_abbreviation_code_types():
    """Test abbreviation mapping for code types."""
    from aurora_cli.commands.memory import _get_type_abbreviation

    assert _get_type_abbreviation("function") == "func"
    assert _get_type_abbreviation("method") == "meth"
    assert _get_type_abbreviation("class") == "class"
    assert _get_type_abbreviation("code") == "code"


def test_get_type_abbreviation_noncode_types():
    """Test abbreviation mapping for non-code types."""
    from aurora_cli.commands.memory import _get_type_abbreviation

    assert _get_type_abbreviation("reasoning") == "reas"
    assert _get_type_abbreviation("knowledge") == "know"
    assert _get_type_abbreviation("document") == "doc"


def test_get_type_abbreviation_unknown():
    """Test abbreviation for unknown types."""
    from aurora_cli.commands.memory import _get_type_abbreviation

    assert _get_type_abbreviation("unknown") == "unk"
    assert _get_type_abbreviation("invalid_type") == "unk"
    assert _get_type_abbreviation("foo") == "unk"


def test_get_type_abbreviation_case_insensitive():
    """Test that abbreviation is case-insensitive."""
    from aurora_cli.commands.memory import _get_type_abbreviation

    assert _get_type_abbreviation("Function") == "func"
    assert _get_type_abbreviation("KNOWLEDGE") == "know"
    assert _get_type_abbreviation("MeThOd") == "meth"
    assert _get_type_abbreviation("CLASS") == "class"
