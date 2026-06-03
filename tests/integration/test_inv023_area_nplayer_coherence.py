"""INV-023 — AREA-NPLAYER-COHERENCE.

ROM ``src/handler.c:1501-1502`` (``char_from_room``) decrements
``ch->in_room->area->nplayer`` whenever a non-NPC leaves a room,
and ``src/handler.c:1561-1568`` (``char_to_room``) increments it
whenever a non-NPC enters one (also clearing ``area->empty`` and
resetting ``area->age``). Every PC movement path in ROM funnels
through ``char_from_room`` + ``char_to_room`` — there is no other
way to change ``ch->in_room``.

``area->nplayer`` is load-bearing: ``src/db.c:1617-1630, 1773,
1808`` use it to decide whether to run resets, mark an area empty,
and tick area age. If a PC moves between areas via a code path
that bypasses the counter, repop and area-age behavior diverges
from ROM (a vacated area appears occupied; a freshly-entered one
appears empty).

The Python equivalents ``room.add_character`` /
``room.remove_character`` (``mud/models/room.py:140-173``) honor
the contract. **But** several PC-movement paths in
``mud/commands/session.py`` and ``mud/commands/imm_commands.py``
mutate ``room.people`` directly (``.append`` / ``.remove``),
bypassing the counter. ``do_recall`` is the most visible offender
— a player recalling from a remote area leaves their old area
permanently "occupied" by their phantom nplayer count, and lands
in the temple area without bumping its counter.

This row pins the cross-file contract that EVERY PC room
transition must go through the canonical helpers (or otherwise
maintain ``area.nplayer``). The regression test exercises
``do_recall`` end-to-end and asserts both areas' counters update.
"""

from __future__ import annotations

import pytest

from mud.commands.session import do_recall
from mud.models.area import Area
from mud.models.character import Character
from mud.models.constants import ROOM_VNUM_TEMPLE, Position
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def _isolated_room_registry():
    snapshot = dict(room_registry)
    room_registry.clear()
    yield
    room_registry.clear()
    room_registry.update(snapshot)


def _make_area(vnum: int, name: str) -> Area:
    return Area(vnum=vnum, name=name, nplayer=0, empty=False, age=0)


def _make_room(vnum: int, area: Area) -> Room:
    room = Room(vnum=vnum, name=f"room-{vnum}", area=area)
    room_registry[vnum] = room
    return room


def test_inv023_recall_decrements_source_area_and_increments_temple_area(
    _isolated_room_registry,
):
    """PC recalling from area A → temple area B must update both nplayer counters.

    ROM src/handler.c:1501-1502 and 1561-1568 — every PC room
    transition adjusts the source and destination area counters.
    """
    src_area = _make_area(vnum=9000, name="Source Area")
    temple_area = _make_area(vnum=9001, name="Temple Area")

    src_room = _make_room(vnum=8500, area=src_area)
    temple_room = _make_room(vnum=ROOM_VNUM_TEMPLE, area=temple_area)

    pc = Character(name="recaller", is_npc=False, level=10, position=Position.STANDING)
    pc.skills = {"recall": 100}
    pc.move = 100
    src_room.add_character(pc)

    assert src_area.nplayer == 1, "precondition: source area counts the PC"
    assert temple_area.nplayer == 0, "precondition: temple area is empty"

    do_recall(pc, "")

    assert pc.room is temple_room, "do_recall must move the PC to the temple"
    assert src_area.nplayer == 0, (
        "do_recall must decrement source area.nplayer (ROM src/handler.c:1501-1502 via char_from_room)"
    )
    assert temple_area.nplayer == 1, (
        "do_recall must increment temple area.nplayer (ROM src/handler.c:1561-1568 via char_to_room)"
    )


def test_inv023_recall_resets_temple_area_empty_and_age(_isolated_room_registry):
    """Entry into a previously-empty area must clear empty + reset age.

    ROM src/handler.c:1563-1566 — ``empty`` flips to FALSE and
    ``age`` resets to 0 when the first non-NPC arrives.
    """
    src_area = _make_area(vnum=9100, name="Source")
    temple_area = _make_area(vnum=9101, name="Temple")
    temple_area.empty = True
    temple_area.age = 20

    src_room = _make_room(vnum=8600, area=src_area)
    _make_room(vnum=ROOM_VNUM_TEMPLE, area=temple_area)

    pc = Character(name="awakener", is_npc=False, level=10, position=Position.STANDING)
    pc.skills = {"recall": 100}
    pc.move = 100
    src_room.add_character(pc)

    do_recall(pc, "")

    assert temple_area.empty is False, "first PC arrival must clear area.empty"
    assert temple_area.age == 0, "first PC arrival must reset area.age"
