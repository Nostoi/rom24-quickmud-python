"""XP / level-up messages from a kill must reach a connected PC's socket at the
moment of the kill — not get stranded in the ``char.messages`` mailbox until the
player's *next* command.

A monster dies during a **combat tick** (``violence_update`` on the game loop),
not while the player's ``kill`` command is being processed. At tick time there is
no command in flight, so ``mud/net/connection.py``'s read loop never drains
``char.messages``. ROM (``src/fight.c:1788`` ``group_gain`` →
``send_to_char(buf, gch)``, ``src/update.c:113``/``:131`` ``advance_level`` /
``gain_exp``) writes these straight to the descriptor, so a connected player sees
them immediately. The Python port routed them through ``Character.send_to_char``
(mailbox-only), so they surfaced only after the player's next command —
the reported bug: "You receive 155 experience points." printed *after* the
player walked north.

The auto-loot line ("You quickly gather the loot from the corpse.") already used
``_push_message`` (async socket send), which is why it arrived on time while the
XP line lagged — the same channel difference these tests assert is now uniform.

These tests deliberately do **not** drain ``char.messages``: at tick time nothing
does, so the only way the line reaches ``conn.sent`` is via the async push.
"""

from __future__ import annotations

import asyncio

from mud.groups.xp import group_gain
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _run_kill_at_tick_time(attacker: Character, victim: Character) -> list[str]:
    """Award XP the way a combat tick does, then flush async pushes.

    Mirrors the live tick: ``group_gain`` runs under the server event loop, but
    NOTHING drains ``char.messages`` (no command is being processed). The only
    path to the socket is the fire-and-forget ``asyncio.create_task`` push.
    """

    conn: _RecordingConn = attacker.connection  # type: ignore[assignment]

    async def scenario() -> list[str]:
        group_gain(attacker, victim)
        for _ in range(5):  # let the create_task() sends fire
            await asyncio.sleep(0)
        return list(conn.sent)

    return asyncio.run(scenario())


def test_xp_message_reaches_socket_at_tick_time() -> None:
    room = Room(vnum=9100)
    attacker = Character(name="Killer", is_npc=False, level=10)
    attacker.position = Position.STANDING
    victim = Character(name="wimpy monster", is_npc=True, level=2)
    for ch in (attacker, victim):
        room.add_character(ch)

    conn = _RecordingConn()
    attacker.connection = conn

    sent = _run_kill_at_tick_time(attacker, victim)

    xp_lines = [s for s in sent if "experience points" in s]
    assert len(xp_lines) == 1, (
        "XP message must reach the connected PC's socket at kill time, not sit in "
        f"char.messages until the next command. conn.sent={sent}, "
        f"mailbox={attacker.messages}"
    )
