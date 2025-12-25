from __future__ import annotations

import pytest

from mud.commands.build import cmd_aedit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO
from mud.net.session import Session
from mud.registry import area_registry


@pytest.fixture
def test_area():
    """Create a test area for editing."""
    area = Area(
        vnum=1,
        name="Test Area",
        file_name="test.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder admin",
        credits="Original Author",
        changed=False,
    )
    area_registry[1] = area
    yield area
    area_registry.pop(1, None)


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


def test_aedit_requires_vnum(builder_char):
    result = cmd_aedit(builder_char, "")
    assert "Syntax: @aedit <area vnum>" in result


def test_aedit_vnum_must_be_number(builder_char):
    result = cmd_aedit(builder_char, "abc")
    assert "Area vnum must be a number" in result


def test_aedit_area_must_exist(builder_char):
    result = cmd_aedit(builder_char, "999")
    assert "That area does not exist" in result


def test_aedit_requires_builder_permission(test_area):
    from mud.models.character import Character

    char = Character()
    char.name = "NotABuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session

    result = cmd_aedit(char, "1")
    assert "Insufficient security" in result


def test_aedit_starts_session(builder_char, test_area):
    result = cmd_aedit(builder_char, "1")
    assert "Now editing area" in result
    assert "Test Area" in result
    assert builder_char.desc.editor == "aedit"
    assert builder_char.desc.editor_state["area"] == test_area


def test_aedit_show_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "show")

    assert "Area: Test Area" in result
    assert "Vnum:     1" in result
    assert "File:     test.are" in result
    assert "Vnums:    1000 - 1099" in result
    assert "Security: 5" in result
    assert "Builders: testbuilder admin" in result
    assert "Credits:  Original Author" in result


def test_aedit_name_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "name New Area Name")

    assert "Area name set to: New Area Name" in result
    assert test_area.name == "New Area Name"
    assert test_area.changed is True


def test_aedit_name_requires_value(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "name")
    assert "Usage: name" in result


def test_aedit_credits_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "credits John Doe")

    assert "Area credits set to: John Doe" in result
    assert test_area.credits == "John Doe"
    assert test_area.changed is True


def test_aedit_credits_requires_value(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "credits")
    assert "Usage: credits" in result


def test_aedit_security_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "security 7")

    assert "Security level set to 7" in result
    assert test_area.security == 7
    assert test_area.changed is True


def test_aedit_security_requires_number(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "security abc")
    assert "Security level must be a number" in result


def test_aedit_security_range_validation(builder_char, test_area):
    cmd_aedit(builder_char, "1")

    result = cmd_aedit(builder_char, "security -1")
    assert "Security level must be between 0 and 9" in result

    result = cmd_aedit(builder_char, "security 10")
    assert "Security level must be between 0 and 9" in result


def test_aedit_builder_add(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "builder add newbuilder")

    assert "Builder 'newbuilder' added" in result
    assert "newbuilder" in test_area.builders.lower()
    assert test_area.changed is True


def test_aedit_builder_add_duplicate(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    cmd_aedit(builder_char, "builder add testbuilder")
    result = cmd_aedit(builder_char, "builder add testbuilder")

    assert "already in the list" in result


def test_aedit_builder_remove(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "builder remove testbuilder")

    assert "Builder 'testbuilder' removed" in result
    assert "testbuilder" not in test_area.builders.lower()
    assert test_area.changed is True


def test_aedit_builder_remove_nonexistent(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "builder remove nonexistent")

    assert "not in the list" in result


def test_aedit_builder_requires_action(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "builder")
    assert "Usage: builder <add|remove> <name>" in result


def test_aedit_vnum_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "vnum 2")

    assert "Area vnum set to 2" in result
    assert test_area.vnum == 2
    assert test_area.changed is True


def test_aedit_lvnum_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "lvnum 2000")

    assert "Lower vnum set to 2000" in result
    assert test_area.min_vnum == 2000
    assert test_area.changed is True


def test_aedit_uvnum_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "uvnum 2099")

    assert "Upper vnum set to 2099" in result
    assert test_area.max_vnum == 2099
    assert test_area.changed is True


def test_aedit_filename_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "filename newfile.are")

    assert "Filename set to: newfile.are" in result
    assert test_area.file_name == "newfile.are"
    assert test_area.changed is True


def test_aedit_done_exits_editor(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "done")

    assert "Exiting area editor" in result
    assert builder_char.desc.editor is None


def test_aedit_exit_exits_editor(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "exit")

    assert "Exiting area editor" in result
    assert builder_char.desc.editor is None


def test_aedit_unknown_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "unknown")

    assert "Unknown area editor command" in result


def test_aedit_empty_command_shows_syntax(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "")

    assert "Syntax:" in result


def test_aedit_nested_aedit_command(builder_char, test_area):
    cmd_aedit(builder_char, "1")
    result = cmd_aedit(builder_char, "@aedit")

    assert "You are already editing this area" in result


def test_aedit_session_recovery(builder_char, test_area):
    """Test that lost session is handled gracefully."""
    cmd_aedit(builder_char, "1")
    builder_char.desc.editor_state = {}

    result = cmd_aedit(builder_char, "show")
    assert "Area editor session lost" in result


def test_aedit_builder_by_name(test_area):
    """Test builder permissions by name match."""
    from mud.models.character import Character

    char = Character()
    char.name = "TestBuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session

    result = cmd_aedit(char, "1")
    assert "Now editing area" in result
