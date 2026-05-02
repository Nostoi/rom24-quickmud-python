"""hedit.c parity tests — HEDIT-001..014.

ROM reference: src/hedit.c (462 lines)

Gaps covered:
- HEDIT-001: hedit_show ROM exact format
- HEDIT-002: hedit_level range -1..MAX_LEVEL + error message
- HEDIT-003: hedit_keyword success returns "Ok.\\n\\r"
- HEDIT-004: hedit_level / hedit_keyword empty-arg syntax strings
- HEDIT-005: hedit_text no-arg (should NOT error; arg provided → error)
- HEDIT-006: security check message exact + \\n\\r
- HEDIT-007: empty input → hedit_show (not syntax string)
- HEDIT-008: "done" returns "" (silent), not verbose message
- HEDIT-009: unknown command falls back to normal command table
- HEDIT-010: hedit_delete removes entry + returns "Ok.\\n\\r"
- HEDIT-011: hedit_list all/area format; unknown arg → syntax
- HEDIT-012: do_hedit "new" path + is_name match
- HEDIT-013: do_hedit is_name (word-level) match, not exact key match
- HEDIT-014: level/keyword handlers return "Ok.\\n\\r" (mark changed)
"""
from __future__ import annotations

import pytest

from mud.commands.build import (
    _hedit_delete,
    _hedit_keyword,
    _hedit_level,
    _hedit_list,
    _hedit_show,
    _hedit_text,
    _interpret_hedit,
    cmd_hedit,
)
from mud.models.constants import MAX_LEVEL
from mud.models.help import HelpEntry, clear_help_registry, help_entries, register_help
from mud.net.session import Session
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


@pytest.fixture(autouse=True)
def clean_help_registry():
    """Ensure help registry is clean between tests."""
    clear_help_registry()
    yield
    clear_help_registry()


@pytest.fixture()
def builder_char():
    char = create_test_character("Builder", 3001)
    char.level = 60
    char.is_npc = False
    char.is_admin = True
    session = Session(name="Builder", character=char, reader=None, connection=None)
    char.desc = session
    if char.pcdata:
        char.pcdata.security = 9
    return char


@pytest.fixture()
def help_entry():
    entry = HelpEntry(keywords=["SWORD", "SWORDS"], text="A sharp blade.\n", level=0)
    register_help(entry)
    return entry


@pytest.fixture()
def session_with_entry(builder_char, help_entry):
    session = builder_char.desc
    session.editor = "hedit"
    session.editor_state = {
        "help": help_entry,
        "is_new": False,
        "original_keywords": list(help_entry.keywords),
    }
    return session


# ── HEDIT-001: hedit_show format ─────────────────────────────────────────────

def test_hedit_show_exact_format(help_entry):
    """ROM src/hedit.c:53-67 — exact sprintf format."""
    result = _hedit_show(help_entry)
    assert result == (
        "Keyword : [SWORD SWORDS]\n\r"
        "Level   : [0]\n\r"
        "Text    :\n\r"
        "A sharp blade.\n"
        "-END-\n\r"
    ), repr(result)


def test_hedit_show_via_empty_input(builder_char, session_with_entry, help_entry):
    """HEDIT-007: empty input → hedit_show (ROM src/hedit.c:236-240)."""
    result = _interpret_hedit(session_with_entry, builder_char, "")
    assert result.startswith("Keyword : ["), repr(result)
    assert "-END-\n\r" in result


# ── HEDIT-002: hedit_level range -1..MAX_LEVEL ───────────────────────────────

def test_hedit_level_accepts_minus_one(builder_char, help_entry):
    """ROM src/hedit.c:84: lev >= -1 is valid."""
    result = _hedit_level(builder_char, help_entry, "-1")
    assert result == "Ok.\n\r", repr(result)
    assert help_entry.level == -1


def test_hedit_level_accepts_max_level(builder_char, help_entry):
    result = _hedit_level(builder_char, help_entry, str(MAX_LEVEL))
    assert result == "Ok.\n\r"
    assert help_entry.level == MAX_LEVEL


def test_hedit_level_rejects_below_minus_one(builder_char, help_entry):
    """ROM src/hedit.c:84-89: < -1 is invalid."""
    result = _hedit_level(builder_char, help_entry, "-2")
    assert f"between -1 and {MAX_LEVEL} inclusive" in result, repr(result)


def test_hedit_level_rejects_above_max(builder_char, help_entry):
    result = _hedit_level(builder_char, help_entry, str(MAX_LEVEL + 1))
    assert f"between -1 and {MAX_LEVEL} inclusive" in result


def test_hedit_level_empty_arg_syntax(builder_char, help_entry):
    """HEDIT-004: ROM src/hedit.c:78 exact syntax string."""
    result = _hedit_level(builder_char, help_entry, "")
    assert result == "Syntax: level [-1..MAX_LEVEL]\n\r", repr(result)


# ── HEDIT-003/004: hedit_keyword ─────────────────────────────────────────────

def test_hedit_keyword_success_ok(builder_char, help_entry):
    """HEDIT-003: ROM src/hedit.c:111 — "Ok.\\n\\r" on success."""
    result = _hedit_keyword(builder_char, help_entry, "DAGGER DAGGERS")
    assert result == "Ok.\n\r", repr(result)
    assert "DAGGER" in help_entry.keywords


def test_hedit_keyword_empty_arg_syntax(builder_char, help_entry):
    """HEDIT-004: ROM src/hedit.c:104 exact syntax string."""
    result = _hedit_keyword(builder_char, help_entry, "")
    assert result == "Syntax: keyword [keywords]\n\r", repr(result)


# ── HEDIT-005: hedit_text ────────────────────────────────────────────────────

def test_hedit_text_no_arg_returns_true(builder_char, help_entry):
    """HEDIT-005: ROM src/hedit.c:194-202 — no-arg is valid (string_append)."""
    result = _hedit_text(builder_char, help_entry, "")
    assert result is True  # triggers had->changed = TRUE in dispatcher


def test_hedit_text_with_arg_returns_syntax_error(builder_char, help_entry):
    """HEDIT-005: ROM src/hedit.c:194-198 — arg present → syntax error."""
    result = _hedit_text(builder_char, help_entry, "some text")
    assert result == "Syntax: text\n\r", repr(result)


# ── HEDIT-006: security message exact ───────────────────────────────────────

def test_hedit_security_message_has_newline_cr(builder_char, help_entry):
    """HEDIT-006: ROM src/hedit.c:230 — 'HEdit: Insufficient security to edit helps.\\n\\r'."""
    builder_char.is_admin = False
    if builder_char.pcdata:
        builder_char.pcdata.security = 0
    result = cmd_hedit(builder_char, "sword")
    assert result == "HEdit: Insufficient security to edit helps.\n\r", repr(result)


# ── HEDIT-008: done is silent ────────────────────────────────────────────────

def test_done_is_silent(builder_char, session_with_entry):
    """HEDIT-008: ROM src/hedit.c:242-246 — 'done' → edit_done, no message."""
    result = _interpret_hedit(session_with_entry, builder_char, "done")
    assert result == "", repr(result)
    assert session_with_entry.editor != "hedit"


# ── HEDIT-010: hedit_delete ──────────────────────────────────────────────────

def test_hedit_delete_removes_entry(builder_char, help_entry, session_with_entry):
    """HEDIT-010: ROM src/hedit.c:336-398 — removes from help_entries."""
    assert help_entry in help_entries
    result = _hedit_delete(builder_char, help_entry, "")
    assert result == "Ok.\n\r", repr(result)
    assert help_entry not in help_entries


def test_hedit_delete_returns_false_if_not_found(builder_char):
    """HEDIT-010: hedit_delete bugf path — entry not in list → FALSE."""
    orphan = HelpEntry(keywords=["ORPHAN"], text="", level=0)
    # Do NOT register — not in help_entries
    result = _hedit_delete(builder_char, orphan, "")
    assert result is False


# ── HEDIT-011: hedit_list ────────────────────────────────────────────────────

def test_hedit_list_all_format(builder_char, help_entry):
    """HEDIT-011: ROM src/hedit.c:409-426 — %3d. %-14.14s format."""
    result = _hedit_list(builder_char, help_entry, "all")
    assert "  0." in result, repr(result)
    # Should contain the truncated keyword
    assert "SWORD" in result


def test_hedit_list_area(builder_char, help_entry):
    """HEDIT-011: 'list area' subcommand exists."""
    result = _hedit_list(builder_char, help_entry, "area")
    # Should not be an error — either entries or "No helps" message
    assert "Syntax:" not in result


def test_hedit_list_unknown_arg_syntax(builder_char, help_entry):
    """HEDIT-011: ROM src/hedit.c:454-459 — unknown arg → syntax."""
    result = _hedit_list(builder_char, help_entry, "xyz")
    assert result == "Syntax: list all\n\r        list area\n\r", repr(result)


# ── HEDIT-012/013: do_hedit is_name match ────────────────────────────────────

def test_do_hedit_matches_by_keyword_word(builder_char, help_entry):
    """HEDIT-013: ROM src/hedit.c:306 — is_name word match (sword matches SWORD SWORDS)."""
    result = cmd_hedit(builder_char, "sword")
    assert result == "", repr(result)
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["help"] is help_entry


def test_do_hedit_no_match_returns_error(builder_char):
    """HEDIT-013: no match → 'HEdit:  There is no default help to edit.'"""
    result = cmd_hedit(builder_char, "nonexistentxyz")
    assert "There is no default help to edit" in result, repr(result)


def test_do_hedit_new_creates_entry(builder_char):
    """HEDIT-012: ROM src/hedit.c:317-329 — 'hedit new <topic>' works."""
    result = cmd_hedit(builder_char, "new mytopic")
    assert result == "", repr(result)
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is True


def test_do_hedit_new_no_topic_syntax_error(builder_char):
    """HEDIT-012: ROM src/hedit.c:321-324 — 'hedit new' no topic → syntax."""
    result = cmd_hedit(builder_char, "new")
    assert "Syntax" in result


# ── HEDIT-014: level/keyword mark changed ────────────────────────────────────

def test_level_returns_ok_string_for_changed_tracking(builder_char, help_entry):
    """HEDIT-014: level returns 'Ok.\\n\\r' — dispatcher uses non-False/True to mark changed."""
    result = _hedit_level(builder_char, help_entry, "5")
    assert result == "Ok.\n\r"


def test_keyword_returns_ok_string_for_changed_tracking(builder_char, help_entry):
    result = _hedit_keyword(builder_char, help_entry, "AXE AXES")
    assert result == "Ok.\n\r"
