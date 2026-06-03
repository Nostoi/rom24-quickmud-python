"""INV-038 — IDLE-TIMER-RESET-ON-INPUT.

ROM tracks player idleness with ``ch->timer``: ``char_update``
(src/update.c:717-753) increments it once per game tick for every
non-immortal PC *regardless of whether a descriptor is attached*, voids the
character to limbo at ``++ch->timer >= 12``, and the autosave/autoquit second
loop quits the character once ``ch->timer > 30`` (src/update.c:682-683 sets
``ch_quit``). The timer is reset to 0 **only when the descriptor delivers
input** (src/comm.c:605, before ``interpret``), on reconnect (src/comm.c:1856),
and on return-from-void (src/comm.c:1918).

The Python port previously reset ``timer = 0`` on every ``char_update`` tick
whenever a descriptor was present (mud/game_loop.py), so a connected player
*never* accumulated idle time: the idle→void (≥12) and idle→autoquit (>30)
mechanics were dead for anyone logged in, and there was no reset-on-input path
anywhere in ``mud/``. This is a cross-file contract: ``char_update`` must let
the timer climb for connected players, and the command-input chokepoint must be
the thing that resets it.
"""

from __future__ import annotations

import asyncio

import mud.game_loop as gl
from mud.game_loop import char_update
from mud.models.area import Area
from mud.models.character import Character, PCData, character_registry
from mud.models.constants import ROOM_VNUM_LIMBO, Position
from mud.models.room import Room, room_registry
from mud.net.connection import _read_player_command
from mud.net.session import Session


def _make_pc(name: str, *, timer: int, room: Room) -> Character:
    pc = Character(
        name=name,
        level=10,
        hit=20,
        max_hit=20,
        mana=15,
        max_mana=15,
        move=10,
        max_move=10,
        is_npc=False,
        position=int(Position.STANDING),
        pcdata=PCData(condition=[48, 48, 48, 48]),
        timer=timer,
    )
    room.add_character(pc)
    character_registry.append(pc)
    return pc


def test_connected_idle_player_climbs_timer_and_voids(monkeypatch):
    """A logged-in PC who never types must accumulate idle time and disappear
    into the void at ``timer >= 12`` — ROM gates the void on ``level < IMMORTAL``
    and the per-tick increment, not on ``desc``."""

    character_registry.clear()
    room_registry.clear()
    gl._AUTOSAVE_ROTATION = 0

    area = Area(name="Idle Hall")
    room = Room(vnum=4100, area=area)
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[room.vnum] = room
    room_registry[limbo.vnum] = limbo

    monkeypatch.setattr(gl, "save_character", lambda ch: None)

    # Connected (descriptor present), one tick away from the void threshold.
    idler = _make_pc("Idler", timer=11, room=room)
    idler.desc = object()

    char_update()

    # ROM src/update.c:738-752 — ++timer hits 12, character disappears to limbo.
    assert idler.timer == 12
    assert idler.room is limbo
    assert idler.was_in_room is room


def test_connected_idle_player_autoquits_via_async_close(monkeypatch):
    """GL-035: a CONNECTED idler past the autoquit threshold (pre-increment
    ``timer > 30``) is quit by ``char_update`` — ROM src/update.c:682-683 +
    897-900 (``ch_quit`` → ``do_quit``) quits idlers regardless of link state.

    The synchronous tick cannot await the socket teardown, so it schedules an
    async close of the live connection (the parked ``readline`` then returns
    ``None`` → the playing loop's ``finally`` runs the real teardown). This test
    asserts the close is scheduled and fired, and that the tick does NOT itself
    synchronously extract the connected Character (the connection ``finally``
    owns that, to avoid a double-remove race)."""

    character_registry.clear()
    room_registry.clear()
    gl._AUTOSAVE_ROTATION = 0

    area = Area(name="Idle Hall")
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[limbo.vnum] = limbo

    monkeypatch.setattr(gl, "save_character", lambda ch: None)

    class _FakeConn:
        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    # Already voided into limbo (was_in_room set), connected, past threshold.
    idler = _make_pc("Idler", timer=31, room=limbo)
    idler.was_in_room = limbo
    idler.desc = object()
    conn = _FakeConn()
    idler.connection = conn

    async def _run() -> None:
        char_update()
        # Let the fire-and-forget close task scheduled by char_update run.
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    asyncio.run(_run())

    # GL-035: the live connection was closed asynchronously...
    assert conn.closed is True
    # ...the timer still climbed (pre-increment 31 → 32)...
    assert idler.timer == 32
    # ...and the tick did NOT synchronously extract — the playing-loop finally
    # (not modeled in this unit test) owns registry/room teardown on a live conn.
    assert idler in character_registry


def test_linkdead_idle_player_autoquits(monkeypatch):
    """A link-dead PC (``desc is None``) past the idle threshold is auto-quit by
    ``char_update`` — ROM src/update.c:682-683 + 897-900 (`ch_quit` → `do_quit`).
    This is the population the path safely handled before and after INV-038."""

    character_registry.clear()
    room_registry.clear()
    gl._AUTOSAVE_ROTATION = 0

    area = Area(name="Ghost Hall")
    room = Room(vnum=4102, area=area)
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[room.vnum] = room
    room_registry[limbo.vnum] = limbo

    monkeypatch.setattr(gl, "save_character", lambda ch: None)

    ghost = _make_pc("Ghost", timer=31, room=limbo)
    ghost.desc = None
    ghost.was_in_room = room

    char_update()

    assert ghost not in character_registry


def test_only_last_idle_player_autoquits_per_tick(monkeypatch):
    """GL-034: ROM auto-quits at most ONE idle char per ``char_update`` tick —
    ``ch_quit`` is a single pointer overwritten each loop iteration
    (src/update.c:682-683), so it holds the LAST char with pre-increment
    ``timer > 30``; the second loop quits only that one (:897-900). Two
    simultaneously-idle PCs must therefore stagger one-per-tick, not quit en
    masse. Uses link-dead chars so the autoquit stays synchronous."""

    character_registry.clear()
    room_registry.clear()
    gl._AUTOSAVE_ROTATION = 0

    area = Area(name="Ghost Hall")
    room = Room(vnum=4103, area=area)
    limbo = Room(vnum=ROOM_VNUM_LIMBO, area=area)
    room_registry[room.vnum] = room
    room_registry[limbo.vnum] = limbo

    monkeypatch.setattr(gl, "save_character", lambda ch: None)

    # Two link-dead idlers, both past the threshold; registry order [first, last].
    first = _make_pc("FirstGhost", timer=31, room=limbo)
    first.desc = None
    first.was_in_room = room
    last = _make_pc("LastGhost", timer=31, room=limbo)
    last.desc = None
    last.was_in_room = room

    char_update()

    # ROM quits only ``ch_quit`` (the LAST timer>30 char in registry order).
    assert last not in character_registry
    assert first in character_registry
    # The survivor's timer still climbed (31 → 32) and it remains the sole
    # candidate next tick.
    assert first.timer == 32

    char_update()
    assert first not in character_registry


def test_input_read_resets_idle_timer():
    """ROM src/comm.c:605 zeroes ``ch->timer`` when the descriptor delivers a
    line, before ``interpret``. The command-read chokepoint must do the same so
    an *active* connected player never idles out."""

    area = Area(name="Active Hall")
    room = Room(vnum=4101, area=area)

    pc = _make_pc("Doer", timer=25, room=room)

    class _Conn:
        def __init__(self) -> None:
            self._responses = ["look"]
            self.ansi_enabled = True

        async def readline(self, *, max_length: int = 256) -> str | None:  # noqa: ARG002
            if not self._responses:
                return ""
            return self._responses.pop(0)

        async def send_line(self, message: str) -> None:  # pragma: no cover - unused
            return

    session = Session(name="Doer", character=pc, reader=None, connection=_Conn())
    pc.desc = session

    result = asyncio.run(_read_player_command(_Conn(), session))

    assert result == "look"
    assert pc.timer == 0
