"""INV-032 — ROOM-FLAGS-SURVIVE-LOAD.

ROM room flags must survive the full ``.are`` → JSON → runtime pipeline.
ROM ``src/db.c:1158-1163 load_rooms`` reads the room header as
``<area-number(discard)> <room_flags via fread_flag> <sector_type>`` and
``fread_flag`` (``src/db.c:2743``) letter-decodes bitvectors like ``ADR``.
Those flags then gate runtime behavior across modules (``room_is_dark`` for
ROOM_DARK, ``is_safe`` for ROOM_SAFE, recall for ROOM_NO_RECALL, …).

DB-001: ``mud/loaders/room_loader.py`` read the wrong token (the discarded
area-number field, always 0) and could not letter-decode bitvectors, so every
room loaded flagless and the converter baked the zeros into all 52 JSONs.

This test locks the contract: boot the live world from ``data/areas/*.json``
and assert the school "Darkened Room" (vnum 3720, ROM flags ``ADR`` =
ROOM_DARK|ROOM_INDOORS|ROOM_NEWBIES_ONLY) is dark at runtime.
"""

from __future__ import annotations

from mud.models.constants import RoomFlag
from mud.registry import room_registry
from mud.world import initialize_world
from mud.world.vision import room_is_dark


def test_school_darkened_room_is_dark_after_full_load() -> None:
    # mirrors ROM src/db.c:1158-1163 — the `ADR` bitvector on room 3720 must
    # survive .are -> JSON -> runtime and make the room dark.
    initialize_world("area/area.lst")  # use_json=True by default

    room = room_registry[3720]
    flags = int(room.room_flags)

    assert flags & int(RoomFlag.ROOM_DARK)
    assert flags & int(RoomFlag.ROOM_INDOORS)
    assert flags & int(RoomFlag.ROOM_NEWBIES_ONLY)
    assert room_is_dark(room) is True


def test_room_flags_present_game_wide_after_load() -> None:
    # DB-001 regression guard: before the fix every room loaded with
    # room_flags == 0. After it, a meaningful fraction of rooms carry flags.
    initialize_world("area/area.lst")

    flagged = sum(1 for room in room_registry.values() if int(room.room_flags) != 0)
    assert flagged > 100, f"expected many flagged rooms game-wide, got {flagged}"
