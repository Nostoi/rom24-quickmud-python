"""INV-001 — say / tell / shout / emote single-deliver to a CONNECTED listener.

SAY-005 / SHOUT-004 / TELL-007 / EMOTE-004 — INV-001 SINGLE-DELIVERY family.
ROM delivers each of these via `act()` / `send_to_char`, which writes to the
recipient's descriptor exactly once. `mud/commands/communication.py` renders a
per-listener PERS-masked string (INV-025) in a hand-rolled loop that was never
migrated to `push_message`:

    if writer is not None:
        asyncio.create_task(send_to_char(listener, per_message))   # live send
    if hasattr(listener, "messages"):
        listener.messages.append(per_message)                       # AND mailbox

For a **connected** listener this is BOTH channels: the async send delivers
immediately, and the connection read loop (`mud/net/connection.py:2002-2005`)
drains `listener.messages` on the listener's next prompt — so the line arrives
**twice**. SAY-004 fixed this once (dropped a redundant `broadcast_room`); the
INV-025 PERS rewrite re-introduced it as a hand-rolled both-channels loop.

The existing comm tests (`test_say_parity.py`, etc.) use **disconnected**
listeners, for which only the mailbox copy exists — so they count 1 and
false-green against the doubled code. The load-bearing assertion here is
`listener.messages == []` (pre-fix `== [line]` → fails; post-fix `push_message`
XOR → empty), plus the line present once on the async channel.
"""

from __future__ import annotations

import asyncio

from mud.commands.dispatcher import process_command
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import Position
from mud.models.room import Room
from mud.registry import room_registry


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _make_room(vnum: int = 9440) -> Room:
    room = Room(vnum=vnum, name="Comm Room", description="", room_flags=0, sector_type=0)
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


class _StubDesc:
    """Minimal session stub so a connected PC is not treated as linkdead by do_tell."""

    editor = None


def _connected_pc(name: str, room: Room) -> tuple[Character, _RecordingConn]:
    pc = Character(name=name, is_npc=False, level=10, room=room, position=int(Position.STANDING))
    pc.messages = []
    conn = _RecordingConn()
    pc.connection = conn
    # A real connected PC has a live session in .desc; without it do_tell's
    # _is_player_linkdead check defers the tell to the mailbox queue.
    pc.desc = _StubDesc()
    room.people.append(pc)
    character_registry.append(pc)
    return pc, conn


def _run_with_registry(coro_factory):
    snapshot = list(character_registry)
    character_registry.clear()
    try:
        return asyncio.run(coro_factory())
    finally:
        character_registry.clear()
        character_registry.extend(snapshot)
        room_registry.pop(9440, None)


def test_say_single_delivers_to_connected_listener() -> None:
    async def scenario():
        room = _make_room()
        speaker, _ = _connected_pc("Speaker", room)
        listener, listener_conn = _connected_pc("Listener", room)
        process_command(speaker, "say hello there")
        for _ in range(5):
            await asyncio.sleep(0)
        return listener_conn.sent, list(listener.messages)

    sent, mailbox = _run_with_registry(scenario)
    said = [s for s in sent if "says" in s.lower() and "hello there" in s.lower()]
    assert len(said) == 1, f"say delivered {len(said)}x on async channel; sent={sent}"
    assert mailbox == [], f"say line stranded in mailbox (double-delivery): {mailbox}"


def test_tell_single_delivers_to_connected_target() -> None:
    async def scenario():
        room = _make_room()
        speaker, _ = _connected_pc("Speaker", room)
        target, target_conn = _connected_pc("Listener", room)
        process_command(speaker, "tell Listener hello there")
        for _ in range(5):
            await asyncio.sleep(0)
        return target_conn.sent, list(target.messages)

    sent, mailbox = _run_with_registry(scenario)
    told = [s for s in sent if "tells you" in s.lower() and "hello there" in s.lower()]
    assert len(told) == 1, f"tell delivered {len(told)}x on async channel; sent={sent}"
    assert mailbox == [], f"tell line stranded in mailbox (double-delivery): {mailbox}"


def test_shout_single_delivers_to_connected_listener() -> None:
    async def scenario():
        room = _make_room()
        speaker, _ = _connected_pc("Speaker", room)
        listener, listener_conn = _connected_pc("Listener", room)
        process_command(speaker, "shout hello there")
        for _ in range(5):
            await asyncio.sleep(0)
        return listener_conn.sent, list(listener.messages)

    sent, mailbox = _run_with_registry(scenario)
    shouted = [s for s in sent if "shouts" in s.lower() and "hello there" in s.lower()]
    assert len(shouted) == 1, f"shout delivered {len(shouted)}x on async channel; sent={sent}"
    assert mailbox == [], f"shout line stranded in mailbox (double-delivery): {mailbox}"


def test_emote_single_delivers_to_connected_listener() -> None:
    async def scenario():
        room = _make_room()
        speaker, _ = _connected_pc("Speaker", room)
        listener, listener_conn = _connected_pc("Listener", room)
        process_command(speaker, "emote waves happily")
        for _ in range(5):
            await asyncio.sleep(0)
        return listener_conn.sent, list(listener.messages)

    sent, mailbox = _run_with_registry(scenario)
    emoted = [s for s in sent if "waves happily" in s.lower()]
    assert len(emoted) == 1, f"emote delivered {len(emoted)}x on async channel; sent={sent}"
    assert mailbox == [], f"emote line stranded in mailbox (double-delivery): {mailbox}"


def test_yell_single_delivers_to_connected_listener() -> None:
    """do_yell's per-listener loop must single-deliver to a CONNECTED listener.

    Characterization lock for the YELL hand-rolled `create_task(send_to_char)` /
    `_queue_personal_message` XOR (the last delivery site that
    `docs/parity/DIVERGENCE_CLASS_ROSTER.md` cites as blocking a Layer-A static
    guard for the async-delivery class). Collapsing it onto the canonical
    `push_message` chokepoint must preserve this contract: socket once, mailbox
    empty. yell is area-gated, so the listener must share the yeller's area.
    """

    async def scenario():
        room = _make_room()
        room.area = Area(name="Comm Area")  # do_yell requires char.room.area and area-match
        speaker, _ = _connected_pc("Speaker", room)
        listener, listener_conn = _connected_pc("Listener", room)
        process_command(speaker, "yell hello there")
        for _ in range(5):
            await asyncio.sleep(0)
        return listener_conn.sent, list(listener.messages)

    sent, mailbox = _run_with_registry(scenario)
    yelled = [s for s in sent if "yells" in s.lower() and "hello there" in s.lower()]
    assert len(yelled) == 1, f"yell delivered {len(yelled)}x on async channel; sent={sent}"
    assert mailbox == [], f"yell line stranded in mailbox (double-delivery): {mailbox}"
