"""
Integration tests for do_compare and do_description critical gap fixes.

ROM Reference: src/act_info.c do_compare (lines 2297-2395)

These tests verify the 6 critical gaps were fixed:
1. Use act() system with $p/$P placeholders (not string formatting)
2. Armor calculation - sum all 3 AC values (pierce+bash+slash)
3. Weapon calculation - check new_format flag, use ROM formula
4. Same object message: "You compare $p to itself.  It looks about the same."
5. Type mismatch message: "You can't compare $p and $P."
6. do_description shows result after add line operation
"""

from __future__ import annotations

import pytest

from mud.commands.character import do_description
from mud.commands.compare import do_compare
from mud.models.character import Character, PCData
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex, ObjectData
from mud.models.room import Room


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_room():
    """Create a test room."""
    room = Room(vnum=1, name="Test Room", description="A test room.")
    room.people = []
    yield room
    room.people.clear()


@pytest.fixture
def test_char(test_room):
    """Create a test character with pcdata."""
    char = Character(
        name="TestChar",
        level=10,
        room=test_room,
        is_npc=False,
        max_hit=100,
        hit=100,
        max_mana=100,
        mana=100,
        max_move=100,
        move=100,
    )
    char.pcdata = PCData()
    char.pcdata.title = ""
    char.description = ""
    char.act = 0
    char.comm = 0
    test_room.people.append(char)
    yield char
    if char in test_room.people:
        test_room.people.remove(char)


def create_weapon(name: str, dice_num: int, dice_type: int, new_format: bool = True) -> ObjectData:
    """Helper to create a weapon object."""
    proto = ObjIndex(
        vnum=1000,
        name=name.lower(),
        short_descr=name,
        description=f"{name} is here.",
        item_type=int(ItemType.WEAPON),
        value=[0, dice_num, dice_type, 0, 0],  # WEAPON: [weapon_type, dice_num, dice_type, dam_type, flags]
    )
    proto.new_format = new_format

    obj = ObjectData(item_type=int(ItemType.WEAPON))
    obj.name = name.lower()
    obj.short_descr = name
    obj.value = [0, dice_num, dice_type, 0, 0]
    obj.pIndexData = proto
    return obj


def create_armor(name: str, ac_pierce: int, ac_bash: int, ac_slash: int) -> ObjectData:
    """Helper to create armor object."""
    obj = ObjectData(item_type=int(ItemType.ARMOR))
    obj.name = name.lower()
    obj.short_descr = name
    obj.value = [ac_pierce, ac_bash, ac_slash, 0, 0]  # ARMOR: [ac_pierce, ac_bash, ac_slash, ac_magic, flags]
    return obj


def create_misc_item(name: str, item_type: ItemType) -> ObjectData:
    """Helper to create misc items (food, light, etc)."""
    obj = ObjectData(item_type=int(item_type))
    obj.name = name.lower()
    obj.short_descr = name
    return obj


# ============================================================================
# CRITICAL GAP TESTS
# ============================================================================


class TestDoCompareCriticalGaps:
    """Test do_compare critical gap fixes."""

    def test_armor_sum_calculation(self, test_char):
        """
        CRITICAL GAP FIX 2: Armor comparison sums all 3 AC values.

        ROM C: lines 2364-2367
        Formula: value1 = obj1->value[0] + obj1->value[1] + obj1->value[2]

        Before fix: Only used value[0]
        After fix: Sums AC_PIERCE + AC_BASH + AC_SLASH
        """
        # Create two armor pieces
        # Armor 1: -5 pierce, -3 bash, -4 slash = -12 total
        armor1 = create_armor("leather armor", ac_pierce=-5, ac_bash=-3, ac_slash=-4)

        # Armor 2: -2 pierce, -2 bash, -2 slash = -6 total
        armor2 = create_armor("cloth armor", ac_pierce=-2, ac_bash=-2, ac_slash=-2)

        test_char.inventory.append(armor1)
        test_char.inventory.append(armor2)

        # Compare armor1 to armor2
        result = do_compare(test_char, "leather cloth")

        # Armor 1 has -12 total AC, armor2 has -6 total AC
        # ROM C logic: value1 > value2 = better, so -12 > -6 = False
        # Therefore armor1 (-12) is "worse" than armor2 (-6)
        assert "worse" in result.lower()

    def test_weapon_new_format_calculation(self, test_char):
        """
        CRITICAL GAP FIX 3: Weapon comparison checks new_format flag.

        ROM C: lines 2369-2379
        new_format formula: value = (1 + dice_type) * dice_num

        Before fix: Used average damage formula with division
        After fix: Uses ROM C formula, checks new_format flag
        """
        # Create two weapons (new format)
        # Weapon 1: 2d6 → (1 + 6) * 2 = 14
        sword1 = create_weapon("longsword", dice_num=2, dice_type=6, new_format=True)

        # Weapon 2: 1d8 → (1 + 8) * 1 = 9
        sword2 = create_weapon("shortsword", dice_num=1, dice_type=8, new_format=True)

        test_char.inventory.append(sword1)
        test_char.inventory.append(sword2)

        # Compare longsword to shortsword
        result = do_compare(test_char, "longsword shortsword")

        # Longsword (14) should be better than shortsword (9)
        assert "better" in result.lower()

    def test_weapon_old_format_calculation(self, test_char):
        """
        CRITICAL GAP FIX 3 (continued): Old format weapon calculation.

        ROM C: lines 2373-2374, 2377-2378
        old_format formula: value = dice_num + dice_type
        """
        # Create two weapons (old format)
        # Weapon 1: 2d6 → 2 + 6 = 8
        sword1 = create_weapon("old longsword", dice_num=2, dice_type=6, new_format=False)

        # Weapon 2: 1d4 → 1 + 4 = 5
        sword2 = create_weapon("old dagger", dice_num=1, dice_type=4, new_format=False)

        test_char.inventory.append(sword1)
        test_char.inventory.append(sword2)

        # Compare old longsword to old dagger
        result = do_compare(test_char, "longsword dagger")

        # Old longsword (8) should be better than old dagger (5)
        assert "better" in result.lower()

    def test_same_object_message(self, test_char):
        """
        CRITICAL GAP FIX 4: Same object comparison message.

        ROM C: lines 2348-2351
        Expected: "You compare $p to itself.  It looks about the same."

        Before fix: "You can't compare an item to itself."
        After fix: Uses act() with $p placeholder
        """
        # Create weapon and add to inventory
        sword = create_weapon("a sharp sword", dice_num=2, dice_type=6)
        test_char.inventory.append(sword)

        # Compare sword to itself
        result = do_compare(test_char, "sword sword")

        # Verify ROM C message format
        assert "compare" in result.lower()
        assert "itself" in result.lower()
        assert "same" in result.lower()

    def test_type_mismatch_message(self, test_char):
        """
        CRITICAL GAP FIX 5: Type mismatch comparison message.

        ROM C: lines 2352-2355
        Expected: "You can't compare $p and $P."

        Before fix: Fell through to weapon/armor comparison
        After fix: Explicit type mismatch check
        """
        # Create weapon and armor
        sword = create_weapon("a sword", dice_num=2, dice_type=6)
        armor = create_armor("leather armor", ac_pierce=-5, ac_bash=-3, ac_slash=-4)

        test_char.inventory.append(sword)
        test_char.inventory.append(armor)

        # Try to compare weapon to armor
        result = do_compare(test_char, "sword armor")

        # Verify ROM C message
        assert "can't compare" in result.lower()

    def test_non_comparable_items_default_message(self, test_char):
        """
        Test default case for non-comparable items.

        ROM C: lines 2360-2362
        Default case: "You can't compare $p and $P."
        """
        # Create two food items (not weapon or armor)
        food1 = create_misc_item("an apple", ItemType.FOOD)
        food2 = create_misc_item("a bread", ItemType.FOOD)

        test_char.inventory.append(food1)
        test_char.inventory.append(food2)

        result = do_compare(test_char, "apple bread")

        # Verify ROM C default message
        assert "can't compare" in result.lower()

    def test_act_formatting_substitution(self, test_char):
        """
        CRITICAL GAP FIX 1: Use act() system with $p and $P placeholders.

        ROM C: line 2393
        Expected: act(msg, ch, obj1, obj2, TO_CHAR)

        Before fix: Manual string formatting with object names
        After fix: act_format() with $p/$P substitution
        """
        # Create two items
        sword1 = create_weapon("a shiny sword", dice_num=3, dice_type=6)
        sword2 = create_weapon("a rusty sword", dice_num=1, dice_type=4)

        test_char.inventory.append(sword1)
        test_char.inventory.append(sword2)

        # Compare items
        result = do_compare(test_char, "shiny rusty")

        # Verify act() substituted object names correctly
        assert "shiny" in result.lower()
        assert "rusty" in result.lower()


class TestDoDescriptionCriticalGap:
    """Test do_description critical gap fix."""

    def test_description_add_line_shows_result(self, test_char):
        """
        CRITICAL GAP FIX 6: Show description after add line operation.

        ROM C: lines 2651-2652 (Always shows description at end)

        Before fix: Just returned "Ok."
        After fix: Shows updated description
        """
        # Add a line to empty description
        result = do_description(test_char, "+ This is a test line")

        # Verify description is shown (not just "Ok.")
        assert "test line" in result.lower()

        # Verify description was added (ROM C adds "\n\r" at line 2646)
        # QuickMUD uses just "\n" instead of "\n\r"
        assert "This is a test line" in test_char.description

    def test_description_replace_shows_result(self, test_char):
        """Verify replace operation also shows result."""
        # Set initial description
        test_char.description = "Old line\n"

        # Replace entire description (ROM C lines 2645-2648)
        # In ROM C, any argument that doesn't start with + or - replaces the whole description
        result = do_description(test_char, "New line")

        # Verify new description is shown
        assert "new line" in result.lower()
        assert "New line" in test_char.description

    def test_description_remove_line_shows_result(self, test_char):
        """Verify remove operation also shows result."""
        # Set initial description
        test_char.description = "Line 1\nLine 2\n"

        # Remove last line (ROM C lines 2588-2628)
        # ROM's "-" removes the LAST line, not a specific line number
        result = do_description(test_char, "-")

        # Verify updated description is shown
        assert "line 1" in result.lower()
        # Line 2 should be removed
        assert "line 2" not in result.lower()
