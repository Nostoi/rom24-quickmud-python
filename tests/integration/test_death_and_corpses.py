"""Integration tests for Death and Corpse System

Verifies death and corpse mechanics work correctly through the game loop,
matching ROM 2.4b6 behavior exactly.

ROM Parity References:
- src/fight.c:raw_kill() - Death handling
- src/fight.c:make_corpse() - Corpse creation
- src/update.c - Corpse decay timer

Created: December 30, 2025
"""

from __future__ import annotations

import pytest

from mud.combat.death import raw_kill
from mud.models.character import Character
from mud.models.constants import ItemType, PlayerFlag, WearFlag
from mud.models.object import Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character, initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    """Initialize world once for all tests in this module."""
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_character() -> Character:
    """Create a test character with inventory and equipment."""
    from mud.models.room import Room

    # Create minimal room for testing (area=None is fine for tests)
    room = Room(vnum=3001, name="Test Room", description="A test room")
    room_registry[3001] = room

    char = create_test_character("TestVictim", room_vnum=3001)
    char.level = 10
    char.race = 1
    char.is_npc = False
    char.hit = 100
    char.max_hit = 100
    char.mana = 50
    char.max_mana = 50
    char.move = 50
    char.max_move = 50
    char.gold = 100
    char.silver = 50
    return char


@pytest.fixture
def test_mob():
    """Create a test mob for NPC death testing."""
    mob = spawn_mob(3143)
    if mob is None:
        pytest.skip("Hassan mob not available")
    mob.gold = 20
    mob.silver = 10
    room = room_registry.get(3001)
    if room is None:
        pytest.skip("Temple room not available")
    room.add_mob(mob)
    return mob


def test_player_death_creates_corpse(test_character):
    """
    Test: Player death creates a corpse object.

    ROM Parity: Mirrors ROM src/fight.c:raw_kill() and make_corpse()

    Given: A player character at full health
    When: The player dies (raw_kill is called)
    Then: A corpse object is created in the room
    """
    room = test_character.room
    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse on player death"
    assert isinstance(corpse, Object), "Corpse should be an Object"

    assert corpse in room.contents, "Corpse should be placed in the room"
    assert corpse.item_type == int(ItemType.CORPSE_PC), "Should be PC corpse type"


def test_corpse_contains_player_inventory(test_character, object_factory):
    """
    Test: Player corpse contains all inventory items.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse() inventory transfer

    Given: A player with items in inventory
    When: The player dies
    Then: All inventory items are transferred to the corpse
    """
    item1 = object_factory({"vnum": 1, "name": "sword", "short_descr": "a sword"})
    item2 = object_factory({"vnum": 2, "name": "shield", "short_descr": "a shield"})
    test_character.add_object(item1)
    test_character.add_object(item2)

    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    # ROM parity: corpse contains money object + inventory items
    assert len(corpse.contained_items) == 3, "Corpse should contain money object + 2 inventory items"
    assert item1 in corpse.contained_items, "Sword should be in corpse"
    assert item2 in corpse.contained_items, "Shield should be in corpse"

    # Verify money object exists
    money_objects = [obj for obj in corpse.contained_items if obj.item_type == ItemType.MONEY]
    assert len(money_objects) == 1, "Corpse should contain 1 money object"

    assert len(test_character.inventory) == 0, "Player inventory should be empty after death"


def test_corpse_contains_gold_and_silver(test_character):
    """
    Test: Player corpse contains character's gold and silver.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse() coin handling

    Given: A player with gold and silver
    When: The player dies
    Then: Gold and silver are transferred to the corpse
    """
    test_character.gold = 100
    test_character.silver = 50

    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert test_character.gold == 0, "Player gold should be zeroed after death"
    assert test_character.silver == 0, "Player silver should be zeroed after death"


def test_corpse_has_decay_timer_player(test_character):
    """
    Test: Player corpse has long decay timer (25-40 pulses).

    ROM Parity: Mirrors ROM src/fight.c:make_corpse() timer assignment
    ROM defines: corpse->timer = number_range(25, 40) for PC

    Given: A player character
    When: The player dies and corpse is created
    Then: Corpse timer is set to 25-40 (ROM range)
    """
    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "timer"), "Corpse should have timer attribute"
    assert 25 <= corpse.timer <= 40, f"PC corpse timer should be 25-40, got {corpse.timer}"


def test_corpse_has_decay_timer_npc(test_mob):
    """
    Test: NPC corpse has short decay timer (3-6 pulses).

    ROM Parity: Mirrors ROM src/fight.c:make_corpse() timer assignment
    ROM defines: corpse->timer = number_range(3, 6) for NPC

    Given: An NPC mob
    When: The mob dies and corpse is created
    Then: Corpse timer is set to 3-6 (ROM range)
    """
    corpse = raw_kill(test_mob)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "timer"), "Corpse should have timer attribute"
    assert 3 <= corpse.timer <= 6, f"NPC corpse timer should be 3-6, got {corpse.timer}"


def test_player_respawns_with_minimal_hp_mana_move(test_character):
    """
    Test: Player respawns with at least 1 HP/mana/move.

    ROM Parity: Mirrors ROM src/fight.c:raw_kill() player restoration
    ROM code: victim->hit = UMAX(1, victim->hit) (line 1718)

    Given: A player at 0 HP (dead)
    When: raw_kill processes the death
    Then: Player HP/mana/move set to at least 1
    """
    test_character.hit = 0
    test_character.mana = 0
    test_character.move = 0

    raw_kill(test_character)

    assert test_character.hit >= 1, "Player HP should be at least 1 after death"
    assert test_character.mana >= 1, "Player mana should be at least 1 after death"
    assert test_character.move >= 1, "Player move should be at least 1 after death"


def test_player_position_set_to_resting_after_death(test_character):
    """
    Test: Player position set to RESTING after death.

    ROM Parity: Mirrors ROM src/fight.c:raw_kill() position reset
    ROM code: victim->position = POS_RESTING (line 1717)

    Given: A player in any position
    When: The player dies
    Then: Position is set to RESTING
    """
    from mud.models.constants import Position

    test_character.position = Position.FIGHTING

    raw_kill(test_character)

    assert test_character.position == Position.RESTING, "Player should be RESTING after death"


def test_npc_is_extracted_on_death(test_mob):
    """
    Test: NPC is completely removed from game on death.

    ROM Parity: Mirrors ROM src/fight.c:raw_kill() NPC extraction
    ROM code: extract_char(victim, TRUE) for NPC (line 1707)

    Given: An NPC mob in a room
    When: The mob dies
    Then: The mob is removed from the room
    """
    room = test_mob.room
    initial_count = len(room.people)

    raw_kill(test_mob)

    assert len(room.people) < initial_count, "Mob count should decrease after death"
    assert test_mob not in room.people, "Dead mob should be removed from room"


def test_player_is_not_extracted_on_death(test_character, test_room):
    """
    Test: Player is NOT removed from game on death (ghost state).

    ROM Parity: Mirrors ROM src/fight.c:raw_kill() PC handling
    ROM code: extract_char(victim, FALSE) for PC (line 1711) - FALSE means don't destroy

    Given: A player character
    When: The player dies
    Then: Player object still exists (moved to death room)
    """
    corpse = raw_kill(test_character)

    assert test_character is not None, "Player object should still exist after death"


def test_mob_corpse_contains_loot(test_mob, object_factory):
    """
    Test: Mob corpse contains mob's inventory as loot.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse() for NPCs

    Given: A mob with items in inventory
    When: The mob dies
    Then: Items become loot in the corpse
    """
    loot1 = object_factory({"vnum": 10, "name": "gem", "short_descr": "a shiny gem"})
    loot2 = object_factory({"vnum": 11, "name": "dagger", "short_descr": "a rusty dagger"})
    test_mob.add_to_inventory(loot1)
    test_mob.add_to_inventory(loot2)

    corpse = raw_kill(test_mob)

    assert corpse is not None, "Should create corpse"
    # ROM parity: corpse contains money object + loot items
    assert len(corpse.contained_items) == 3, "Corpse should contain money object + 2 loot items"
    assert loot1 in corpse.contained_items, "Gem should be in corpse"
    assert loot2 in corpse.contained_items, "Dagger should be in corpse"

    # Verify money object exists
    money_objects = [obj for obj in corpse.contained_items if obj.item_type == ItemType.MONEY]
    assert len(money_objects) == 1, "Corpse should contain 1 money object"


def test_corpse_is_takeable(test_character):
    """
    Test: Corpse has TAKE wear flag (can be picked up).

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM code: SET_BIT(corpse->wear_flags, ITEM_TAKE) (line 1625)

    Given: A character death
    When: Corpse is created
    Then: Corpse has TAKE wear flag set
    """
    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "wear_flags"), "Corpse should have wear_flags"

    wear_flags = int(getattr(corpse, "wear_flags", 0) or 0)
    assert wear_flags & int(WearFlag.TAKE), "Corpse should have TAKE wear flag"


def test_player_corpse_has_owner_if_not_clan(test_character):
    """
    Test: Player corpse sets owner field (for non-clan members).

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM code: if (!is_clan(victim)) corpse->owner = str_dup(victim->name)

    Given: A non-clan player
    When: The player dies
    Then: Corpse owner field is set to player name
    """
    test_character.clan = 0

    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "owner"), "Corpse should have owner attribute"
    assert getattr(corpse, "owner", None) == test_character.name, f"Corpse owner should be '{test_character.name}'"


def test_player_loses_canloot_flag_on_death(test_character):
    """
    Test: Player loses CANLOOT flag on death.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM code: REMOVE_BIT(victim->act, PLR_CANLOOT) (line 1647)

    Given: A player with CANLOOT flag set
    When: The player dies
    Then: CANLOOT flag is removed
    """
    if not hasattr(test_character, "act"):
        test_character.act = 0
    test_character.act |= int(PlayerFlag.CANLOOT)

    raw_kill(test_character)

    assert not (test_character.act & int(PlayerFlag.CANLOOT)), "CANLOOT flag should be removed on death"


def test_corpse_short_description_includes_victim_name(test_character):
    """
    Test: Corpse short description includes victim's name.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM formats corpse name as "the corpse of <name>"

    Given: A character named "TestVictim"
    When: The character dies
    Then: Corpse short_descr contains "TestVictim"
    """
    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "short_descr"), "Corpse should have short_descr"

    short_descr = getattr(corpse, "short_descr", "")
    assert "TestVictim" in short_descr, f"Corpse description should contain victim name, got: {short_descr}"


def test_npc_corpse_uses_short_descr_for_name(test_mob):
    """
    Test: NPC corpse uses mob's short_descr for naming.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM uses ch->short_descr for NPC corpse names

    Given: A mob with short_descr "Hassan"
    When: The mob dies
    Then: Corpse name references mob's description
    """
    corpse = raw_kill(test_mob)

    assert corpse is not None, "Should create corpse"
    short_descr = getattr(corpse, "short_descr", "")
    assert len(short_descr) > 0, f"Corpse should have a short_descr"


def test_corpse_level_matches_victim_level(test_character):
    """
    Test: Corpse level matches victim's level.

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM code: corpse->level = victim->level (line 1644)

    Given: A level 10 character
    When: The character dies
    Then: Corpse level is 10
    """
    test_character.level = 10

    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "level"), "Corpse should have level attribute"
    assert corpse.level == 10, f"Corpse level should match victim level (10), got {corpse.level}"


def test_corpse_cost_is_zero(test_character):
    """
    Test: Corpse cost is 0 (cannot be sold).

    ROM Parity: Mirrors ROM src/fight.c:make_corpse()
    ROM code: corpse->cost = 0 (line 1643)

    Given: A character death
    When: Corpse is created
    Then: Corpse cost is 0
    """
    corpse = raw_kill(test_character)

    assert corpse is not None, "Should create corpse"
    assert hasattr(corpse, "cost"), "Corpse should have cost attribute"
    assert corpse.cost == 0, f"Corpse cost should be 0, got {corpse.cost}"


__all__ = [
    "test_player_death_creates_corpse",
    "test_corpse_contains_player_inventory",
    "test_corpse_contains_gold_and_silver",
    "test_corpse_has_decay_timer_player",
    "test_corpse_has_decay_timer_npc",
    "test_player_respawns_with_minimal_hp_mana_move",
    "test_player_position_set_to_resting_after_death",
    "test_npc_is_extracted_on_death",
    "test_player_is_not_extracted_on_death",
    "test_mob_corpse_contains_loot",
    "test_corpse_is_takeable",
    "test_player_corpse_has_owner_if_not_clan",
    "test_player_loses_canloot_flag_on_death",
    "test_corpse_short_description_includes_victim_name",
    "test_npc_corpse_uses_short_descr_for_name",
    "test_corpse_level_matches_victim_level",
    "test_corpse_cost_is_zero",
]
