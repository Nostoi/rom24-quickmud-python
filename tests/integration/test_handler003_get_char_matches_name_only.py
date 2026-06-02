"""HANDLER-003 — get_char_room / get_char_world match the keyword `name` only.

ROM's room/world char lookup gates solely on `is_name(arg, rch->name)`
(`src/handler.c:2207`, `:2237`) — the keyword `name` list, NOT the `short_descr`.
A mob whose keyword name is "guard" and short_descr "a city guard" is therefore
reachable as `guard` but NOT as `city`: ROM's `is_name("city", "guard")` is
FALSE (whole-word match against the keyword list, not a substring of the
description).

Python's helpers additionally tested `name_lower in occupant_short` (the
`short_descr`), so `look city` resolved "a city guard" where ROM would return
nothing. The fix drops the `short_descr`/`keywords` substring match and gates on
`is_name(arg, occupant.name)` alone, matching ROM.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.registry import room_registry
from mud.world import initialize_world
from mud.world.char_find import get_char_room, get_char_world


@pytest.fixture(scope="module", autouse=True)
def setup_world():
    initialize_world("area/area.lst")
    yield


def _make_char(room, name: str, short_descr: str, is_npc: bool = True) -> Character:
    ch = Character(
        name=name,
        short_descr=short_descr,
        is_npc=is_npc,
        level=10,
        position=Position.STANDING,
        room=room,
    )
    room.add_character(ch)
    character_registry.append(ch)
    return ch


def _cleanup(*chars):
    for c in chars:
        if c.room is not None and c in c.room.people:
            c.room.people.remove(c)
        if c in character_registry:
            character_registry.remove(c)


# Unique tokens so the positive keyword never collides with a real loaded mob's
# name and the negative word never collides with a real loaded short_descr.
_KEYWORD = "zzqguardian"
_DESCWORD = "zzqcitadel"


def test_get_char_room_matches_keyword_name_not_short_descr():
    # mirrors ROM src/handler.c:2207 — is_name(arg, rch->name); the descword is in
    # the short_descr but NOT the keyword name, so ROM does not resolve it.
    room = room_registry.get(3001)
    observer = _make_char(room, "observer", "an observer", is_npc=False)
    guard = _make_char(room, _KEYWORD, f"a {_DESCWORD} sentinel")
    try:
        # Keyword name matches.
        assert get_char_room(observer, _KEYWORD) is guard
        # short_descr-only word does NOT match (ROM is_name against name only).
        assert get_char_room(observer, _DESCWORD) is None
    finally:
        _cleanup(observer, guard)


def test_get_char_world_matches_keyword_name_not_short_descr():
    # mirrors ROM src/handler.c:2237 — get_char_world also gates on
    # is_name(arg, wch->name); the world fallback must not match short_descr.
    room_a = room_registry.get(3001)
    room_b = room_registry.get(3002)
    observer = _make_char(room_a, "observer", "an observer", is_npc=False)
    guard = _make_char(room_b, _KEYWORD, f"a {_DESCWORD} sentinel")
    try:
        assert get_char_world(observer, _KEYWORD) is guard
        assert get_char_world(observer, _DESCWORD) is None
    finally:
        _cleanup(observer, guard)
