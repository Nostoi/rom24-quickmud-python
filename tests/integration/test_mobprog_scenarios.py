"""
Integration tests for MobProg scenarios.

Tests complete MobProg workflows to ensure ROM C parity:
- Quest-giving NPCs
- Combat-triggered behaviors
- Multi-trigger cascades
- Complex conditional logic

ROM C Reference: src/mob_prog.c, src/mob_cmds.c
"""

from __future__ import annotations

import pytest

from mud.mobprog import (
    Trigger,
    call_prog,
    mp_death_trigger,
    mp_greet_trigger,
    mp_hprct_trigger,
    register_program_code,
    run_prog,
)
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.mob import MobProgram
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room


@pytest.fixture
def quest_room():
    """Room with quest-giver NPC."""
    room = Room(vnum=5000, name="Quest Hall")
    return room


@pytest.fixture
def quest_giver(quest_room):
    """NPC that gives quests."""
    mob = Character(name="Quest Master", is_npc=True)
    mob.position = Position.STANDING
    mob.default_pos = Position.STANDING
    quest_room.add_character(mob)
    return mob


@pytest.fixture
def test_player(quest_room):
    """Test player character."""
    player = Character(name="Hero", is_npc=False)
    player.position = Position.STANDING
    quest_room.add_character(player)
    return player


class TestQuestWorkflows:
    """Test complete quest workflows using MobProgs."""

    def test_simple_quest_accept_workflow(self, quest_giver, test_player, monkeypatch):
        """
        Test player accepts quest from NPC:
        1. Player says "quest"
        2. NPC checks if player already has quest item
        3. NPC gives quest item if not
        4. NPC explains quest

        ROM C Reference: Common quest pattern from ROM contrib areas
        """
        # Setup quest acceptance program
        quest_prog = MobProgram(
            trig_type=int(Trigger.SPEECH),
            trig_phrase="quest",
            vnum=5001,
            code="""if ispc $n
  if has_item $n 1234
    say You already have my quest, $n.
  else
    say I need you to find the Golden Widget.
    mob echoat $n You receive a quest.
  endif
endif
""",
        )
        quest_giver.mob_programs = [quest_prog]

        # Mock command processing to capture mob commands
        executed_commands = []

        def fake_process_command(char, command_line):
            executed_commands.append(command_line)
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

        # Execute: player triggers quest
        results = run_prog(
            quest_giver,
            Trigger.SPEECH,
            actor=test_player,
            phrase="I want a quest",
        )

        # Verify: NPC responded with quest offer
        assert len(results) >= 1
        assert any("quest" in r.argument.lower() for r in results)

        # Verify: Player received quest notification
        assert "You receive a quest" in test_player.messages[-1]

    def test_quest_completion_workflow(self, quest_giver, test_player, monkeypatch):
        """
        Test player completes quest:
        1. Player gives quest item to NPC
        2. NPC verifies item is correct
        3. NPC removes quest item
        4. NPC gives reward

        ROM C Reference: src/mob_prog.c:1100-1150 (mp_give_trigger)
        """
        # Setup quest completion program
        complete_prog = MobProgram(
            trig_type=int(Trigger.GIVE),
            trig_phrase="1234",  # Quest item vnum
            vnum=5002,
            code="""if ispc $n
  say Excellent work, $n!
  mob junk $o
  mob echoat $n You receive 1000 gold as a reward.
endif
""",
        )
        quest_giver.mob_programs = [complete_prog]

        # Create quest item
        quest_item_idx = ObjIndex(
            vnum=1234,
            name="golden widget",
            short_descr="a golden widget",
        )
        quest_item = Object(instance_id=None, prototype=quest_item_idx)
        if not hasattr(test_player, "carrying"):
            test_player.carrying = []
        test_player.carrying.append(quest_item)
        quest_item.carried_by = test_player

        # Mock command processing
        executed_commands = []

        def fake_process_command(char, command_line):
            executed_commands.append(command_line)
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

        run_prog(
            quest_giver,
            Trigger.GIVE,
            actor=test_player,
            arg1=quest_item,
            phrase="1234",
        )

        # Verify: NPC acknowledged completion
        assert any("excellent" in cmd.lower() for cmd in executed_commands if "say" in cmd)

        # Verify: Reward message sent
        assert "reward" in test_player.messages[-1].lower()


class TestCombatBehaviors:
    """Test combat-triggered MobProg behaviors."""

    def test_mob_casts_spell_at_low_health(self, test_player, monkeypatch):
        """
        Test mob uses special ability at low HP:
        1. Combat reduces mob to 30% HP
        2. HPCNT trigger fires
        3. Mob casts defensive spell

        ROM C Reference: src/mob_prog.c:1200-1250 (mp_hpcnt_trigger)
        """
        room = Room(vnum=6000, name="Combat Arena")
        mob = Character(name="Boss Monster", is_npc=True)
        mob.position = Position.STANDING
        mob.default_pos = Position.STANDING
        mob.max_hit = 100
        mob.hit = 100
        room.add_character(mob)
        room.add_character(test_player)

        hpcnt_prog = MobProgram(
            trig_type=int(Trigger.HPCNT),
            trig_phrase="30",
            vnum=6001,
            code="mob cast 'heal' self",
        )
        mob.mob_programs = [hpcnt_prog]

        executed_commands = []

        def fake_mob_interpret(char, command_line):
            executed_commands.append(command_line)

        monkeypatch.setattr("mud.mob_cmds.mob_interpret", fake_mob_interpret)

        mob.hit = 29
        mp_hprct_trigger(mob, test_player)

        assert any("cast" in cmd and "heal" in cmd for cmd in executed_commands)

    def test_mob_death_curse(self, test_player, monkeypatch):
        """
        Test mob executes death script:
        1. Mob dies in combat
        2. Death trigger fires
        3. Mob curses killer

        ROM C Reference: src/mob_prog.c:1150-1200 (mp_death_trigger)
        """
        room = Room(vnum=6100, name="Cursed Chamber")
        mob = Character(name="Cursed Mage", is_npc=True)
        mob.position = Position.STANDING
        mob.default_pos = Position.STANDING
        room.add_character(mob)
        room.add_character(test_player)

        # Setup death trigger
        death_prog = MobProgram(
            trig_type=int(Trigger.DEATH),
            trig_phrase="100",
            vnum=6101,
            code="""mob echoat $n You feel a curse settle upon you...
mob echo The mage's final words echo in your mind.
""",
        )
        mob.mob_programs = [death_prog]

        # Mock command processing
        executed_commands = []

        def fake_process_command(char, command_line):
            executed_commands.append(command_line)
            # Simulate message delivery
            if "echoat" in command_line and test_player.name in command_line:
                test_player.messages.append("You feel a curse settle upon you...")
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

        # Execute: trigger death (would be called by combat system)
        # Note: Death trigger is already called in apply_damage, this just tests the function

        mp_death_trigger(mob, test_player)  # Mob died, player killed it

        # Verify: Curse message delivered
        assert any("curse" in msg.lower() for msg in test_player.messages)


class TestTriggerCascades:
    """Test complex multi-trigger scenarios."""

    def test_guard_chain_reaction(self, test_player, monkeypatch):
        """
        Test cascading triggers:
        1. Player enters restricted area
        2. Guard 1 challenges player (entry trigger)
        3. Guard 2 reacts to Guard 1's speech (speech trigger)
        4. Guards coordinate response

        ROM C Reference: src/mob_prog.c:1250-1350 (trigger chaining)
        """
        room = Room(vnum=7000, name="Palace Gate")

        guard1 = Character(name="First Guard", is_npc=True)
        guard1.position = Position.STANDING
        guard1.default_pos = Position.STANDING

        guard2 = Character(name="Second Guard", is_npc=True)
        guard2.position = Position.STANDING
        guard2.default_pos = Position.STANDING

        room.add_character(guard1)
        room.add_character(guard2)
        room.add_character(test_player)

        entry_prog = MobProgram(
            trig_type=int(Trigger.GREET),
            trig_phrase="100",
            vnum=7001,
            code="""if ispc $n
  say Halt! State your business.
  mob remember $n
endif
""",
        )
        guard1.mob_programs = [entry_prog]

        speech_prog = MobProgram(
            trig_type=int(Trigger.SPEECH),
            trig_phrase="halt",
            vnum=7002,
            code="say I'll handle this, brother.",
        )
        guard2.mob_programs = [speech_prog]

        executed_commands = []
        speech_events = []

        def fake_process_command(char, command_line):
            executed_commands.append((char.name, command_line))
            if "say" in command_line.lower():
                speech_events.append(command_line)
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)
        monkeypatch.setattr("mud.mobprog.rng_mm.number_percent", lambda: 50)

        mp_greet_trigger(test_player)

        guard1_spoke = any("halt" in cmd.lower() for name, cmd in executed_commands if name == "First Guard")
        assert guard1_spoke

        if speech_events:
            run_prog(guard2, Trigger.SPEECH, actor=guard1, phrase=speech_events[0].lower())

        guard2_spoke = any("handle" in cmd.lower() for name, cmd in executed_commands if name == "Second Guard")
        assert guard2_spoke


class TestConditionalLogic:
    """Test complex conditional logic in MobProgs."""

    def test_nested_conditionals(self, quest_giver, test_player, monkeypatch):
        """
        Test nested if/else logic:
        - Check if player is PC
        - Check player level
        - Check player class
        - Give appropriate response

        ROM C Reference: src/mob_prog.c:500-800 (program interpreter)
        """
        complex_prog = MobProgram(
            trig_type=int(Trigger.SPEECH),
            trig_phrase="help",
            vnum=8001,
            code="""if ispc $n
  if level $n < 10
    say You're too inexperienced for this quest.
  else
    if level $n < 20
      say This quest is perfect for you!
    else
      say This quest might be too easy for you.
    endif
  endif
else
  say I don't speak to other monsters.
endif
""",
        )
        quest_giver.mob_programs = [complex_prog]

        executed_commands = []

        def fake_process_command(char, command_line):
            executed_commands.append(command_line)
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

        # Test: Low level player
        test_player.level = 5
        run_prog(quest_giver, Trigger.SPEECH, actor=test_player, phrase="help me")
        assert any("inexperienced" in cmd.lower() for cmd in executed_commands)

        # Test: Mid level player
        executed_commands.clear()
        test_player.level = 15
        run_prog(quest_giver, Trigger.SPEECH, actor=test_player, phrase="help me")
        assert any("perfect" in cmd.lower() for cmd in executed_commands)

        # Test: High level player
        executed_commands.clear()
        test_player.level = 25
        run_prog(quest_giver, Trigger.SPEECH, actor=test_player, phrase="help me")
        assert any("easy" in cmd.lower() for cmd in executed_commands)


class TestRecursionLimits:
    """Test MobProg recursion and call depth limits."""

    def test_mpcall_respects_max_depth(self, monkeypatch):
        """
        Test that nested mpcall respects MAX_CALL_LEVEL:
        - Program calls itself recursively
        - Should stop at depth limit

        ROM C Reference: src/mob_prog.c:300-350 (call depth checking)
        """
        from mud.mobprog import MAX_CALL_LEVEL

        room = Room(vnum=9000, name="Recursion Test")
        mob = Character(name="Recursive Mob", is_npc=True)
        mob.position = Position.STANDING
        room.add_character(mob)

        # Program that calls itself
        recursive_prog = MobProgram(
            trig_type=0,  # Not a trigger, only callable
            vnum=9001,
            code="""mob call 9001
say Depth reached
""",
        )
        mob.mob_programs = [recursive_prog]

        # Register for call_prog lookup
        register_program_code(9001, recursive_prog.code)

        executed_commands = []

        def fake_process_command(char, command_line):
            executed_commands.append(command_line)
            return ""

        monkeypatch.setattr("mud.commands.dispatcher.process_command", fake_process_command)

        # Execute: trigger recursion
        results = call_prog(9001, mob)

        # Verify: Stopped at max depth
        say_count = sum(1 for cmd in executed_commands if cmd.startswith("say"))
        assert say_count == MAX_CALL_LEVEL, f"Expected {MAX_CALL_LEVEL} calls, got {say_count}"

        # Verify: No stack overflow
        assert len(results) > 0  # Successfully completed without crash


# Mark these tests to run with integration suite
pytestmark = pytest.mark.integration
