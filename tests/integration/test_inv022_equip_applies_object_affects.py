"""INV-022 — EQUIP-APPLIES-OBJECT-AFFECTS.

ROM ``src/handler.c:1754-1797 equip_char`` is the canonical equip
path. After setting ``obj->wear_loc`` it walks ``obj->affected``
(and the unenchanted ``obj->pIndexData->affected`` list) and calls
``affect_modify(ch, paf, TRUE)`` for every affect — applying stat
modifiers, AC deltas, and bitvector grants in lockstep with the
equip. ``unequip_char`` (``src/handler.c:1804-1877``) is the
inverse: ``affect_modify(ch, paf, FALSE)`` for each, then clears
``wear_loc``.

The contract spans three modules:

- ``mud/commands/equipment.py`` (the ``do_wear`` / ``do_remove``
  command surface) — must call ``mud/handler.py:equip_char`` /
  ``unequip_char``, NOT the lower-level
  ``Character.equip_object`` / ``Character.remove_object`` (which
  only move the obj between inventory and equipment dict and do
  not propagate the affected list).
- ``mud/handler.py:equip_char`` / ``unequip_char`` — the canonical
  affect-applying path.
- ``mud/handler.py:affect_modify`` — the per-affect apply/strip
  primitive.

Without the canonical path, a +N-hitroll sword's bonus never
attaches when the player wields it (or never detaches when they
remove it), and the same hole applies to every other apply
location and every bitvector grant.

This row pins the affect-propagation contract end-to-end via the
production ``equip_char`` API. The two ``Character.equip_object``
direct call sites (``mud/commands/inventory.py:159, :172``
inside ``give_school_outfit``) operate on items whose
``obj.affected`` is empty by design — they are an intentional
fast path for items with no stat modifiers. If a future school-
outfit item gains an affect, that call site must move to
``equip_char``; this test documents the contract that will catch
it.
"""

from __future__ import annotations

import pytest

from mud.handler import equip_char, unequip_char
from mud.models.character import Character
from mud.models.constants import WearLocation
from mud.models.obj import Affect, ObjIndex
from mud.models.object import Object

APPLY_HITROLL = 18
APPLY_DAMROLL = 19


def _make_char() -> Character:
    return Character(
        name="wearer",
        is_npc=False,
        level=10,
        hitroll=0,
        damroll=0,
        armor=[100, 100, 100, 100],
    )


def _make_sword_with_affect(location: int, modifier: int) -> Object:
    # item_type=5 is ItemType.WEAPON; equip_char tries int(item_type) so the
    # default string "trash" would crash. Production data uses numeric codes.
    proto = ObjIndex(vnum=8001, short_descr="enchanted blade", item_type=5)
    proto.affected = []  # not used; we'll set obj.affected (the per-instance list)
    obj = Object(instance_id=0, prototype=proto)
    obj.short_descr = "enchanted blade"
    obj.level = 10
    obj.wear_loc = int(WearLocation.NONE)
    obj.affected = [
        Affect(
            where=0,
            type=0,
            level=10,
            duration=-1,
            location=location,
            modifier=modifier,
            bitvector=0,
        )
    ]
    return obj


def test_inv022_equip_char_applies_hitroll_modifier():
    """ROM src/handler.c:1796 — affect_modify(ch, paf, TRUE) raises ch.hitroll."""
    char = _make_char()
    sword = _make_sword_with_affect(APPLY_HITROLL, 5)
    assert char.hitroll == 0

    equip_char(char, sword, int(WearLocation.WIELD))

    assert char.hitroll == 5, (
        f"equip_char must propagate +5 hitroll from obj.affected "
        f"(ROM src/handler.c:1796); got {char.hitroll}"
    )
    assert sword.wear_loc == int(WearLocation.WIELD)


def test_inv022_unequip_char_strips_hitroll_modifier():
    """ROM src/handler.c:1804-1877 — affect_modify(ch, paf, FALSE) on each affect."""
    char = _make_char()
    sword = _make_sword_with_affect(APPLY_HITROLL, 5)

    equip_char(char, sword, int(WearLocation.WIELD))
    assert char.hitroll == 5  # precondition

    unequip_char(char, sword)

    assert char.hitroll == 0, (
        f"unequip_char must strip the +5 hitroll bonus "
        f"(ROM src/handler.c:1804-1877); got {char.hitroll}"
    )


def test_inv022_equip_unequip_round_trip_zero_delta_damroll():
    """Equip → unequip → net zero delta on every modifier site."""
    char = _make_char()
    sword = _make_sword_with_affect(APPLY_DAMROLL, 7)

    initial_damroll = char.damroll
    equip_char(char, sword, int(WearLocation.WIELD))
    assert char.damroll == initial_damroll + 7
    unequip_char(char, sword)
    assert char.damroll == initial_damroll, (
        "equip → unequip must be a zero-sum operation on damroll"
    )


@pytest.mark.parametrize(
    "location,modifier",
    [(APPLY_HITROLL, 3), (APPLY_HITROLL, -2), (APPLY_DAMROLL, 4), (APPLY_DAMROLL, -1)],
)
def test_inv022_equip_unequip_zero_delta_parametrized(location: int, modifier: int):
    """Net zero delta across positive and negative modifiers."""
    char = _make_char()
    obj = _make_sword_with_affect(location, modifier)

    snapshot_hitroll = char.hitroll
    snapshot_damroll = char.damroll
    equip_char(char, obj, int(WearLocation.WIELD))
    unequip_char(char, obj)

    assert char.hitroll == snapshot_hitroll
    assert char.damroll == snapshot_damroll
