"""`"Enjoy your pet."` must SINGLE-DELIVER to a connected PC buying a pet.

INV-001 (e) — SINGLE-DELIVERY family, the `do_kill` / `do_rescue` / INV-001 (d)
shape. `do_buy`'s pet-shop branch (`mud/commands/shop.py:_handle_pet_shop_purchase`)
did ``char.messages.append("Enjoy your pet.")`` **and** returned the same line.
The connection read loop (`mud/net/connection.py:1980-2000`) sends a command's
return value AND drains ``char.messages``, so a connected PC buying a pet saw
"Enjoy your pet." **twice**. ROM `do_buy` (`src/act_obj.c:2635`) does
``send_to_char("Enjoy your pet.\n\r", ch)`` once and returns void.

Fix: keep the return (the single canonical delivery), drop the mailbox append
(the INV-001 (d) recipe). Surfaced 2026-05-29 by the advisor while closing
SHOP-PET-002 (which rewrote this function). See
`docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md` INV-001 (e).
"""

from __future__ import annotations

import asyncio

from mud.commands.shop import do_buy
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, Position, RoomFlag
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.registry import mob_registry, room_registry
from mud.spawning.templates import MobInstance

_STOREFRONT_VNUM = 48800
_KENNEL_VNUM = _STOREFRONT_VNUM + 1
_PET_PROTO_VNUM = 48850


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


def test_buy_pet_delivers_enjoy_line_once_to_connected_pc() -> None:
    """A connected PC buying a pet sees "Enjoy your pet." exactly once."""

    room_snapshot = dict(room_registry)
    mob_snapshot = dict(mob_registry)
    char_snapshot = list(character_registry)

    try:
        storefront = Room(vnum=_STOREFRONT_VNUM, name="Pet Shop Lobby")
        storefront.room_flags = int(RoomFlag.ROOM_PET_SHOP)
        kennel = Room(vnum=_KENNEL_VNUM, name="Kennel")
        room_registry[storefront.vnum] = storefront
        room_registry[kennel.vnum] = kennel

        proto = MobIndex(
            vnum=_PET_PROTO_VNUM,
            short_descr="a cuddly companion",
            player_name="companion pet",
        )
        proto.level = 3
        proto.act_flags = int(ActFlag.PET)
        mob_registry[proto.vnum] = proto
        kennel.add_mob(MobInstance.from_prototype(proto))

        buyer = Character(name="Buyer", is_npc=False, level=10, position=int(Position.STANDING))
        buyer.messages = []
        conn = _RecordingConn()
        buyer.connection = conn
        buyer.gold = 10  # cost = 10 * 3 * 3 = 90 coins
        buyer.silver = 0
        storefront.add_character(buyer)
        character_registry.append(buyer)

        async def scenario():
            # Mirror mud/net/connection.py's per-command delivery: send the return
            # value, let any fire-and-forget push tasks fire, then drain the mailbox.
            response = do_buy(buyer, "companion")
            assert response == "Enjoy your pet."
            await send_to_char(buyer, response)
            for _ in range(5):
                await asyncio.sleep(0)
            while buyer.messages:
                await send_to_char(buyer, buyer.messages.pop(0))
            return conn.sent

        sent = asyncio.run(scenario())

        enjoy = [s for s in sent if "Enjoy your pet." in s]
        assert len(enjoy) == 1, (
            f'"Enjoy your pet." delivered {len(enjoy)}x to connected PC (expected 1 '
            f"— SINGLE-DELIVERY/INV-001 (e)). Sent: {sent}"
        )
    finally:
        room_registry.clear()
        room_registry.update(room_snapshot)
        mob_registry.clear()
        mob_registry.update(mob_snapshot)
        character_registry[:] = char_snapshot
