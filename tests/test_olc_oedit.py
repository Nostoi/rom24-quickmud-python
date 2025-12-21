from __future__ import annotations

import pytest

from mud.commands.build import cmd_oedit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO
from mud.models.obj import ObjIndex, obj_index_registry
from mud.net.session import Session
from mud.registry import area_registry


@pytest.fixture(autouse=True)
def isolate_area_registry():
    previous = dict(area_registry)
    area_registry.clear()
    try:
        yield
    finally:
        area_registry.clear()
        area_registry.update(previous)


@pytest.fixture
def test_area():
    """Create a test area for object editing."""
    area = Area(
        vnum=1,
        name="Test Area",
        file_name="test.are",
        min_vnum=1000,
        max_vnum=1099,
        security=5,
        builders="testbuilder",
        changed=False,
    )
    area_registry[area.vnum] = area
    yield area


@pytest.fixture
def test_object(test_area):
    """Create a test object prototype."""
    obj = ObjIndex(
        vnum=1001,
        name="test object",
        short_descr="a test object",
        description="A test object lies here.",
        item_type="treasure",
        level=10,
        weight=5,
        cost=100,
        material="wood",
        area=test_area,
    )
    obj_index_registry[1001] = obj
    yield obj
    obj_index_registry.pop(1001, None)


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


def test_oedit_requires_vnum(builder_char):
    result = cmd_oedit(builder_char, "")
    assert "Syntax: @oedit <object vnum>" in result


def test_oedit_vnum_must_be_number(builder_char):
    result = cmd_oedit(builder_char, "abc")
    assert "Object vnum must be a number" in result


def test_oedit_creates_new_object_if_vnum_in_range(builder_char, test_area):
    result = cmd_oedit(builder_char, "1050")
    assert "New object prototype created" in result
    assert 1050 in obj_index_registry
    assert obj_index_registry[1050].vnum == 1050
    assert test_area.changed is True


def test_oedit_vnum_not_in_area_range(builder_char):
    result = cmd_oedit(builder_char, "5000")
    assert "That vnum is not assigned to an area" in result


def test_oedit_requires_builder_permission(test_object):
    from mud.models.character import Character

    char = Character()
    char.name = "NotABuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session

    result = cmd_oedit(char, "1001")
    assert "Insufficient security" in result


def test_oedit_starts_session(builder_char, test_object):
    result = cmd_oedit(builder_char, "1001")
    assert "Now editing object" in result
    assert "a test object" in result
    assert builder_char.desc.editor == "oedit"
    assert builder_char.desc.editor_state["obj_proto"] == test_object


def test_oedit_show_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "show")

    assert "Object: a test object" in result
    assert "Vnum:     1001" in result
    assert "Name:     test object" in result
    assert "Short:    a test object" in result
    assert "Long:     A test object lies here." in result
    assert "Type:     treasure" in result
    assert "Level:    10" in result
    assert "Weight:   5" in result
    assert "Cost:     100" in result
    assert "Material: wood" in result


def test_oedit_name_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "name sword weapon blade")

    assert "Object name (keywords) set to: sword weapon blade" in result
    assert test_object.name == "sword weapon blade"
    assert test_object.area.changed is True


def test_oedit_name_requires_value(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "name")
    assert "Usage: name" in result


def test_oedit_short_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "short a shiny sword")

    assert "Short description set to: a shiny sword" in result
    assert test_object.short_descr == "a shiny sword"
    assert test_object.area.changed is True


def test_oedit_short_requires_value(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "short")
    assert "Usage: short" in result


def test_oedit_long_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "long A shiny sword is stuck in the ground here.")

    assert "Long description set to: A shiny sword is stuck in the ground here." in result
    assert test_object.description == "A shiny sword is stuck in the ground here."
    assert test_object.area.changed is True


def test_oedit_long_requires_value(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "long")
    assert "Usage: long" in result


def test_oedit_type_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "type weapon")

    assert "Item type set to: weapon" in result
    assert test_object.item_type == "weapon"
    assert test_object.area.changed is True


def test_oedit_type_requires_value(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "type")
    assert "Usage: type" in result


def test_oedit_level_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "level 20")

    assert "Object level set to 20" in result
    assert test_object.level == 20
    assert test_object.area.changed is True


def test_oedit_level_requires_number(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "level abc")
    assert "Level must be a number" in result


def test_oedit_level_must_be_nonnegative(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "level -5")
    assert "Level must be non-negative" in result


def test_oedit_weight_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "weight 15")

    assert "Weight set to 15" in result
    assert test_object.weight == 15
    assert test_object.area.changed is True


def test_oedit_weight_requires_number(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "weight abc")
    assert "Weight must be a number" in result


def test_oedit_cost_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "cost 500")

    assert "Cost set to 500" in result
    assert test_object.cost == 500
    assert test_object.area.changed is True


def test_oedit_cost_requires_number(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "cost abc")
    assert "Cost must be a number" in result


def test_oedit_material_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "material steel")

    assert "Material set to: steel" in result
    assert test_object.material == "steel"
    assert test_object.area.changed is True


def test_oedit_material_requires_value(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "material")
    assert "Usage: material" in result


def test_oedit_value_commands(builder_char, test_object):
    cmd_oedit(builder_char, "1001")

    for i in range(5):
        result = cmd_oedit(builder_char, f"v{i} {i * 10}")
        assert f"Value[{i}] set to {i * 10}" in result
        assert test_object.value[i] == i * 10

    assert test_object.area.changed is True


def test_oedit_value_requires_number(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "v0 abc")
    assert "Value must be a number" in result


def test_oedit_value_requires_argument(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "v0")
    assert "Usage: v0" in result


def test_oedit_ed_list_empty(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "ed list")
    assert "No extra descriptions defined" in result


def test_oedit_ed_add(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "ed add runes")

    assert "Extra description 'runes' created" in result
    assert len(test_object.extra_descr) == 1
    assert test_object.extra_descr[0]["keyword"] == "runes"
    assert test_object.area.changed is True


def test_oedit_ed_add_duplicate(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    cmd_oedit(builder_char, "ed add runes")
    result = cmd_oedit(builder_char, "ed add runes")

    assert "already exists" in result


def test_oedit_ed_desc(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    cmd_oedit(builder_char, "ed add runes")
    result = cmd_oedit(builder_char, "ed desc runes Ancient runes glow faintly.")

    assert "Extra description 'runes' updated" in result
    assert test_object.extra_descr[0]["description"] == "Ancient runes glow faintly."
    assert test_object.area.changed is True


def test_oedit_ed_desc_creates_if_not_exists(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "ed desc inscription You see old text.")

    assert "Extra description 'inscription' created and set" in result
    assert len(test_object.extra_descr) == 1
    assert test_object.extra_descr[0]["keyword"] == "inscription"
    assert test_object.extra_descr[0]["description"] == "You see old text."


def test_oedit_ed_delete(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    cmd_oedit(builder_char, "ed add runes")
    result = cmd_oedit(builder_char, "ed delete runes")

    assert "Extra description 'runes' removed" in result
    assert len(test_object.extra_descr) == 0
    assert test_object.area.changed is True


def test_oedit_ed_delete_nonexistent(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "ed delete runes")

    assert "No extra description named 'runes'" in result


def test_oedit_ed_list_with_items(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    cmd_oedit(builder_char, "ed desc runes Ancient runes glow.")
    cmd_oedit(builder_char, "ed desc inscription Old text here.")
    result = cmd_oedit(builder_char, "ed list")

    assert "Extra descriptions:" in result
    assert "runes" in result
    assert "inscription" in result


def test_oedit_done_exits_editor(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "done")

    assert "Exiting object editor" in result
    assert builder_char.desc.editor is None


def test_oedit_exit_exits_editor(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "exit")

    assert "Exiting object editor" in result
    assert builder_char.desc.editor is None


def test_oedit_unknown_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "unknown")

    assert "Unknown object editor command" in result


def test_oedit_empty_command_shows_syntax(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "")

    assert "Syntax:" in result


def test_oedit_nested_oedit_command(builder_char, test_object):
    cmd_oedit(builder_char, "1001")
    result = cmd_oedit(builder_char, "@oedit")

    assert "You are already editing this object" in result


def test_oedit_session_recovery(builder_char, test_object):
    """Test that lost session is handled gracefully."""
    cmd_oedit(builder_char, "1001")
    builder_char.desc.editor_state = {}

    result = cmd_oedit(builder_char, "show")
    assert "Object editor session lost" in result
