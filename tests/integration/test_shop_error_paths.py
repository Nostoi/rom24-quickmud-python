"""Integration tests for do_buy / do_sell error-exit paths.

BUY-006: ROM src/act_obj.c:2688 — afford check must precede level check (2702).
SELL-002: ROM src/act_obj.c:2905 — can-see denial must use keeper name ($n expansion).
SELL-003: ROM src/act_obj.c:2913 — "looks uninterested" message must use keeper name + item.
"""

from __future__ import annotations

from mud.commands.shop import do_buy, do_sell
from mud.models.constants import ExtraFlag
from mud.spawning.mob_spawner import spawn_mob
from mud.spawning.obj_spawner import spawn_object
from mud.time import time_info
from mud.world import create_test_character, initialize_world


def _setup_weaponsmith(char):
    """Spawn weaponsmith (vnum 3003) into char's room."""
    keeper = spawn_mob(3003)
    assert keeper is not None, "spawn_mob(3003) must succeed"
    keeper.move_to_room(char.room)
    return keeper


def test_buy_afford_checked_before_level():
    """BUY-006: ROM src/act_obj.c:2688 — afford check precedes level check (line 2702).

    A char with 0 wealth trying to buy an item above their level should receive
    "can't afford to buy" (line 2688 fires first), NOT "can't use $p yet" (line 2702).
    The discriminating case requires both checks to fail simultaneously.
    """
    initialize_world("area/area.lst")
    char = create_test_character("Tester", 3001)
    char.level = 5
    char.gold = 0
    char.silver = 0

    keeper = _setup_weaponsmith(char)

    # Long sword (vnum 3022): level 7 (> char.level 5), cost 610.
    # Buy price = 610 * profit_buy(120) / 100 = 732 silver (> 0 wealth).
    # Both checks fail: ROM fires afford (line 2688) first, Python was firing
    # level (line 2702) first.
    sword = spawn_object(3022)
    assert sword is not None
    keeper.add_to_inventory(sword)

    previous_hour = time_info.hour
    try:
        time_info.hour = 12
        result = do_buy(char, "sword")
    finally:
        time_info.hour = previous_hour

    # mirroring ROM src/act_obj.c:2688-2698 — afford check precedes level check
    result_lower = (result or "").lower()
    assert "afford" in result_lower, (
        f"ROM src/act_obj.c:2688 — afford check must fire before level check; got: {result!r}"
    )
    assert "use" not in result_lower, f"level check must not fire before afford check; got: {result!r}"


def test_sell_cant_see_uses_keeper_name():
    """SELL-002: ROM src/act_obj.c:2905-2908 — keeper-can't-see branch must use keeper name.

    ROM C: act("$n doesn't see what you are offering.", keeper, NULL, ch, TO_VICT)
    Expands to e.g. "the weaponsmith doesn't see what you are offering."
    Python was returning hardcoded "The shopkeeper doesn't see what you are offering."
    """
    initialize_world("area/area.lst")
    char = create_test_character("Tester", 3001)
    char.level = 20
    char.gold = 50

    keeper = _setup_weaponsmith(char)
    # Make the object invisible so keeper can't see it but can still see the customer.
    # mirroring ROM src/act_obj.c:2904 — can_see_obj(keeper, obj) fails when ITEM_INVIS
    # and keeper lacks DETECT_INVIS. A blind keeper also fails find_keeper's customer-
    # visibility check before reaching this branch, so invisible object is the right setup.
    sword = spawn_object(3021)
    assert sword is not None
    sword.extra_flags = int(getattr(sword, "extra_flags", 0) or 0) | int(ExtraFlag.INVIS)
    char.inventory.append(sword)

    previous_hour = time_info.hour
    try:
        time_info.hour = 12
        result = do_sell(char, "sword")
    finally:
        time_info.hour = previous_hour

    # ROM src/act_obj.c:2905-2908 — "$n doesn't see what you are offering."
    result_lower = (result or "").lower()
    keeper_name = (getattr(keeper, "short_descr", None) or "the weaponsmith").lower()
    assert keeper_name.split()[-1] in result_lower, (
        f"ROM src/act_obj.c:2905 — keeper name must appear in can't-see message; got: {result!r}"
    )
    assert "doesn't see" in result_lower or "does not see" in result_lower, (
        f"ROM src/act_obj.c:2905 — message must contain 'doesn't see'; got: {result!r}"
    )


def test_sell_uninterested_uses_keeper_name():
    """SELL-003: ROM src/act_obj.c:2913 — get_cost<=0 branch must use keeper name via $n.

    ROM C: act("$n looks uninterested in $p.", keeper, obj, ch, TO_VICT)
    Expands to e.g. "the weaponsmith looks uninterested in a small sword."
    Python was returning hardcoded "The shopkeeper doesn't buy that."
    """
    initialize_world("area/area.lst")
    char = create_test_character("Tester", 3001)
    char.level = 20
    char.gold = 50

    keeper = _setup_weaponsmith(char)

    # Vnum 3030 is a torch (item_type=light) — not in weaponsmith's buy list (types 5/6/7).
    # get_cost(keeper, torch, buy=False) returns 0, triggering the ROM line 2911-2914 branch.
    torch = spawn_object(3030)
    assert torch is not None, "spawn_object(3030) must succeed"
    char.inventory.append(torch)

    previous_hour = time_info.hour
    try:
        time_info.hour = 12
        result = do_sell(char, "torch")
    finally:
        time_info.hour = previous_hour

    # mirroring ROM src/act_obj.c:2913 — act("$n looks uninterested in $p.", keeper, obj, ch, TO_VICT)
    result_lower = (result or "").lower()
    keeper_name = (getattr(keeper, "short_descr", None) or "the weaponsmith").lower()
    assert keeper_name.split()[-1] in result_lower, (
        f"ROM src/act_obj.c:2913 — keeper name must appear in 'looks uninterested' message; got: {result!r}"
    )
    assert "uninterested" in result_lower or "interested" in result_lower, (
        f"ROM src/act_obj.c:2913 — message must contain 'uninterested' (not 'doesn't buy'); got: {result!r}"
    )
