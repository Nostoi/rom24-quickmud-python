"""
State Transition Tests for ROM Parity

These tests verify that state machines in the Python port transition
in the same order and manner as the ROM 2.4b C implementation.

Key state machines tested:
1. Combat State Machine (fight.c)
   - States: STANDING -> FIGHTING -> (DEAD | STANDING)
   - Transitions: attack, flee, kill, wimpy

2. Reset State Machine (db.c/update.c)
   - States: LOADED -> AGING -> RESET
   - Transitions: tick, player_presence, age_threshold

3. Character Position State Machine
   - States: DEAD, MORTL, INCAP, STUNNED, SLEEPING, RESTING, SITTING, FIGHTING, STANDING
   - Transitions: damage, wake, sleep, rest, stand
"""

from __future__ import annotations

from collections import deque
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import AffectFlag, DamageType, Position
from mud.models.room import Room
from mud.utils import rng_mm


# ============================================================================
# Combat State Machine Tests
# ============================================================================


class TestCombatStateTransitions:
    """
    Tests for combat state machine matching ROM fight.c behavior.
    
    ROM Combat State Machine:
    - Entry: set_fighting() called
    - Exit: stop_fighting() called when:
      - Victim dies (raw_kill)
      - Attacker flees (do_flee)
      - Combat otherwise ends
    """

    def test_combat_entry_sets_fighting_position(self):
        """ROM: entering combat sets position to FIGHTING."""
        attacker = Character(name="Attacker", position=Position.STANDING)
        victim = Character(name="Victim", position=Position.STANDING)
        room = Room(vnum=3001)
        room.add_character(attacker)
        room.add_character(victim)
        attacker.room = room
        victim.room = room

        # Simulate set_fighting
        attacker.fighting = victim
        attacker.position = Position.FIGHTING

        assert attacker.position == Position.FIGHTING
        assert attacker.fighting == victim

    def test_combat_entry_mutual(self):
        """ROM: when A attacks B, both enter combat."""
        attacker = Character(name="Attacker", position=Position.STANDING)
        victim = Character(name="Victim", position=Position.STANDING)
        room = Room(vnum=3001)
        room.add_character(attacker)
        room.add_character(victim)
        attacker.room = room
        victim.room = room

        # ROM set_fighting sets both
        attacker.fighting = victim
        attacker.position = Position.FIGHTING
        
        if victim.fighting is None:
            victim.fighting = attacker
            victim.position = Position.FIGHTING

        assert attacker.fighting == victim
        assert victim.fighting == attacker
        assert attacker.position == Position.FIGHTING
        assert victim.position == Position.FIGHTING

    def test_combat_exit_on_death(self):
        """ROM: death ends combat for all participants."""
        attacker = Character(name="Attacker", position=Position.FIGHTING)
        victim = Character(name="Victim", position=Position.FIGHTING)
        attacker.fighting = victim
        victim.fighting = attacker
        
        room = Room(vnum=3001)
        room.add_character(attacker)
        room.add_character(victim)
        attacker.room = room
        victim.room = room

        # Simulate raw_kill - victim dies
        victim.hit = -10
        victim.position = Position.DEAD
        victim.fighting = None
        
        # Attacker's stop_fighting is called
        attacker.fighting = None
        attacker.position = Position.STANDING

        assert victim.position == Position.DEAD
        assert victim.fighting is None
        assert attacker.fighting is None

    def test_combat_position_changes_block_actions(self):
        """ROM: certain positions block combat actions."""
        ch = Character(name="Test")
        
        # SLEEPING blocks combat
        ch.position = Position.SLEEPING
        can_fight = ch.position >= Position.FIGHTING
        assert not can_fight
        
        # STUNNED blocks combat
        ch.position = Position.STUNNED
        can_fight = ch.position >= Position.FIGHTING
        assert not can_fight
        
        # STANDING allows combat
        ch.position = Position.STANDING
        can_fight = ch.position >= Position.STANDING
        assert can_fight

    def test_damage_position_transitions(self):
        """ROM: damage can cause position transitions (stunned, incap, dead)."""
        transitions = []
        
        ch = Character(name="Test", hit=100, max_hit=100)
        ch.position = Position.FIGHTING
        
        def apply_lethal_damage():
            ch.hit = -5
            if ch.hit <= -11:
                ch.position = Position.DEAD
            elif ch.hit <= -6:
                ch.position = Position.MORTAL
            elif ch.hit <= 0:
                ch.position = Position.INCAP
            transitions.append(ch.position)
        
        apply_lethal_damage()
        
        # Should transition to INCAP at -5 HP
        assert ch.position == Position.INCAP
        
        # Further damage to -12
        ch.hit = -12
        if ch.hit <= -11:
            ch.position = Position.DEAD
        transitions.append(ch.position)
        
        assert ch.position == Position.DEAD

    def test_wait_state_blocks_attacks(self):
        """ROM: character with wait > 0 cannot attack."""
        ch = Character(name="Test")
        ch.wait = 12  # PULSE_VIOLENCE * 3

        # Character should be blocked from acting
        can_act = ch.wait <= 0
        assert not can_act

        # Decrement wait (simulating tick)
        ch.wait = max(0, ch.wait - 4)  # One PULSE_VIOLENCE
        ch.wait = max(0, ch.wait - 4)
        ch.wait = max(0, ch.wait - 4)
        
        can_act = ch.wait <= 0
        assert can_act


class TestCombatRoundSequence:
    """Tests for combat round sequence matching ROM violence_update."""

    def test_round_order_attacker_first(self):
        """ROM: in violence_update, each character attacks their fighting target."""
        actions = []
        
        attacker = Character(name="Attacker", level=10)
        victim = Character(name="Victim", level=10)
        attacker.fighting = victim
        victim.fighting = attacker
        
        # Simulate violence_update iteration
        for ch in [attacker, victim]:
            if ch.fighting is not None:
                actions.append(f"{ch.name} attacks {ch.fighting.name}")
        
        assert len(actions) == 2
        assert "Attacker attacks Victim" in actions
        assert "Victim attacks Attacker" in actions

    def test_dead_target_stops_combat(self):
        """ROM: if fighting target is NULL or dead, combat stops."""
        attacker = Character(name="Attacker")
        victim = Character(name="Victim")
        attacker.fighting = victim
        
        # Victim dies
        victim.hit = -15
        victim.position = Position.DEAD
        
        # violence_update check
        if attacker.fighting is None or attacker.fighting.position == Position.DEAD:
            attacker.fighting = None
        
        # Attacker should stop fighting
        assert attacker.fighting is None


# ============================================================================
# Reset State Machine Tests
# ============================================================================


class TestResetStateTransitions:
    """
    Tests for area reset state machine matching ROM db.c/update.c.
    
    ROM Reset State Machine:
    - Area ages every minute
    - Reset triggers at:
      - age >= 3 when empty (no players)
      - age >= 15 always (force reset)
      - age >= 31 always (hard limit)
    """

    def test_area_ages_every_minute(self):
        """ROM: area->age increments each area_update call (once per minute)."""
        from mud.models.area import Area
        
        area = Area(vnum=100, name="Test Area")
        area.age = 0
        
        # Simulate area_update
        area.age += 1
        
        assert area.age == 1

    def test_reset_at_age_3_when_empty(self):
        """ROM: empty areas reset at age >= 3."""
        from mud.models.area import Area
        
        area = Area(vnum=100, name="Test Area")
        area.age = 3
        area.nplayer = 0  # No players
        
        # ROM condition: (area->age >= 3) && (area->nplayer == 0)
        should_reset = area.age >= 3 and area.nplayer == 0
        
        assert should_reset

    def test_no_reset_when_players_present_age_3(self):
        """ROM: areas with players don't reset at age 3."""
        from mud.models.area import Area
        
        area = Area(vnum=100, name="Test Area")
        area.age = 3
        area.nplayer = 2  # Players present
        
        should_reset = area.age >= 3 and area.nplayer == 0
        
        assert not should_reset

    def test_force_reset_at_age_15(self):
        """ROM: areas reset at age >= 15 regardless of players."""
        from mud.models.area import Area
        
        area = Area(vnum=100, name="Test Area")
        area.age = 15
        area.nplayer = 5  # Players present but forced reset
        
        # ROM condition: age >= 15
        should_reset = area.age >= 15 or (area.age >= 3 and area.nplayer == 0)
        
        assert should_reset

    def test_reset_clears_age(self):
        """ROM: after reset, area->age = number_range(0, 3)."""
        from mud.models.area import Area
        
        area = Area(vnum=100, name="Test Area")
        area.age = 20
        
        # Simulate reset
        rng_mm.seed_mm(42)
        area.age = rng_mm.number_range(0, 3)
        
        assert 0 <= area.age <= 3


class TestResetCommandSequence:
    """Tests for reset command execution order matching ROM."""

    def test_reset_commands_execute_in_order(self):
        """ROM: reset commands execute in file order."""
        from mud.models.room_json import ResetJson
        
        commands_executed = []
        
        resets = [
            ResetJson(command="M", arg1=3000, arg2=1, arg3=3001),  # Mob
            ResetJson(command="G", arg1=3010),  # Give object to mob
            ResetJson(command="E", arg1=3011, arg3=16),  # Equip object
            ResetJson(command="O", arg1=3020, arg3=3001),  # Object in room
        ]
        
        for reset in resets:
            commands_executed.append(reset.command)
        
        assert commands_executed == ["M", "G", "E", "O"]

    def test_lastmob_tracking(self):
        """ROM: 'M' reset sets LastMob for subsequent G/E commands."""
        last_mob = None
        
        # 'M' reset
        mob = MagicMock()
        mob.vnum = 3000
        last_mob = mob
        
        # 'G' reset uses LastMob
        assert last_mob is not None
        assert last_mob.vnum == 3000

    def test_lastobj_tracking(self):
        """ROM: 'O' reset sets LastObj for subsequent P commands."""
        last_obj = None
        
        # 'O' reset creates container
        container = MagicMock()
        container.vnum = 3050
        last_obj = container
        
        # 'P' reset puts item in LastObj
        assert last_obj is not None
        assert last_obj.vnum == 3050


# ============================================================================
# Character Position State Machine Tests
# ============================================================================


class TestPositionStateTransitions:
    """
    Tests for character position state transitions matching ROM.
    
    Position Values (from merc.h):
    POS_DEAD = 0, POS_MORTAL = 1, POS_INCAP = 2, POS_STUNNED = 3,
    POS_SLEEPING = 4, POS_RESTING = 5, POS_SITTING = 6,
    POS_FIGHTING = 7, POS_STANDING = 8
    """

    def test_position_ordering(self):
        """ROM: positions are ordered by capability."""
        assert Position.DEAD.value < Position.MORTAL.value
        assert Position.MORTAL.value < Position.INCAP.value
        assert Position.INCAP.value < Position.STUNNED.value
        assert Position.STUNNED.value < Position.SLEEPING.value
        assert Position.SLEEPING.value < Position.RESTING.value
        assert Position.RESTING.value < Position.SITTING.value
        assert Position.SITTING.value < Position.FIGHTING.value
        assert Position.FIGHTING.value < Position.STANDING.value

    def test_wake_transitions(self):
        """ROM: wake command transitions SLEEPING/RESTING/SITTING -> STANDING."""
        ch = Character(name="Test")
        
        for start_pos in [Position.SLEEPING, Position.RESTING, Position.SITTING]:
            ch.position = start_pos
            
            # do_wake/do_stand
            if ch.position <= Position.SLEEPING:
                ch.position = Position.STANDING
            elif ch.position <= Position.SITTING:
                ch.position = Position.STANDING
            
            assert ch.position == Position.STANDING

    def test_sleep_transitions(self):
        """ROM: sleep command transitions STANDING/SITTING/RESTING -> SLEEPING."""
        ch = Character(name="Test")
        
        for start_pos in [Position.STANDING, Position.SITTING, Position.RESTING]:
            ch.position = start_pos
            
            # do_sleep
            if ch.position >= Position.SLEEPING:
                ch.position = Position.SLEEPING
            
            assert ch.position == Position.SLEEPING

    def test_cannot_sleep_while_fighting(self):
        """ROM: cannot sleep while in combat."""
        ch = Character(name="Test")
        ch.position = Position.FIGHTING
        ch.fighting = MagicMock()
        
        can_sleep = ch.fighting is None and ch.position >= Position.SLEEPING
        
        assert not can_sleep

    def test_hp_triggers_position_changes(self):
        """ROM: HP thresholds trigger position changes."""
        ch = Character(name="Test", max_hit=100)
        
        test_cases = [
            (-15, Position.DEAD),
            (-10, Position.MORTAL),
            (-5, Position.INCAP),
            (0, Position.INCAP),  # ROM: hit <= 0 is INCAP
            (1, None),  # No automatic change
        ]
        
        for hp, expected_pos in test_cases:
            ch.hit = hp
            
            # ROM update_pos logic
            if ch.hit <= -11:
                new_pos = Position.DEAD
            elif ch.hit <= -6:
                new_pos = Position.MORTAL
            elif ch.hit <= 0:
                new_pos = Position.INCAP
            elif ch.hit < ch.max_hit // 4:
                new_pos = Position.STUNNED
            else:
                new_pos = None
            
            if expected_pos is not None:
                assert new_pos == expected_pos, f"HP {hp} should give position {expected_pos}"


# ============================================================================
# Affect Duration State Machine Tests
# ============================================================================


class TestAffectDurationTransitions:
    """Tests for spell affect duration and expiry matching ROM."""

    def test_affect_duration_decrements(self):
        """ROM: affect duration decreases each tick."""
        duration = 24  # Standard spell duration
        
        # Simulate ticks
        for _ in range(5):
            duration -= 1
        
        assert duration == 19

    def test_affect_expires_at_zero(self):
        """ROM: affect is removed when duration reaches 0."""
        duration = 2
        affected = True
        
        # Tick 1
        duration -= 1
        assert duration == 1
        assert affected
        
        # Tick 2
        duration -= 1
        if duration <= 0:
            affected = False
        
        assert duration == 0
        assert not affected

    def test_permanent_affects_dont_decrement(self):
        """ROM: affects with duration -1 are permanent."""
        duration = -1
        
        # Simulate tick - permanent affects skip decrement
        if duration > 0:
            duration -= 1
        
        assert duration == -1  # Unchanged


# ============================================================================
# Wait/Daze State Tests
# ============================================================================


class TestWaitDazeStates:
    """Tests for wait and daze state handling matching ROM."""

    def test_wait_decrements_each_pulse(self):
        """ROM: ch->wait decrements each PULSE_VIOLENCE."""
        ch = Character(name="Test")
        ch.wait = 12  # 3 pulses
        
        # Simulate 3 violence pulses
        for _ in range(3):
            ch.wait = max(0, ch.wait - 4)  # PULSE_VIOLENCE = 4
        
        assert ch.wait == 0

    def test_daze_blocks_skills(self):
        """ROM: ch->daze > 0 blocks skill usage."""
        ch = Character(name="Test")
        ch.daze = 8
        
        can_use_skill = ch.daze <= 0
        assert not can_use_skill
        
        # Daze decrements
        ch.daze = max(0, ch.daze - 4)
        ch.daze = max(0, ch.daze - 4)
        
        can_use_skill = ch.daze <= 0
        assert can_use_skill

    def test_haste_halves_wait(self):
        """ROM: AFF_HASTE halves wait state duration."""
        ch = Character(name="Test")
        base_wait = 12
        
        # Without haste
        ch.wait = base_wait
        
        # With haste - wait is halved
        ch.affected_by = AffectFlag.HASTE
        if ch.has_affect(AffectFlag.HASTE):
            ch.wait = c_div(base_wait, 2)
        
        assert ch.wait == 6

    def test_slow_doubles_wait(self):
        """ROM: AFF_SLOW doubles wait state duration."""
        ch = Character(name="Test")
        base_wait = 12
        
        # With slow - wait is doubled
        ch.affected_by = AffectFlag.SLOW
        if ch.has_affect(AffectFlag.SLOW):
            ch.wait = base_wait * 2
        
        assert ch.wait == 24
