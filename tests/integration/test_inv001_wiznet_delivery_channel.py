"""INV-001 — wiznet single-delivers to a CONNECTED immortal via the async channel.

The final site of the INV-001 wrong-channel sweep. ROM ``src/act_wiz.c:171-194
wiznet`` delivers each line straight to the descriptor with ``send_to_char`` —
an immediate, single write. The Python ``mud/wiznet.py:_wiznet_deliver`` appended
to ``ch.messages`` unconditionally, so a *connected* immortal received its wiznet
lines late (on the next prompt drain) instead of immediately.

This was the one tricky site: its reconnect-announce callers
(``_broadcast_reconnect_notifications`` etc.) run **synchronously outside an
event loop**, so a naive ``push_message`` migration tripped
``asyncio.create_task``'s "no running event loop". The fix makes ``push_message``
loop-aware (mailbox fallback when no loop is running) and routes
``_wiznet_deliver`` through it — so a connected immortal under the live server
loop gets the async send, while the sync reconnect callers (and tests) fall back
to the mailbox exactly as before.

Load-bearing assertion: with a CONNECTED immortal under a running loop, the line
arrives on the async channel and ``messages`` stays empty (pre-fix it is stranded
in the mailbox).
"""

from __future__ import annotations

import asyncio

from mud import registry as global_registry
from mud.models.character import Character, character_registry
from mud.models.constants import Sector
from mud.models.room import Room
from mud.wiznet import WiznetFlag, wiznet


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def _connected_immortal(name: str) -> tuple[Character, _RecordingConn]:
    imm = Character(name=name, is_npc=False, is_admin=True, level=60, trust=60)
    imm.wiznet = int(WiznetFlag.WIZ_ON | WiznetFlag.WIZ_TICKS)
    imm.messages = []
    # INV-027: act_format gates $n/$N through can_see_character, which dereferences
    # the looker's room; Sector.INSIDE is never dark. Production wiznet recipients
    # are always roomed immortals.
    room = Room(vnum=49100, name="Wiznet Test Hall", sector_type=int(Sector.INSIDE))
    room.people = []
    room.people.append(imm)
    imm.room = room
    conn = _RecordingConn()
    imm.connection = conn
    return imm, conn


def test_wiznet_single_delivers_to_connected_immortal() -> None:
    async def scenario():
        character_registry.clear()
        global_registry.descriptor_list = []  # force the registry-iteration path
        imm, conn = _connected_immortal("Watcher")
        character_registry.append(imm)
        try:
            # mirrors ROM src/act_wiz.c:184-189 — send_to_char writes immediately.
            wiznet("TICK!", None, None, WiznetFlag.WIZ_TICKS, None, 0)
            for _ in range(5):
                await asyncio.sleep(0)
            return conn.sent, list(imm.messages)
        finally:
            character_registry.clear()

    sent, mailbox = asyncio.run(scenario())
    hits = [s for s in sent if "TICK" in s]
    assert len(hits) == 1, f"wiznet delivered {len(hits)}x on async channel; sent={sent}"
    assert mailbox == [], f"wiznet line stranded in mailbox (late delivery): {mailbox}"
