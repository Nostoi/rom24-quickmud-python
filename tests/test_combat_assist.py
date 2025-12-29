"""
Tests for check_assist combat mechanics (ROM src/fight.c:105-181)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mud.combat.assist import check_assist
from mud.combat.engine import multi_hit, is_good, is_evil, is_neutral
from mud.models.character import Character
from mud.models.constants import AffectFlag, OffFlag, PlayerFlag, Position
from mud.models.room import Room


@pytest.fixture
def test_room():
    """Create a test room."""
    room = Room(vnum=1, name="Test Room", description="A test room.")
    room.people = []
    return room


@pytest.fixture
def create_char(test_room, monkeypatch):
    """Factory to create test characters."""

    # Mock multi_hit to just set fighting without full combat
    def mock_multi_hit(attacker, victim, dt=None):
        attacker.fighting = victim
        if not hasattr(victim, "fighting") or victim.fighting is None:
            victim.fighting = attacker
        return []

    # Patch multi_hit in the assist module
    from mud.combat import assist

    monkeypatch.setattr(assist, "multi_hit", mock_multi_hit)

    # Track group leaders
    group_leaders = {}

    def _create(name: str, is_npc: bool = False, level: int = 10, **kwargs):
        char = Character()
        char.name = name
        char.short_descr = name
        char.is_npc = is_npc
        char.level = level
        char.position = Position.STANDING
        char.fighting = None
        char.room = test_room
        char.act = 0
        char.off_flags = 0
        char.affected_by = 0
        char.alignment = 0
        char.vnum = kwargs.get("vnum", None)
        char.race = kwargs.get("race", "human")

        # Handle group membership (create leader if needed)
        group_name = kwargs.get("group", None)
        if group_name:
            if group_name not in group_leaders:
                group_leaders[group_name] = char
            char.leader = group_leaders[group_name]
        else:
            char.leader = None

        # Set additional attributes
        for key, value in kwargs.items():
            if key not in ("vnum", "race", "group"):
                setattr(char, key, value)

        test_room.people.append(char)

        # Mock send method
        char.messages = []
        char.send = lambda msg: char.messages.append(msg)

        return char

    return _create


class TestAssistPlayers:
    """Test ASSIST_PLAYERS flag (ROM lines 116-124)"""

    def test_mob_assists_player_vs_lower_level_mob(self, test_room, create_char):
        """Mob with ASSIST_PLAYERS helps player fighting weaker mob."""
        player = create_char("Player", is_npc=False, level=10)
        mob = create_char("Guardian", is_npc=True, level=15, off_flags=OffFlag.ASSIST_PLAYERS)
        victim = create_char("Rat", is_npc=True, level=8)  # mob.level + 6 = 21 > 8

        # Player attacks rat
        player.fighting = victim

        # Clear messages
        for char in test_room.people:
            char.messages = []

        check_assist(player, victim)

        # Guardian should assist (level 15 + 6 = 21 > 8)
        assert mob.fighting is not None, "Guardian should assist player"
        assert mob.fighting == victim, "Guardian should attack the victim"

    def test_mob_does_not_assist_vs_higher_level(self, test_room, create_char):
        """Mob with ASSIST_PLAYERS won't help vs higher level mob."""
        player = create_char("Player", is_npc=False, level=10)
        mob = create_char("Guardian", is_npc=True, level=10, off_flags=OffFlag.ASSIST_PLAYERS)
        victim = create_char("Dragon", is_npc=True, level=20)  # mob.level + 6 = 16 < 20

        player.fighting = victim

        check_assist(player, victim)

        # Guardian should NOT assist (level 10 + 6 = 16 < 20)
        assert mob.fighting is None, "Guardian should not assist vs higher level mob"


class TestPlayerAutoAssist:
    """Test PLR_AUTOASSIST flag (ROM lines 126-135)"""

    def test_player_autoassists_grouped_player(self, test_room, create_char):
        """Player with PLR_AUTOASSIST helps grouped player."""
        attacker = create_char("Alice", is_npc=False, level=10, group="party1")
        helper = create_char("Bob", is_npc=False, level=10, group="party1", act=PlayerFlag.AUTOASSIST)
        victim = create_char("Orc", is_npc=True, level=10)

        attacker.fighting = victim

        check_assist(attacker, victim)

        # Bob should assist Alice (same group + AUTOASSIST)
        assert helper.fighting is not None, "Bob should assist Alice"
        assert helper.fighting == victim, "Bob should attack the orc"

    def test_player_does_not_assist_different_group(self, test_room, create_char):
        """Player won't assist non-grouped player."""
        attacker = create_char("Alice", is_npc=False, level=10, group="party1")
        helper = create_char("Bob", is_npc=False, level=10, group="party2", act=PlayerFlag.AUTOASSIST)
        victim = create_char("Orc", is_npc=True, level=10)

        attacker.fighting = victim

        check_assist(attacker, victim)

        # Bob should NOT assist (different group)
        assert helper.fighting is None, "Bob should not assist different group"

    def test_charmed_mob_assists_master(self, test_room, create_char):
        """Charmed mob assists master."""
        master = create_char("Player", is_npc=False, level=10, group="party1")
        charmed = create_char("Pet", is_npc=True, level=8, group="party1", affected_by=AffectFlag.CHARM)
        victim = create_char("Orc", is_npc=True, level=10)

        master.fighting = victim

        check_assist(master, victim)

        # Charmed mob should assist master
        assert charmed.fighting is not None, "Charmed mob should assist master"


class TestNPCAssist:
    """Test NPC assist types (ROM lines 137-178)"""

    def test_assist_all(self, test_room, create_char):
        """Mob with ASSIST_ALL assists any mob."""
        attacker_mob = create_char("Goblin", is_npc=True, level=10)
        helper_mob = create_char("Orc", is_npc=True, level=10, off_flags=OffFlag.ASSIST_ALL)
        victim = create_char("Player", is_npc=False, level=10)

        attacker_mob.fighting = victim

        # Run check_assist multiple times (50% chance)
        assisted = False
        for _ in range(20):  # Try 20 times, should eventually assist
            check_assist(attacker_mob, victim)
            if helper_mob.fighting is not None:
                assisted = True
                break

        assert assisted, "Mob with ASSIST_ALL should eventually assist"

    def test_assist_race(self, test_room, create_char):
        """Mob with ASSIST_RACE assists same race."""
        attacker_mob = create_char("Goblin1", is_npc=True, level=10, race="goblin")
        helper_mob = create_char("Goblin2", is_npc=True, level=10, race="goblin", off_flags=OffFlag.ASSIST_RACE)
        other_mob = create_char("Orc", is_npc=True, level=10, race="orc", off_flags=OffFlag.ASSIST_RACE)
        victim = create_char("Player", is_npc=False, level=10)

        attacker_mob.fighting = victim

        # Run multiple times (50% chance)
        assisted = False
        for _ in range(20):
            check_assist(attacker_mob, victim)
            if helper_mob.fighting is not None:
                assisted = True
                break

        assert assisted, "Same race mob should eventually assist"
        assert other_mob.fighting is None, "Different race mob should not assist"

    def test_assist_align_good(self, test_room, create_char):
        """Mob with ASSIST_ALIGN assists same alignment (good)."""
        attacker_mob = create_char("Paladin", is_npc=True, level=10, alignment=500)  # Good
        helper_mob = create_char("Cleric", is_npc=True, level=10, alignment=400, off_flags=OffFlag.ASSIST_ALIGN)  # Good
        evil_mob = create_char("Demon", is_npc=True, level=10, alignment=-500, off_flags=OffFlag.ASSIST_ALIGN)  # Evil
        victim = create_char("Skeleton", is_npc=True, level=10, alignment=-600)  # Evil

        attacker_mob.fighting = victim

        # Run multiple times
        assisted = False
        for _ in range(20):
            check_assist(attacker_mob, victim)
            if helper_mob.fighting is not None:
                assisted = True
                break

        assert assisted, "Good mob should assist good mob"
        assert evil_mob.fighting is None, "Evil mob should not assist good mob"

    def test_assist_align_evil(self, test_room, create_char):
        """Mob with ASSIST_ALIGN assists same alignment (evil)."""
        attacker_mob = create_char("Demon", is_npc=True, level=10, alignment=-500)  # Evil
        helper_mob = create_char("Devil", is_npc=True, level=10, alignment=-400, off_flags=OffFlag.ASSIST_ALIGN)  # Evil
        victim = create_char("Paladin", is_npc=True, level=10, alignment=600)  # Good

        attacker_mob.fighting = victim

        # Run multiple times
        assisted = False
        for _ in range(20):
            check_assist(attacker_mob, victim)
            if helper_mob.fighting is not None:
                assisted = True
                break

        assert assisted, "Evil mob should assist evil mob"

    def test_assist_vnum(self, test_room, create_char):
        """Mob with ASSIST_VNUM assists same vnum."""
        attacker_mob = create_char("Guard1", is_npc=True, level=10, vnum=1000)
        helper_mob = create_char("Guard2", is_npc=True, level=10, vnum=1000, off_flags=OffFlag.ASSIST_VNUM)
        other_mob = create_char("Orc", is_npc=True, level=10, vnum=2000, off_flags=OffFlag.ASSIST_VNUM)
        victim = create_char("Player", is_npc=False, level=10)

        attacker_mob.fighting = victim

        # Run multiple times
        assisted = False
        for _ in range(20):
            check_assist(attacker_mob, victim)
            if helper_mob.fighting is not None:
                assisted = True
                break

        assert assisted, "Same vnum mob should eventually assist"
        assert other_mob.fighting is None, "Different vnum mob should not assist"


class TestAssistTargetSelection:
    """Test random target selection from victim's group (ROM lines 159-170)"""

    def test_assists_random_group_member(self, test_room, create_char):
        """Assisting mob targets random member of victim's group."""
        attacker_mob = create_char("Orc", is_npc=True, level=10)
        helper_mob = create_char("Goblin", is_npc=True, level=10, off_flags=OffFlag.ASSIST_ALL)

        victim1 = create_char("Alice", is_npc=False, level=10, group="heroes")
        victim2 = create_char("Bob", is_npc=False, level=10, group="heroes")
        victim3 = create_char("Carol", is_npc=False, level=10, group="heroes")

        attacker_mob.fighting = victim1

        # Run multiple times and collect targets
        targets = set()
        for _ in range(50):
            helper_mob.fighting = None  # Reset
            check_assist(attacker_mob, victim1)
            if helper_mob.fighting is not None:
                targets.add(helper_mob.fighting.name)

        # Should target at least 2 different group members (random selection)
        assert len(targets) >= 2, "Should target multiple group members randomly"


class TestAssistConditions:
    """Test assist conditions (ROM lines 113, 156)"""

    def test_sleeping_mob_does_not_assist(self, test_room, create_char):
        """Sleeping mob won't assist."""
        attacker_mob = create_char("Orc", is_npc=True, level=10)
        helper_mob = create_char(
            "Goblin", is_npc=True, level=10, off_flags=OffFlag.ASSIST_ALL, position=Position.SLEEPING
        )
        victim = create_char("Player", is_npc=False, level=10)

        attacker_mob.fighting = victim

        check_assist(attacker_mob, victim)

        assert helper_mob.fighting is None, "Sleeping mob should not assist"

    def test_already_fighting_mob_does_not_assist(self, test_room, create_char):
        """Mob already fighting won't assist."""
        attacker_mob = create_char("Orc", is_npc=True, level=10)
        helper_mob = create_char("Goblin", is_npc=True, level=10, off_flags=OffFlag.ASSIST_ALL)
        victim = create_char("Player1", is_npc=False, level=10)
        other_enemy = create_char("Player2", is_npc=False, level=10)

        attacker_mob.fighting = victim
        helper_mob.fighting = other_enemy  # Already fighting someone else

        check_assist(attacker_mob, victim)

        assert helper_mob.fighting == other_enemy, "Mob should continue fighting current opponent"


class TestAssistIntegration:
    """Test check_assist integration with multi_hit"""

    def test_assist_triggered_during_combat(self, test_room, create_char):
        """check_assist is called during multi_hit."""
        attacker = create_char("Player", is_npc=False, level=10, group="party")
        helper = create_char("Ally", is_npc=False, level=10, group="party", act=PlayerFlag.AUTOASSIST)
        victim = create_char("Orc", is_npc=True, level=10)

        # Give attacker minimal stats to avoid death
        attacker.hit = 100
        attacker.max_hit = 100
        victim.hit = 100
        victim.max_hit = 100

        # Initiate combat with multi_hit
        multi_hit(attacker, victim)

        # Helper should have assisted
        assert helper.fighting is not None, "Ally should assist after combat starts"
