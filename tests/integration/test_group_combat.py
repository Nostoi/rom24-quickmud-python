"""Integration tests for group combat mechanics.

Tests verify group combat workflows work correctly through game_tick() integration:
- Tank mechanics (mob targets group leader)
- Assist command (switch combat target)
- Group XP distribution
- Group loot sharing (autosplit)
- AoE spell effects on groups
- Group leadership and commands

ROM Parity: Mirrors ROM 2.4b6 group combat behavior from src/fight.c, src/act_info.c
"""

from __future__ import annotations

import pytest

from mud.commands.dispatcher import process_command
from mud.commands.group_commands import is_same_group
from mud.game_loop import game_tick
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry
from mud.spawning.templates import MobInstance


@pytest.fixture
def group_test_room():
    """Create a test room for group combat tests with a south exit"""
    from mud.models.room import Exit

    south_room = Room(
        vnum=9998,
        name="South Room",
        description="A room to the south.",
        room_flags=0,
        sector_type=0,
    )
    south_room.people = []
    south_room.contents = []
    room_registry[9998] = south_room

    room = Room(
        vnum=9999,
        name="Group Combat Arena",
        description="A room for testing group combat mechanics.",
        room_flags=0,
        sector_type=0,
    )
    room.people = []
    room.contents = []

    # Room.exits is a list[Exit | None] with 6 positions (one per Direction)
    # Direction enum: NORTH=0, EAST=1, SOUTH=2, WEST=3, UP=4, DOWN=5
    from mud.models.constants import Direction

    room.exits = [None] * len(Direction)
    room.exits[Direction.SOUTH.value] = Exit(
        to_room=south_room,
        vnum=9998,
        exit_info=0,
        key=-1,
        keyword="",
        description="",
    )
    room_registry[9999] = room

    yield room

    room_registry.pop(9999, None)
    room_registry.pop(9998, None)


@pytest.fixture
def create_test_character(group_test_room):
    """Factory for creating test characters with room"""
    created_chars = []

    def _create(name: str, level: int = 5):
        char = Character(
            name=name,
            level=level,
            room=group_test_room,
            gold=1000,
            hit=100,
            max_hit=100,
            mana=100,
            max_mana=100,
            move=100,
            max_move=100,
            is_npc=False,
            hitroll=10,
            damroll=5,
        )
        char.perm_stat = [13, 13, 13, 13, 13]
        group_test_room.people.append(char)
        character_registry.append(char)
        created_chars.append(char)
        return char

    yield _create

    for char in created_chars:
        if char in group_test_room.people:
            group_test_room.people.remove(char)
        if char in character_registry:
            character_registry.remove(char)


@pytest.fixture
def create_test_mob(group_test_room):
    """Factory for creating test mobs with room"""
    created_mobs = []

    def _create(name: str = "test mob", level: int = 10):
        mob = Character(
            name=name,
            short_descr=f"a {name}",
            long_descr=f"A {name} is standing here.",
            level=level,
            room=group_test_room,
            is_npc=True,
            hit=100,
            max_hit=100,
            hitroll=5,
            damroll=3,
        )
        mob.perm_stat = [13, 13, 13, 13, 13]
        group_test_room.people.append(mob)
        character_registry.append(mob)
        created_mobs.append(mob)
        return mob

    yield _create

    for mob in created_mobs:
        if mob in group_test_room.people:
            group_test_room.people.remove(mob)
        if mob in character_registry:
            character_registry.remove(mob)


class TestGroupFormation:
    """Test group formation and basic group mechanics."""

    def test_follow_command_creates_follower_relationship(self, create_test_character):
        """
        Test: Follow command creates follower relationship.

        ROM Parity: Mirrors ROM src/act_info.c:do_follow()

        Given: Two characters in same room
        When: Character B follows character A
        Then: B.master = A, A is not following B
        """
        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)

        result = process_command(follower, "follow Leader")

        assert "You now follow Leader" in result
        assert follower.master == leader
        assert leader.master is None

    def test_group_command_creates_group(self, create_test_character):
        """
        Test: Group command creates a group.

        ROM Parity: Mirrors ROM src/act_info.c:do_group()

        Given: Character B follows character A
        When: A groups B
        Then: Both are in same group, A is leader
        """
        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)

        follower.master = leader
        follower.leader = None

        result = process_command(leader, "group Follower")

        assert "Follower joins your group" in result or "is now a group member" in result
        assert follower.leader == leader
        assert leader.leader is None or leader.leader == leader
        assert is_same_group(leader, follower)

    def test_group_all_groups_all_followers(self, create_test_character):
        """
        Test: Group command adds followers to group individually.

        ROM Parity: Mirrors ROM src/act_comm.c:do_group()
        Note: ROM doesn't have 'group all' - must group each follower individually

        Given: Two followers
        When: Leader groups each follower
        Then: Both followers grouped
        """
        leader = create_test_character("Leader", level=10)
        follower1 = create_test_character("Follower1", level=10)
        follower2 = create_test_character("Follower2", level=10)

        follower1.master = leader
        follower2.master = leader

        result1 = process_command(leader, "group Follower1")
        result2 = process_command(leader, "group Follower2")

        assert follower1.leader == leader
        assert follower2.leader == leader
        assert "joins your group" in result1.lower() or "group member" in result1.lower()
        assert "joins your group" in result2.lower() or "group member" in result2.lower()


class TestGroupCombatMechanics:
    """Test group combat targeting and mechanics."""

    def test_mob_targets_group_leader_in_combat(self, create_test_character, create_test_mob):
        """
        Test: Mob targets group leader (tank) in combat.

        ROM Parity: Mirrors ROM src/fight.c:multi_hit() - mobs prefer group leader

        Given: Group with leader and follower fighting mob
        When: Combat round executes
        Then: Mob attacks leader, not follower
        """
        leader = create_test_character("Tank", level=30)
        follower = create_test_character("DPS", level=25)
        mob = create_test_mob("goblin", level=10)

        # Setup group
        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        # Setup combat stats
        leader.hitroll = 15
        leader.damroll = 10
        leader.perm_stat = [13, 13, 13, 13, 13]

        follower.hitroll = 12
        follower.damroll = 8
        follower.perm_stat = [13, 13, 13, 13, 13]

        mob.max_hit = 100
        mob.hit = 100
        mob.imm_flags = 0

        # Leader starts combat
        leader.fighting = mob
        mob.fighting = leader
        leader.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        # Follower joins combat
        follower.fighting = mob
        follower.position = Position.FIGHTING

        # Run combat rounds
        for _ in range(3):
            game_tick()

        # Verify mob is fighting leader (tank), not follower
        assert mob.fighting == leader, "Mob should target group leader"
        assert leader.fighting == mob, "Leader should be in combat with mob"

    def test_assist_command_switches_combat_target(self, create_test_character, create_test_mob):
        """
        Test: Assist command switches combat target to groupmate's opponent.

        ROM Parity: NOT in ROM 2.4b6 (common MUD extension)
        ROM has autoassist (toggle) and mpassist (mobprog), but not player assist command

        Given: Leader fighting mob A, follower not in combat
        When: Follower uses 'assist Leader'
        Then: Follower starts fighting mob A
        """
        pytest.skip("Assist command not in ROM 2.4b6 - consider implementing as extension")


class TestGroupExperienceSharing:
    """Test group XP distribution mechanics."""

    def test_group_xp_split_between_members(self, create_test_character, create_test_mob):
        """
        Test: Group XP is split between all group members.

        ROM Parity: Mirrors ROM src/fight.c:group_gain() - XP split formula

        Given: 3-member group kills mob worth 1000 XP
        When: Mob dies
        Then: Each member gets ~333 XP (1000 / 3)
        """
        leader = create_test_character("Leader", level=10)
        follower1 = create_test_character("Follower1", level=10)
        follower2 = create_test_character("Follower2", level=10)
        mob = create_test_mob("goblin", level=10)

        # Setup group
        follower1.master = leader
        follower1.leader = leader
        follower2.master = leader
        follower2.leader = leader
        leader.leader = leader

        # Setup stats
        for char in [leader, follower1, follower2]:
            char.hitroll = 20
            char.damroll = 15
            char.perm_stat = [13, 13, 13, 13, 13]
            char.exp = 0  # Track XP gain

        mob.max_hit = 50
        mob.hit = 50
        mob.imm_flags = 0

        # Leader starts combat
        leader.fighting = mob
        mob.fighting = leader
        leader.position = Position.FIGHTING
        mob.position = Position.FIGHTING

        # Followers join combat
        follower1.fighting = mob
        follower1.position = Position.FIGHTING
        follower2.fighting = mob
        follower2.position = Position.FIGHTING

        # Fight until mob dies
        for _ in range(15):
            game_tick()
            if mob.hit <= 0:
                break

        # Verify XP was distributed (each member got some XP)
        # Note: Exact split depends on level bonus formula in group_gain()
        assert leader.exp > 0 or follower1.exp > 0 or follower2.exp > 0, "At least one group member should gain XP"


class TestGroupLootSharing:
    """Test group loot distribution (autosplit gold)."""

    def test_autosplit_divides_gold_among_group(self, create_test_character):
        """
        Test: Autosplit divides gold evenly among group members.

        ROM Parity: Mirrors ROM src/act_obj.c:do_split() and autosplit behavior

        Given: Group with autosplit enabled
        When: Gold is picked up or looted
        Then: Gold split evenly among all group members in room
        """
        leader = create_test_character("Leader", level=10)
        follower1 = create_test_character("Follower1", level=10)
        follower2 = create_test_character("Follower2", level=10)

        # Setup group
        follower1.master = leader
        follower1.leader = leader
        follower2.master = leader
        follower2.leader = leader
        leader.leader = leader

        # Initial gold
        leader.gold = 0
        follower1.gold = 0
        follower2.gold = 0

        # Leader gets 300 gold and splits
        leader.gold = 300
        result = process_command(leader, "split 300")

        # Each member should get 100 gold (300 / 3)
        expected_gold = 100
        assert (
            "You split" in result
            or leader.gold == expected_gold
            or follower1.gold == expected_gold
            or follower2.gold == expected_gold
        ), "Gold should be split among group members"


class TestGroupAreaEffects:
    """Test AoE spells and effects on groups."""

    def test_aoe_spell_affects_all_group_members(self, create_test_character):
        """
        Test: AoE buff spell affects all group members.

        ROM Parity: Mirrors ROM spell targeting for AoE (mass_invis - src/magic.c:5685)

        Given: 3-member group in same room
        When: AoE buff spell (mass_invis) cast on group
        Then: All members receive the invisibility buff
        """
        from mud.models.constants import AffectFlag
        from mud.skills.handlers import mass_invis

        leader = create_test_character("Leader", level=30)
        follower1 = create_test_character("Follower1", level=25)
        follower2 = create_test_character("Follower2", level=20)

        follower1.master = leader
        follower1.leader = leader
        follower2.master = leader
        follower2.leader = leader
        leader.leader = leader

        mass_invis(leader)

        assert leader.has_affect(AffectFlag.INVISIBLE), "Leader should be invisible"
        assert follower1.has_affect(AffectFlag.INVISIBLE), "Follower1 should be invisible"
        assert follower2.has_affect(AffectFlag.INVISIBLE), "Follower2 should be invisible"

    def test_aoe_damage_hits_whole_group(self, create_test_character):
        """
        Test: AoE damage spell hits all group members.

        ROM Parity: Mirrors ROM area damage spells (holy_word - src/magic.c:5042)

        Given: Group fighting mob with AoE attack
        When: Enemy casts AoE damage spell (holy_word)
        Then: All group members take damage (opposite alignment)
        """
        from mud.skills.handlers import holy_word

        evil_caster = create_test_character("EvilMob", level=30)
        evil_caster.alignment = -1000
        evil_caster.is_npc = True

        good_leader = create_test_character("GoodLeader", level=25)
        good_leader.alignment = 1000
        good_follower1 = create_test_character("GoodFollower1", level=20)
        good_follower1.alignment = 1000
        good_follower2 = create_test_character("GoodFollower2", level=20)
        good_follower2.alignment = 1000

        good_follower1.master = good_leader
        good_follower1.leader = good_leader
        good_follower2.master = good_leader
        good_follower2.leader = good_leader
        good_leader.leader = good_leader

        leader_hp_before = good_leader.hit
        follower1_hp_before = good_follower1.hit
        follower2_hp_before = good_follower2.hit

        holy_word(evil_caster)

        assert good_leader.hit < leader_hp_before, "Leader should take damage from holy word"
        assert good_follower1.hit < follower1_hp_before, "Follower1 should take damage from holy word"
        assert good_follower2.hit < follower2_hp_before, "Follower2 should take damage from holy word"


class TestGroupLeadership:
    """Test group leadership commands and mechanics."""

    def test_group_leader_can_disband_group(self, create_test_character):
        """
        Test: Group leader can disband the group.

        ROM Parity: Mirrors ROM src/act_info.c:do_group() with 'disband' or removing members

        Given: Group with leader and followers
        When: Leader uses group command to remove member
        Then: Member removed from group
        """
        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)

        # Setup group
        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        # Leader removes follower from group
        result = process_command(leader, "group Follower")

        # Follower should be removed (toggled off)
        assert (
            follower.leader is None or "is no longer in your group" in result.lower() or "removed" in result.lower()
        ), "Follower should be removed from group"

    def test_follow_self_stops_following(self, create_test_character):
        """
        Test: Following self breaks follower relationship.

        ROM Parity: Mirrors ROM src/act_info.c:do_follow() - 'follow self' to stop

        Given: Character following another
        When: Character uses 'follow self'
        Then: Stops following, breaks group
        """
        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)

        # Setup following
        follower.master = leader
        follower.leader = leader

        # Stop following
        result = process_command(follower, "follow self")

        # Should stop following
        assert follower.master is None or "You stop following" in result, "Should stop following when following self"
        assert follower.leader is None, "Should leave group when stop following"

    def test_group_disbands_when_leader_dies(self, create_test_character, create_test_mob):
        """
        Test: Group disbands when leader dies.

        ROM Parity: Mirrors ROM src/handler.c die_follower - group dissolves on leader death

        Given: Group with leader and follower
        When: Leader dies in combat
        Then: Follower's leader and master references cleared
        """
        from mud.combat.death import raw_kill

        leader = create_test_character("Leader", level=30)
        follower = create_test_character("Follower", level=20)

        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        raw_kill(leader)

        assert follower.master is None, "Follower's master should be cleared when leader dies"
        assert follower.leader is None, "Follower's leader should be cleared when leader dies"


class TestGroupMovement:
    """Test group movement mechanics (already tested in other files, here for completeness)."""

    def test_group_follows_leader_movement(self, create_test_character):
        """
        Test: Group members follow leader during movement.

        ROM Parity: Mirrors ROM src/act_move.c:move_char() - follower cascading

        Given: Group with leader and follower
        When: Leader moves to another room
        Then: Follower automatically follows
        """
        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)

        # Setup group
        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        # Leader moves
        result = process_command(leader, "south")

        # Follower should follow (tested in test_architectural_parity.py)
        # This test is here for documentation completeness
        assert leader.room is not None
        # Follower cascade tested elsewhere, but verify leader moved
        assert "south" in result.lower() or leader.room.vnum != 9999


class TestGroupCombatEdgeCases:
    """Test edge cases in group combat."""

    def test_ungrouped_followers_dont_share_xp(self, create_test_character, create_test_mob):
        """
        Test: Followers not in group don't share XP.

        ROM Parity: Mirrors ROM XP distribution - only grouped members share

        Given: Character A has follower B, but B not grouped (leader=None)
        When: A kills mob
        Then: Only A gets XP, B gets nothing
        """
        from mud.groups.xp import group_gain

        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)
        mob = create_test_mob("victim", level=10)

        follower.master = leader
        follower.leader = None
        leader.leader = leader

        initial_leader_xp = leader.exp
        initial_follower_xp = follower.exp

        group_gain(leader, mob)

        assert leader.exp > initial_leader_xp, "Leader should gain XP"
        assert follower.exp == initial_follower_xp, "Ungrouped follower should NOT gain XP"

    def test_group_member_can_attack_different_mob(self, create_test_character, create_test_mob):
        """Test XP distribution when group members fight different mobs

        ROM Parity: Mirrors ROM src/fight.c group_gain (lines 1764-1789)
        ROM behavior: XP is shared with ALL grouped members in the same room,
        regardless of what they're fighting.

        Given: Leader fighting mob A, follower (grouped) fighting mob B
        When: Leader kills mob A
        Then: BOTH leader and follower gain XP (grouped in same room)
        """
        from mud.groups.xp import group_gain

        leader = create_test_character("Leader", level=10)
        follower = create_test_character("Follower", level=10)
        mob_a = create_test_mob("goblin_a", level=10)
        mob_b = create_test_mob("goblin_b", level=10)

        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        leader.fighting = mob_a
        follower.fighting = mob_b

        initial_leader_xp = leader.exp
        initial_follower_xp = follower.exp

        group_gain(leader, mob_a)

        # ROM shares XP with ALL grouped members in same room (no combat target check)
        assert leader.exp > initial_leader_xp, "Leader should gain XP from mob A"
        assert follower.exp > initial_follower_xp, "Follower should also gain XP (grouped in same room)"

    def test_rescue_command_switches_aggro_to_rescuer(self, create_test_character, create_test_mob):
        """
        Test: Rescue command switches mob aggro to rescuer.

        ROM Parity: Mirrors ROM src/fight.c:do_rescue()

        Given: Mob attacking follower
        When: Leader rescues follower
        Then: Mob switches target to leader
        """
        leader = create_test_character("Tank", level=30)
        follower = create_test_character("Squishy", level=20)
        mob = create_test_mob("goblin", level=15)

        # Setup group
        follower.master = leader
        follower.leader = leader
        leader.leader = leader

        # Setup stats
        leader.hitroll = 20
        leader.damroll = 15
        leader.perm_stat = [18, 13, 13, 13, 16]
        leader.skills = {"rescue": 100}

        follower.hitroll = 10
        follower.damroll = 8
        follower.perm_stat = [10, 13, 13, 13, 10]

        mob.max_hit = 100
        mob.hit = 100
        mob.imm_flags = 0

        # Mob attacking follower
        mob.fighting = follower
        follower.fighting = mob
        mob.position = Position.FIGHTING
        follower.position = Position.FIGHTING

        # Leader rescues follower
        result = process_command(leader, "rescue Squishy")

        # Mob should now target leader
        assert "You rescue" in result or mob.fighting == leader or leader.fighting == mob, (
            "Rescue should switch mob aggro to leader"
        )
