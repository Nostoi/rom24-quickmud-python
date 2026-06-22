"""Divergence-class 14 — Connection / session lifecycle (net-death link-dead).

ROM `close_socket` (`src/comm.c:1075-1093`) keeps a `CON_PLAYING` char link-dead
on a socket drop (`ch->desc = NULL`, char stays in `char_list`/room), and
`check_reconnect` (`src/comm.c:1836`, fConn=TRUE, called at `nanny.c:281` AFTER
the password is verified) rebinds a returning player to that SAME in-world
instance — preserving combat/position/transient affects — rather than reloading
from disk. The Python port previously treated link loss as `do_quit` and removed
the char immediately (the divergence filed as roster class 14).

These tests pin the faithful behavior:
  * the link-dead lookup (`_find_linkdead_character`) and rebind decision in
    `_select_character` (Commit 1 — inert until link-dead chars can exist);
  * the socket-drop → link-dead linger in the disconnect finally (Commit 2);
  * the end-to-end drop → reconnect → same-instance, no-duplicate invariant
    (the INV-009 no-duplicates property, preserved via the new mechanism).
"""

from __future__ import annotations

import asyncio

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.connection import _finalize_disconnect, _find_linkdead_character, _select_character


@pytest.fixture(autouse=True)
def _clean_registry():
    character_registry.clear()
    yield
    character_registry.clear()


def _linkdead_pc(name: str = "Frodo") -> Character:
    """A char in the world flagged link-dead with no descriptor — ROM net-death."""
    ch = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    ch.desc = None
    ch.connection = None
    ch.link_dead = True  # explicit marker the linger path sets (Commit 2)
    character_registry.append(ch)
    return ch


class _StubConn:
    host = "localhost"

    async def send_line(self, msg: str) -> None:  # only hit on error branches
        pass


def test_find_linkdead_character_matches_desc_none_pc_by_name() -> None:
    ld = _linkdead_pc("Bilbo")
    assert _find_linkdead_character("bilbo") is ld
    assert _find_linkdead_character("Bilbo") is ld


def test_find_linkdead_ignores_connected_npc_and_wrong_name() -> None:
    connected = Character(name="Sam", is_npc=False)
    connected.desc = None
    connected.connection = object()  # live link → not link-dead
    character_registry.append(connected)

    npc = Character(name="Orc", is_npc=True)
    npc.desc = None
    npc.connection = None
    character_registry.append(npc)

    _linkdead_pc("Merry")

    assert _find_linkdead_character("Sam") is None  # still connected
    assert _find_linkdead_character("Orc") is None  # NPC
    assert _find_linkdead_character("Pippin") is None  # no such char
    assert _find_linkdead_character("Merry") is not None


def test_select_character_rebinds_to_linkdead_instance_without_disk_load() -> None:
    sentinel = object()

    async def scenario():
        ld = _linkdead_pc("Frodo")
        ld._reconnect_sentinel = sentinel  # transient in-world state
        result = await _select_character(_StubConn(), object(), "frodo")
        return result, ld

    result, ld = asyncio.run(scenario())
    assert result is not None, "rebind must resolve a link-dead char, not fail to load"
    char, reconnecting = result
    assert char is ld, "must rebind the SAME in-world instance, not load a fresh char from disk"
    assert reconnecting is True, "rebinding a link-dead char is a reconnect"
    assert char._reconnect_sentinel is sentinel, "transient in-world state must survive the rebind"
    assert char.link_dead is False, "rebind must clear the link-dead marker (it now has a descriptor)"


# --- Commit 2: socket-drop → link-dead linger (the disconnect finally) ---------


def _in_world_pc(name: str, *, conn: object) -> tuple[Character, Room]:
    room = Room(vnum=3001, name="r", description="", room_flags=0, sector_type=0)
    room.people = []
    ch = Character(name=name, is_npc=False, level=10, position=int(Position.STANDING))
    ch.connection = conn
    ch.desc = object()
    room.add_character(ch)
    character_registry.append(ch)
    return ch, room


def test_finalize_disconnect_link_drop_lingers_in_world() -> None:
    """An unexpected socket drop (no quit) keeps the char in the world link-dead."""
    conn = object()
    ch, room = _in_world_pc("Dropper", conn=conn)
    # No _quit_requested → genuine net-death link drop.

    _finalize_disconnect(ch, session=None, conn=conn, username="dropper", forced_disconnect=False)

    assert ch in character_registry, "link-dead char must remain in the registry (ROM keeps it in char_list)"
    assert ch in room.people, "link-dead char must remain in its room"
    assert ch.link_dead is True, "the link-dead marker must be set"
    assert ch.desc is None, "the descriptor must be detached"
    assert ch.connection is None, "the connection must be detached"


def test_finalize_disconnect_quit_fully_extracts() -> None:
    """An explicit quit (ROM do_quit) removes the char from the world."""
    conn = object()
    ch, room = _in_world_pc("Quitter", conn=conn)
    ch._quit_requested = True

    _finalize_disconnect(ch, session=None, conn=conn, username="quitter", forced_disconnect=False)

    assert ch not in character_registry, "a quit must remove the char from the registry"
    assert ch not in room.people, "a quit must remove the char from its room"
    assert ch.link_dead is False, "a quit is not link-dead"


def test_finalize_disconnect_forced_takeover_is_noop() -> None:
    """A forced disconnect (descriptor takeover) leaves the live char untouched."""
    conn = object()
    ch, room = _in_world_pc("Taken", conn=conn)

    _finalize_disconnect(ch, session=None, conn=conn, username="taken", forced_disconnect=True)

    assert ch in character_registry, "takeover transfers the live char — must not remove it"
    assert ch in room.people
    assert ch.connection is conn, "takeover must not detach the connection (transfer handles it)"
    assert ch.link_dead is False
