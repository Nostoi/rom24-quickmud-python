"""ARITH-205: runtime extract path must not floor carry_number at 0.

ROM `src/handler.c:1678` obj_from_char does `ch->carry_number -= get_obj_number(obj);`
raw, with no floor. extract_obj (`src/handler.c:2051`) routes through obj_from_char.
The Python runtime extract path (`mud/game_loop.py:_extract_obj` ->
`_remove_from_character`) clamped with `max(0, current_number - slot_cost)`, masking a
desynced carry_number. ROM subtracts raw, letting the counter drift negative so the
desync is visible (same philosophy as ARITH-107 nplayer / INV-023).

carry_weight is re-summed via `_recalculate_carry_weight()` after the subtraction, so
only the carry_number side could diverge — hence ARITH-205 is tested on its own, not
batched with ARITH-201.
"""

from __future__ import annotations

from mud.game_loop import _remove_from_character
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object


def _mk_obj(*, weight: int = 5) -> Object:
    proto = ObjIndex(vnum=92005, short_descr="a test object", weight=weight, item_type=int(ItemType.TRASH))
    return Object(instance_id=None, prototype=proto)


def test_remove_from_character_carry_number_allows_negative_on_desync():
    ch = Character(name="Zoe", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0  # desync: carrying an object below, but counter is already 0

    obj = _mk_obj(weight=5)
    ch.inventory.append(obj)  # in inventory without incrementing the cached counter
    obj.carried_by = ch

    _remove_from_character(obj, ch)

    # mirrors ROM src/handler.c:1678 — raw `ch->carry_number -= get_obj_number(obj)`
    # 0 - 1 = -1; pre-fix Python clamped to floored 0
    assert ch.carry_number == -1
    assert obj not in ch.inventory
