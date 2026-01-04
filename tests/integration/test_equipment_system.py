"""Integration tests for Equipment System.

Verifies equipment mechanics work correctly through the game loop,
matching ROM 2.4b6 behavior for wear/remove/stats/AC/damage.

ROM Parity References:
- src/act_obj.c:do_wear() - Wearing equipment
- src/act_obj.c:do_remove() - Removing equipment
- src/handler.c:equip_char() - Apply equipment bonuses
- src/handler.c:unequip_char() - Remove equipment bonuses

Created: December 31, 2025
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.models.character import Character
from mud.models.constants import ItemType, WearFlag, WearLocation
from mud.models.object import Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clear_registries():
    """Clear all registries before each test."""
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_character() -> Character:
    """Create test character with minimal room setup."""
    from mud.models.room import Room

    room = Room(vnum=3001, name="Test Room", description="A test room")
    room_registry[3001] = room

    char = create_test_character("TestChar", room_vnum=3001)
    char.level = 10
    char.is_npc = False
    char.max_hit = 100
    char.hit = 100
    char.max_mana = 100
    char.mana = 100
    char.max_move = 100
    char.move = 100
    char.armor = [100, 100, 100, 100]
    char.perm_stat = [13, 13, 13, 13, 13]
    char.mod_stat = [0, 0, 0, 0, 0]
    return char


def test_wear_armor_increases_ac(test_character, object_factory):
    """
    Test: Wearing armor increases armor class.

    ROM Parity: Mirrors ROM src/handler.c:equip_char() AC application

    Given: A character with base AC
    When: Character wears armor with AC bonus
    Then: Character's AC improves by armor value
    """
    char = test_character
    initial_ac = char.armor[0] if hasattr(char, "armor") else 100

    armor = object_factory(
        {
            "vnum": 1001,
            "name": "plate mail",
            "short_descr": "a suit of plate mail",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_BODY),
            "value": [10, 0, 0, 0],
        }
    )
    char.add_object(armor)

    result = process_command(char, "wear mail")

    assert "wear" in result.lower(), f"Should confirm wearing, got: {result}"
    assert armor.wear_loc == int(WearLocation.BODY), "Armor should be worn on body"
    assert armor in char.equipment.values(), "Armor should be in equipment"
    if hasattr(char, "armor") and isinstance(char.armor, list) and len(char.armor) > 0:
        assert char.armor[0] < initial_ac, "AC should improve (lower is better)"


def test_remove_armor_reverts_ac(test_character, object_factory):
    """
    Test: Removing armor reverts AC to original value.

    ROM Parity: Mirrors ROM src/handler.c:unequip_char() AC removal

    Given: A character wearing armor
    When: Character removes the armor
    Then: AC returns to base value
    """
    char = test_character
    initial_ac = char.armor[0] if hasattr(char, "armor") else 100

    armor = object_factory(
        {
            "vnum": 1002,
            "name": "leather vest",
            "short_descr": "a leather vest",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_BODY),
            "value": [5, 0, 0, 0],
        }
    )
    char.add_object(armor)
    process_command(char, "wear vest")

    result = process_command(char, "remove vest")

    assert "stop using" in result.lower(), f"Should confirm removal, got: {result}"
    assert armor.wear_loc == int(WearLocation.NONE), "Armor should not be worn"
    assert armor not in char.equipment.values(), "Armor should not be in equipment"
    if hasattr(char, "armor") and isinstance(char.armor, list) and len(char.armor) > 0:
        assert char.armor[0] == initial_ac, "AC should revert to original value"


def test_wield_weapon_sets_weapon_slot(test_character, object_factory):
    """
    Test: Wielding weapon places it in WIELD slot.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() weapon handling

    Given: A character with a weapon
    When: Character wields the weapon
    Then: Weapon is in WIELD equipment slot
    """
    char = test_character

    weapon = object_factory(
        {
            "vnum": 1003,
            "name": "longsword sword",
            "short_descr": "a longsword",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 3, 6, 0],
        }
    )
    char.add_object(weapon)

    result = process_command(char, "wield sword")

    assert "wield" in result.lower() or "wear" in result.lower(), f"Should confirm wielding, got: {result}"
    assert weapon.wear_loc == int(WearLocation.WIELD), "Weapon should be wielded"
    assert weapon in char.equipment.values(), "Weapon should be in equipment"


def test_wear_shield_sets_shield_slot(test_character, object_factory):
    """
    Test: Wearing shield places it in SHIELD slot.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() shield handling

    Given: A character with a shield
    When: Character wears the shield
    Then: Shield is in SHIELD equipment slot
    """
    char = test_character

    shield = object_factory(
        {
            "vnum": 1004,
            "name": "wooden shield",
            "short_descr": "a wooden shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [8, 0, 0, 0],
        }
    )
    char.add_object(shield)

    result = process_command(char, "wear shield")

    assert "wear" in result.lower(), f"Should confirm wearing, got: {result}"
    assert shield.wear_loc == int(WearLocation.SHIELD), "Shield should be in shield slot"
    assert shield in char.equipment.values(), "Shield should be in equipment"


def test_cannot_wear_two_shields(test_character, object_factory):
    """
    Test: Cannot wear two shields simultaneously.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() slot conflict check

    Given: A character wearing a shield
    When: Character tries to wear second shield
    Then: Second shield is rejected (slot occupied)
    """
    char = test_character

    shield1 = object_factory(
        {
            "vnum": 1005,
            "name": "iron shield",
            "short_descr": "an iron shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [10, 0, 0, 0],
        }
    )
    shield2 = object_factory(
        {
            "vnum": 1006,
            "name": "bronze shield",
            "short_descr": "a bronze shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [9, 0, 0, 0],
        }
    )
    char.add_object(shield1)
    char.add_object(shield2)

    process_command(char, "wear iron")
    result = process_command(char, "wear bronze")

    assert "already" in result.lower() or "wearing" in result.lower(), f"Should reject second shield, got: {result}"
    assert shield1.wear_loc == int(WearLocation.SHIELD), "First shield still worn"
    assert shield2.wear_loc == int(WearLocation.NONE), "Second shield not worn"


def test_wear_all_wears_multiple_items(test_character, object_factory):
    """
    Test: 'wear all' command wears all wearable items in inventory.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() with "all" argument

    Given: A character with multiple wearable items
    When: Character types 'wear all'
    Then: All compatible items are worn in appropriate slots
    """
    char = test_character

    helmet = object_factory(
        {
            "vnum": 1007,
            "name": "helmet",
            "short_descr": "a helmet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [5, 0, 0, 0],
        }
    )
    boots = object_factory(
        {
            "vnum": 1008,
            "name": "boots",
            "short_descr": "leather boots",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FEET),
            "value": [3, 0, 0, 0],
        }
    )
    char.add_object(helmet)
    char.add_object(boots)

    result = process_command(char, "wear all")

    assert helmet.wear_loc == int(WearLocation.HEAD), "Helmet should be worn"
    assert boots.wear_loc == int(WearLocation.FEET), "Boots should be worn"


def test_remove_all_removes_all_equipment(test_character, object_factory):
    """
    Test: 'remove all' command removes all worn equipment.

    ROM Parity: Mirrors ROM src/act_obj.c:do_remove() with "all" argument

    Given: A character wearing multiple items
    When: Character types 'remove all'
    Then: All items are removed and returned to inventory
    """
    char = test_character

    helmet = object_factory(
        {
            "vnum": 1009,
            "name": "helmet",
            "short_descr": "a steel helmet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [6, 0, 0, 0],
        }
    )
    gloves = object_factory(
        {
            "vnum": 1010,
            "name": "gloves",
            "short_descr": "leather gloves",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HANDS),
            "value": [2, 0, 0, 0],
        }
    )
    char.add_object(helmet)
    char.add_object(gloves)
    process_command(char, "wear helmet")
    process_command(char, "wear gloves")

    result = process_command(char, "remove all")

    assert helmet.wear_loc == int(WearLocation.NONE), "Helmet should be removed"
    assert gloves.wear_loc == int(WearLocation.NONE), "Gloves should be removed"
    assert len(char.equipment) == 0, "No equipment should remain"


def test_equipment_with_stat_bonus(test_character, object_factory):
    """
    Test: Equipment with stat bonuses increases character stats.

    ROM Parity: Mirrors ROM src/handler.c:equip_char() affect application

    Given: A character with base stats
    When: Character wears item with +STR bonus
    Then: Character's STR increases by bonus amount
    """
    from mud.commands.dispatcher import process_command
    from mud.models.constants import ItemType, Stat, WearFlag

    char = test_character

    initial_str = char.get_curr_stat(Stat.STR)

    gauntlets = object_factory(
        {
            "vnum": 9003,
            "name": "gauntlets strength power",
            "short_descr": "gauntlets of strength",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HANDS),
            "value": [3, 0, 0, 0],
            "level": 5,
        }
    )

    gauntlets.prototype.affected = [{"location": 1, "modifier": 2}]

    char.add_object(gauntlets)

    wear_result = process_command(char, "wear gauntlets")
    assert "wear" in wear_result.lower(), f"Should be able to wear gauntlets, got: {wear_result}"

    new_str = char.get_curr_stat(Stat.STR)
    assert new_str == initial_str + 2, f"STR should increase by 2 (was {initial_str}, now {new_str})"

    remove_result = process_command(char, "remove gauntlets")
    assert "stop using" in remove_result.lower(), f"Should be able to remove gauntlets, got: {remove_result}"

    final_str = char.get_curr_stat(Stat.STR)
    assert final_str == initial_str, f"STR should return to {initial_str} after removal, got {final_str}"


def test_cursed_item_cannot_be_removed(test_character, object_factory):
    """
    Test: Cursed equipment cannot be removed normally.

    ROM Parity: Mirrors ROM src/act_obj.c:do_remove() ITEM_NOREMOVE check

    Given: A character wearing cursed item
    When: Character tries to remove cursed item
    Then: Removal fails with curse message
    """
    from mud.commands.dispatcher import process_command
    from mud.models.constants import ExtraFlag, ItemType, WearFlag

    char = test_character

    # Create a cursed helmet
    cursed_helmet = object_factory(
        {
            "vnum": 9001,
            "name": "cursed helmet dark",
            "short_descr": "a cursed dark helmet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "extra_flags": int(ExtraFlag.NOREMOVE),  # ROM's ITEM_NOREMOVE flag
            "value": [5, 0, 0, 0],
        }
    )

    # Give helmet to character and wear it
    char.add_object(cursed_helmet)
    wear_result = process_command(char, "wear helmet")
    assert "wear" in wear_result.lower(), f"Should be able to wear helmet, got: {wear_result}"

    # Try to remove it - should fail
    remove_result = process_command(char, "remove helmet")
    assert "can't remove" in remove_result.lower() or "cursed" in remove_result.lower(), (
        f"Cursed item removal should fail with curse message, got: {remove_result}"
    )


def test_two_handed_weapon_prevents_shield(test_character, object_factory):
    """
    Test: Wielding two-handed weapon prevents wearing shield.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() TWO_HANDS check

    Given: A character wielding two-handed weapon
    When: Character tries to wear shield
    Then: Shield wear fails (hands occupied)
    """
    from mud.commands.dispatcher import process_command
    from mud.models.constants import ItemType, WearFlag, WeaponFlag

    char = test_character

    greatsword = object_factory(
        {
            "vnum": 9004,
            "name": "greatsword huge",
            "short_descr": "a huge greatsword",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 1, 6, 3, int(WeaponFlag.TWO_HANDS)],
            "level": 10,
            "weight": 100,
        }
    )

    shield = object_factory(
        {
            "vnum": 9005,
            "name": "shield wooden",
            "short_descr": "a wooden shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [5, 0, 0, 0],
            "level": 5,
        }
    )

    char.add_object(greatsword)
    char.add_object(shield)

    wield_result = process_command(char, "wield greatsword")
    assert "wield" in wield_result.lower(), f"Should wield greatsword, got: {wield_result}"

    wear_result = process_command(char, "wear shield")
    assert "hands are tied up" in wear_result.lower() or "two hands" in wear_result.lower(), (
        f"Should fail to wear shield with two-handed weapon, got: {wear_result}"
    )


def test_dual_wield_requires_secondary_slot(test_character, object_factory):
    r"""
    Test: Dual wielding places second weapon in SECONDARY slot.

    NOT ROM 2.4b6 PARITY - Dual wield is not present in ROM 2.4b6 C source.
    This would be a post-ROM enhancement feature (ROM 2.5+ or derivatives).

    Verified: grep -rn "dual\|SECONDARY" src/ shows no dual wield implementation.

    Given: A character wielding primary weapon
    When: Character wields second weapon
    Then: Second weapon goes to SECONDARY slot
    """
    pytest.skip("NOT A ROM 2.4b6 FEATURE - Dual wield was added in later MUD derivatives, not in original ROM 2.4b6")


def test_item_level_restriction(test_character, object_factory):
    """
    Test: Cannot wear items above character level.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() level check

    Given: A level 10 character
    When: Character tries to wear level 20 item
    Then: Wear fails with level requirement message
    """
    from mud.commands.dispatcher import process_command
    from mud.models.constants import ItemType, WearFlag

    char = test_character
    char.level = 10

    # Create a high-level helmet (level 20)
    high_level_helmet = object_factory(
        {
            "vnum": 9002,
            "name": "epic helmet legendary",
            "short_descr": "an epic legendary helmet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "level": 20,
            "value": [15, 0, 0, 0],
        }
    )

    char.add_object(high_level_helmet)

    # Try to wear it - should fail
    result = process_command(char, "wear helmet")
    assert "must be level" in result.lower() or "level 20" in result, (
        f"Should fail with level requirement, got: {result}"
    )


def test_equipment_shown_in_equipment_command(test_character, object_factory):
    """
    Test: 'equipment' command shows all worn items.

    ROM Parity: Mirrors ROM src/act_info.c:do_equipment()

    Given: A character wearing multiple items
    When: Character types 'equipment'
    Then: All worn items are listed by slot
    """
    char = test_character

    helmet = object_factory(
        {
            "vnum": 1011,
            "name": "helmet",
            "short_descr": "a bronze helmet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [7, 0, 0, 0],
        }
    )
    char.add_object(helmet)
    process_command(char, "wear helmet")

    result = process_command(char, "equipment")

    assert "helmet" in result.lower(), f"Equipment list should show helmet, got: {result}"
    assert "head" in result.lower() or "<worn on head>" in result.lower(), "Should show head slot"


def test_wear_light_sets_light_slot(test_character, object_factory):
    """
    Test: Wearing light source places it in LIGHT slot.

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() light handling

    Given: A character with a light source
    When: Character wears the light
    Then: Light is in LIGHT equipment slot
    """
    char = test_character

    torch = object_factory(
        {
            "vnum": 1012,
            "name": "torch",
            "short_descr": "a burning torch",
            "item_type": int(ItemType.LIGHT),
            "wear_flags": int(WearFlag.HOLD),
            "value": [100, 0, 0, 0],
        }
    )
    char.add_object(torch)

    result = process_command(char, "wear torch")

    assert "hold" in result.lower() or "light" in result.lower(), f"Should confirm wearing, got: {result}"
    assert torch in char.equipment.values(), "Torch should be in equipment"


def test_wear_neck_items_allows_two(test_character, object_factory):
    """
    Test: Can wear two neck items (NECK_1 and NECK_2 slots).

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() multiple neck slots

    Given: A character with two amulets
    When: Character wears both amulets
    Then: Both are worn (NECK_1 and NECK_2 slots)
    """
    char = test_character

    amulet1 = object_factory(
        {
            "vnum": 1013,
            "name": "amulet gold",
            "short_descr": "a gold amulet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_NECK),
            "value": [1, 0, 0, 0],
        }
    )
    amulet2 = object_factory(
        {
            "vnum": 1014,
            "name": "amulet silver",
            "short_descr": "a silver amulet",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_NECK),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(amulet1)
    char.add_object(amulet2)

    process_command(char, "wear gold")
    result = process_command(char, "wear silver")

    worn_items = [item for item in char.equipment.values() if item in (amulet1, amulet2)]
    assert len(worn_items) == 2, "Should be able to wear both amulets"


def test_wear_finger_items_allows_two(test_character, object_factory):
    """
    Test: Can wear two rings (FINGER_L and FINGER_R slots).

    ROM Parity: Mirrors ROM src/act_obj.c:do_wear() multiple finger slots

    Given: A character with two rings
    When: Character wears both rings
    Then: Both are worn (FINGER_L and FINGER_R slots)
    """
    char = test_character

    ring1 = object_factory(
        {
            "vnum": 1015,
            "name": "ring ruby",
            "short_descr": "a ruby ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    ring2 = object_factory(
        {
            "vnum": 1016,
            "name": "ring emerald",
            "short_descr": "an emerald ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(ring1)
    char.add_object(ring2)

    process_command(char, "wear ruby")
    result = process_command(char, "wear emerald")

    worn_items = [item for item in char.equipment.values() if item in (ring1, ring2)]
    assert len(worn_items) == 2, "Should be able to wear both rings"
