"""Integration tests for string_append (STRING-002).

Mirrors ROM src/string.c:66-86. Tests entering APPEND mode.
"""

from __future__ import annotations

from mud.olc.editor_state import MAX_STRING_EDIT_LENGTH, StringEdit
from mud.utils.string_editor import string_append


def test_string_append_returns_banner():
    """string_append returns the editor banner matching ROM verbatim."""
    string_edit_obj = StringEdit()
    banner = string_append(string_edit_obj, "")
    # ROM sends 4 banner lines via send_to_char calls
    expected_lines = [
        "-=======- Entering APPEND Mode -========-",
        "    Type .h on a new line for help",
        " Terminate with a ~ or @ on a blank line.",
        "-=======================================-",
    ]
    for line in expected_lines:
        assert line in banner


def test_string_append_banner_exact_text():
    """Banner matches ROM src/string.c:68-71 exactly."""
    string_edit_obj = StringEdit()
    banner = string_append(string_edit_obj, "")
    # The exact banner from ROM (with \n\r line endings)
    expected_start = (
        "-=======- Entering APPEND Mode -========-\n\r"
        "    Type .h on a new line for help\n\r"
        " Terminate with a ~ or @ on a blank line.\n\r"
        "-=======================================-\n\r"
    )
    assert banner.startswith(expected_start)


def test_string_append_preserves_existing_buffer():
    """string_append preserves the existing string (APPEND, not EDIT mode)."""
    existing = "line1\n\rline2\n\r"
    string_edit_obj = StringEdit()
    string_append(string_edit_obj, existing)
    # Buffer should be set to existing content
    assert string_edit_obj.buffer == existing


def test_string_append_empty_string_produces_empty_numlines():
    """string_append with empty string includes empty numlines section."""
    string_edit_obj = StringEdit()
    result = string_append(string_edit_obj, "")
    # numlines("") returns "", so result is just the banner
    expected_start = (
        "-=======- Entering APPEND Mode -========-\n\r"
        "    Type .h on a new line for help\n\r"
        " Terminate with a ~ or @ on a blank line.\n\r"
        "-=======================================-\n\r"
    )
    assert result == expected_start


def test_string_append_with_single_line():
    """string_append with single line includes numline listing."""
    string_edit_obj = StringEdit()
    current = "hello world"
    result = string_append(string_edit_obj, current)
    # numlines() on "hello world" (no \n\r) produces " 1. hello world\n\r"
    assert " 1. hello world\n\r" in result
    assert string_edit_obj.buffer == current


def test_string_append_with_multiple_lines():
    """string_append with multiple lines includes full numlines listing."""
    string_edit_obj = StringEdit()
    current = "first\n\rsecond\n\rthird\n\r"
    result = string_append(string_edit_obj, current)
    # numlines should produce numbered lines
    assert " 1. first\n\r" in result
    assert " 2. second\n\r" in result
    assert " 3. third\n\r" in result
    assert string_edit_obj.buffer == current


def test_string_append_preserves_max_length():
    """string_append preserves max_length parameter."""
    max_len = 3000
    string_edit_obj = StringEdit(max_length=max_len)
    string_append(string_edit_obj, "test")
    assert string_edit_obj.max_length == max_len


def test_string_append_defaults_max_length():
    """string_append defaults max_length to MAX_STRING_EDIT_LENGTH."""
    string_edit_obj = StringEdit()
    string_append(string_edit_obj, "test")
    assert string_edit_obj.max_length == MAX_STRING_EDIT_LENGTH


def test_string_append_with_on_commit_callback():
    """string_append preserves on_commit callback."""
    called = []

    def on_commit(text: str) -> None:
        called.append(text)

    string_edit_obj = StringEdit(on_commit=on_commit)
    string_append(string_edit_obj, "existing text")
    assert string_edit_obj.on_commit is on_commit
