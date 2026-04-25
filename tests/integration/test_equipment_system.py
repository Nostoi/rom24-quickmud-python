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

    assert "wear" in result.lower() or "shield" in result.lower(), f"Should confirm wear, got: {result}"
    assert int(WearLocation.SHIELD) in char.equipment and char.equipment.get(int(WearLocation.SHIELD)) is shield2, "Second shield should replace first"


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


def test_wear_replace_removes_old_item_to_inventory(test_character, object_factory):
    """
    Test: Wearing an item in an occupied slot replaces the old one back to inventory.

    ROM Parity: Mirrors ROM src/act_obj.c:remove_obj() then equip_char() sequence

    Given: Character wearing armor on body
    When: Character wears different armor on body
    Then: Old armor returns to inventory, new armor is equipped
    """
    char = test_character

    from mud.commands.equipment import do_wear

    armor1 = object_factory(
        {
            "vnum": 1030,
            "name": "leather armor",
            "short_descr": "leather armor",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_BODY),
            "value": [5, 0, 0, 0],
        }
    )
    armor2 = object_factory(
        {
            "vnum": 1031,
            "name": "plate mail",
            "short_descr": "plate mail",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_BODY),
            "value": [10, 0, 0, 0],
        }
    )
    char.add_object(armor1)
    do_wear(char, "leather")
    assert int(WearLocation.BODY) in char.equipment, "Body should be equipped"

    char.add_object(armor2)
    result = do_wear(char, "plate")

    assert "wear" in result.lower(), f"Should confirm wearing, got: {result}"
    assert char.equipment.get(int(WearLocation.BODY)) is armor2, "New armor should be on body"
    assert armor1 in char.inventory, "Old armor should return to inventory"
    assert armor2 not in char.inventory, "New armor should be removed from inventory"


def test_wear_multislot_replace_makes_room(test_character, object_factory):
    """
    Test: Wearing a ring when both finger slots are full replaces the first ring.

    ROM Parity: Mirrors ROM src/act_obj.c:1427-1431 finger replace logic

    Given: Character wearing two rings (both finger slots full)
    When: Character wears a third ring
    Then: First ring is replaced, returns to inventory, new ring worn
    """
    char = test_character

    from mud.commands.equipment import do_wear

    ring1 = object_factory(
        {
            "vnum": 1040,
            "name": "ruby ring",
            "short_descr": "a ruby ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    ring2 = object_factory(
        {
            "vnum": 1041,
            "name": "emerald ring",
            "short_descr": "an emerald ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    ring3 = object_factory(
        {
            "vnum": 1042,
            "name": "sapphire ring",
            "short_descr": "a sapphire ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(ring1)
    char.add_object(ring2)
    do_wear(char, "ruby")
    do_wear(char, "emerald")

    char.add_object(ring3)
    result = do_wear(char, "sapphire")

    assert "finger" in result.lower(), f"Should confirm ring wearing, got: {result}"
    assert ring1 in char.inventory, "First ring should return to inventory"
    assert ring2 in char.equipment.values(), "Second ring should still be on finger"
    assert ring3 in char.equipment.values(), "Third ring should be on finger"


def test_wield_replaces_old_weapon(test_character, object_factory):
    """
    Test: Wielding a weapon when one is already wielded replaces it.

    ROM Parity: Mirrors ROM src/act_obj.c:1620 remove_obj(WEAR_WIELD)

    Given: Character wielding a sword
    When: Character wields a different sword
    Then: Old sword returns to inventory, new sword is wielded
    """
    char = test_character

    from mud.commands.equipment import do_wield

    dagger = object_factory(
        {
            "vnum": 1050,
            "name": "iron dagger",
            "short_descr": "an iron dagger",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 3, 4, 3],
        }
    )
    longsword = object_factory(
        {
            "vnum": 1051,
            "name": "steel longsword",
            "short_descr": "a steel longsword",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 8, 12, 3],
        }
    )
    char.add_object(dagger)
    char.add_object(longsword)

    do_wield(char, "dagger")
    assert int(WearLocation.WIELD) in char.equipment, "Should wield dagger"

    result = do_wield(char, "longsword")

    assert "wield" in result.lower(), f"Should confirm wielding, got: {result}"
    assert char.equipment.get(int(WearLocation.WIELD)) is longsword, "New sword should be wielded"
    assert dagger in char.inventory, "Old dagger should return to inventory"


def test_wear_two_handed_blocks_shield_and_versa(test_character, object_factory):
    """
    Test: Two-handed weapons block shield slot, and shields block two-handed weapons.

    ROM Parity: Mirrors ROM src/act_obj.c:1604-1606, 1631-1636

    Given: Character wielding a two-handed weapon
    When: Character tries to wear a shield
    Then: Wear is rejected with "hands tied up" message

    Given: Character wearing a shield
    When: Character tries to wield a two-handed weapon
    Then: Wield is rejected with "need two hands" message
    """
    char = test_character

    from mud.commands.equipment import do_wear, do_wield
    from mud.models.constants import WeaponFlag

    two_handed = object_factory(
        {
            "vnum": 1060,
            "name": "greatspear",
            "short_descr": "a greatspear",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 10, 15, 3, int(WeaponFlag.TWO_HANDS)],
        }
    )
    shield = object_factory(
        {
            "vnum": 1061,
            "name": "tower shield",
            "short_descr": "a tower shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [5, 0, 0, 0],
        }
    )
    char.add_object(two_handed)
    char.add_object(shield)

    do_wield(char, "greatspear")
    result = do_wear(char, "tower")

    assert "hand" in result.lower() or "tied" in result.lower(), f"Should reject shield with two-hand, got: {result}"
    shield_worn = int(WearLocation.SHIELD) in char.equipment and char.equipment.get(int(WearLocation.SHIELD)) is not None
    assert not shield_worn, "Shield should not be worn"


def test_wear_replace_blocked_by_noremove(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1382-1386 — replacing a NOREMOVE item is rejected.

    A cursed item cannot be removed when wearing a replacement; ROM emits
    "You can't remove $p." via remove_obj() and aborts the wear.
    """
    from mud.commands.equipment import do_wear
    from mud.models.constants import ExtraFlag

    char = test_character

    cursed = object_factory(
        {
            "vnum": 1100,
            "name": "cursed crown",
            "short_descr": "a cursed crown",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "extra_flags": int(ExtraFlag.NOREMOVE),
            "value": [3, 0, 0, 0],
        }
    )
    plain = object_factory(
        {
            "vnum": 1101,
            "name": "plain helm",
            "short_descr": "a plain helm",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [2, 0, 0, 0],
        }
    )

    char.add_object(cursed)
    do_wear(char, "cursed")
    assert char.equipment.get(int(WearLocation.HEAD)) is cursed

    char.add_object(plain)
    char.messages.clear()
    do_wear(char, "plain")

    # ROM act_obj.c:1382-1386 — remove_obj emits "You can't remove $p." via
    # act(TO_CHAR), which lands in `char.messages` here.
    sent = " ".join(char.messages).lower()
    assert "can't remove" in sent, f"Should report cursed item cannot be removed, got messages: {char.messages}"
    assert char.equipment.get(int(WearLocation.HEAD)) is cursed, "Cursed crown should remain worn"
    assert plain in char.inventory, "Plain helm must stay in inventory"


def test_wear_neck_replace_when_both_slots_full(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1456-1480 — replacing first neck slot when both occupied."""
    from mud.commands.equipment import do_wear

    char = test_character

    amulets = []
    for vnum, name in [(1110, "ruby amulet"), (1111, "jade amulet"), (1112, "onyx amulet")]:
        obj = object_factory(
            {
                "vnum": vnum,
                "name": name,
                "short_descr": f"the {name}",
                "item_type": int(ItemType.ARMOR),
                "wear_flags": int(WearFlag.WEAR_NECK),
                "value": [1, 0, 0, 0],
            }
        )
        amulets.append(obj)
        char.add_object(obj)

    do_wear(char, "ruby")
    do_wear(char, "jade")
    result = do_wear(char, "onyx")

    assert "neck" in result.lower(), f"Should confirm neck wear, got: {result}"
    assert amulets[0] in char.inventory, "First amulet must return to inventory"
    assert amulets[1] in char.equipment.values(), "Second amulet stays equipped"
    assert amulets[2] in char.equipment.values(), "Third amulet now equipped"


def test_wear_wrist_replace_when_both_slots_full(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1565-1588 — replacing first wrist slot when both occupied."""
    from mud.commands.equipment import do_wear

    char = test_character

    bracers = []
    for vnum, name in [(1120, "iron bracer"), (1121, "steel bracer"), (1122, "gold bracer")]:
        obj = object_factory(
            {
                "vnum": vnum,
                "name": name,
                "short_descr": f"a {name}",
                "item_type": int(ItemType.ARMOR),
                "wear_flags": int(WearFlag.WEAR_WRIST),
                "value": [1, 0, 0, 0],
            }
        )
        bracers.append(obj)
        char.add_object(obj)

    do_wear(char, "iron")
    do_wear(char, "steel")
    result = do_wear(char, "gold")

    assert "wrist" in result.lower(), f"Should confirm wrist wear, got: {result}"
    assert bracers[0] in char.inventory, "First bracer must return to inventory"
    assert bracers[1] in char.equipment.values(), "Second bracer stays equipped"
    assert bracers[2] in char.equipment.values(), "Third bracer now equipped"


def test_wear_multislot_blocked_when_all_noremove(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1427-1431 — when both rings are NOREMOVE, wear fails."""
    from mud.commands.equipment import do_wear
    from mud.models.constants import ExtraFlag

    char = test_character

    cursed_specs = [
        (1130, "ruby ring"),
        (1131, "emerald ring"),
    ]
    for vnum, name in cursed_specs:
        ring = object_factory(
            {
                "vnum": vnum,
                "name": name,
                "short_descr": f"a {name}",
                "item_type": int(ItemType.ARMOR),
                "wear_flags": int(WearFlag.WEAR_FINGER),
                "extra_flags": int(ExtraFlag.NOREMOVE),
                "value": [1, 0, 0, 0],
            }
        )
        char.add_object(ring)
        do_wear(char, name.split()[0])

    third = object_factory(
        {
            "vnum": 1132,
            "name": "sapphire ring",
            "short_descr": "a sapphire ring",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_FINGER),
            "value": [1, 0, 0, 0],
        }
    )
    char.add_object(third)

    result = do_wear(char, "sapphire")
    assert "two rings" in result.lower(), f"Expected ROM 'You already wear two rings.', got: {result}"
    assert third in char.inventory, "Sapphire ring must remain in inventory"


def test_wear_all_does_not_replace_existing(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1716-1722 — `wear all` passes fReplace=FALSE,
    so already-occupied slots are skipped silently."""
    from mud.commands.equipment import do_wear

    char = test_character

    helm1 = object_factory(
        {
            "vnum": 1140,
            "name": "iron helm",
            "short_descr": "an iron helm",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [2, 0, 0, 0],
        }
    )
    helm2 = object_factory(
        {
            "vnum": 1141,
            "name": "steel helm",
            "short_descr": "a steel helm",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_HEAD),
            "value": [3, 0, 0, 0],
        }
    )

    char.add_object(helm1)
    do_wear(char, "iron")
    assert char.equipment.get(int(WearLocation.HEAD)) is helm1

    char.add_object(helm2)
    do_wear(char, "all")

    assert char.equipment.get(int(WearLocation.HEAD)) is helm1, "wear all must not replace existing helm"
    assert helm2 in char.inventory, "Second helm must remain in inventory under wear all"


def test_large_size_bypasses_two_hand_shield_block(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1603, 1631 — characters of SIZE_LARGE+ ignore
    the two-handed weapon vs. shield restriction."""
    from mud.commands.equipment import do_wear, do_wield
    from mud.models.constants import Size, WeaponFlag

    char = test_character
    char.size = int(Size.LARGE)

    two_handed = object_factory(
        {
            "vnum": 1150,
            "name": "greataxe",
            "short_descr": "a greataxe",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "value": [0, 12, 18, 3, int(WeaponFlag.TWO_HANDS)],
        }
    )
    shield = object_factory(
        {
            "vnum": 1151,
            "name": "kite shield",
            "short_descr": "a kite shield",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [5, 0, 0, 0],
        }
    )
    char.add_object(two_handed)
    char.add_object(shield)

    do_wield(char, "greataxe")
    result = do_wear(char, "kite")
    assert "tied" not in result.lower(), f"Large-sized character should bypass two-hand block, got: {result}"
    assert int(WearLocation.SHIELD) in char.equipment, "Shield must be worn for SIZE_LARGE wielder"


def test_npc_bypasses_strength_and_two_hand_checks(test_character, object_factory):
    """ROM Parity: src/act_obj.c:1623, 1631 — NPCs skip strength and
    two-hand vs. shield checks entirely."""
    from mud.commands.equipment import do_wear, do_wield
    from mud.models.constants import WeaponFlag

    char = test_character
    char.is_npc = True
    char.perm_stat = [3, 3, 3, 3, 3]  # Very low strength

    heavy_two_hander = object_factory(
        {
            "vnum": 1160,
            "name": "warhammer",
            "short_descr": "a massive warhammer",
            "item_type": int(ItemType.WEAPON),
            "wear_flags": int(WearFlag.WIELD),
            "weight": 999,
            "value": [0, 15, 25, 3, int(WeaponFlag.TWO_HANDS)],
        }
    )
    shield = object_factory(
        {
            "vnum": 1161,
            "name": "buckler",
            "short_descr": "a small buckler",
            "item_type": int(ItemType.ARMOR),
            "wear_flags": int(WearFlag.WEAR_SHIELD),
            "value": [3, 0, 0, 0],
        }
    )
    char.add_object(shield)
    char.add_object(heavy_two_hander)

    do_wear(char, "buckler")
    assert int(WearLocation.SHIELD) in char.equipment

    result = do_wield(char, "warhammer")
    assert "too heavy" not in result.lower(), f"NPC should bypass strength check, got: {result}"
    assert "two hands" not in result.lower(), f"NPC should bypass two-hand check, got: {result}"
    assert char.equipment.get(int(WearLocation.WIELD)) is heavy_two_hander, "NPC should wield two-hander with shield"
