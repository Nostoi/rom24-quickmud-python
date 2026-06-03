"""Shop haggle success lines must deliver through the connected player channel.

INV-001 wrong-channel cousin: ROM sends shop haggle success text immediately
via ``send_to_char``/``act(TO_CHAR)`` in ``src/act_obj.c``. The Python shop
branches must not strand those lines in ``char.messages`` for connected PCs.
"""

from __future__ import annotations

import asyncio

from mud.commands.shop import do_buy, do_sell
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, Position, RoomFlag
from mud.models.mob import MobIndex
from mud.models.room import Room
from mud.net.protocol import send_to_char
from mud.registry import mob_registry, room_registry, shop_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.spawning.templates import MobInstance
from mud.time import time_info
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world

_STOREFRONT_VNUM = 48900
_KENNEL_VNUM = _STOREFRONT_VNUM + 1
_PET_PROTO_VNUM = 48950


class _RecordingConn:
    """Connection stub matching the duck-typed interface ``send_to_char`` uses."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_line(self, msg: str) -> None:
        self.sent.append(msg)

    async def send(self, msg: str) -> None:
        self.sent.append(msg)


async def _simulate_connection_delivery(char: Character, response: str) -> tuple[list[str], list[str], list[str]]:
    for _ in range(5):
        await asyncio.sleep(0)
    sent_before_drain = list(char.connection.sent)
    mailbox_before_drain = list(char.messages)
    if response:
        await send_to_char(char, response)
    for _ in range(5):
        await asyncio.sleep(0)
    while char.messages:
        await send_to_char(char, char.messages.pop(0))
    return sent_before_drain, mailbox_before_drain, list(char.connection.sent)


def _assert_haggle_immediate(sent_before_drain: list[str], mailbox_before_drain: list[str], expected: str) -> None:
    assert any(expected in line for line in sent_before_drain), (
        f"shop haggle line must reach the connected PC before mailbox drain "
        f"(ROM src/act_obj.c immediate TO_CHAR); sent before drain={sent_before_drain!r}, "
        f"mailbox before drain={mailbox_before_drain!r}"
    )
    assert not any(expected in line for line in mailbox_before_drain), (
        f"shop haggle line must not be stranded in connected PC mailbox; mailbox before drain={mailbox_before_drain!r}"
    )


def test_pet_buy_haggle_delivers_immediately_to_connected_pc() -> None:
    """ROM src/act_obj.c:2606-2607 sends pet-shop haggle text via send_to_char."""

    room_snapshot = dict(room_registry)
    mob_snapshot = dict(mob_registry)
    char_snapshot = list(character_registry)
    original_roll = rng_mm.number_percent

    try:
        storefront = Room(vnum=_STOREFRONT_VNUM, name="Pet Shop Lobby")
        storefront.room_flags = int(RoomFlag.ROOM_PET_SHOP)
        kennel = Room(vnum=_KENNEL_VNUM, name="Kennel")
        room_registry[storefront.vnum] = storefront
        room_registry[kennel.vnum] = kennel

        proto = MobIndex(
            vnum=_PET_PROTO_VNUM,
            short_descr="a costly companion",
            player_name="companion pet",
        )
        proto.level = 3
        proto.act_flags = int(ActFlag.PET)
        mob_registry[proto.vnum] = proto
        kennel.add_mob(MobInstance.from_prototype(proto))

        buyer = Character(name="Buyer", is_npc=False, level=10, position=int(Position.STANDING))
        buyer.messages = []
        buyer.connection = _RecordingConn()
        buyer.gold = 10
        buyer.silver = 0
        buyer.skills = {"haggle": 100}
        storefront.add_character(buyer)
        character_registry.append(buyer)

        async def scenario() -> tuple[list[str], list[str], list[str]]:
            response = do_buy(buyer, "companion")
            assert response == "Enjoy your pet."
            return await _simulate_connection_delivery(buyer, response)

        rng_mm.number_percent = lambda: 40
        sent_before_drain, mailbox_before_drain, _ = asyncio.run(scenario())

        _assert_haggle_immediate(sent_before_drain, mailbox_before_drain, "You haggle the price down to 72 coins.")
    finally:
        rng_mm.number_percent = original_roll
        room_registry.clear()
        room_registry.update(room_snapshot)
        mob_registry.clear()
        mob_registry.update(mob_snapshot)
        character_registry[:] = char_snapshot


def test_item_buy_haggle_delivers_immediately_to_connected_pc() -> None:
    """ROM src/act_obj.c:2728 sends item-buy haggle text via act(TO_CHAR)."""

    initialize_world("area/area.lst")
    char = create_test_character("Buyer", 3010)
    char.level = 60
    char.gold = 200
    char.silver = 0
    char.skills = {"haggle": 100}
    char.connection = _RecordingConn()
    char.messages = []

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry), None
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    original_roll = rng_mm.number_percent
    try:
        time_info.hour = 10
        ration = spawn_object(3031)
        assert ration is not None
        ration.prototype.short_descr = "a connected haggle ration"
        ration.prototype.cost = 100
        ration.extra_flags |= int(ration.prototype.extra_flags)
        keeper.inventory.append(ration)

        async def scenario() -> tuple[list[str], list[str], list[str]]:
            response = do_buy(char, "ration")
            assert "connected haggle ration" in response.lower()
            return await _simulate_connection_delivery(char, response)

        rng_mm.number_percent = lambda: 40
        sent_before_drain, mailbox_before_drain, _ = asyncio.run(scenario())
    finally:
        time_info.hour = previous_hour
        rng_mm.number_percent = original_roll

    _assert_haggle_immediate(sent_before_drain, mailbox_before_drain, "You haggle with the shopkeeper.")


def test_item_sell_haggle_delivers_immediately_to_connected_pc() -> None:
    """ROM src/act_obj.c:2929 sends item-sell haggle text via send_to_char."""

    initialize_world("area/area.lst")
    char = create_test_character("Seller", 3010)
    char.level = 60
    char.gold = 200
    char.silver = 0
    char.connection = _RecordingConn()
    char.messages = []

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry), None
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    previous_hour = time_info.hour
    original_roll = rng_mm.number_percent
    try:
        time_info.hour = 10
        ration = spawn_object(3031)
        assert ration is not None
        ration.prototype.short_descr = "a sell haggle ration"
        ration.prototype.cost = 100
        keeper.inventory.append(ration)
        buy_response = do_buy(char, "ration")
        assert "sell haggle ration" in buy_response.lower()

        char.messages.clear()
        char.skills = {"haggle": 100}

        async def scenario() -> tuple[list[str], list[str], list[str]]:
            response = do_sell(char, "ration")
            assert "sell haggle ration" in response.lower()
            return await _simulate_connection_delivery(char, response)

        rng_mm.number_percent = lambda: 40
        sent_before_drain, mailbox_before_drain, _ = asyncio.run(scenario())
    finally:
        time_info.hour = previous_hour
        rng_mm.number_percent = original_roll

    _assert_haggle_immediate(sent_before_drain, mailbox_before_drain, "You haggle with the shopkeeper.")
