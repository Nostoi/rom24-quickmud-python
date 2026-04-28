"""Integration parity tests for src/scan.c.

Each test mirrors a specific ROM C line range from src/scan.c and asserts
the QuickMUD-Python output / broadcast behavior matches.
"""

from __future__ import annotations

import pytest

from mud.commands.inspection import do_scan
from mud.models.character import Character, character_registry
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture
def two_char_room():
    """Single room with a scanner and an observer, both attached to messages buffers."""
    room = Room(vnum=9001, name="Scan Test Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[9001] = room

    scanner = Character(name="Scanner", level=10, room=room, is_npc=False, hit=100, max_hit=100)
    scanner.messages = []
    observer = Character(name="Observer", level=10, room=room, is_npc=False, hit=100, max_hit=100)
    observer.messages = []
    room.people.extend([scanner, observer])
    character_registry.extend([scanner, observer])

    yield room, scanner, observer

    for ch in (scanner, observer):
        if ch in room.people:
            room.people.remove(ch)
        if ch in character_registry:
            character_registry.remove(ch)
    room_registry.pop(9001, None)


def test_scan_no_arg_broadcasts_looks_all_around(two_char_room):
    """SCAN-001 — mirrors ROM src/scan.c:60.

    `act("$n looks all around.", ch, NULL, NULL, TO_ROOM);` must reach onlookers
    when do_scan is invoked with no argument. The scanner itself does NOT
    receive the broadcast (TO_ROOM excludes ch).
    """
    room, scanner, observer = two_char_room

    do_scan(scanner, "")

    assert any("Scanner looks all around." in msg for msg in observer.messages), (
        f"Observer never received TO_ROOM scan broadcast. Got: {observer.messages!r}"
    )
    assert not any("looks all around" in msg for msg in scanner.messages), (
        "Scanner should not receive their own TO_ROOM broadcast."
    )


def test_scan_directional_emits_peer_intently_pair(two_char_room):
    """SCAN-002 — mirrors ROM src/scan.c:89-91.

    Directional do_scan must emit:
      act("You peer intently $T.", ch, NULL, dir_name[door], TO_CHAR);
      act("$n peers intently $T.", ch, NULL, dir_name[door], TO_ROOM);

    The "Looking <dir> you see:" header is NOT sent by ROM (it builds the
    string in `buf` but never calls send_to_char). Python must drop the header.
    """
    room, scanner, observer = two_char_room

    result = do_scan(scanner, "north")

    # TO_CHAR: returned to scanner
    assert "You peer intently north." in result, (
        f"Scanner missing TO_CHAR 'You peer intently north.' Got: {result!r}"
    )
    # TO_ROOM: broadcast to observer
    assert any("Scanner peers intently north." in msg for msg in observer.messages), (
        f"Observer missing TO_ROOM peer broadcast. Got: {observer.messages!r}"
    )
    # ROM never sends the "Looking <dir> you see:" header
    assert "Looking north you see:" not in result, (
        f"Spurious 'Looking north you see:' header should be removed (ROM builds "
        f"buf at scan.c:91 but never sends it). Got: {result!r}"
    )


def test_scan_empty_room_emits_no_fallback(two_char_room):
    """SCAN-003 — mirrors ROM src/scan.c:48-104.

    ROM never emits a "No one is nearby." or "Nothing of note." fallback
    when no visible characters exist. Python should not invent extras.
    """
    room, scanner, observer = two_char_room
    # Drop the observer so scanner is alone in the room with no exits.
    room.people.remove(observer)

    no_arg_result = do_scan(scanner, "")
    dir_result = do_scan(scanner, "north")

    assert "No one is nearby." not in no_arg_result, (
        f"ROM emits no fallback when room is empty. Got: {no_arg_result!r}"
    )
    assert "Nothing of note" not in dir_result, (
        f"ROM emits no fallback when no exit/visible characters. Got: {dir_result!r}"
    )
