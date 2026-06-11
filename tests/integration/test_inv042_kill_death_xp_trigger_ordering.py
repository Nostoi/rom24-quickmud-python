"""INV-042 — KILL-DEATH-XP-TRIGGER-ORDERING.

ROM src/fight.c:883-924 mandates a strict three-step call order inside
the death-handling path:

  1. group_gain(ch, victim)               -- XP delivery while victim stats intact
  2. mp_percent_trigger(victim, TRIG_DEATH) -- mob prog fires before extraction
  3. raw_kill(victim)                      -- victim extraction always last

Python equivalent: mud/combat/engine.py:_handle_death (lines 1351-1368).

Rationale for ordering:
  - group_gain reads victim.level/exp to compute XP share — must precede
    raw_kill which extracts the victim from the registry.
  - TRIG_DEATH fires AFTER group_gain/XP but BEFORE raw_kill: the victim
    is still present in the registry and its position is temporarily reset
    to STANDING so the mob can act during the trigger.
  - raw_kill is always last — it extracts the victim from char_list/registry.

Both tests are mutation-verified: swapping any adjacent pair in the call
sequence causes the call_log assertion to fail (RED).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mud.combat.engine import _handle_death
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _isolated_registry():
    char_snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(char_snapshot)
    room_registry.pop(9451, None)


def _make_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name="Test Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _make_pc(name: str, room: Room, level: int = 10) -> Character:
    ch = Character(name=name, is_npc=False, level=level, room=room, position=int(Position.STANDING))
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    ch.mana = 100
    ch.move = 100
    ch.armor = [100, 100, 100, 100]
    ch.exp = 5000
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def _make_npc(name: str, room: Room, level: int = 10) -> Character:
    ch = Character(name=name, is_npc=True, level=level, room=room, position=int(Position.STANDING))
    ch.messages = []
    ch.hit = 100
    ch.max_hit = 100
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_kill_death_xp_trigger_ordering_with_trig_death():
    """group_gain → mp_death_trigger → raw_kill must fire in this exact order.

    ROM src/fight.c:883,918-922,924 — three-step ordering when victim has TRIG_DEATH.
    Mutation-verified: swapping any adjacent pair fails the call_log assertion.
    """
    room = _make_room(9451)
    attacker = _make_pc("attacker", room)
    victim = _make_npc("victim_with_trig", room)

    call_log: list[str] = []

    def spy_group_gain(ch, v):
        call_log.append("group_gain")

    def spy_mp_death_trigger(v, ch):
        call_log.append("mp_death_trigger")

    def spy_raw_kill(v):
        call_log.append("raw_kill")
        return MagicMock()

    with (
        patch("mud.combat.engine.group_gain", side_effect=spy_group_gain),
        patch("mud.combat.engine.raw_kill", side_effect=spy_raw_kill),
        patch("mud.combat.engine._send_wiznet_death"),
        patch("mud.combat.engine._clear_pk_flags"),
        patch("mud.combat.engine._handle_auto_actions"),
        patch("mud.mobprog.mob_has_trigger", return_value=True),
        patch("mud.mobprog.mp_death_trigger", side_effect=spy_mp_death_trigger),
    ):
        _handle_death(attacker, victim)

    assert call_log == ["group_gain", "mp_death_trigger", "raw_kill"], (
        f"INV-042: ROM src/fight.c:883-924 requires group_gain → mp_death_trigger → raw_kill. Actual order: {call_log}"
    )


def test_kill_xp_before_raw_kill_no_trig_death():
    """group_gain fires before raw_kill even when victim has no TRIG_DEATH.

    ROM src/fight.c:883,924 — XP-then-kill is unconditional.
    Mutation-verified: putting raw_kill before group_gain fails the assertion.
    """
    room = _make_room(9451)
    attacker = _make_pc("attacker", room)
    victim = _make_npc("victim_no_trig", room)

    call_log: list[str] = []

    def spy_group_gain(ch, v):
        call_log.append("group_gain")

    def spy_raw_kill(v):
        call_log.append("raw_kill")
        return MagicMock()

    with (
        patch("mud.combat.engine.group_gain", side_effect=spy_group_gain),
        patch("mud.combat.engine.raw_kill", side_effect=spy_raw_kill),
        patch("mud.combat.engine._send_wiznet_death"),
        patch("mud.combat.engine._clear_pk_flags"),
        patch("mud.combat.engine._handle_auto_actions"),
        patch("mud.mobprog.mob_has_trigger", return_value=False),
    ):
        _handle_death(attacker, victim)

    assert call_log == ["group_gain", "raw_kill"], (
        f"INV-042: group_gain must precede raw_kill unconditionally. Actual order: {call_log}"
    )
