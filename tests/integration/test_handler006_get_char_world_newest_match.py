"""HANDLER-006 — get_char_world returns the NEWEST name match (ROM char_list order).

ROM's `get_char_world` world scan (`src/handler.c:2234-2240`) walks `char_list`,
which is head-inserted (`src/db.c:2256-2257` create_mobile, `src/nanny.c:757-758`
PC login), so the FIRST `is_name` match — and therefore the unnumbered lookup —
is the NEWEST matching char, and `2.name` counts from newest toward oldest.
Python's `character_registry` is append-order (oldest-first), so the forward scan
returned the OLDEST match. INV-045 consequence class (b): first-match selection.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.registry import room_registry
from mud.world import initialize_world
from mud.world.char_find import get_char_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


def _spawn(name: str, room_vnum: int, *, is_npc: bool = True) -> Character:
    room = room_registry.get(room_vnum)
    char = Character(
        name=name,
        short_descr=name,
        is_npc=is_npc,
        level=10,
        position=Position.STANDING,
        room=room,
    )
    if room is not None:
        room.add_character(char)
    character_registry.append(char)
    return char


def test_get_char_world_returns_newest_match_and_counts_newest_first():
    # mirrors ROM src/handler.c:2234-2240 — the char_list walk visits the
    # NEWEST char first (head-insert), so the unnumbered world lookup resolves
    # the most recently created same-named char and `2.name` the next-newest.
    observer = _spawn("observer", 3001, is_npc=False)
    # Same keyword, different room from the observer so get_char_room misses
    # and the world scan decides. Unique keyword so nothing else matches.
    old_mob = _spawn("zzparityguard", 3004)
    new_mob = _spawn("zzparityguard", 3004)

    try:
        assert get_char_world(observer, "zzparityguard") is new_mob, (
            "world lookup must resolve the NEWEST match (ROM char_list is head-inserted)"
        )
        # `2.zzparityguard` counts matches in the same newest-first walk order.
        assert get_char_world(observer, "2.zzparityguard") is old_mob
    finally:
        for c in (observer, old_mob, new_mob):
            if c.room is not None and c in c.room.people:
                c.room.people.remove(c)
            if c in character_registry:
                character_registry.remove(c)
