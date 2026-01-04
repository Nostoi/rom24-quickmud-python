"""Integration tests for do_equipment command ROM C parity.

ROM Reference: src/act_info.c do_equipment (lines 2263-2295)

This test suite verifies:
- Header format ("You are using:\\n")
- Visibility filtering (can_see_obj check)
- Invisible equipment shows "something."
- Empty equipment shows "Nothing."
- Slot name formatting matches ROM C where_name array
"""

from __future__ import annotations

import pytest


def test_equipment_header_separate_line(movable_char_factory, object_factory):
    """Test that 'You are using:' header is on separate line (ROM C line 2268)."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    # Equip an item
    obj = object_factory({"vnum": 1, "name": "sword", "short_descr": "a steel sword"})
    obj.wear_loc = int(WearLocation.WIELD)
    char.equipment = {int(WearLocation.WIELD): obj}

    # Execute command
    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify header on separate line (ROM C format)
    assert output.startswith("You are using:\n")
    assert "a steel sword" in output


def test_equipment_empty_shows_nothing(movable_char_factory):
    """Test that empty equipment shows 'Nothing.' (ROM C line 2291)."""
    char = movable_char_factory("TestChar", 3001)
    char.equipment = {}

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify ROM C format
    assert output == "You are using:\nNothing.\n"


def test_equipment_visible_shows_object_name(movable_char_factory, object_factory):
    """Test that visible equipment shows object name (ROM C line 2279)."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    # Equip visible item
    sword = object_factory({"vnum": 1, "name": "sword", "short_descr": "a steel sword"})
    sword.wear_loc = int(WearLocation.WIELD)
    char.equipment = {int(WearLocation.WIELD): sword}

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify object name shown
    assert "<wielded>" in output
    assert "a steel sword" in output


def test_equipment_invisible_shows_something(movable_char_factory, object_factory):
    """Test that invisible equipment shows 'something.' (ROM C line 2283)."""
    from mud.models.constants import WearLocation, ExtraFlag

    char = movable_char_factory("TestChar", 3001)

    # Equip invisible item
    cloak = object_factory(
        {
            "vnum": 2,
            "name": "cloak",
            "short_descr": "an invisible cloak",
            "extra_flags": int(ExtraFlag.INVIS),
        }
    )
    cloak.wear_loc = int(WearLocation.ABOUT)
    char.equipment = {int(WearLocation.ABOUT): cloak}

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify "something." shown for invisible item
    assert "<worn about body>" in output
    assert "something." in output
    assert "invisible cloak" not in output.lower()


def test_equipment_multiple_items(movable_char_factory, object_factory):
    """Test multiple equipment items display correctly."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    # Equip multiple items
    sword = object_factory({"vnum": 1, "name": "sword", "short_descr": "a steel sword"})
    sword.wear_loc = int(WearLocation.WIELD)

    shield = object_factory({"vnum": 2, "name": "shield", "short_descr": "a wooden shield"})
    shield.wear_loc = int(WearLocation.SHIELD)

    ring = object_factory({"vnum": 3, "name": "ring", "short_descr": "a gold ring"})
    ring.wear_loc = int(WearLocation.FINGER_L)

    char.equipment = {
        int(WearLocation.WIELD): sword,
        int(WearLocation.SHIELD): shield,
        int(WearLocation.FINGER_L): ring,
    }

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify all items shown
    assert "You are using:\n" in output
    assert "<wielded>" in output and "a steel sword" in output
    assert "<worn as shield>" in output and "a wooden shield" in output
    assert "<worn on finger>" in output and "a gold ring" in output


def test_equipment_slot_name_formatting(movable_char_factory, object_factory):
    """Test that slot names match ROM C where_name array formatting."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    # Test various slot names
    test_cases = [
        (WearLocation.LIGHT, "<used as light>"),
        (WearLocation.FINGER_L, "<worn on finger>"),
        (WearLocation.NECK_1, "<worn around neck>"),
        (WearLocation.BODY, "<worn on torso>"),
        (WearLocation.HEAD, "<worn on head>"),
        (WearLocation.LEGS, "<worn on legs>"),
        (WearLocation.FEET, "<worn on feet>"),
        (WearLocation.HANDS, "<worn on hands>"),
        (WearLocation.ARMS, "<worn on arms>"),
        (WearLocation.SHIELD, "<worn as shield>"),
        (WearLocation.ABOUT, "<worn about body>"),
        (WearLocation.WAIST, "<worn about waist>"),
        (WearLocation.WRIST_L, "<worn around wrist>"),
        (WearLocation.WIELD, "<wielded>"),
        (WearLocation.HOLD, "<held>"),
        (WearLocation.FLOAT, "<floating nearby>"),
    ]

    from mud.commands.inventory import do_equipment

    for wear_loc, expected_slot_name in test_cases:
        obj = object_factory({"vnum": 1, "name": "item", "short_descr": "test item"})
        obj.wear_loc = int(wear_loc)
        char.equipment = {int(wear_loc): obj}

        output = do_equipment(char, "")

        # Verify slot name appears (with padding)
        assert expected_slot_name in output, f"Slot {wear_loc} should show '{expected_slot_name}'"


def test_equipment_mixed_visible_invisible(movable_char_factory, object_factory):
    """Test mixed visible and invisible equipment."""
    from mud.models.constants import WearLocation, ExtraFlag

    char = movable_char_factory("TestChar", 3001)

    # Visible sword
    sword = object_factory({"vnum": 1, "name": "sword", "short_descr": "a steel sword"})
    sword.wear_loc = int(WearLocation.WIELD)

    # Invisible cloak
    cloak = object_factory(
        {
            "vnum": 2,
            "name": "cloak",
            "short_descr": "an invisible cloak",
            "extra_flags": int(ExtraFlag.INVIS),
        }
    )
    cloak.wear_loc = int(WearLocation.ABOUT)

    char.equipment = {
        int(WearLocation.WIELD): sword,
        int(WearLocation.ABOUT): cloak,
    }

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify visible shows name, invisible shows "something."
    assert "a steel sword" in output
    assert "something." in output
    assert "invisible cloak" not in output.lower()


def test_equipment_all_slots_filled(movable_char_factory, object_factory):
    """Test all 19 equipment slots filled (MAX_WEAR = 19)."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    # Fill all 19 slots
    all_slots = [
        WearLocation.LIGHT,
        WearLocation.FINGER_L,
        WearLocation.FINGER_R,
        WearLocation.NECK_1,
        WearLocation.NECK_2,
        WearLocation.BODY,
        WearLocation.HEAD,
        WearLocation.LEGS,
        WearLocation.FEET,
        WearLocation.HANDS,
        WearLocation.ARMS,
        WearLocation.SHIELD,
        WearLocation.ABOUT,
        WearLocation.WAIST,
        WearLocation.WRIST_L,
        WearLocation.WRIST_R,
        WearLocation.WIELD,
        WearLocation.HOLD,
        WearLocation.FLOAT,
    ]

    equipment = {}
    for i, slot in enumerate(all_slots):
        obj = object_factory({"vnum": i + 1, "name": f"item{i}", "short_descr": f"item {i}"})
        obj.wear_loc = int(slot)
        equipment[int(slot)] = obj

    char.equipment = equipment

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify header and 19 items shown
    assert output.startswith("You are using:\n")
    lines = output.strip().split("\n")
    assert len(lines) == 20  # Header + 19 items


def test_equipment_multiline_format(movable_char_factory, object_factory):
    """Test that each equipment item is on separate line."""
    from mud.models.constants import WearLocation

    char = movable_char_factory("TestChar", 3001)

    sword = object_factory({"vnum": 1, "name": "sword", "short_descr": "a steel sword"})
    sword.wear_loc = int(WearLocation.WIELD)

    shield = object_factory({"vnum": 2, "name": "shield", "short_descr": "a wooden shield"})
    shield.wear_loc = int(WearLocation.SHIELD)

    char.equipment = {
        int(WearLocation.WIELD): sword,
        int(WearLocation.SHIELD): shield,
    }

    from mud.commands.inventory import do_equipment

    output = do_equipment(char, "")

    # Verify multi-line format
    lines = output.strip().split("\n")
    assert len(lines) == 3  # Header + 2 items
    assert lines[0] == "You are using:"
    assert "wielded" in lines[1] or "shield" in lines[1]
    assert "wielded" in lines[2] or "shield" in lines[2]
