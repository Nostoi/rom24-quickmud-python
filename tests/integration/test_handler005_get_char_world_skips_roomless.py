"""HANDLER-005 — get_char_world skips roomless chars (ROM `wch->in_room == NULL`).

ROM's `get_char_world` world-list scan (`src/handler.c:2234-2241`) skips any char
whose `in_room == NULL` BEFORE the `can_see`/`is_name` tests:

    if (wch->in_room == NULL || !can_see(ch, wch) || !is_name(arg, wch->name))
        continue;

so a roomless char is never resolved by a world lookup. Python's loop omitted the
`in_room == NULL` guard. This is live-relevant after VISION-001 (2026-05-29)
dropped the `target_room is None` bail in `can_see_character`: a roomless registry
char is now visible, so `get_char_world` would return it where ROM skips. The fix
adds the `ch.room is None` skip as the first loop gate.
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


def test_get_char_world_skips_roomless_target():
    # mirrors ROM src/handler.c:2236 — wch->in_room == NULL is skipped before
    # can_see/is_name, so a roomless registry char is never resolved world-wide.
    room = room_registry.get(3001)  # lit temple, so the dark gate never masks
    observer = Character(
        name="observer",
        short_descr="an observer",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=room,
    )
    room.add_character(observer)
    character_registry.append(observer)

    # A char in the registry but NOT placed in any room (room is None) — e.g. the
    # CON_GET_NEW_CLASS wiznet subject. Unique keyword so only it could match.
    ghost = Character(
        name="zzphantomsubject",
        short_descr="a forming spirit",
        is_npc=False,
        level=10,
        position=Position.STANDING,
        room=None,
    )
    character_registry.append(ghost)

    try:
        # ROM skips the roomless char; the world lookup resolves nothing.
        assert get_char_world(observer, "zzphantomsubject") is None
    finally:
        for c in (observer, ghost):
            if c.room is not None and c in c.room.people:
                c.room.people.remove(c)
            if c in character_registry:
                character_registry.remove(c)
