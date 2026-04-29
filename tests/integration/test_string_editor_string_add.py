"""Integration tests for string_add (STRING-004).

Mirrors ROM src/string.c:121-286 — the per-line OLC editor input dispatcher.
Called by the game loop whenever session.string_edit is not None.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from mud.olc.editor_state import EditorMode, StringEdit
from mud.utils.string_editor import string_add

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_session(
    buffer: str = "",
    on_commit: Any = None,
    max_length: int = 4604,
    editor_mode: EditorMode = EditorMode.NONE,
) -> MagicMock:
    """Create a minimal fake Session with string_edit plumbing."""
    session = MagicMock()
    session.string_edit = StringEdit(
        buffer=buffer,
        on_commit=on_commit,
        max_length=max_length,
    )
    session.editor_mode = editor_mode
    return session


# ---------------------------------------------------------------------------
# 1. Normal line append
# ---------------------------------------------------------------------------


def test_normal_line_appended_to_buffer():
    """Normal line is appended to buffer with \\n\\r suffix; returns None."""
    session = make_session(buffer="existing\n\r")
    result = string_add(session, "new line")
    assert result is None
    assert session.string_edit.buffer == "existing\n\rnew line\n\r"


def test_normal_line_append_to_empty_buffer():
    """Appending to an empty buffer works correctly."""
    session = make_session(buffer="")
    result = string_add(session, "first line")
    assert result is None
    assert session.string_edit.buffer == "first line\n\r"


# ---------------------------------------------------------------------------
# 2. Tilde smashing
# ---------------------------------------------------------------------------


def test_tildes_in_normal_line_are_smashed():
    """Tildes inside a normal line are replaced with '-' before appending."""
    session = make_session(buffer="")
    result = string_add(session, "hello~world")
    assert result is None
    # tilde smashed to '-'
    assert "~" not in session.string_edit.buffer
    assert "hello-world\n\r" in session.string_edit.buffer


# ---------------------------------------------------------------------------
# 3. Termination — '~' and '@'
# ---------------------------------------------------------------------------


def test_at_terminator_calls_on_commit_and_clears_state():
    """@ terminates editing: on_commit is called with current buffer, string_edit cleared."""
    committed: list[str] = []
    session = make_session(buffer="some text\n\r", on_commit=committed.append)
    string_add(session, "@")
    assert session.string_edit is None
    assert committed == ["some text\n\r"]


def test_tilde_terminator_calls_on_commit_and_clears_state():
    """~ terminates editing (checked before smash): on_commit called, string_edit cleared.

    ROM src/string.c:128 smashes tildes BEFORE the terminator check at line 230,
    making ~ dead code at runtime. Python port checks terminator first (pragmatic
    deviation from ROM bug). Documented per audit Phase 4.
    """
    committed: list[str] = []
    session = make_session(buffer="text\n\r", on_commit=committed.append)
    string_add(session, "~")
    assert session.string_edit is None
    assert committed == ["text\n\r"]


def test_terminator_with_no_on_commit_does_not_raise():
    """@ with on_commit=None clears state without error."""
    session = make_session(buffer="text\n\r", on_commit=None)
    string_add(session, "@")
    assert session.string_edit is None


def test_terminator_on_commit_not_called_if_none():
    """on_commit=None: no call attempt."""
    session = make_session(buffer="text\n\r", on_commit=None)
    string_add(session, "@")  # should not raise
    assert session.string_edit is None


# ---------------------------------------------------------------------------
# 4. .c — clear
# ---------------------------------------------------------------------------


def test_dot_c_clears_buffer():
    """'.c' clears the buffer and returns 'String cleared.\\n\\r'."""
    session = make_session(buffer="some text\n\r")
    result = string_add(session, ".c")
    assert result == "String cleared.\n\r"
    assert session.string_edit.buffer == ""
    # Still in edit mode
    assert session.string_edit is not None


def test_dot_c_then_terminate_on_commit_sees_empty_buffer():
    """After .c the buffer is empty; on_commit should receive empty string on termination."""
    committed: list[str] = []
    session = make_session(buffer="old text\n\r", on_commit=committed.append)
    string_add(session, ".c")
    string_add(session, "@")
    assert committed == [""]


# ---------------------------------------------------------------------------
# 5. .s — show
# ---------------------------------------------------------------------------


def test_dot_s_returns_header_and_numlines_listing():
    """'.s' returns 'String so far:\\n\\r' followed by numlines listing."""
    session = make_session(buffer="alpha\n\r")
    result = string_add(session, ".s")
    assert result is not None
    assert result.startswith("String so far:\n\r")
    assert " 1. alpha\n\r" in result


def test_dot_s_does_not_modify_buffer():
    """'.s' is read-only — buffer unchanged."""
    session = make_session(buffer="alpha\n\r")
    string_add(session, ".s")
    assert session.string_edit.buffer == "alpha\n\r"


# ---------------------------------------------------------------------------
# 6. .r — replace
# ---------------------------------------------------------------------------


def test_dot_r_replaces_first_occurrence():
    """'.r' replaces first occurrence of old with new; returns confirmation."""
    session = make_session(buffer="foo bar foo\n\r")
    result = string_add(session, ".r 'foo' 'baz'")
    assert result is not None
    assert "'foo' replaced with 'baz'.\n\r" in result
    # Only first occurrence replaced
    assert session.string_edit.buffer == "baz bar foo\n\r"


def test_dot_r_missing_old_arg_returns_usage():
    """'.r' with no old string returns the usage message (mirrors ROM line 161-162)."""
    session = make_session(buffer="some text\n\r")
    result = string_add(session, ".r")
    assert result == 'usage:  .r "old string" "new string"\n\r'


def test_dot_r_empty_new_arg_deletes_old():
    """'.r' with empty new arg is valid — deletes the old substring."""
    session = make_session(buffer="hello world\n\r")
    string_add(session, ".r 'hello ' ''")
    # arg3 is empty — replaces with "", effectively deletes
    assert session.string_edit.buffer == "world\n\r"


# ---------------------------------------------------------------------------
# 7. .f — format
# ---------------------------------------------------------------------------


def test_dot_f_formats_buffer():
    """'.f' runs format_string on buffer; returns 'String formatted.\\n\\r'."""
    session = make_session(buffer="hello world\n\r")
    result = string_add(session, ".f")
    assert result == "String formatted.\n\r"
    # buffer is now format_string'd (sentence capitalized at minimum)
    assert "Hello world" in session.string_edit.buffer


# ---------------------------------------------------------------------------
# 8. .h — help
# ---------------------------------------------------------------------------


def test_dot_h_returns_help_text_with_all_commands():
    """'.h' returns help text mentioning all dot-commands."""
    session = make_session(buffer="")
    result = string_add(session, ".h")
    assert result is not None
    for cmd in (".r", ".h", ".s", ".f", ".c", ".ld", ".li", ".lr", "@"):
        assert cmd in result, f"Expected {cmd!r} in .h output"


# ---------------------------------------------------------------------------
# 9. .ld — line delete
# ---------------------------------------------------------------------------


def test_dot_ld_deletes_line():
    """'.ld 2' removes line 2 from the buffer; returns 'Line deleted.\\n\\r'."""
    session = make_session(buffer="line1\n\rline2\n\rline3\n\r")
    result = string_add(session, ".ld 2")
    assert result == "Line deleted.\n\r"
    assert "line2" not in session.string_edit.buffer
    assert "line1\n\r" in session.string_edit.buffer
    assert "line3\n\r" in session.string_edit.buffer


# ---------------------------------------------------------------------------
# 10. .li — line insert
# ---------------------------------------------------------------------------


def test_dot_li_inserts_line():
    """'.li 2 inserted line' inserts text at line 2; returns 'Line inserted.\\n\\r'."""
    session = make_session(buffer="line1\n\rline3\n\r")
    result = string_add(session, ".li 2 inserted line")
    assert result == "Line inserted.\n\r"
    lines = session.string_edit.buffer.split("\n\r")
    # After split: ['line1', 'inserted line', 'line3', '']
    assert lines[0] == "line1"
    assert lines[1] == "inserted line"
    assert lines[2] == "line3"


def test_dot_li_with_multiword_text_inserts_full_remainder():
    """'.li' uses the raw remainder after arg2, so multi-word text is preserved."""
    session = make_session(buffer="line1\n\rline3\n\r")
    result = string_add(session, ".li 2 some text with spaces")
    assert result == "Line inserted.\n\r"
    assert "some text with spaces" in session.string_edit.buffer


# ---------------------------------------------------------------------------
# 11. .lr — line replace
# ---------------------------------------------------------------------------


def test_dot_lr_replaces_line():
    """'.lr 2 replaced line' replaces line 2; returns 'Line replaced.\\n\\r'."""
    session = make_session(buffer="line1\n\rline2\n\rline3\n\r")
    result = string_add(session, ".lr 2 replaced line")
    assert result == "Line replaced.\n\r"
    assert "line2" not in session.string_edit.buffer
    assert "replaced line" in session.string_edit.buffer
    assert "line1\n\r" in session.string_edit.buffer
    assert "line3\n\r" in session.string_edit.buffer


# ---------------------------------------------------------------------------
# 12. Unknown dot-command
# ---------------------------------------------------------------------------


def test_unknown_dot_command_returns_error():
    """An unknown dot-command returns the SEdit error message."""
    session = make_session(buffer="")
    result = string_add(session, ".x")
    assert result == "SEdit:  Invalid dot command.\n\r"


# ---------------------------------------------------------------------------
# 13. Length cap
# ---------------------------------------------------------------------------


def test_length_cap_rejects_over_length_line():
    """If buffer + line >= max_length, the line is rejected with an error message.

    ROM src/string.c:271 forces pString = NULL on overflow, so session.string_edit
    will be None after this call (not an observable buffer length).
    """
    session = make_session(buffer="x" * 4600, max_length=4604)
    # 4600 + 10 >= 4604 → overflow
    result = string_add(session, "0123456789")
    assert result is not None
    assert "too long" in result.lower()
    # ROM forces exit from editor (pString = NULL)
    assert session.string_edit is None


def test_length_cap_forces_exit_from_edit_mode():
    """On overflow ROM forces exit from editor (pString = NULL; mirrors ROM src/string.c:271)."""
    session = make_session(buffer="x" * 4600, max_length=4604)
    on_commit = MagicMock()
    session.string_edit.on_commit = on_commit
    string_add(session, "0123456789")
    # ROM sets pString = NULL — exit edit mode; on_commit NOT called
    assert session.string_edit is None
    on_commit.assert_not_called()


def test_line_exactly_at_cap_is_rejected():
    """Buffer + line == max_length (>= boundary) is rejected."""
    # 4600 + 4 == 4604 >= 4604 → overflow
    session = make_session(buffer="x" * 4600, max_length=4604)
    result = string_add(session, "abcd")
    assert result is not None
    assert "too long" in result.lower()
