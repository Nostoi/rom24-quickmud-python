"""Integration tests for string_edit (STRING-001).

Mirrors ROM src/string.c:38-57. Tests entering EDIT mode.
"""

from __future__ import annotations

from mud.olc.editor_state import MAX_STRING_EDIT_LENGTH, StringEdit
from mud.utils.string_editor import string_edit


def test_string_edit_returns_banner():
    """string_edit returns the editor banner matching ROM verbatim."""
    banner = string_edit(StringEdit())
    # ROM sends 4 lines via send_to_char calls
    expected_lines = [
        "-========- Entering EDIT Mode -=========-",
        "    Type .h on a new line for help",
        " Terminate with a ~ or @ on a blank line.",
        "-=======================================-",
    ]
    for line in expected_lines:
        assert line in banner


def test_string_edit_banner_exact_text():
    """Banner matches ROM src/string.c:40-43 exactly."""
    banner = string_edit(StringEdit())
    # The exact banner from ROM (with \n\r line endings)
    expected = (
        "-========- Entering EDIT Mode -=========-\n\r"
        "    Type .h on a new line for help\n\r"
        " Terminate with a ~ or @ on a blank line.\n\r"
        "-=======================================-\n\r"
    )
    assert banner == expected


def test_string_edit_initializes_empty_buffer():
    """string_edit initializes buffer to empty string."""
    string_edit_obj = StringEdit()
    string_edit(string_edit_obj)
    assert string_edit_obj.buffer == ""


def test_string_edit_preserves_max_length():
    """string_edit preserves max_length parameter."""
    max_len = 2000
    string_edit_obj = StringEdit(max_length=max_len)
    string_edit(string_edit_obj)
    assert string_edit_obj.max_length == max_len


def test_string_edit_defaults_max_length():
    """string_edit defaults max_length to MAX_STRING_EDIT_LENGTH."""
    string_edit_obj = StringEdit()
    string_edit(string_edit_obj)
    assert string_edit_obj.max_length == MAX_STRING_EDIT_LENGTH


def test_string_edit_with_on_commit_callback():
    """string_edit preserves on_commit callback."""
    called = []

    def on_commit(text: str) -> None:
        called.append(text)

    string_edit_obj = StringEdit(on_commit=on_commit)
    string_edit(string_edit_obj)
    assert string_edit_obj.on_commit is on_commit
