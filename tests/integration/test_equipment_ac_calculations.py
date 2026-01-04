"""
Integration tests for equipment AC calculations.

Verifies QuickMUD matches ROM C handler.c:1688-1726 (apply_ac) behavior.

ROM C AC System:
- AC values are "better" when more negative
- Different armor slots provide different multipliers:
  - WEAR_BODY: 3x (torso armor most important)
  - WEAR_HEAD: 2x (helmet)
  - WEAR_LEGS: 2x (leg armor)
  - WEAR_ABOUT: 2x (cloak/robe)
  - All other slots: 1x (feet, hands, arms, shield, necks, waist, wrists, hold)
- Each armor has 4 AC values: [pierce, bash, slash, exotic]
"""

from __future__ import annotations

import pytest

from mud.handler import apply_ac, equip_char, unequip_char
from mud.models.constants import ItemType, WearLocation
from mud.models.obj import ObjIndex
from mud.models.object import Object


@pytest.fixture
def platemail_body_armor():
    """Create platemail body armor with ROM C typical values.

    ROM C values for platemail: [-10, -10, -10, -10] (AC for pierce/bash/slash/exotic)
    """
    proto = ObjIndex(
        vnum=1001,
        name="platemail",
        short_descr="a suit of platemail armor",
        item_type=int(ItemType.ARMOR),
        value=[-10, -10, -10, -10, 0],  # Strong AC values
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


@pytest.fixture
def steel_helmet():
    """Create steel helmet with ROM C typical values.

    ROM C values for helmet: [-5, -5, -5, -5]
    """
    proto = ObjIndex(
        vnum=1002,
        name="helmet",
        short_descr="a steel helmet",
        item_type=int(ItemType.ARMOR),
        value=[-5, -5, -5, -5, 0],
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


@pytest.fixture
def leather_leggings():
    """Create leather leggings with ROM C typical values.

    ROM C values for leather legs: [-3, -3, -3, -3]
    """
    proto = ObjIndex(
        vnum=1003,
        name="leggings",
        short_descr="leather leggings",
        item_type=int(ItemType.ARMOR),
        value=[-3, -3, -3, -3, 0],
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


@pytest.fixture
def cloak():
    """Create cloak with ROM C typical values.

    ROM C values for cloak: [-2, -2, -2, -2]
    """
    proto = ObjIndex(
        vnum=1004,
        name="cloak",
        short_descr="a dark cloak",
        item_type=int(ItemType.ARMOR),
        value=[-2, -2, -2, -2, 0],
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


@pytest.fixture
def leather_boots():
    """Create leather boots with ROM C typical values.

    ROM C values for boots: [-2, -2, -2, -2]
    """
    proto = ObjIndex(
        vnum=1005,
        name="boots",
        short_descr="leather boots",
        item_type=int(ItemType.ARMOR),
        value=[-2, -2, -2, -2, 0],
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


@pytest.fixture
def non_armor_item():
    """Create a non-armor item (should provide no AC)."""
    proto = ObjIndex(
        vnum=2001,
        name="sword",
        short_descr="a steel sword",
        item_type=int(ItemType.WEAPON),
        value=[1, 6, 3, 0, 0],  # 1d6+3 weapon
    )
    obj = Object(instance_id=None, prototype=proto)
    return obj


# ============================================================================
# ROM C Golden Value Tests (src/handler.c:1688-1726)
# ============================================================================


def test_body_armor_applies_3x_multiplier(platemail_body_armor):
    """
    ROM C handler.c:1697: case WEAR_BODY: return 3 * obj->value[type];

    Body armor should provide 3x the base AC value.
    """
    wear_loc = int(WearLocation.BODY)

    # Test all 4 AC types
    for ac_type in range(4):
        ac_bonus = apply_ac(platemail_body_armor, wear_loc, ac_type)
        expected = -10 * 3  # Base value * 3x multiplier
        assert ac_bonus == expected, f"Body armor AC type {ac_type}: expected {expected}, got {ac_bonus}"


def test_head_armor_applies_2x_multiplier(steel_helmet):
    """
    ROM C handler.c:1699: case WEAR_HEAD: return 2 * obj->value[type];

    Helmet should provide 2x the base AC value.
    """
    wear_loc = int(WearLocation.HEAD)

    for ac_type in range(4):
        ac_bonus = apply_ac(steel_helmet, wear_loc, ac_type)
        expected = -5 * 2  # Base value * 2x multiplier
        assert ac_bonus == expected, f"Head armor AC type {ac_type}: expected {expected}, got {ac_bonus}"


def test_legs_armor_applies_2x_multiplier(leather_leggings):
    """
    ROM C handler.c:1701: case WEAR_LEGS: return 2 * obj->value[type];

    Leg armor should provide 2x the base AC value.
    """
    wear_loc = int(WearLocation.LEGS)

    for ac_type in range(4):
        ac_bonus = apply_ac(leather_leggings, wear_loc, ac_type)
        expected = -3 * 2  # Base value * 2x multiplier
        assert ac_bonus == expected, f"Legs armor AC type {ac_type}: expected {expected}, got {ac_bonus}"


def test_about_armor_applies_2x_multiplier(cloak):
    """
    ROM C handler.c:1715: case WEAR_ABOUT: return 2 * obj->value[type];

    Cloak/robe should provide 2x the base AC value.
    """
    wear_loc = int(WearLocation.ABOUT)

    for ac_type in range(4):
        ac_bonus = apply_ac(cloak, wear_loc, ac_type)
        expected = -2 * 2  # Base value * 2x multiplier
        assert ac_bonus == expected, f"About armor AC type {ac_type}: expected {expected}, got {ac_bonus}"


def test_feet_armor_applies_1x_multiplier(leather_boots):
    """
    ROM C handler.c:1703: case WEAR_FEET: return obj->value[type];

    Boots should provide 1x the base AC value (no multiplier).
    """
    wear_loc = int(WearLocation.FEET)

    for ac_type in range(4):
        ac_bonus = apply_ac(leather_boots, wear_loc, ac_type)
        expected = -2 * 1  # Base value * 1x multiplier
        assert ac_bonus == expected, f"Feet armor AC type {ac_type}: expected {expected}, got {ac_bonus}"


def test_non_armor_provides_zero_ac(non_armor_item):
    """
    ROM C handler.c:1690-1691: if (obj->item_type != ITEM_ARMOR) return 0;

    Non-armor items (weapons, containers, etc.) should provide 0 AC.
    """
    wear_loc = int(WearLocation.HOLD)

    for ac_type in range(4):
        ac_bonus = apply_ac(non_armor_item, wear_loc, ac_type)
        assert ac_bonus == 0, f"Non-armor item should provide 0 AC, got {ac_bonus} for type {ac_type}"


def test_invalid_ac_type_returns_zero(platemail_body_armor):
    """
    AC type must be 0-3 (pierce, bash, slash, exotic).
    Invalid values should return 0.
    """
    wear_loc = int(WearLocation.BODY)

    assert apply_ac(platemail_body_armor, wear_loc, -1) == 0, "Negative AC type should return 0"
    assert apply_ac(platemail_body_armor, wear_loc, 4) == 0, "AC type 4 should return 0"
    assert apply_ac(platemail_body_armor, wear_loc, 999) == 0, "AC type 999 should return 0"


# ============================================================================
# Full Armor Set Tests (ROM C Realistic Scenarios)
# ============================================================================


def test_full_armor_set_ac_totals():
    """
    Test a complete armor set to verify ROM C AC totals.

    Typical ROM C warrior full set:
    - Body: platemail (-10 * 3 = -30)
    - Head: helmet (-5 * 2 = -10)
    - Legs: leggings (-3 * 2 = -6)
    - About: cloak (-2 * 2 = -4)
    - Feet: boots (-2 * 1 = -2)
    - Total: -52 AC pierce
    """
    # Create armor set
    platemail = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1001, name="platemail", item_type=int(ItemType.ARMOR), value=[-10, -10, -10, -10, 0]),
    )
    helmet = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1002, name="helmet", item_type=int(ItemType.ARMOR), value=[-5, -5, -5, -5, 0]),
    )
    leggings = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1003, name="leggings", item_type=int(ItemType.ARMOR), value=[-3, -3, -3, -3, 0]),
    )
    cloak = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1004, name="cloak", item_type=int(ItemType.ARMOR), value=[-2, -2, -2, -2, 0]),
    )
    boots = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1005, name="boots", item_type=int(ItemType.ARMOR), value=[-2, -2, -2, -2, 0]),
    )

    # Calculate total AC (pierce)
    total_ac = 0
    total_ac += apply_ac(platemail, int(WearLocation.BODY), 0)  # -30
    total_ac += apply_ac(helmet, int(WearLocation.HEAD), 0)  # -10
    total_ac += apply_ac(leggings, int(WearLocation.LEGS), 0)  # -6
    total_ac += apply_ac(cloak, int(WearLocation.ABOUT), 0)  # -4
    total_ac += apply_ac(boots, int(WearLocation.FEET), 0)  # -2

    expected_total = -52  # ROM C golden value
    assert total_ac == expected_total, f"Full armor set should provide {expected_total} AC pierce, got {total_ac}"


def test_body_armor_is_most_important_slot():
    """
    Verify that body armor provides more AC than any other slot.

    ROM C design: Body slot has 3x multiplier, making it the most valuable armor slot.
    """
    base_ac = -10

    body_armor = Object(
        instance_id=None,
        prototype=ObjIndex(
            vnum=1001, name="armor", item_type=int(ItemType.ARMOR), value=[base_ac, base_ac, base_ac, base_ac, 0]
        ),
    )

    body_ac = apply_ac(body_armor, int(WearLocation.BODY), 0)  # -30
    head_ac = apply_ac(body_armor, int(WearLocation.HEAD), 0)  # -20
    legs_ac = apply_ac(body_armor, int(WearLocation.LEGS), 0)  # -20
    about_ac = apply_ac(body_armor, int(WearLocation.ABOUT), 0)  # -20
    feet_ac = apply_ac(body_armor, int(WearLocation.FEET), 0)  # -10

    assert body_ac < head_ac, "Body armor should provide more AC than head armor"
    assert body_ac < legs_ac, "Body armor should provide more AC than leg armor"
    assert body_ac < about_ac, "Body armor should provide more AC than about armor"
    assert body_ac < feet_ac, "Body armor should provide more AC than feet armor"


def test_all_ac_types_calculated_independently():
    """
    Verify all 4 AC types (pierce, bash, slash, exotic) are calculated independently.

    ROM C allows armor to have different AC values for different damage types.
    """
    # Armor with different AC values per type
    mixed_armor = Object(
        instance_id=None,
        prototype=ObjIndex(
            vnum=1001,
            name="mixed",
            item_type=int(ItemType.ARMOR),
            value=[-10, -8, -6, -4, 0],  # Different AC per type
        ),
    )

    wear_loc = int(WearLocation.BODY)  # 3x multiplier

    pierce_ac = apply_ac(mixed_armor, wear_loc, 0)  # -10 * 3 = -30
    bash_ac = apply_ac(mixed_armor, wear_loc, 1)  # -8 * 3 = -24
    slash_ac = apply_ac(mixed_armor, wear_loc, 2)  # -6 * 3 = -18
    exotic_ac = apply_ac(mixed_armor, wear_loc, 3)  # -4 * 3 = -12

    assert pierce_ac == -30, f"Expected -30 pierce AC, got {pierce_ac}"
    assert bash_ac == -24, f"Expected -24 bash AC, got {bash_ac}"
    assert slash_ac == -18, f"Expected -18 slash AC, got {slash_ac}"
    assert exotic_ac == -12, f"Expected -12 exotic AC, got {exotic_ac}"


# ============================================================================
# Edge Cases
# ============================================================================


def test_zero_ac_armor_provides_no_bonus():
    """Armor with 0 AC values should provide no AC bonus."""
    zero_armor = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1001, name="cloth", item_type=int(ItemType.ARMOR), value=[0, 0, 0, 0, 0]),
    )

    # Even with 3x multiplier, 0 * 3 = 0
    ac_bonus = apply_ac(zero_armor, int(WearLocation.BODY), 0)
    assert ac_bonus == 0, "Zero AC armor should provide no bonus"


def test_positive_ac_armor_makes_character_easier_to_hit():
    """
    ROM C allows positive AC values (makes character easier to hit).
    This is used for cursed armor.
    """
    cursed_armor = Object(
        instance_id=None,
        prototype=ObjIndex(
            vnum=1001,
            name="cursed",
            item_type=int(ItemType.ARMOR),
            value=[5, 5, 5, 5, 0],  # Positive = worse AC
        ),
    )

    ac_penalty = apply_ac(cursed_armor, int(WearLocation.BODY), 0)
    expected = 5 * 3  # Positive value amplified by multiplier
    assert ac_penalty == expected, f"Cursed armor should provide {expected} AC penalty, got {ac_penalty}"


def test_all_1x_multiplier_slots():
    """
    Verify all remaining slots use 1x multiplier.

    ROM C slots with 1x: FEET, HANDS, ARMS, SHIELD, NECK_1, NECK_2, WAIST, WRIST_L, WRIST_R, HOLD
    """
    armor = Object(
        instance_id=None,
        prototype=ObjIndex(vnum=1001, name="armor", item_type=int(ItemType.ARMOR), value=[-5, -5, -5, -5, 0]),
    )

    # All these slots should have 1x multiplier
    slots_1x = [
        WearLocation.FEET,
        WearLocation.HANDS,
        WearLocation.ARMS,
        WearLocation.SHIELD,
        WearLocation.NECK_1,
        WearLocation.NECK_2,
        WearLocation.WAIST,
        WearLocation.WRIST_L,
        WearLocation.WRIST_R,
        WearLocation.HOLD,
    ]

    for slot in slots_1x:
        ac_bonus = apply_ac(armor, int(slot), 0)
        expected = -5 * 1  # Base value * 1x multiplier
        assert ac_bonus == expected, f"Slot {slot.name} should have 1x multiplier, expected {expected}, got {ac_bonus}"
