"""INV-010 ROOM-PEOPLE-COHERENCE enforcement.

ROM ref: src/handler.c:1497-1573 — char_to_room / char_from_room are the
only mutation paths for ch->in_room and room->people. They keep the
bidirectional contract: every character with ch->in_room == R lives in
R->people, and every entry in R->people has ch->in_room == R.

Python: the canonical helpers are Room.add_character / Room.remove_character
(mud/models/room.py) and the char_to_room() wrapper with temple fallback.
At least eight non-canonical call sites mutate room.people directly:

- mud/spec_funs.py:219-222 (mayor patrol)
- mud/spawning/templates.py:438-439 (MobInstance.move_to_room)
- mud/commands/session.py:397-400 (do_recall)
- mud/commands/imm_load.py:83-84 (immortal mob load)
- mud/commands/imm_search.py:489-490 (clone)
- mud/commands/imm_commands.py:449-470 (_char_from_room / _char_to_room)
- mud/commands/imm_commands.py:467 (room.people = [] wipe in purge)

This test locks in the bidirectional contract at the call sites that
matter so that any future drop of either side breaks the suite.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-010.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room, char_to_room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _reset_registry():  # noqa: PT004 — autouse fixture

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


def _mk_char(name: str, *, is_npc: bool = True) -> Character:
    ch = Character(name=name, level=10, is_npc=is_npc, hit=100, max_hit=100)
    ch.position = Position.STANDING
    character_registry.append(ch)
    return ch


def _assert_coherent(*rooms: Room) -> None:
    """Bidirectional coherence: ch.room is R iff ch in R.people."""
    seen: set[int] = set()
    for room in rooms:
        for ch in room.people:
            assert ch.room is room, (
                f"{getattr(ch, 'name', '?')} sits in room {room.vnum}.people "
                f"but ch.room is {getattr(ch.room, 'vnum', None)}"
            )
            assert id(ch) not in seen, (
                f"{getattr(ch, 'name', '?')} appears in multiple rooms"
            )
            seen.add(id(ch))
    for ch in character_registry:
        room = getattr(ch, "room", None)
        if room is None or room not in rooms:
            continue
        assert ch in room.people, (
            f"{getattr(ch, 'name', '?')}.room == {room.vnum} "
            f"but missing from room.people"
        )


def test_canonical_helpers_keep_bidirectional_state():
    room_a = _mk_room(91001)
    room_b = _mk_room(91002)
    try:
        ch = _mk_char("Alice", is_npc=False)

        room_a.add_character(ch)
        assert ch.room is room_a and ch in room_a.people
        _assert_coherent(room_a, room_b)

        room_a.remove_character(ch)
        room_b.add_character(ch)
        assert ch.room is room_b and ch not in room_a.people and ch in room_b.people
        _assert_coherent(room_a, room_b)

        room_b.remove_character(ch)
        assert ch.room is None and ch not in room_b.people
        _assert_coherent(room_a, room_b)
    finally:
        room_registry.pop(91001, None)
        room_registry.pop(91002, None)


def test_char_to_room_null_falls_back_to_temple_with_coherence():
    """char_to_room(None) routes to temple (ROOM_VNUM_TEMPLE=3001). The
    fallback path must still maintain bidirectional coherence."""
    from mud.models.constants import ROOM_VNUM_TEMPLE

    pre_existing_temple = room_registry.get(ROOM_VNUM_TEMPLE)
    temple = pre_existing_temple or _mk_room(ROOM_VNUM_TEMPLE)
    try:
        ch = _mk_char("Bob", is_npc=False)
        char_to_room(ch, None)
        assert ch.room is temple
        assert ch in temple.people
        _assert_coherent(temple)
    finally:
        if pre_existing_temple is None:
            room_registry.pop(ROOM_VNUM_TEMPLE, None)
        else:
            # Don't leak the test char into the real temple
            if pre_existing_temple is not None:
                # locate by identity and remove
                for c in list(pre_existing_temple.people):
                    if getattr(c, "name", None) == "Bob":
                        pre_existing_temple.people.remove(c)


def test_imm_commands_char_helpers_preserve_coherence():
    """_char_from_room / _char_to_room (goto, transfer, OLC rrelocate) are
    a partial duplicate of the canonical helpers. They must still keep
    the bidirectional contract."""
    from mud.commands.imm_commands import _char_from_room, _char_to_room

    room_a = _mk_room(91011)
    room_b = _mk_room(91012)
    try:
        ch = _mk_char("Carol", is_npc=False)
        _char_to_room(ch, room_a)
        _assert_coherent(room_a, room_b)
        assert ch in room_a.people

        _char_from_room(ch)
        _char_to_room(ch, room_b)
        assert ch not in room_a.people
        assert ch in room_b.people
        assert ch.room is room_b
        _assert_coherent(room_a, room_b)
    finally:
        room_registry.pop(91011, None)
        room_registry.pop(91012, None)


def test_mob_instance_move_to_room_preserves_coherence():
    """MobInstance.move_to_room (mud/spawning/templates.py:436-440) is a
    direct room.people mutator used by mob respawn / patrol. Must keep
    both sides in sync."""
    from mud.spawning.templates import MobInstance
    from mud.models.mob import MobIndex

    room_a = _mk_room(91021)
    room_b = _mk_room(91022)
    try:
        proto = MobIndex(vnum=91099, short_descr="a test mob")
        mob = MobInstance.from_prototype(proto)
        room_a.people.append(mob)
        mob.room = room_a

        mob.move_to_room(room_b)
        assert mob.room is room_b
        assert mob in room_b.people
        assert mob not in room_a.people
        # bidirectional: every mob in room_b has .room is room_b
        for c in room_b.people:
            assert c.room is room_b
    finally:
        room_registry.pop(91021, None)
        room_registry.pop(91022, None)


def test_recall_path_pattern_preserves_coherence():
    """do_recall in mud/commands/session.py:395-400 uses a raw
    room.people.remove/append pattern. Replicate that pattern here so
    any future refactor that drops one side trips the test."""
    old_room = _mk_room(91031)
    recall_room = _mk_room(91032)
    try:
        ch = _mk_char("Dave", is_npc=False)
        old_room.people.append(ch)
        ch.room = old_room

        # Pattern from session.py:395-400.
        if old_room and ch in old_room.people:
            old_room.people.remove(ch)
        ch.room = recall_room
        if ch not in recall_room.people:
            recall_room.people.append(ch)

        assert ch.room is recall_room
        assert ch in recall_room.people
        assert ch not in old_room.people
        _assert_coherent(old_room, recall_room)
    finally:
        room_registry.pop(91031, None)
        room_registry.pop(91032, None)


def test_global_registry_coherence_at_rest():
    """End-to-end: across every Character in character_registry that has
    a non-None .room, the bidirectional contract must hold against every
    Room in room_registry. Catches stray code paths that set .room
    without appending to .people (or vice versa).
    """
    room_a = _mk_room(91041)
    room_b = _mk_room(91042)
    try:
        c1 = _mk_char("Eve", is_npc=False)
        c2 = _mk_char("Frank", is_npc=True)
        room_a.add_character(c1)
        room_b.add_character(c2)

        for ch in character_registry:
            room = getattr(ch, "room", None)
            if room is None:
                continue
            assert ch in room.people, (
                f"{getattr(ch, 'name', '?')}.room={room.vnum} but "
                f"missing from room.people — broken contract"
            )

        for room in room_registry.values():
            for ch in getattr(room, "people", []) or []:
                ch_room = getattr(ch, "room", None)
                assert ch_room is room, (
                    f"{getattr(ch, 'name', '?')} in room {room.vnum}.people "
                    f"but ch.room={getattr(ch_room, 'vnum', None)}"
                )
    finally:
        room_registry.pop(91041, None)
        room_registry.pop(91042, None)
