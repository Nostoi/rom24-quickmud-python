"""INV-006 FIGHTING-POINTER-COHERENCE enforcement.

ROM ref: src/fight.c:stop_fighting(victim, TRUE) sweeps char_list and clears
``fch->fighting`` for every fch where ``fch->fighting == victim``. This keeps
multi-attacker scenarios from leaving stale ``.fighting`` pointers when the
shared target dies.

Python: mud/combat/engine.py:stop_fighting(ch, both=True) iterates
``character_registry``. If that sweep regresses (wrong list, wrong predicate,
``both`` ignored), surviving attackers would keep targeting a dead victim and
re-enter combat on the next violence pulse.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-006.
"""

from __future__ import annotations

import pytest

from mud.combat.engine import stop_fighting
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


def test_stop_fighting_both_clears_all_attackers() -> None:
    room = _mk_room(91001)
    try:
        victim = _mk_char("Victim", room, is_npc=False)
        a1 = _mk_char("Mob1", room, is_npc=True)
        a2 = _mk_char("Mob2", room, is_npc=True)
        a3 = _mk_char("Mob3", room, is_npc=True)
        bystander = _mk_char("Bystander", room, is_npc=True)

        a1.fighting = victim
        a2.fighting = victim
        a3.fighting = victim
        victim.fighting = a1
        bystander.fighting = None  # not in combat

        stop_fighting(victim, both=True)

        assert victim.fighting is None
        assert a1.fighting is None, "attacker a1 still pointed at dead victim"
        assert a2.fighting is None, "attacker a2 still pointed at dead victim"
        assert a3.fighting is None, "attacker a3 still pointed at dead victim"
        assert bystander.fighting is None  # untouched

        # Position handling — NPCs go to default_pos (STANDING for our mobs);
        # the PC victim goes to STANDING.
        assert victim.position == Position.STANDING
        assert a1.position == Position.STANDING
    finally:
        room_registry.pop(91001, None)


def test_stop_fighting_both_false_only_clears_self() -> None:
    """Inverse: both=False must NOT sweep other attackers.

    ROM ref: src/fight.c:stop_fighting(ch, FALSE) only clears ch->fighting.
    """
    room = _mk_room(91002)
    try:
        victim = _mk_char("Victim", room, is_npc=False)
        a1 = _mk_char("Mob1", room, is_npc=True)
        a2 = _mk_char("Mob2", room, is_npc=True)

        a1.fighting = victim
        a2.fighting = victim
        victim.fighting = a1

        stop_fighting(a1, both=False)

        assert a1.fighting is None
        assert a2.fighting is victim, "both=False should not sweep other attackers"
        assert victim.fighting is a1, "both=False should not touch victim's pointer"
    finally:
        room_registry.pop(91002, None)
