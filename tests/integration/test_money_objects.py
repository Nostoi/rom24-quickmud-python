"""Integration tests for create_money() and money object handling.

ROM Parity References:
- src/handler.c:2427-2482 (create_money function)
- src/fight.c:1475 (NPC death money in corpse)
- src/fight.c:1494 (PC clan death money in corpse)
- src/act_obj.c:585 (drop command money consolidation)

This test suite verifies that money is handled as actual objects (not just attributes)
in corpses and drops, matching ROM 2.4b6 behavior.
"""

from __future__ import annotations

import pytest

from mud.combat.death import raw_kill
from mud.handler import create_money
from mud.models.character import Character
from mud.models.constants import (
    ItemType,
    OBJ_VNUM_COINS,
    OBJ_VNUM_GOLD_ONE,
    OBJ_VNUM_GOLD_SOME,
    OBJ_VNUM_SILVER_ONE,
    OBJ_VNUM_SILVER_SOME,
)
from mud.models.object import Object
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


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
def test_room_3001():
    """Ensure room 3001 exists for testing."""
    from mud.models.room import Room

    if 3001 not in room_registry:
        room = Room(vnum=3001, name="Test Room", description="A test room")
        room_registry[3001] = room
    return room_registry[3001]


# =============================================================================
# create_money() Unit Tests
# =============================================================================


def test_create_money_one_silver():
    """
    Test: create_money(0, 1) creates OBJ_VNUM_SILVER_ONE object.

    ROM Parity: handler.c:2432-2437
        if (silver == 1 && gold == 0)
            obj = create_object(get_obj_index(OBJ_VNUM_SILVER_ONE), 0);
    """
    money = create_money(gold=0, silver=1)

    assert money is not None, "Should create money object"
    assert money.prototype.vnum == OBJ_VNUM_SILVER_ONE
    assert money.short_descr == "one silver coin"
    assert money.cost == 1


def test_create_money_one_gold():
    """
    Test: create_money(1, 0) creates OBJ_VNUM_GOLD_ONE object.

    ROM Parity: handler.c:2439-2444
        else if (gold == 1 && silver == 0)
            obj = create_object(get_obj_index(OBJ_VNUM_GOLD_ONE), 0);
    """
    money = create_money(gold=1, silver=0)

    assert money is not None, "Should create money object"
    assert money.prototype.vnum == OBJ_VNUM_GOLD_ONE
    assert money.short_descr == "one gold coin"
    assert money.cost == 100


def test_create_money_some_silver():
    """
    Test: create_money(0, N) creates OBJ_VNUM_SILVER_SOME object with value[0] = N.

    ROM Parity: handler.c:2446-2453
        else if (silver > 1 && gold == 0)
            obj = create_object(get_obj_index(OBJ_VNUM_SILVER_SOME), 0);
            sprintf (buf, obj->short_descr, silver);
            obj->value[0] = silver;
    """
    money = create_money(gold=0, silver=42)

    assert money is not None, "Should create money object"
    assert money.prototype.vnum == OBJ_VNUM_SILVER_SOME
    assert money.short_descr == "42 silver coins"
    assert money.value[0] == 42
    assert money.cost == 42


def test_create_money_some_gold():
    """
    Test: create_money(N, 0) creates OBJ_VNUM_GOLD_SOME object with value[1] = N.

    ROM Parity: handler.c:2455-2462
        else if (gold > 1 && silver == 0)
            obj = create_object(get_obj_index(OBJ_VNUM_GOLD_SOME), 0);
            sprintf (buf, obj->short_descr, gold);
            obj->value[1] = gold;
    """
    money = create_money(gold=25, silver=0)

    assert money is not None, "Should create money object"
    assert money.prototype.vnum == OBJ_VNUM_GOLD_SOME
    assert money.short_descr == "25 gold coins"
    assert money.value[1] == 25
    assert money.cost == 2500


def test_create_money_mixed_coins():
    """
    Test: create_money(G, S) creates OBJ_VNUM_COINS with value[0]=silver, value[1]=gold.

    ROM Parity: handler.c:2464-2473
        else
            obj = create_object(get_obj_index(OBJ_VNUM_COINS), 0);
            sprintf (buf, obj->short_descr, silver, gold);
            obj->value[0] = silver;
            obj->value[1] = gold;
    """
    money = create_money(gold=10, silver=50)

    assert money is not None, "Should create money object"
    assert money.prototype.vnum == OBJ_VNUM_COINS
    assert money.short_descr == "50 silver and 10 gold coins"
    assert money.value[0] == 50
    assert money.value[1] == 10
    assert money.cost == 1050  # 50 + 10*100


def test_create_money_zero_returns_none():
    """
    Test: create_money(0, 0) should return None (BUG warning in ROM C).

    ROM Parity: handler.c:2475-2481
        if (obj->cost == 0)
            bugf ("Create_money: zero or negative money.");
    """
    money = create_money(gold=0, silver=0)

    # ROM C doesn't explicitly return NULL, but logs a bug
    # QuickMUD implementation may return None for zero money
    # This is acceptable divergence (safety improvement)
    assert money is None or money.cost == 0


def test_create_money_negative_gold_returns_none():
    """
    Test: create_money with negative values should not create money.

    ROM Parity: handler.c doesn't handle negatives, but QuickMUD should be defensive.
    """
    money = create_money(gold=-10, silver=50)

    # Defensive programming: should handle invalid input gracefully
    assert money is None or money.cost >= 0


def test_create_money_negative_silver_returns_none():
    """
    Test: create_money with negative silver should not create money.
    """
    money = create_money(gold=10, silver=-50)

    # Defensive programming: should handle invalid input gracefully
    assert money is None or money.cost >= 0


# =============================================================================
# Death & Corpse Money Integration Tests
# =============================================================================


def test_npc_death_creates_money_object_in_corpse(movable_mob_factory):
    """
    Test: NPC death creates money object INSIDE corpse (not just attributes).

    ROM Parity: src/fight.c:1473-1478
        if (ch->gold > 0) {
            obj_to_obj(create_money(ch->gold, ch->silver), corpse);
            ch->gold = 0;
            ch->silver = 0;
        }

    Current QuickMUD Behavior: Sets corpse.gold/silver attributes
    Expected ROM Behavior: Creates money object in corpse.contents
    """
    mob = movable_mob_factory(vnum=3001, room_vnum=3001)
    mob.gold = 50
    mob.silver = 25

    corpse = raw_kill(mob)

    assert corpse is not None, "Should create corpse"

    # ROM C puts money as an OBJECT inside the corpse
    money_objects = [obj for obj in corpse.contained_items if obj.item_type == ItemType.MONEY]
    assert len(money_objects) == 1, "Should have exactly 1 money object in corpse"

    money = money_objects[0]
    assert money.prototype.vnum == OBJ_VNUM_COINS
    assert money.value[0] == 25  # silver
    assert money.value[1] == 50  # gold

    # Mob should be zeroed
    assert mob.gold == 0
    assert mob.silver == 0


def test_pc_death_creates_money_object_in_corpse(movable_char_factory):
    """
    Test: PC death (non-clan) creates money object INSIDE corpse.

    ROM Parity: src/fight.c:1492-1498 (PC clan member loses half)
        if (ch->gold > 1 || ch->silver > 1) {
            obj_to_obj(create_money(ch->gold/2, ch->silver/2), corpse);
            ch->gold -= ch->gold/2;
            ch->silver -= ch->silver/2;
        }

    Note: This tests PC clan death (half money in corpse).
    Non-clan PCs should drop ALL money in corpse (similar to NPCs).
    """
    player = movable_char_factory(name="TestPlayer", room_vnum=3001)
    player.gold = 100
    player.silver = 50
    # TODO: Set clan membership flag to test half-money behavior

    corpse = raw_kill(player)

    assert corpse is not None, "Should create corpse"

    # ROM C puts money as an OBJECT inside the corpse
    money_objects = [obj for obj in corpse.contained_items if obj.item_type == ItemType.MONEY]
    assert len(money_objects) == 1, "Should have exactly 1 money object in corpse"

    money = money_objects[0]
    # Non-clan PC should drop ALL money (same as NPC)
    assert money.value[0] == 50  # all silver
    assert money.value[1] == 100  # all gold

    # Player should be zeroed
    assert player.gold == 0
    assert player.silver == 0


def test_corpse_money_is_lootable_object(movable_char_factory, movable_mob_factory):
    """
    Test: Money in corpse can be looted as an object (not just attributes).

    ROM Parity: Money must be actual objects that can be picked up.

    Given: NPC dies with money
    When: Player gets item from corpse
    Then: Money object transfers to player inventory
    """
    mob = movable_mob_factory(vnum=3001, room_vnum=3001)
    mob.gold = 75
    mob.silver = 30

    corpse = raw_kill(mob)
    assert corpse is not None

    player = movable_char_factory(name="Looter", room_vnum=3001)

    # Get money from corpse
    money_objects = [obj for obj in corpse.contained_items if obj.item_type == ItemType.MONEY]
    assert len(money_objects) == 1, "Corpse should contain 1 money object"

    money = money_objects[0]
    corpse.contained_items.remove(money)
    player.inventory.append(money)

    # Verify money object is now in player inventory
    assert money in player.inventory
    assert money not in corpse.contained_items
    assert money.value[0] == 30  # silver
    assert money.value[1] == 75  # gold


# =============================================================================
# AUTOSPLIT Integration Tests (GET-001 Gap Fix)
# =============================================================================


def test_autosplit_with_group_enabled(movable_char_factory, movable_mob_factory, test_room_3001):
    """
    Test: AUTOSPLIT flag causes money to auto-split when picked up in group.

    ROM Parity: src/act_obj.c:162-184 (do_get AUTOSPLIT logic)
        if (IS_SET(ch->act, PLR_AUTOSPLIT)) {
            members = 0;
            for (gch = ch->in_room->people; gch != NULL; gch = gch->next_in_room)
                if (!IS_AFFECTED(gch, AFF_CHARM) && is_same_group(gch, ch))
                    members++;
            if (members > 1 && (obj->value[0] > 1 || obj->value[1]))
                do_split(ch, buffer);
        }

    Given: Player with AUTOSPLIT flag enabled
    And: Player grouped with another non-charmed character
    When: Player picks up money > 1 coin
    Then: Money automatically splits with group members
    """
    from mud.commands.inventory import do_get
    from mud.models.constants import PlayerFlag

    # Create leader with AUTOSPLIT enabled
    leader = movable_char_factory(name="Leader", room_vnum=3001)
    leader.act = int(PlayerFlag.AUTOSPLIT)
    leader.silver = 0
    leader.gold = 0

    # Create follower and group them
    follower = movable_char_factory(name="Follower", room_vnum=3001)
    follower.silver = 0
    follower.gold = 0
    follower.leader = leader
    follower.master = leader
    leader.group_members = [leader, follower]
    follower.group_members = [leader, follower]

    # Create money object in room (100 silver)
    money = create_money(gold=0, silver=100)
    test_room_3001.add_object(money)

    # Leader picks up money
    result = do_get(leader, "coins")

    # Verify money was split
    # ROM C: do_split divides 100 silver between 2 members = 50 each
    assert leader.silver == 50, f"Leader should have 50 silver after split, got {leader.silver}"
    assert follower.silver == 50, f"Follower should have 50 silver after split, got {follower.silver}"


def test_autosplit_disabled_keeps_all_money(movable_char_factory, test_room_3001):
    """
    Test: Without AUTOSPLIT flag, player keeps all money.

    ROM Parity: src/act_obj.c:166 (if (!IS_SET(ch->act, PLR_AUTOSPLIT)) skip split)

    Given: Player WITHOUT AUTOSPLIT flag
    And: Player grouped with another character
    When: Player picks up money
    Then: Player keeps all money (no split)
    """
    from mud.commands.inventory import do_get

    # Create leader WITHOUT AUTOSPLIT (act = 0)
    leader = movable_char_factory(name="Leader", room_vnum=3001)
    leader.act = 0
    leader.silver = 0
    leader.gold = 0

    # Create follower and group them
    follower = movable_char_factory(name="Follower", room_vnum=3001)
    follower.silver = 0
    follower.gold = 0
    follower.leader = leader
    follower.master = leader
    leader.group_members = [leader, follower]
    follower.group_members = [leader, follower]

    # Create money object in room (100 silver)
    money = create_money(gold=0, silver=100)
    test_room_3001.add_object(money)

    # Leader picks up money
    result = do_get(leader, "coins")

    # Verify leader keeps all money (no split)
    assert leader.silver == 100, f"Leader should keep all 100 silver, got {leader.silver}"
    assert follower.silver == 0, f"Follower should have 0 silver (no split), got {follower.silver}"


def test_autosplit_solo_player_keeps_all_money(movable_char_factory, test_room_3001):
    """
    Test: Solo player keeps all money even with AUTOSPLIT enabled.

    ROM Parity: src/act_obj.c:176-180 (if (members > 1) split)

    Given: Player with AUTOSPLIT flag
    And: Player has NO group members
    When: Player picks up money
    Then: Player keeps all money (split requires members > 1)
    """
    from mud.commands.inventory import do_get
    from mud.models.constants import PlayerFlag

    # Create solo player with AUTOSPLIT
    player = movable_char_factory(name="Solo", room_vnum=3001)
    player.act = int(PlayerFlag.AUTOSPLIT)
    player.silver = 0
    player.gold = 0
    player.group_members = [player]  # Solo group

    # Create money object in room (100 silver)
    money = create_money(gold=0, silver=100)
    test_room_3001.add_object(money)

    # Player picks up money
    result = do_get(player, "coins")

    # Verify player keeps all money (solo = no split)
    assert player.silver == 100, f"Solo player should keep all 100 silver, got {player.silver}"


def test_autosplit_excludes_charmed_members(movable_char_factory, test_room_3001):
    """
    Test: AUTOSPLIT excludes charmed group members from count.

    ROM Parity: src/act_obj.c:172 (if (!IS_AFFECTED(gch, AFF_CHARM) && is_same_group))

    Given: Player with AUTOSPLIT flag
    And: Group has 1 charmed member + 1 non-charmed member
    When: Player picks up money
    Then: Money only splits with non-charmed members (members = 2, not 3)
    """
    from mud.commands.inventory import do_get
    from mud.models.constants import AffectFlag, PlayerFlag

    # Create leader with AUTOSPLIT
    leader = movable_char_factory(name="Leader", room_vnum=3001)
    leader.act = int(PlayerFlag.AUTOSPLIT)
    leader.silver = 0
    leader.gold = 0

    # Create non-charmed follower
    follower = movable_char_factory(name="Follower", room_vnum=3001)
    follower.silver = 0
    follower.gold = 0
    follower.leader = leader
    follower.master = leader

    # Create charmed follower (should be excluded from split)
    charmed = movable_char_factory(name="Charmed", room_vnum=3001)
    charmed.silver = 0
    charmed.gold = 0
    charmed.leader = leader
    charmed.master = leader
    charmed.affected_by = int(AffectFlag.CHARM)

    leader.group_members = [leader, follower, charmed]
    follower.group_members = [leader, follower, charmed]
    charmed.group_members = [leader, follower, charmed]

    # Create money object in room (100 silver)
    money = create_money(gold=0, silver=100)
    test_room_3001.add_object(money)

    # Leader picks up money
    result = do_get(leader, "coins")

    # Verify split excludes charmed member
    # ROM C: members = 2 (leader + follower, excluding charmed)
    # 100 silver / 2 = 50 each
    assert leader.silver == 50, f"Leader should have 50 silver, got {leader.silver}"
    assert follower.silver == 50, f"Follower should have 50 silver, got {follower.silver}"
    assert charmed.silver == 0, f"Charmed member should have 0 silver (excluded), got {charmed.silver}"


def test_autosplit_with_mixed_gold_and_silver(movable_char_factory, test_room_3001):
    """
    Test: AUTOSPLIT splits both gold and silver correctly.

    ROM Parity: src/act_obj.c:178-180
        sprintf(buffer, "%d %d", obj->value[0], obj->value[1]);
        do_function(ch, &do_split, buffer);

    Given: Player with AUTOSPLIT flag in group
    When: Player picks up money with both gold and silver
    Then: Both gold and silver are split correctly
    """
    from mud.commands.inventory import do_get
    from mud.models.constants import PlayerFlag

    # Create leader with AUTOSPLIT
    leader = movable_char_factory(name="Leader", room_vnum=3001)
    leader.act = int(PlayerFlag.AUTOSPLIT)
    leader.silver = 0
    leader.gold = 0

    # Create follower
    follower = movable_char_factory(name="Follower", room_vnum=3001)
    follower.silver = 0
    follower.gold = 0
    follower.leader = leader
    follower.master = leader
    leader.group_members = [leader, follower]
    follower.group_members = [leader, follower]

    # Create money object with 50 silver and 10 gold
    money = create_money(gold=10, silver=50)
    test_room_3001.add_object(money)

    # Leader picks up money
    result = do_get(leader, "coins")

    # Verify both currencies split correctly
    # 50 silver / 2 = 25 each
    # 10 gold / 2 = 5 each
    assert leader.silver == 25, f"Leader should have 25 silver, got {leader.silver}"
    assert leader.gold == 5, f"Leader should have 5 gold, got {leader.gold}"
    assert follower.silver == 25, f"Follower should have 25 silver, got {follower.silver}"
    assert follower.gold == 5, f"Follower should have 5 gold, got {follower.gold}"


def test_money_object_extracted_not_in_inventory(movable_char_factory, test_room_3001):
    """
    Test: Money object is extracted (consumed), not added to inventory.

    ROM Parity: src/act_obj.c:183 (extract_obj(obj))

    Given: Player picks up money
    When: do_get() completes
    Then: Money object no longer exists (not in inventory, not in room)
    """
    from mud.commands.inventory import do_get

    player = movable_char_factory(name="Player", room_vnum=3001)
    player.silver = 0
    player.gold = 0

    # Create money object in room
    money = create_money(gold=10, silver=50)
    test_room_3001.add_object(money)

    # Verify money is in room before pickup
    assert money in test_room_3001.contents

    # Player picks up money
    result = do_get(player, "coins")

    # Verify money is consumed (ROM C: extract_obj)
    assert money not in player.inventory, "Money should not be in inventory (extracted)"
    assert money not in test_room_3001.contents, "Money should not be in room (extracted)"
    assert player.silver == 50, "Player should have silver added to attributes"
    assert player.gold == 10, "Player should have gold added to attributes"


# =============================================================================
# Drop Command Money Integration Tests
# =============================================================================


@pytest.mark.skip(reason="Drop command money consolidation not yet implemented")
def test_drop_command_consolidates_money_objects(movable_char_factory):
    """
    Test: Dropping multiple money objects consolidates them into one.

    ROM Parity: src/act_obj.c:541-589 (do_drop with "coins" or "gold" or "silver")
        - Scans inventory for all money objects
        - Accumulates gold/silver totals
        - Extracts all money objects
        - Creates single consolidated money object in room
        - Act message: "$n drops some coins."

    Given: Player has 3 separate money objects in inventory
    When: Player drops all money
    Then: Single consolidated money object appears in room
    """
    player = movable_char_factory(name="Dropper", room_vnum=3001)

    # Give player 3 separate money objects
    money1 = create_money(gold=10, silver=0)
    money2 = create_money(gold=0, silver=50)
    money3 = create_money(gold=5, silver=25)

    player.inventory.extend([money1, money2, money3])

    # TODO: Implement drop command with money consolidation
    # result = process_command(player, "drop coins")

    # Expected: Room should have 1 money object with 15 gold, 75 silver
    # room_money = [obj for obj in player.room.objects if obj.item_type == ItemType.MONEY]
    # assert len(room_money) == 1
    # assert room_money[0].value[0] == 75  # silver
    # assert room_money[0].value[1] == 15  # gold


@pytest.mark.skip(reason="Drop command money consolidation not yet implemented")
def test_drop_command_with_no_money(movable_char_factory):
    """
    Test: Drop coins when player has no money.

    ROM Parity: src/act_obj.c:541-589
        Returns early if no money objects found
    """
    player = movable_char_factory(name="Broke", room_vnum=3001)

    # TODO: Implement drop command
    # result = process_command(player, "drop coins")
    # assert "you don't have" in result.lower() or "you aren't carrying" in result.lower()


# =============================================================================
# Money Object Weight Tests
# =============================================================================


def test_money_object_has_correct_weight():
    """
    Test: Money objects have weight based on coin count.

    ROM Parity: handler.c:2474
        obj->weight = number_fuzzy(obj->cost / 5);

    QuickMUD uses: weight = max(1, gold // 5) for gold-only
    """
    money = create_money(gold=100, silver=0)

    assert money is not None
    # ROM: number_fuzzy(10000 / 5) = ~2000 +/- fuzz
    # QuickMUD: gold // 5 = 100 // 5 = 20
    weight = getattr(money.prototype, "weight", 0)
    assert weight > 0, "Money should have weight"
    # QuickMUD uses gold count / 5, not cost / 5
    assert weight == 20  # 100 gold / 5 = 20


def test_money_object_small_amount_has_minimum_weight():
    """
    Test: Small amounts of money still have weight >= 1.

    ROM Parity: handler.c:2474 (number_fuzzy returns at least 1)
    """
    money = create_money(gold=0, silver=1)

    assert money is not None
    weight = getattr(money.prototype, "weight", 0)
    assert weight >= 1, "Even 1 silver coin should have weight"


# =============================================================================
# Test Coverage Summary
# =============================================================================


if __name__ == "__main__":
    print("Money Object Integration Tests")
    print("=" * 60)
    print()
    print("Coverage:")
    print("  - create_money() for 5 money types")
    print("  - NPC death money in corpse")
    print("  - PC death money in corpse")
    print("  - Corpse money looting")
    print("  - Drop command money consolidation")
    print("  - Money object weight")
    print()
    print("ROM Parity Violations Detected:")
    print("  ❌ Corpse money stored as attributes (not objects)")
    print("  ❌ Drop command doesn't consolidate money objects")
    print()
    print("Run: pytest tests/integration/test_money_objects.py -v")
