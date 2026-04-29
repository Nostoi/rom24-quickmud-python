"""Integration tests for numlines (STRING-012).

Mirrors ROM src/string.c:676-692. Tests the line-numbering formatter.
"""

from __future__ import annotations

from mud.utils.string_editor import numlines


def test_numlines_single_line():
    """Single line is numbered as ' 1. '."""
    result = numlines("alpha\n\r")
    assert result == " 1. alpha\n\r"


def test_numlines_multiple_lines():
    """Multiple lines are numbered sequentially, 1-indexed, %2d format."""
    input_str = "alpha\n\rbravo\n\r"
    expected = " 1. alpha\n\r 2. bravo\n\r"
    assert numlines(input_str) == expected


def test_numlines_three_lines():
    """Three lines with proper 1-indexing."""
    input_str = "first\n\rsecond\n\rthird\n\r"
    expected = " 1. first\n\r 2. second\n\r 3. third\n\r"
    assert numlines(input_str) == expected


def test_numlines_double_digit_line_number():
    """Line 10+ uses %2d format (right-aligned 2-char width)."""
    lines = [f"line{i}" for i in range(1, 12)]
    input_str = "\n\r".join(lines) + "\n\r"
    result = numlines(input_str)
    # Line 10 should be "10. " (no leading space)
    assert "10. line10\n\r" in result
    # Line 9 should be " 9. " (one leading space for alignment)
    assert " 9. line9\n\r" in result


def test_numlines_empty_lines():
    """Empty lines are still numbered."""
    input_str = "text\n\r\n\rmore\n\r"
    result = numlines(input_str)
    # Second line is empty but still gets numbered
    assert " 1. text\n\r" in result
    assert " 2. \n\r" in result
    assert " 3. more\n\r" in result


def test_numlines_empty_string():
    """Empty string produces no output."""
    assert numlines("") == ""


def test_numlines_single_line_no_ending():
    """Single line without trailing line-ending."""
    result = numlines("text")
    # merc_getline returns "text" as-is if no \n found
    assert result == " 1. text\n\r"
