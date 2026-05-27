"""GROUP-001 — do_group add/remove broadcasts reach live sockets.

ROM C: ``src/act_comm.c:1838-1854``
    Add:    act("$N joins $n's group.", ch, NULL, victim, TO_NOTVICT);
            act("You join $n's group.",  ch, NULL, victim, TO_VICT);
    Remove: act("$N removes you from $s group.", ch, NULL, victim, TO_VICT);
            act("$N removes $n from $s group.",  ch, NULL, victim, TO_NOTVICT);

ROM `act()` writes to the recipient's socket. Pre-fix Python only appended to
the test-fallback ``.messages`` list, so connected players saw nothing on
group join/remove. This test asserts both TO_VICT and TO_NOTVICT route through
``_send_to_char_sync`` which fires the async socket task.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.room import Room
from mud.registry import room_registry


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room_registry[vnum] = room
    return room


def _player(name: str, room: Room):
    from mud.world import create_test_character

    char = create_test_character(name, room.vnum)
    char.is_npc = False
    char.level = 30
    char.messages = []
    return char


def test_do_group_add_emits_via_socket_path(monkeypatch):
    # mirrors ROM src/act_comm.c:1850-1854 — TO_VICT and TO_NOTVICT via act()
    from mud.commands import group_commands as gc

    room = _room(50600)
    leader = _player("Leader", room)
    follower = _player("Follower", room)
    _player("Watcher", room)

    # Make follower a follower of leader so do_group can add them
    follower.master = leader

    send_calls: list[tuple[str, str]] = []

    def fake_send(char, message):
        send_calls.append((getattr(char, "name", "?"), message))

    monkeypatch.setattr(gc, "_send_to_char_sync", fake_send, raising=False)

    gc.do_group(leader, "Follower")

    vict_msgs = [m for n, m in send_calls if n == "Follower"]
    assert any("You join Leader's group" in m for m in vict_msgs), (
        f"missing TO_VICT via _send_to_char_sync; got {send_calls!r}"
    )
    notvict_msgs = [m for n, m in send_calls if n == "Watcher"]
    assert any("Follower joins Leader's group" in m for m in notvict_msgs), (
        f"missing TO_NOTVICT via _send_to_char_sync; got {send_calls!r}"
    )


def test_do_group_remove_emits_via_socket_path(monkeypatch):
    # mirrors ROM src/act_comm.c:1838-1847 — TO_VICT and TO_NOTVICT via act()
    from mud.commands import group_commands as gc

    room = _room(50700)
    leader = _player("Leader", room)
    follower = _player("Follower", room)
    _player("Watcher", room)

    follower.master = leader
    follower.leader = leader  # already in group

    send_calls: list[tuple[str, str]] = []

    def fake_send(char, message):
        send_calls.append((getattr(char, "name", "?"), message))

    monkeypatch.setattr(gc, "_send_to_char_sync", fake_send, raising=False)

    gc.do_group(leader, "Follower")

    vict_msgs = [m for n, m in send_calls if n == "Follower"]
    assert any("removes you" in m for m in vict_msgs), (
        f"missing TO_VICT (remove) via _send_to_char_sync; got {send_calls!r}"
    )
    notvict_msgs = [m for n, m in send_calls if n == "Watcher"]
    assert any("removes Follower" in m for m in notvict_msgs), (
        f"missing TO_NOTVICT (remove) via _send_to_char_sync; got {send_calls!r}"
    )
