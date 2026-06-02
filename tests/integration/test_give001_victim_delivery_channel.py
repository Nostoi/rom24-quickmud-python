"""GIVE-001 — `do_give` TO_VICT line reaches a connected recipient immediately.

INV-001 SINGLE-DELIVERY / MAGIC-003 wrong-channel family (the ACT_COMM-003
shape). ROM `do_give` writes the recipient's line straight to the descriptor
via `act(..., TO_VICT)` — immediate delivery:

    act ("$n gives you $p.", ch, obj, victim, TO_VICT);        # object branch, act_obj.c:834
    act ("$n gives you some coins.", ...) / send_to_char(...)  # coins branch, act_obj.c ~726

Python's `do_give` (`mud/commands/give.py`) delivered both the object-give and
coins-give recipient lines via raw `victim.messages.append(...)` — the mailbox
fallback that a **connected** PC only drains on its next prompt. So a connected
recipient saw "X gives you Y." **late** instead of immediately. The giver's
TO_CHAR line is already correct (returned by `do_give`, sent by the connection
loop); only the victim leg was wrong-channel.

Existing give tests use disconnected chars (mailbox fallback) so they
false-green against the unfixed code. This test uses **connected** PCs and
asserts the recipient line lands on the async connection channel with the
mailbox left empty.
"""

from __future__ import annotations

import asyncio

import pytest

from mud.commands.dispatcher import process_command
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import initialize_world


@pytest.fixture(scope="module", autouse=True)
def _initialize_world():
    initialize_world("area/area.lst")
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def test_room_3001():
    from mud.models.room import Room

    if 3001 not in room_registry:
        room_registry[3001] = Room(vnum=3001, name="Test Room", description="A test room")
    return room_registry[3001]


@pytest.fixture(autouse=True)
def clean_test_state(test_room_3001):
    test_room_3001.contents.clear()
    test_room_3001.people.clear()
    yield
    test_room_3001.contents.clear()
    test_room_3001.people.clear()


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connect(pc) -> _RecordingConn:
    conn = _RecordingConn()
    pc.connection = conn
    pc.messages = []
    return conn


def test_give_object_to_connected_pc_delivers_on_async_channel(movable_char_factory, object_factory, test_room_3001):
    # mirrors ROM src/act_obj.c:834 — act("$n gives you $p.", …, TO_VICT) writes
    # to the recipient's descriptor immediately; a connected PC must receive via
    # the async push, not the mailbox fallback.
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    _connect(giver)
    victim_conn = _connect(victim)

    apple = object_factory({"vnum": 9301, "name": "apple fruit", "short_descr": "a red apple"})
    giver.add_object(apple)

    async def scenario():
        process_command(giver, "give apple Receiver")
        for _ in range(5):
            await asyncio.sleep(0)
        return victim_conn.sent, list(victim.messages)

    victim_sent, victim_mailbox = asyncio.run(scenario())

    assert any("gives you" in s.lower() for s in victim_sent), (
        f"recipient's TO_VICT line not on the async channel (MAGIC-003 wrong-channel "
        f"shape); sent={victim_sent}"
    )
    assert victim_mailbox == [], f"recipient line stranded in mailbox: {victim_mailbox}"
    assert apple in victim.inventory


def test_give_coins_to_connected_pc_delivers_on_async_channel(movable_char_factory, test_room_3001):
    # mirrors ROM src/act_obj.c coins branch — the recipient's "$n gives you …"
    # line writes to the descriptor immediately.
    giver = movable_char_factory("Giver", 3001)
    victim = movable_char_factory("Receiver", 3001)
    _connect(giver)
    victim_conn = _connect(victim)
    giver.silver = 100

    async def scenario():
        process_command(giver, "give 10 coins Receiver")
        for _ in range(5):
            await asyncio.sleep(0)
        return victim_conn.sent, list(victim.messages)

    victim_sent, victim_mailbox = asyncio.run(scenario())

    assert any("gives you" in s.lower() for s in victim_sent), (
        f"recipient's coins TO_VICT line not on the async channel (MAGIC-003 wrong-channel "
        f"shape); sent={victim_sent}"
    )
    assert victim_mailbox == [], f"recipient coins line stranded in mailbox: {victim_mailbox}"
