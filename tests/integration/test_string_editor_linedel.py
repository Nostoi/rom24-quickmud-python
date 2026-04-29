"""Integration tests for string_linedel (STRING-009).

Mirrors ROM src/string.c:574-605. Tests the line-deletion function.
"""

from __future__ import annotations

from mud.utils.string_editor import string_linedel


def test_linedel_first_of_three():
    """Deleting line 1 from a three-line string."""
    input_str = "a\n\rb\n\rc\n\r"
    result = string_linedel(input_str, 1)
    assert result == "b\n\rc\n\r"


def test_linedel_middle_of_three():
    """Deleting line 2 from a three-line string."""
    input_str = "a\n\rb\n\rc\n\r"
    result = string_linedel(input_str, 2)
    assert result == "a\n\rc\n\r"


def test_linedel_last_of_three():
    """Deleting line 3 from a three-line string."""
    input_str = "a\n\rb\n\rc\n\r"
    result = string_linedel(input_str, 3)
    assert result == "a\n\rb\n\r"


def test_linedel_only_line():
    """Deleting the only line leaves empty string."""
    input_str = "single\n\r"
    result = string_linedel(input_str, 1)
    assert result == ""


def test_linedel_out_of_range_low():
    """Deleting line 0 is a no-op."""
    input_str = "a\n\rb\n\r"
    result = string_linedel(input_str, 0)
    assert result == "a\n\rb\n\r"


def test_linedel_out_of_range_high():
    """Deleting a line number beyond the end is a no-op."""
    input_str = "a\n\rb\n\r"
    result = string_linedel(input_str, 10)
    assert result == "a\n\rb\n\r"


def test_linedel_preserves_line_endings():
    """Line endings are preserved as \n\r throughout."""
    input_str = "line1\n\rline2\n\rline3\n\r"
    result = string_linedel(input_str, 2)
    # Ensure \n\r endings are intact on both remaining lines
    assert "\n\r" in result
    assert result.count("\n\r") == 2


def test_linedel_multiple_sequential():
    """Deleting multiple lines one at a time."""
    s = "a\n\rb\n\rc\n\rd\n\r"
    s = string_linedel(s, 2)  # Remove "b"
    assert s == "a\n\rc\n\rd\n\r"
    s = string_linedel(s, 2)  # Remove "c" (now at index 2)
    assert s == "a\n\rd\n\r"
