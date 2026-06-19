"""ARITH-111: item-shop haggle must not floor `unit_price` at 0.

ROM ``src/act_obj.c:2722-2729`` (`do_buy`, item-shop branch):

    /* haggle */
    roll = number_percent ();
    if (!IS_OBJ_STAT (obj, ITEM_SELL_EXTRACT)
        && roll < get_skill (ch, gsn_haggle))
    {
        cost -= obj->cost / 2 * roll / 100;
        ...
    }

ROM subtracts the haggle discount raw — ``cost`` is allowed to go
negative when the shop's ``profit_buy`` is below 50 and the haggle
roll is high enough that ``obj->cost / 2 * roll / 100`` exceeds the
marked-up unit price.

When ``cost`` is negative, ``deduct_cost(ch, cost * number)`` at
``src/handler.c:2397-2422`` refunds the player (the
``ch->silver -= silver`` line at 2410 with negative ``silver`` adds
to the player's purse).  Python's ``deduct_cost``
(``mud/handler.py:885``) already mirrors that — only the
``max(0, unit_price - discount)`` clamp at
``mud/commands/shop.py:822`` blocks the divergence.

This test reproduces the negative-haggle case and asserts the player
is refunded, matching ROM.  Pre-fix the clamp turns the buy into a
"free item" — player's wealth is unchanged across the transaction.

Note: keeper-side bookkeeping (``_set_keeper_total_wealth`` clamping
to 0) is a *separate* divergence and is intentionally not asserted
here.  See ARITH-115 in
``docs/parity/audits/ARITHMETIC_BOUNDARY.md``.  The keeper is given
plenty of starting wealth so its clamp does not fire on this path.
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


def test_buy_haggle_negative_cost_refunds_player():
    """ARITH-111: with profit_buy < 50 and a winning haggle, ROM's
    raw `cost -= obj->cost/2 * roll/100` drives unit_price negative
    and the player gets refunded silver via deduct_cost.

    Setup numbers (chosen to make the floor unambiguously fire):

    - proto.cost = 100 (unmarked-up reference price)
    - shop.profit_buy = 40 → base unit_price = 100*40/100 = 40
    - haggle roll = 99, haggle skill = 100 → succeeds
    - discount = c_div(c_div(100, 2) * 99, 100) = c_div(50*99, 100)
              = c_div(4950, 100) = 49
    - unit_price - discount = 40 - 49 = -9

    ROM: `deduct_cost(ch, -9)` → `silver = min(ch->silver, -9) = -9`
    (because ch->silver >= 0). `silver < cost` is `-9 < -9` false,
    so `gold = 0`, then `ch->silver -= -9` adds 9 silver. Player
    wealth INCREASES by 9.

    Python pre-fix: `max(0, 40 - 49) = 0` → free item, no refund.
    """
    initialize_world("area/area.lst")
    assert 3002 in shop_registry

    char = create_test_character("Haggler", 3010)
    char.level = 20
    char.gold = 1
    char.silver = 0  # total wealth = 100 silver
    char.skills = {"haggle": 100}

    keeper = next(
        (p for p in char.room.people if getattr(p, "prototype", None) and p.prototype.vnum in shop_registry),
        None,
    )
    if keeper is None:
        keeper = spawn_mob(3002)
        assert keeper is not None
        keeper.move_to_room(char.room)

    # Keep keeper-wealth-clamp out of the way (ARITH-115 is separate).
    keeper.gold = 1000
    keeper.silver = 0

    shop = shop_registry.get(3002)
    saved_profit_buy = shop.profit_buy
    previous_hour = time_info.hour
    original_roll = rng_mm.number_percent
    try:
        # Drive unit_price below half-cost.
        shop.profit_buy = 40
        time_info.hour = 10

        ration = spawn_object(3031)
        assert ration is not None
        ration.prototype.short_descr = "an arith-111 ration"
        ration.prototype.cost = 100
        proto_extra = int(getattr(ration.prototype, "extra_flags", 0) or 0)
        ration.prototype.extra_flags = proto_extra | int(ITEM_INVENTORY)
        ration.extra_flags = int(getattr(ration, "extra_flags", 0) or 0) | int(ITEM_INVENTORY)
        keeper.inventory.append(ration)
        # GETCOST-001: get_cost uses the RUNTIME obj.cost; spawn_object(3031) shares
        # its proto with the grocer's default 3031 stock, so sync every live 3031's
        # runtime cost to the mutated proto cost (the ROM spawn invariant).
        for stock in keeper.inventory:
            if getattr(stock.prototype, "vnum", None) == 3031:
                stock.cost = 100

        before_wealth = _total_wealth(char)

        rng_mm.number_percent = lambda: 99  # winning haggle roll

        response = process_command(char, "buy ration")
    finally:
        shop.profit_buy = saved_profit_buy
        time_info.hour = previous_hour
        rng_mm.number_percent = original_roll

    assert "arith-111 ration" in response.lower()

    base_unit_price = c_div(100 * 40, 100)
    expected_discount = c_div(c_div(100, 2) * 99, 100)
    expected_unit_price = base_unit_price - expected_discount

    assert expected_unit_price < 0, f"test setup must drive unit_price negative; got {expected_unit_price}"

    # ROM: player wealth increases by |negative cost|.
    after_wealth = _total_wealth(char)
    assert after_wealth == before_wealth - expected_unit_price, (
        f"ARITH-111: with negative haggle cost, player must be refunded "
        f"(ROM src/handler.c:2410 deduct_cost). Expected wealth "
        f"{before_wealth - expected_unit_price} (= before {before_wealth} "
        f"- cost {expected_unit_price}); got {after_wealth}."
    )
