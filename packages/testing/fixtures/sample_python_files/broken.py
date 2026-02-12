"""
Broken Python file with syntax errors for testing error handling.
"""


def valid_function():
    """This function is valid."""
    return "valid"


def broken_function(:  # Syntax error: missing parameter name
    """This function has a syntax error."""
    return "broken"


class BrokenClass
    """Missing colon after class declaration."""

    def method(self):
        return "broken"


# Unclosed string literal
message = "This string is never closed

def another_function():
    """Function after syntax error."""
    return "another"
