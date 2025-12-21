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
    """Create a character with builder privileges."""
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 9})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session
    return char


# @hedit - starting editor tests


def test_hedit_requires_keyword(builder_char):
    result = cmd_hedit(builder_char, "")
    assert "Syntax: @hedit <keyword> or @hedit new" in result


def test_hedit_new_creates_entry(builder_char):
    result = cmd_hedit(builder_char, "new")

    assert "Creating new help entry" in result
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is True


def test_hedit_nonexistent_keyword_creates_entry(builder_char):
    result = cmd_hedit(builder_char, "newkeyword")

    assert "Creating new help entry for 'newkeyword'" in result
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is True

    help_entry = builder_char.desc.editor_state["help"]
    assert "newkeyword" in help_entry.keywords


def test_hedit_existing_keyword_edits_entry(builder_char, test_help_entry):
    result = cmd_hedit(builder_char, "magic")

    assert "Editing help entry" in result
    assert "magic spells" in result
    assert builder_char.desc.editor == "hedit"
    assert builder_char.desc.editor_state["is_new"] is False


# @hedit - editor commands


def test_hedit_show_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "show")

    assert "Keywords: magic spells" in result
    assert "Level:    0" in result
    assert "Text:" in result
    assert "Magic requires" in result


def test_hedit_keywords_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "keywords magic spells casting sorcery")

    assert "Keywords set to: magic spells casting sorcery" in result

    help_entry = builder_char.desc.editor_state["help"]
    assert help_entry.keywords == ["magic", "spells", "casting", "sorcery"]


def test_hedit_keywords_requires_value(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "keywords")

    assert "Usage: keywords" in result


def test_hedit_text_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "text This is the new help text about magic.")

    assert "Help text updated" in result

    help_entry = builder_char.desc.editor_state["help"]
    assert help_entry.text == "This is the new help text about magic."


def test_hedit_text_requires_value(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "text")

    assert "Usage: text" in result


def test_hedit_level_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level 51")

    assert "Level set to 51" in result

    help_entry = builder_char.desc.editor_state["help"]
    assert help_entry.level == 51


def test_hedit_level_requires_number(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level abc")

    assert "Level must be a number" in result


def test_hedit_level_must_be_nonnegative(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "level -5")

    assert "Level must be non-negative" in result


def test_hedit_done_saves_new_entry(builder_char):
    cmd_hedit(builder_char, "newhelp")
    cmd_hedit(builder_char, "keywords newhelp test")
    cmd_hedit(builder_char, "text This is a test help entry.")

    initial_count = len(help_entries)

    result = cmd_hedit(builder_char, "done")

    assert "Help entry saved" in result
    assert "Use '@hesave' to write to disk" in result
    assert builder_char.desc.editor is None
    assert len(help_entries) == initial_count + 1
    assert "newhelp" in help_registry


def test_hedit_done_updates_existing_entry(builder_char, test_help_entry):
    initial_count = len(help_entries)

    cmd_hedit(builder_char, "magic")
    cmd_hedit(builder_char, "text Updated magic text.")
    result = cmd_hedit(builder_char, "done")

    assert "Help entry saved" in result
    assert builder_char.desc.editor is None
    assert len(help_entries) == initial_count


def test_hedit_exit_exits_editor(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "exit")

    assert "Help entry saved" in result
    assert builder_char.desc.editor is None


def test_hedit_unknown_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "unknown")

    assert "Unknown help editor command" in result


def test_hedit_empty_command_shows_syntax(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "")

    assert "Syntax:" in result


def test_hedit_nested_hedit_command(builder_char, test_help_entry):
    cmd_hedit(builder_char, "magic")
    result = cmd_hedit(builder_char, "@hedit")

    assert "You are already editing this help entry" in result


def test_hedit_session_recovery(builder_char, test_help_entry):
    """Test that lost session is handled gracefully."""
    cmd_hedit(builder_char, "magic")
    builder_char.desc.editor_state = {}

    result = cmd_hedit(builder_char, "show")
    assert "Help editor session lost" in result


# @hesave tests


def test_hesave_saves_help_entries(builder_char, test_help_entry, tmp_path):
    """Test that help entries are correctly saved to disk."""
    # Add another entry
    entry2 = HelpEntry(keywords=["combat", "fighting"], text="Combat guide.", level=0)
    register_help(entry2)

    test_file = tmp_path / "test_help.json"

    result = cmd_hesave(builder_char, "", help_file=test_file)

    # Verify result message
    assert "Saved 2 help entries" in result

    # Verify file was created and has correct content
    assert test_file.exists()
    with open(test_file) as f:
        saved_data = json.load(f)

    assert len(saved_data) == 2
    assert any(e["keywords"] == ["magic", "spells"] for e in saved_data)
    assert any(e["keywords"] == ["combat", "fighting"] for e in saved_data)


def test_hesave_empty_help_list(builder_char, tmp_path):
    """Test saving when there are no help entries."""
    test_file = tmp_path / "empty_help.json"

    result = cmd_hesave(builder_char, "", help_file=test_file)

    assert "Saved 0 help entries" in result
    assert test_file.exists()


def test_hesave_preserves_all_fields(builder_char, tmp_path):
    """Test that all help entry fields are preserved when saving."""
    entry = HelpEntry(keywords=["advanced", "magic"], text="Advanced magic techniques require level 40.", level=40)
    register_help(entry)

    test_file = tmp_path / "fields_help.json"

    cmd_hesave(builder_char, "", help_file=test_file)

    with open(test_file) as f:
        saved_data = json.load(f)

    assert len(saved_data) == 1
    saved_entry = saved_data[0]
    assert saved_entry["keywords"] == ["advanced", "magic"]
    assert saved_entry["text"] == "Advanced magic techniques require level 40."
    assert saved_entry["level"] == 40


def test_hedit_workflow_create_edit_save(builder_char, tmp_path):
    """Test complete workflow: create entry, edit it, save to disk."""
    # Create new entry
    cmd_hedit(builder_char, "new")
    cmd_hedit(builder_char, "keywords quickmud rom mud")
    cmd_hedit(builder_char, "text QuickMUD is a ROM 2.4 Python port.")
    cmd_hedit(builder_char, "level 0")
    cmd_hedit(builder_char, "done")

    # Verify entry exists in memory
    assert "quickmud" in help_registry
    entries = help_registry["quickmud"]
    assert len(entries) == 1
    assert entries[0].keywords == ["quickmud", "rom", "mud"]
    assert entries[0].text == "QuickMUD is a ROM 2.4 Python port."
    assert entries[0].level == 0

    test_file = tmp_path / "workflow_help.json"

    result = cmd_hesave(builder_char, "", help_file=test_file)

    assert "Saved 1 help entries" in result

    # Verify saved content
    with open(test_file) as f:
        saved_data = json.load(f)

    assert len(saved_data) == 1
    assert saved_data[0]["keywords"] == ["quickmud", "rom", "mud"]
