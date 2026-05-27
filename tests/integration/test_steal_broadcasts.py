"""STEAL-001 — _steal_failure TO_VICT and TO_NOTVICT live-socket delivery.

ROM C: ``src/act_obj.c:2222-2223``
    act("$n tried to steal from you.", ch, NULL, victim, TO_VICT);
    act("$n tried to steal from $N.",  ch, NULL, victim, TO_NOTVICT);

ROM uses ``act()`` which writes directly to the recipient's socket. Pre-fix
Python only appended to the test-fallback ``.messages`` list, so connected
players saw nothing. This test asserts the failure-path emits TO_VICT via
``send_to_char`` and TO_NOTVICT via ``broadcast_room`` (which schedules the
async socket task for any bystander with a ``connection``).
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.constants import Position
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


def _make_thief(name: str, room: Room):
    from mud.world import create_test_character

    char = create_test_character(name, room.vnum)
    char.is_npc = False
    char.level = 30
    char.skills["steal"] = 1  # near-guaranteed failure
    char.act = 0
    char.messages = []
    return char


def _make_victim(name: str, room: Room, *, is_npc: bool = False):
    from mud.world import create_test_character

    char = create_test_character(name, room.vnum)
    char.is_npc = is_npc
    char.level = 30
    char.position = Position.STANDING
    char.messages = []
    return char


def test_steal_failure_emits_to_vict_and_to_notvict_via_protocol(monkeypatch):
    # mirrors ROM src/act_obj.c:2222-2223 — must reach real sockets, not just .messages
    from mud.commands import thief_skills as ts

    room = _room(50500)
    thief = _make_thief("Thief", room)
    victim = _make_victim("Mark", room, is_npc=False)
    _make_victim("Watcher", room, is_npc=False)

    monkeypatch.setattr(ts, "number_percent", lambda: 100)  # force failure
    monkeypatch.setattr(ts, "number_range", lambda lo, hi: 0)

    send_calls: list[tuple[str, str]] = []

    def fake_send(char, message):
        send_calls.append((getattr(char, "name", "?"), message))

    monkeypatch.setattr(ts, "_send_to_char_sync", fake_send)

    ts._steal_failure(thief, victim)

    vict_msgs = [m for n, m in send_calls if n == "Mark"]
    assert any("Thief tried to steal from you" in m for m in vict_msgs), (
        f"missing TO_VICT via _send_to_char_sync; got {send_calls!r}"
    )
    bystander_msgs = [m for n, m in send_calls if n == "Watcher"]
    assert any("Thief tried to steal from Mark" in m for m in bystander_msgs), (
        f"missing TO_NOTVICT via _send_to_char_sync; got {send_calls!r}"
    )
    # actor and victim must NOT receive the TO_NOTVICT message
    actor_notvict = [m for n, m in send_calls if n == "Thief" and "from Mark" in m]
    victim_notvict = [m for n, m in send_calls if n == "Mark" and "from Mark" in m]
    assert not actor_notvict, f"actor leaked TO_NOTVICT: {actor_notvict!r}"
    assert not victim_notvict, f"victim leaked TO_NOTVICT: {victim_notvict!r}"
