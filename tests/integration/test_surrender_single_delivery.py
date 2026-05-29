"""`surrender` must not double-send / wrong-perspective-leak the NPC counterattack.

INV-001 SINGLE-DELIVERY follow-up (b). ROM `do_surrender` (`src/fight.c:3222-3242`)
ends with `multi_hit(mob, ch, TYPE_UNDEFINED)` as a **void** call — the NPC's
counterattack output flows through `act()`/`send_to_char` to descriptors, there
is no return channel. The Python `do_surrender` captured that return
(`attack_messages = multi_hit(opponent, char); messages.extend(attack_messages)`)
and folded it into its own return value, which the connection loop sends to the
**surrendering PC**. So the PC received:
  - the TO_VICT push ("the brute hits you", rendered `{4…{x`) — correct, and
  - the returned **attacker-perspective** line ("You hit …", rendered `{2…{x`) —
    a return-value double-send PLUS a wrong-perspective leak (the PC sees the
    NPC's point of view).

Fix: discard `multi_hit`'s return like `do_kill` (FIGHT-020). The PC sees only
the TO_VICT line, delivered once.
"""

from __future__ import annotations

import asyncio

from mud.commands import process_command
from mud.models.character import Character
from mud.models.constants import Position
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.utils import rng_mm


class _RecordingConn:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def test_surrender_does_not_leak_attacker_perspective_to_pc(monkeypatch) -> None:
    # nat-19 forces the NPC's counterattack to land through the ROM THAC0 roll.
    monkeypatch.setattr(rng_mm, "number_bits", lambda *_: 19)

    async def scenario() -> str:
        room = Room(vnum=9200)
        pc = Character(name="Coward", is_npc=False, level=10)
        pc.position = Position.FIGHTING
        pc.armor = [100, 100, 100, 100]
        mob = Character(name="brute", is_npc=True, level=10)
        mob.position = Position.FIGHTING
        mob.hitroll = 100
        mob.skills["hand to hand"] = 100
        for ch in (pc, mob):
            room.add_character(ch)
        pc.fighting = mob
        mob.fighting = pc

        conn = _RecordingConn()
        pc.connection = conn

        # Mirror mud/net/connection.py per-command delivery.
        response = process_command(pc, "surrender")
        await send_to_char(pc, response)
        for _ in range(5):
            await asyncio.sleep(0)
        while pc.messages:
            await send_to_char(pc, pc.messages.pop(0))
        return "\n".join(conn.sent)

    delivered = asyncio.run(scenario())

    # The PC must NOT receive an attacker-perspective combat line ({2 = fight_yhit,
    # the "You hit X" POV that belongs to the NPC, not the surrendering PC).
    assert "{2" not in delivered, (
        f"surrender leaked the NPC's attacker-perspective combat line to the PC "
        f"(INV-001 return-value double-send + wrong perspective). Delivered:\n{delivered}"
    )
    # The PC still sees the surrender flow and the NPC's refusal (TO_CHAR).
    assert "You surrender to brute!" in delivered
    assert "seems to ignore your cowardly act!" in delivered
