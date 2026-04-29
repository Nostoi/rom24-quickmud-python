"""Integration tests for string_lineadd (STRING-010).

Mirrors ROM src/string.c:607-645. Tests the line-insertion function.
"""

from __future__ import annotations

from mud.utils.string_editor import string_lineadd


def test_lineadd_insert_at_beginning():
    """Insert as line 1 when string is empty."""
    result = string_lineadd("", "first", 1)
    assert result == "first\n\r"


def test_lineadd_insert_before_existing():
    """Insert line 1 in front of existing content."""
    input_str = "b\n\rc\n\r"
    result = string_lineadd(input_str, "a", 1)
    assert result == "a\n\rb\n\rc\n\r"


def test_lineadd_insert_middle():
    """Insert as line 2 between existing lines."""
    input_str = "a\n\rc\n\r"
    result = string_lineadd(input_str, "b", 2)
    assert result == "a\n\rb\n\rc\n\r"


def test_lineadd_insert_after_all():
    """Insert as line 3 after all existing lines."""
    input_str = "a\n\rb\n\r"
    result = string_lineadd(input_str, "c", 3)
    assert result == "a\n\rb\n\rc\n\r"


def test_lineadd_insert_past_end():
    """Insert at line number past the end is a no-op (never reached)."""
    input_str = "a\n\rb\n\r"
    result = string_lineadd(input_str, "c", 99)
    # Per ROM behavior, if line number is never reached, insertion doesn't happen
    assert result == "a\n\rb\n\r"


def test_lineadd_empty_newstr():
    """Inserting an empty string still adds the \n\r line-ending."""
    input_str = "a\n\rb\n\r"
    result = string_lineadd(input_str, "", 2)
    assert result == "a\n\r\n\rb\n\r"


def test_lineadd_preserves_endings():
    """Line endings are preserved as \n\r throughout."""
    input_str = "line1\n\rline2\n\r"
    result = string_lineadd(input_str, "inserted", 2)
    # Result should have 3 lines, each ending with \n\r
    assert result.count("\n\r") == 3


def test_lineadd_multiple_sequential():
    """Adding multiple lines sequentially."""
    s = "a\n\rd\n\r"
    s = string_lineadd(s, "b", 2)  # Insert at line 2
    assert s == "a\n\rb\n\rd\n\r"
    s = string_lineadd(s, "c", 3)  # Insert at line 3
    assert s == "a\n\rb\n\rc\n\rd\n\r"


def test_lineadd_at_one_when_empty():
    """Inserting at line 1 in empty string."""
    result = string_lineadd("", "only", 1)
    assert result == "only\n\r"


def test_lineadd_zero_line_number():
    """Inserting at line 0 (invalid) is a no-op."""
    # ROM behavior: cnt starts at 1, so cnt == line at line 0 is never true
    # The line never matches, so insertion never happens
    input_str = "a\n\rb\n\r"
    result = string_lineadd(input_str, "x", 0)
    # Based on ROM logic, line 0 never matches, so no insertion
    assert result == input_str
