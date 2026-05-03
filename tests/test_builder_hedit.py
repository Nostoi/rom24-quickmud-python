"""ROM-parity tests for cmd_hedit / cmd_hesave.

ROM reference: src/hedit.c (do_hedit lines 284-333, hedit dispatcher 205-260)

These tests verify the ROM-faithful implementation introduced in HEDIT-001..014.
All expected strings mirror the exact send_to_char() calls in ROM hedit.c.
"""
from __future__ import annotations

import json

import pytest

from mud.commands.build import cmd_hedit, cmd_hesave
from mud.models.constants import LEVEL_HERO
from mud.models.help import HelpEntry, clear_help_registry, help_entries, help_registry, register_help
from mud.net.session import Session


@pytest.fixture(autouse=True)
def clean_help_registry():
    """Clear help registry before and after each test."""
    clear_help_registry()
    yield
    clear_help_registry()


@pytest.fixture
def test_help_entry():
    """Create and register a test help entry."""
    entry = HelpEntry(keywords=["magic", "spells"], text="Magic requires mana and practice.", level=0)
    register_help(entry)
    return entry


@pytest.fixture
def builder_char():
    """Create a character with builder privileges (security=9)."""
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


# ── Entry-point: no args ─────────────────────────────────────────────────────

def test_hedit_requires_keyword(builder_char):
    """ROM src/hedit.c:284-286 — no arg → 'HEdit:  There is no default help to edit.'"""
    result = cmd_hedit(builder_char, "")
    assert "HEdit:  There is no default help to edit." in result


# ── Entry-point: 'new' subcommand ────────────────────────────────────────────

def test_hedit_new_without_topic_returns_syntax(builder_char):
    """ROM src/hedit.c:317-321 — 'new' alone → syntax error."""
    result = cmd_hedit(builder_char, "new")
    assert "Syntax: edit help new" in result


def test_hedit_new_with_topic_opens_editor(builder_char):
    """ROM src/hedit.c:317-329 — 'new <topic>' opens hedit session silently."""
    result = cmd_hedit(builder_char, "new sorcery")
    # ROM returns "" (no send_to_char) on successful open
    assert result == ""
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is True
    entry = builder_char.desc.editor_state["help"]
    assert "sorcery" in entry.keywords


# ── Entry-point: existing keyword ────────────────────────────────────────────

def test_hedit_existing_keyword_opens_editor(builder_char, test_help_entry):
    """ROM src/hedit.c:296-313 — matching keyword opens hedit session silently."""
    result = cmd_hedit(builder_char, "magic")
    assert result == ""
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is False
    assert builder_char.desc.editor_state["help"] is test_help_entry


def test_hedit_nonexistent_keyword_returns_no_default(builder_char):
    """ROM src/hedit.c:328-333 — no match → 'HEdit:  There is no default help to edit.'"""
    result = cmd_hedit(builder_char, "nosuchkeyword")
    assert "HEdit:  There is no default help to edit." in result


# ── In-session: empty input ───────────────────────────────────────────────────

def test_hedit_empty_in_session_shows_entry(builder_char, test_help_entry):
    """ROM src/hedit.c:236-240 — empty input while in session → hedit_show."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "")
    # ROM hedit_show format: "Keyword : [%s]\n\rLevel   : [%d]\n\rText    :\n\r%s-END-\n\r"
    assert "Keyword : [magic spells]" in result
    assert "Level   : [0]" in result
    assert "-END-" in result


# ── In-session: show ──────────────────────────────────────────────────────────

def test_hedit_show_command(builder_char, test_help_entry):
    """ROM src/hedit.c:53-67 — hedit_show exact format."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "show")
    assert "Keyword : [magic spells]" in result
    assert "Level   : [0]" in result
    assert "Magic requires mana" in result
    assert "-END-" in result


# ── In-session: keyword ───────────────────────────────────────────────────────

def test_hedit_keyword_command_sets_keywords(builder_char, test_help_entry):
    """ROM src/hedit.c:96-113 — keyword subcommand → Ok."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "keyword fire flames")
    assert result == "Ok.\n\r"
    assert builder_char.desc.editor_state["help"].keywords == ["fire", "flames"]


def test_hedit_keyword_requires_value(builder_char, test_help_entry):
    """ROM src/hedit.c:98-100 — no argument → Syntax error."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "keyword")
    assert "Syntax: keyword" in result


# ── In-session: level ─────────────────────────────────────────────────────────

def test_hedit_level_command_sets_level(builder_char, test_help_entry):
    """ROM src/hedit.c:69-94 — level <n> → Ok."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level 51")
    assert result == "Ok.\n\r"
    assert builder_char.desc.editor_state["help"].level == 51


def test_hedit_level_minus_one_allowed(builder_char, test_help_entry):
    """ROM src/hedit.c:69-94 — level -1 is a valid sentinel value."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level -1")
    assert result == "Ok.\n\r"
    assert builder_char.desc.editor_state["help"].level == -1


def test_hedit_level_requires_number(builder_char, test_help_entry):
    """ROM src/hedit.c:76-79 — non-numeric arg → Syntax error."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level abc")
    assert "Syntax:" in result


def test_hedit_level_out_of_range_rejected(builder_char, test_help_entry):
    """ROM src/hedit.c:80-83 — out-of-range level → bounds message."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level 9999")
    assert "HEdit" in result or "level" in result.lower()


# ── In-session: text ──────────────────────────────────────────────────────────

def test_hedit_text_with_no_arg_marks_changed(builder_char, test_help_entry):
    """ROM src/hedit.c:188-203 — text with no arg invokes string_append (Python: marks changed)."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "text")
    # ROM string_append path: returns empty (changed=True, no message)
    assert result == ""


def test_hedit_text_with_arg_returns_syntax(builder_char, test_help_entry):
    """ROM src/hedit.c:190-193 — text with inline arg → Syntax error (ROM uses string_append)."""
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "text inline content not allowed")
    assert "Syntax:" in result


# ── In-session: done ──────────────────────────────────────────────────────────

def test_hedit_done_saves_new_entry_to_registry(builder_char):
    """ROM src/hedit.c:242-246 — done on new entry registers it silently."""
    cmd_hedit(builder_char, "new combat")
    builder_char.desc.editor_state["help"].text = "Combat guide."
    initial_count = len(help_entries)
    result = cmd_hedit(builder_char, "done")
    assert result == ""
    assert builder_char.desc.editor is None
    assert len(help_entries) == initial_count + 1
    assert "combat" in help_registry


def test_hedit_done_updates_existing_entry(builder_char, test_help_entry):
    """ROM src/hedit.c:242-246 — done on existing entry closes session silently."""
    initial_count = len(help_entries)
    cmd_hedit(builder_char, "magic")
    cmd_hedit(builder_char, "level 5")
    result = cmd_hedit(builder_char, "done")
    assert result == ""
    assert builder_char.desc.editor is None
    # No new entry added
    assert len(help_entries) == initial_count
    assert test_help_entry.level == 5


# ── In-session: session integrity ────────────────────────────────────────────

def test_hedit_session_lost_returns_error(builder_char, test_help_entry):
    """ROM src/hedit.c:209-212 — missing help_entry in state → error message."""
    cmd_hedit(builder_char, "magic")
    builder_char.desc.editor_state = {}  # corrupt state
    result = cmd_hedit(builder_char, "show")
    assert "session lost" in result.lower() or "HEdit" in result


# ── In-session: unknown command falls through to dispatcher ──────────────────

def test_hedit_unknown_command_does_not_recurse(builder_char, test_help_entry):
    """ROM src/hedit.c:258 — unknown cmd falls through to normal command table (no RecursionError)."""
    cmd_hedit(builder_char, "magic")
    # 'look' is a real command — should not recurse
    try:
        result = cmd_hedit(builder_char, "look")
        # Any string response is fine; what matters is no RecursionError
    except RecursionError:
        pytest.fail("cmd_hedit fell into infinite recursion on unknown command")


# ── hesave ────────────────────────────────────────────────────────────────────

def test_hesave_saves_entries_to_file(builder_char, test_help_entry, tmp_path):
    """cmd_hesave writes JSON array with all registered entries."""
    entry2 = HelpEntry(keywords=["combat", "fighting"], text="Combat guide.", level=0)
    register_help(entry2)
    test_file = tmp_path / "test_help.json"
    result = cmd_hesave(builder_char, "", help_file=test_file)
    assert "2" in result
    assert test_file.exists()
    with open(test_file) as f:
        saved = json.load(f)
    assert len(saved) == 2
    assert any(e["keywords"] == ["magic", "spells"] for e in saved)
    assert any(e["keywords"] == ["combat", "fighting"] for e in saved)


def test_hesave_empty_registry(builder_char, tmp_path):
    """cmd_hesave with no entries writes empty array."""
    test_file = tmp_path / "empty.json"
    result = cmd_hesave(builder_char, "", help_file=test_file)
    assert "0" in result
    assert test_file.exists()


def test_hesave_preserves_all_fields(builder_char, tmp_path):
    """cmd_hesave persists keywords, text, and level faithfully."""
    entry = HelpEntry(keywords=["advanced", "magic"], text="Advanced techniques.", level=40)
    register_help(entry)
    test_file = tmp_path / "fields.json"
    cmd_hesave(builder_char, "", help_file=test_file)
    with open(test_file) as f:
        saved = json.load(f)
    assert saved[0]["keywords"] == ["advanced", "magic"]
    assert saved[0]["text"] == "Advanced techniques."
    assert saved[0]["level"] == 40


# ── Full workflow ─────────────────────────────────────────────────────────────

def test_hedit_workflow_new_edit_save(builder_char, tmp_path):
    """End-to-end: create via 'new', set keyword+level, done, hesave."""
    cmd_hedit(builder_char, "new quickmud")
    state_help = builder_char.desc.editor_state["help"]
    state_help.text = "QuickMUD is a ROM 2.4 Python port."
    cmd_hedit(builder_char, "keyword quickmud rom mud")
    cmd_hedit(builder_char, "level 0")
    cmd_hedit(builder_char, "done")

    assert "quickmud" in help_registry
    entries = help_registry["quickmud"]
    assert entries[0].keywords == ["quickmud", "rom", "mud"]
    assert entries[0].text == "QuickMUD is a ROM 2.4 Python port."

    test_file = tmp_path / "workflow.json"
    result = cmd_hesave(builder_char, "", help_file=test_file)
    assert "1" in result
    with open(test_file) as f:
        saved = json.load(f)
    assert saved[0]["keywords"] == ["quickmud", "rom", "mud"]
