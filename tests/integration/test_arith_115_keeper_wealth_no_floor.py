"""ARITH-115: keeper-side wealth bookkeeping must not floor at 0.

ROM ``src/act_obj.c:2747-2748`` (`do_buy`, item-shop branch):

    keeper->gold   += cost * number / 100;
    keeper->silver += cost * number - (cost * number / 100) * 100;

ROM adds raw — when ``cost`` is negative (the ARITH-111 player-refund
branch with ``shop.profit_buy < 50`` and a winning haggle), keeper
gold/silver are allowed to drift below zero.  There is no keeper-side
safety clamp; ROM's only normalization is ``deduct_cost``'s
end-of-function ``gold < 0 / silver < 0`` rebalance, which is applied
to the *character*, not the keeper.

Python wraps the keeper update through ``_set_keeper_total_wealth``
(``mud/commands/shop.py:461``), which floors total at 0 — when the
keeper is near broke and the buy refund pushes its total below zero,
the loss is silently swallowed.  Companion clamp at
``_set_character_total_wealth`` (line 473) has the same shape.

This test reproduces the negative-haggle case with a near-broke
keeper and asserts the keeper's total wealth drops below zero by the
refund amount.  Pre-fix: keeper wealth stays at 0 (the shop "ate"
the loss).  Post-fix: keeper total wealth = original + negative cost.
"""

from __future__ import annotations

from mud.commands.dispatcher import process_command
from mud.math.c_compat import c_div
from mud.models.constants import ITEM_INVENTORY
from mud.registry import shop_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.time import time_info
from mud.utils import rng_mm
from mud.world import create_test_character, initialize_world


def _total_wealth(ch) -> int:
    return int(getattr(ch, "gold", 0)) * 100 + int(getattr(ch, "silver", 0))


def test_buy_haggle_negative_cost_drives_keeper_wealth_below_zero():
    """ARITH-115: with profit_buy < 50 and a winning haggle, ROM's
    raw ``keeper->gold += cost*number/100; keeper->silver += ...`` at
    src/act_obj.c:2747-2748 lets keeper wealth drift negative when
    ``cost`` is negative and keeper has less than ``|cost|`` on hand.

    Same setup math as ARITH-111 (unit_price = -9), but the keeper
    starts at 0 wealth so the refund pushes its total negative.
    """
    initialize_world("area/area.lst")
    assert 3002 in shop_registry

    char = create_test_character("Refundee", 3010)
    char.level = 20
    char.gold = 1
    char.silver = 0  # 100 silver total — enough that the player path runs
    char.skills = {"haggle": 100}

    keeper = next(
        (
            p
            for p in char.room.people
            if getattr(p, "prototype", None)
            and p.prototype.vnum in shop_registry
        ),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    # Keeper near broke — the refund must drive its wealth below zero.
    keeper.gold = 0
    keeper.silver = 0

    shop = shop_registry.get(3002)
    saved_profit_buy = shop.profit_buy
    previous_hour = time_info.hour
    original_roll = rng_mm.number_percent
    try:
        shop.profit_buy = 40
        time_info.hour = 10

        ration = spawn_object(3031)
        assert ration is not None
        ration.prototype.short_descr = "an arith-115 ration"
        ration.prototype.cost = 100
        proto_extra = int(getattr(ration.prototype, "extra_flags", 0) or 0)
        ration.prototype.extra_flags = proto_extra | int(ITEM_INVENTORY)
        ration.extra_flags = int(getattr(ration, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
        keeper.inventory.append(ration)

        keeper_before = _total_wealth(keeper)
        assert keeper_before == 0

        rng_mm.number_percent = lambda: 99  # winning haggle roll

        response = process_command(char, "buy ration")
    finally:
        shop.profit_buy = saved_profit_buy
        time_info.hour = previous_hour
        rng_mm.number_percent = original_roll

    assert "arith-115 ration" in response.lower()

    base_unit_price = c_div(100 * 40, 100)
    expected_discount = c_div(c_div(100, 2) * 99, 100)
    expected_unit_price = base_unit_price - expected_discount  # -9
    assert expected_unit_price < 0

    keeper_after = _total_wealth(keeper)
    assert keeper_after == keeper_before + expected_unit_price, (
        f"ARITH-115: with negative haggle cost and a near-broke keeper, "
        f"keeper wealth must drift negative (no floor) to mirror ROM "
        f"src/act_obj.c:2747-2748. Expected total {keeper_before + expected_unit_price} "
        f"(= before {keeper_before} + cost {expected_unit_price}); "
        f"got {keeper_after} (gold={keeper.gold}, silver={keeper.silver})."
    )
