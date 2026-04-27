"""Integration tests for ``mp_greet_trigger`` ROM parity gaps.

Mirrors ROM ``src/mob_prog.c:1325-1349``: a mob with both GREET and GRALL
triggers, when awake and able to see the entrant, only attempts the GREET
trigger. The GRALL branch is reserved for the busy/blind case (``else if``
in C, not a fall-through after a failed percent roll).
"""

from __future__ import annotations

import pytest

from mud import mobprog
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.mob import MobProgram
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _clear_registries():
    room_registry.clear()
    character_registry.clear()
    yield
    room_registry.clear()
    character_registry.clear()


def test_greet_failure_does_not_fall_through_to_grall(monkeypatch):
    """ROM src/mob_prog.c:1340-1345 — once GREET path is taken, GRALL is skipped.

    Even if the GREET percent roll fails, GRALL must not fire when the mob is
    awake (position == default_pos) and can see the entrant.
    """
    room = Room(vnum=4000, name="Hall")
    room_registry[4000] = room

    mob = Character(name="warden", is_npc=True)
    mob.position = Position.STANDING
    mob.default_pos = Position.STANDING
    # GREET prog with phrase "0" — number_percent() >= 0 is always true,
    # so the percent gate is failed on every roll.
    greet_prog = MobProgram(trig_type=int(mobprog.Trigger.GREET), trig_phrase="0", code=":")
    grall_prog = MobProgram(trig_type=int(mobprog.Trigger.GRALL), trig_phrase="100", code=":")
    mob.mprog_target = None
    mob.mob_programs = [greet_prog, grall_prog]
    room.add_character(mob)
    character_registry.append(mob)

    player = Character(name="hero", is_npc=False)
    player.position = Position.STANDING
    room.add_character(player)
    character_registry.append(player)

    calls: list[mobprog.Trigger] = []

    def _record(mob_arg, ch_arg, *args, trigger=None, **kwargs):
        calls.append(trigger)
        return False

    monkeypatch.setattr(mobprog, "mp_percent_trigger", _record)

    mobprog.mp_greet_trigger(player)

    assert mobprog.Trigger.GREET in calls
    assert mobprog.Trigger.GRALL not in calls


def test_grall_fires_when_mob_is_busy(monkeypatch):
    """ROM src/mob_prog.c:1344-1345 — GRALL is the busy/blind fallback."""
    room = Room(vnum=4001, name="Battle Hall")
    room_registry[4001] = room

    mob = Character(name="warden", is_npc=True)
    mob.position = Position.FIGHTING
    mob.default_pos = Position.STANDING
    grall_prog = MobProgram(trig_type=int(mobprog.Trigger.GRALL), trig_phrase="100", code=":")
    greet_prog = MobProgram(trig_type=int(mobprog.Trigger.GREET), trig_phrase="100", code=":")
    mob.mob_programs = [greet_prog, grall_prog]
    room.add_character(mob)
    character_registry.append(mob)

    player = Character(name="hero", is_npc=False)
    player.position = Position.STANDING
    room.add_character(player)
    character_registry.append(player)

    calls: list[mobprog.Trigger] = []

    def _record(mob_arg, ch_arg, *args, trigger=None, **kwargs):
        calls.append(trigger)
        return False

    monkeypatch.setattr(mobprog, "mp_percent_trigger", _record)

    mobprog.mp_greet_trigger(player)

    assert mobprog.Trigger.GRALL in calls
    assert mobprog.Trigger.GREET not in calls
