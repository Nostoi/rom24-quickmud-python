"""Probe: shop do_buy / do_sell must emit TO_ROOM broadcasts.

ROM ``src/act_obj.c``:

  - do_buy (line 2734-2745): emits ``$n buys $p[N].`` (multi) or
    ``$n buys $p.`` (single) to the room before deducting cost.
  - do_sell (line 2923): emits ``$n sells $p.`` to the room before
    haggle/cost-transfer.

Python ``mud/commands/shop.py`` has zero ``broadcast_room`` calls — the
buyer/seller gets a TO_CHAR string but no witness in the room sees the
transaction. ROM-divergent: in the original engine, every onlooker sees
shop activity.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.registry import shop_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.time import time_info
from mud.world import create_test_character, initialize_world


def _grocer_in_room(char):
    return next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )


def _ensure_lantern(keeper):
    if not any((obj.short_descr or "").lower().startswith("a hooded brass lantern") for obj in keeper.inventory):
        lantern = spawn_object(3031)
        assert lantern is not None
        lantern.prototype.short_descr = "a hooded brass lantern"
        keeper.inventory.append(lantern)


def test_do_buy_broadcasts_to_room():
    """ROM src/act_obj.c:2742 — `act("$n buys $p.", ch, obj, NULL, TO_ROOM)`."""
    initialize_world("area/area.lst")
    char = create_test_character("Buyer", 3010)
    char.level = 20
    char.gold = 100
    keeper = _grocer_in_room(char) or spawn_mob(3002)
    assert keeper is not None
    if keeper not in char.room.people:
        keeper.move_to_room(char.room)

    witness = create_test_character("Witness", 3010)
    witness.messages = []

    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        _ensure_lantern(keeper)
        process_command(char, "buy lantern")
    finally:
        time_info.hour = previous_hour

    joined = "\n".join(witness.messages)
    assert "buys" in joined.lower() and "lantern" in joined.lower(), (
        f"witness must see `$n buys $p.` broadcast (ROM src/act_obj.c:2742); witness.messages = {witness.messages!r}"
    )
    # Buyer should be excluded from the room broadcast.
    assert not any("buys" in m.lower() for m in getattr(char, "messages", []) or []), (
        "buyer should not receive the TO_ROOM `$n buys $p.` broadcast"
    )


def test_do_sell_broadcasts_to_room():
    """ROM src/act_obj.c:2923 — `act("$n sells $p.", ch, obj, NULL, TO_ROOM)`."""
    initialize_world("area/area.lst")
    char = create_test_character("Seller", 3010)
    char.level = 20
    char.gold = 100
    keeper = _grocer_in_room(char) or spawn_mob(3002)
    assert keeper is not None
    if keeper not in char.room.people:
        keeper.move_to_room(char.room)

    # Buy a lantern so the seller has something the keeper will buy back.
    previous_hour = time_info.hour
    try:
        time_info.hour = 10
        _ensure_lantern(keeper)
        process_command(char, "buy lantern")
    finally:
        time_info.hour = previous_hour

    witness = create_test_character("Witness", 3010)
    witness.messages = []
    if hasattr(char, "messages"):
        char.messages.clear()

    try:
        time_info.hour = 10
        process_command(char, "sell lantern")
    finally:
        time_info.hour = previous_hour

    joined = "\n".join(witness.messages)
    assert "sells" in joined.lower() and "lantern" in joined.lower(), (
        f"witness must see `$n sells $p.` broadcast (ROM src/act_obj.c:2923); witness.messages = {witness.messages!r}"
    )
    assert not any("sells" in m.lower() for m in getattr(char, "messages", []) or []), (
        "seller should not receive the TO_ROOM `$n sells $p.` broadcast"
    )


def test_do_buy_dispatches_act_trigger_to_npc_witness():
    """INV-025 — the converted `$n buys $p.` broadcast now routes through
    ``act_to_room`` (was a bare ``.broadcast`` with NO TRIG_ACT), so a listening
    NPC in the shop receives ``mp_act_trigger`` per ROM src/comm.c:2384.

    PERS masking is unreachable for shops (the keeper refuses an invisible
    customer — ROM src/act_obj.c:2395 `if (!can_see(keeper, ch))`), so the
    visible-name render is covered by ``test_do_buy_broadcasts_to_room``; this
    test locks the genuinely-new behavior (TRIG_ACT dispatch).
    """
    import mud.mobprog as mobprog
    from mud.mobprog import Trigger

    initialize_world("area/area.lst")
    char = create_test_character("Buyer", 3010)
    char.level = 20
    char.gold = 100
    keeper = _grocer_in_room(char) or spawn_mob(3002)
    assert keeper is not None
    if keeper not in char.room.people:
        keeper.move_to_room(char.room)

    listener = spawn_mob(3002)
    assert listener is not None
    proto = listener.prototype
    proto.mprogs = [
        type(
            "_FakeProg",
            (),
            {"trig_type": int(Trigger.ACT), "trig_phrase": "buys", "code": 'mob echo "SEEN"\n', "vnum": proto.vnum},
        )()
    ]
    listener.move_to_room(char.room)

    fired: list[tuple[str, str]] = []
    original = mobprog.mp_act_trigger

    def _probe(argument, mob, ch, *a, **k):
        fired.append((getattr(mob, "name", "?"), str(argument)))
        return original(argument, mob, ch, *a, **k)

    previous_hour = time_info.hour
    mobprog.mp_act_trigger = _probe
    try:
        time_info.hour = 10
        _ensure_lantern(keeper)
        process_command(char, "buy lantern")
    finally:
        time_info.hour = previous_hour
        mobprog.mp_act_trigger = original

    assert any("buys" in arg.lower() for _, arg in fired), fired
