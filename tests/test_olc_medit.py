from __future__ import annotations

import pytest

from mud.commands.build import cmd_medit
from mud.models.area import Area
from mud.models.constants import LEVEL_HERO, Sex
from mud.models.mob import MobIndex, mob_registry
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
    """Create a test area for mobile editing."""
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
def test_mobile(test_area):
    """Create a test mobile prototype."""
    mob = MobIndex(
        vnum=1001,
        player_name="test mob",
        short_descr="a test mob",
        long_descr="A test mob is standing here.",
        description="This is a test mob.",
        level=10,
        alignment=0,
        hitroll=5,
        race="human",
        sex=Sex.NONE,
        wealth=100,
        area=test_area,
    )
    mob_registry[1001] = mob
    yield mob
    mob_registry.pop(1001, None)


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


def test_medit_requires_vnum(builder_char):
    result = cmd_medit(builder_char, "")
    assert "Syntax: @medit <mobile vnum>" in result


def test_medit_vnum_must_be_number(builder_char):
    result = cmd_medit(builder_char, "abc")
    assert "Mobile vnum must be a number" in result


def test_medit_creates_new_mobile_if_vnum_in_range(builder_char, test_area):
    result = cmd_medit(builder_char, "1050")
    assert "New mobile prototype created" in result
    assert 1050 in mob_registry
    assert mob_registry[1050].vnum == 1050
    assert test_area.changed is True


def test_medit_vnum_not_in_area_range(builder_char):
    result = cmd_medit(builder_char, "5000")
    assert "That vnum is not assigned to an area" in result


def test_medit_requires_builder_permission(test_mobile):
    from mud.models.character import Character

    char = Character()
    char.name = "NotABuilder"
    char.level = LEVEL_HERO
    char.trust = LEVEL_HERO
    char.pcdata = type("PCData", (), {"security": 0})()
    session = Session(name=char.name or "", character=char, reader=None, connection=None)
    char.desc = session

    result = cmd_medit(char, "1001")
    assert "Insufficient security" in result


def test_medit_starts_session(builder_char, test_mobile):
    result = cmd_medit(builder_char, "1001")
    assert "Now editing mobile" in result
    assert "a test mob" in result
    assert builder_char.desc.editor == "medit"
    assert builder_char.desc.editor_state["mob_proto"] == test_mobile


def test_medit_show_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "show")

    assert "Mobile: a test mob" in result
    assert "Vnum:       1001" in result
    assert "Name:       test mob" in result
    assert "Short:      a test mob" in result
    assert "Long:       A test mob is standing here." in result
    assert "Description: This is a test mob." in result
    assert "Level:      10" in result
    assert "Alignment:  0" in result
    assert "Hitroll:    5" in result
    assert "Race:       human" in result
    assert "Sex:        none" in result
    assert "Wealth:     100" in result


def test_medit_name_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "name guard soldier")

    assert "Player name set to: guard soldier" in result
    assert test_mobile.player_name == "guard soldier"
    assert test_mobile.area.changed is True


def test_medit_name_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "name")
    assert "Usage: name" in result


def test_medit_short_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "short a city guard")

    assert "Short description set to: a city guard" in result
    assert test_mobile.short_descr == "a city guard"
    assert test_mobile.area.changed is True


def test_medit_short_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "short")
    assert "Usage: short" in result


def test_medit_long_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "long A city guard stands here watching for trouble.")

    assert "Long description set to: A city guard stands here watching for trouble." in result
    assert test_mobile.long_descr == "A city guard stands here watching for trouble."
    assert test_mobile.area.changed is True


def test_medit_long_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "long")
    assert "Usage: long" in result


def test_medit_desc_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "desc He is wearing chainmail and carrying a sword.")

    assert "Description set to: He is wearing chainmail and carrying a sword." in result
    assert test_mobile.description == "He is wearing chainmail and carrying a sword."
    assert test_mobile.area.changed is True


def test_medit_desc_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "desc")
    assert "Usage: desc" in result


def test_medit_level_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "level 20")

    assert "Mobile level set to 20" in result
    assert test_mobile.level == 20
    assert test_mobile.area.changed is True


def test_medit_level_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "level abc")
    assert "Level must be a number" in result


def test_medit_level_must_be_positive(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "level 0")
    assert "Level must be at least 1" in result


def test_medit_alignment_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "align -500")

    assert "Alignment set to -500" in result
    assert test_mobile.alignment == -500
    assert test_mobile.area.changed is True


def test_medit_alignment_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "align abc")
    assert "Alignment must be a number" in result


def test_medit_alignment_range_validation(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")

    result = cmd_medit(builder_char, "align -1001")
    assert "Alignment must be between -1000 and 1000" in result

    result = cmd_medit(builder_char, "align 1001")
    assert "Alignment must be between -1000 and 1000" in result


def test_medit_hitroll_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "hitroll 10")

    assert "Hitroll set to 10" in result
    assert test_mobile.hitroll == 10
    assert test_mobile.area.changed is True


def test_medit_hitroll_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "hitroll abc")
    assert "Hitroll must be a number" in result


def test_medit_damroll_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "damroll 5")

    assert "Damroll set to 5" in result
    assert test_mobile.thac0 == 5
    assert test_mobile.area.changed is True


def test_medit_damroll_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "damroll abc")
    assert "Damroll must be a number" in result


def test_medit_race_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "race elf")

    assert "Race set to: elf" in result
    assert test_mobile.race == "elf"
    assert test_mobile.area.changed is True


def test_medit_race_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "race")
    assert "Usage: race" in result


def test_medit_sex_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")

    result = cmd_medit(builder_char, "sex male")
    assert "Sex set to: male" in result
    assert test_mobile.sex == Sex.MALE

    result = cmd_medit(builder_char, "sex female")
    assert "Sex set to: female" in result
    assert test_mobile.sex == Sex.FEMALE

    result = cmd_medit(builder_char, "sex neutral")
    assert "Sex set to: neutral" in result
    assert test_mobile.sex == Sex.NONE


def test_medit_sex_invalid_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "sex invalid")
    assert "Sex must be male, female, neutral, or none" in result


def test_medit_sex_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "sex")
    assert "Usage: sex" in result


def test_medit_wealth_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "wealth 500")

    assert "Wealth set to 500" in result
    assert test_mobile.wealth == 500
    assert test_mobile.area.changed is True


def test_medit_wealth_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "wealth abc")
    assert "Wealth must be a number" in result


def test_medit_wealth_must_be_nonnegative(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "wealth -10")
    assert "Wealth must be non-negative" in result


def test_medit_group_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "group 5")

    assert "Group set to 5" in result
    assert test_mobile.group == 5
    assert test_mobile.area.changed is True


def test_medit_group_requires_number(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "group abc")
    assert "Group must be a number" in result


def test_medit_hit_dice_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "hit 5d8+20")

    assert "Hit dice set to: 5d8+20" in result
    assert test_mobile.hit_dice == "5d8+20"
    assert test_mobile.area.changed is True


def test_medit_hit_dice_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "hit")
    assert "Usage: hit" in result


def test_medit_mana_dice_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "mana 100d10+50")

    assert "Mana dice set to: 100d10+50" in result
    assert test_mobile.mana_dice == "100d10+50"
    assert test_mobile.area.changed is True


def test_medit_mana_dice_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "mana")
    assert "Usage: mana" in result


def test_medit_damage_dice_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "dam 2d6+4")

    assert "Damage dice set to: 2d6+4" in result
    assert test_mobile.damage_dice == "2d6+4"
    assert test_mobile.area.changed is True


def test_medit_damage_dice_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "dam")
    assert "Usage: dam" in result


def test_medit_damtype_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "damtype slash")

    assert "Damage type set to: slash" in result
    assert test_mobile.damage_type == "slash"
    assert test_mobile.area.changed is True


def test_medit_damtype_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "damtype")
    assert "Usage: damtype" in result


def test_medit_ac_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "ac 10d1+0")

    assert "AC dice set to: 10d1+0" in result
    assert test_mobile.ac == "10d1+0"
    assert test_mobile.area.changed is True


def test_medit_ac_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "ac")
    assert "Usage: ac" in result


def test_medit_material_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "material flesh")

    assert "Material set to: flesh" in result
    assert test_mobile.material == "flesh"
    assert test_mobile.area.changed is True


def test_medit_material_requires_value(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "material")
    assert "Usage: material" in result


def test_medit_done_exits_editor(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "done")

    assert "Exiting mobile editor" in result
    assert builder_char.desc.editor is None


def test_medit_exit_exits_editor(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "exit")

    assert "Exiting mobile editor" in result
    assert builder_char.desc.editor is None


def test_medit_unknown_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "unknown")

    assert "Unknown mobile editor command" in result


def test_medit_empty_command_shows_syntax(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "")

    assert "Syntax:" in result


def test_medit_nested_medit_command(builder_char, test_mobile):
    cmd_medit(builder_char, "1001")
    result = cmd_medit(builder_char, "@medit")

    assert "You are already editing this mobile" in result


def test_medit_session_recovery(builder_char, test_mobile):
    """Test that lost session is handled gracefully."""
    cmd_medit(builder_char, "1001")
    builder_char.desc.editor_state = {}

    result = cmd_medit(builder_char, "show")
    assert "Mobile editor session lost" in result
