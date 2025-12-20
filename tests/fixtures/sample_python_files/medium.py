"""
Medium complexity Python file for testing class and method extraction.
"""

import os
from typing import Optional


class Calculator:
    """A simple calculator class."""

    def __init__(self, initial_value: float = 0.0):
        """Initialize calculator with an initial value."""
        self.value = initial_value

    def add(self, x: float) -> float:
        """Add a number to the current value."""
        self.value += x
        return self.value

    def subtract(self, x: float) -> float:
        """Subtract a number from the current value."""
        self.value -= x
        return self.value

    def multiply(self, x: float) -> float:
        """Multiply the current value by a number."""
        self.value *= x
        return self.value

    def divide(self, x: float) -> Optional[float]:
        """
        Divide the current value by a number.

        Returns None if division by zero is attempted.
        """
        if x == 0:
            return None
        self.value /= x
        return self.value

    def reset(self) -> None:
        """Reset the calculator to zero."""
        self.value = 0.0


def process_file(path: str) -> bool:
    """Process a file if it exists."""
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
            return len(content) > 0
    return False
