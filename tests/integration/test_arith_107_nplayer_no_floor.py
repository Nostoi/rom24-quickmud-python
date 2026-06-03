"""ARITH-107 — area.nplayer floor in Room.remove_character.

ROM ``src/handler.c:1501-1502`` (``char_from_room``) does a bare
``--ch->in_room->area->nplayer`` with no floor whenever a non-NPC
leaves a room. If ``nplayer`` is already 0 (e.g. desynced by a
prior bypass of the canonical helpers — see INV-023), ROM allows
the counter to go negative, exposing the desync bug for diagnosis
in ``src/db.c:1617-1630`` repop/age logic.

Python's ``Room.remove_character`` historically clamped this with
``max(0, current - 1)``, silently absorbing the desync. ARITH-107
removes the floor so behavior matches ROM exactly.
"""

from __future__ import annotations

from mud.models.area import Area
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


def test_arith_107_remove_character_allows_negative_nplayer_on_desync():
    """When area.nplayer is already 0, remove_character must decrement to -1.

    mirrors ROM src/handler.c:1502 — bare ``--area->nplayer`` with no floor.
    """
    area = Area(vnum=7000, name="Desynced Area", nplayer=0, empty=False, age=0)
    room = Room(vnum=7500, name="room", area=area)

    pc = Character(name="ghost", is_npc=False, level=10, position=Position.STANDING)
    # Bypass add_character so nplayer stays at 0 — simulates the INV-023
    # desync where a prior code path mutated room.people directly.
    room.people.append(pc)
    pc.room = room

    assert area.nplayer == 0, "precondition: counter desynced to 0 while PC is present"

    room.remove_character(pc)

    assert area.nplayer == -1, (
        "ROM src/handler.c:1502 does bare --area->nplayer with no floor; Python must not clamp to 0 (ARITH-107)."
    )


def test_arith_107_npc_removal_still_does_not_touch_nplayer():
    """NPC removal is gated by IS_NPC check; counter must stay untouched.

    mirrors ROM src/handler.c:1501 — ``if (!IS_NPC(ch))`` guard.
    """
    area = Area(vnum=7100, name="NPC Area", nplayer=0, empty=False, age=0)
    room = Room(vnum=7600, name="room", area=area)

    mob = Character(name="mob", is_npc=True, level=10, position=Position.STANDING)
    room.people.append(mob)
    mob.room = room

    room.remove_character(mob)

    assert area.nplayer == 0, "NPC removal must not change area.nplayer"


def test_arith_107_normal_pc_removal_decrements_to_zero():
    """Happy path: PC added then removed must net to nplayer == 0."""
    area = Area(vnum=7200, name="Normal Area", nplayer=0, empty=False, age=0)
    room = Room(vnum=7700, name="room", area=area)

    pc = Character(name="walker", is_npc=False, level=10, position=Position.STANDING)
    room.add_character(pc)
    assert area.nplayer == 1

    room.remove_character(pc)
    assert area.nplayer == 0, "balanced add/remove must net to 0"
