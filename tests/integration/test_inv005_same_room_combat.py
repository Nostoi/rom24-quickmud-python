"""INV-005 SAME-ROOM-COMBAT-ONLY enforcement.

ROM ref: src/fight.c:violence_update — combat round only fires when
ch->in_room == victim->in_room. Mismatched rooms cause stop_fighting(ch, FALSE).

Python: mud/game_loop.py:violence_tick gates multi_hit() on
``getattr(ch, "room", None) == getattr(victim, "room", None)``. If that gate
ever regresses, attackers would damage victims across rooms.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-005.
"""

from __future__ import annotations

import pytest

from mud.game_loop import violence_tick
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _reset_registry():
    snapshot = list(character_registry)
    character_registry.clear()
    yield
    character_registry.clear()
    character_registry.extend(snapshot)


def _mk_room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _mk_char(name: str, room: Room, *, is_npc: bool) -> Character:
    ch = Character(name=name, level=10, room=room, is_npc=is_npc, hit=100, max_hit=100)
    ch.position = Position.FIGHTING
    room.people.append(ch)
    character_registry.append(ch)
    return ch


def test_violence_tick_skips_cross_room_attackers() -> None:
    room_a = _mk_room(90001)
    room_b = _mk_room(90002)
    try:
        attacker = _mk_char("Attacker", room_a, is_npc=True)
        victim = _mk_char("Victim", room_b, is_npc=False)

        attacker.fighting = victim
        victim.fighting = attacker
        starting_hit = victim.hit

        violence_tick(do_combat=True)

        assert victim.hit == starting_hit, "cross-room attacker landed damage"
        assert attacker.fighting is None, "stop_fighting did not run for cross-room attacker"
    finally:
        room_registry.pop(90001, None)
        room_registry.pop(90002, None)


def test_violence_tick_engages_same_room_attackers() -> None:
    """Sanity check: same-room combat still produces a multi_hit call.

    If multi_hit ever gets gated incorrectly (e.g. equality flipped), this
    catches the false negative.
    """
    room = _mk_room(90003)
    try:
        attacker = _mk_char("Attacker", room, is_npc=True)
        victim = _mk_char("Victim", room, is_npc=False)
        attacker.fighting = victim
        victim.fighting = attacker

        called: list[tuple[str, str]] = []

        import mud.combat.engine as engine

        original = engine.multi_hit

        def _spy(ch, vict, dt=None):
            called.append((ch.name, vict.name))

        engine.multi_hit = _spy
        try:
            violence_tick(do_combat=True)
        finally:
            engine.multi_hit = original

        assert called, "same-room combat did not invoke multi_hit"
        assert attacker.fighting is victim, "attacker stopped fighting in same-room case"
    finally:
        room_registry.pop(90003, None)
