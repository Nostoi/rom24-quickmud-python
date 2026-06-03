"""INV-011 CARRY-WEIGHT-COHERENCE enforcement.

ROM ref: src/handler.c:1626 obj_to_char / 1642 obj_from_char keep
`ch->carry_weight` and `ch->carry_number` in sync with the linked list
`ch->carrying`. Every obj_to_char adds the obj's weight and a number
slot; every obj_from_char subtracts them. extract_obj (src/handler.c:
2051) routes through obj_from_char before unlinking.

Python contract (INV-011):

    ch.carry_weight == sum(_object_carry_weight(o) for o in ch.inventory)
                     + sum(_object_carry_weight(o) for o in ch.equipment.values())
    ch.carry_number == sum(_object_carry_number(o) for o in ch.inventory)
                     + sum(_object_carry_number(o) for o in ch.equipment.values())

Canonical mutators (mud/models/character.py): `Character.add_object`,
`Character.equip_object`, `Character.remove_object`. Each calls
`_recalculate_carry_weight` and adjusts `carry_number`.

The runtime extract path (`mud/game_loop.py:_extract_obj` →
`_remove_from_character`) bypasses both helpers — it removes the obj
from `inventory` / `equipment` but never re-syncs the cached counters.
That is the gap this invariant locks in.

See docs/parity/CROSS_FILE_INVARIANTS_TRACKER.md INV-011.
"""

from __future__ import annotations

from mud.models.character import Character, _object_carry_number, _object_carry_weight
from mud.models.constants import ItemType, WearLocation
from mud.models.obj import ObjIndex
from mud.models.object import Object


def _mk_obj(*, weight: int = 5, item_type: int | None = None) -> Object:
    proto = ObjIndex(
        vnum=92000,
        short_descr="a test object",
        weight=weight,
        item_type=item_type if item_type is not None else int(ItemType.TRASH),
    )
    return Object(instance_id=None, prototype=proto)


def _expected_carry_weight(ch: Character) -> int:
    return sum(_object_carry_weight(o) for o in ch.inventory) + sum(
        _object_carry_weight(o) for o in ch.equipment.values()
    )


def _expected_carry_number(ch: Character) -> int:
    return sum(_object_carry_number(o) for o in ch.inventory) + sum(
        _object_carry_number(o) for o in ch.equipment.values()
    )


def _assert_coherent(ch: Character) -> None:
    assert ch.carry_weight == _expected_carry_weight(ch), (
        f"carry_weight={ch.carry_weight} but inventory+equipment sum to {_expected_carry_weight(ch)}"
    )
    assert ch.carry_number == _expected_carry_number(ch), (
        f"carry_number={ch.carry_number} but inventory+equipment count is {_expected_carry_number(ch)}"
    )


def test_add_object_keeps_coherence():
    ch = Character(name="Alice", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0

    obj1 = _mk_obj(weight=5)
    ch.add_object(obj1)
    _assert_coherent(ch)

    obj2 = _mk_obj(weight=3)
    ch.add_object(obj2)
    _assert_coherent(ch)


def test_equip_object_keeps_coherence():
    ch = Character(name="Bob", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0

    sword = _mk_obj(weight=10, item_type=int(ItemType.WEAPON))
    ch.add_object(sword)
    _assert_coherent(ch)

    ch.equip_object(sword, str(int(WearLocation.WIELD)))
    _assert_coherent(ch)


def test_remove_object_keeps_coherence():
    ch = Character(name="Carol", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0

    o = _mk_obj(weight=7)
    ch.add_object(o)
    _assert_coherent(ch)

    ch.remove_object(o)
    _assert_coherent(ch)
    assert ch.carry_weight == 0
    assert ch.carry_number == 0


def test_extract_obj_keeps_coherence_after_inventory_drop():
    """Runtime extract path: a carried object that decays / is extracted
    via `_extract_obj` must leave carry_weight + carry_number in sync
    with the post-extract inventory. ROM mirrors this in extract_obj →
    obj_from_char (`src/handler.c:2051, 2058-2059, 1642`).
    """
    from mud.game_loop import _extract_obj

    ch = Character(name="Dave", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0

    keeper = _mk_obj(weight=4)
    doomed = _mk_obj(weight=11)
    ch.add_object(keeper)
    ch.add_object(doomed)
    _assert_coherent(ch)

    # Mark `doomed` as carried_by ch so _extract_obj's carrier branch fires.
    doomed.carried_by = ch
    _extract_obj(doomed)

    assert doomed not in ch.inventory
    _assert_coherent(ch)


def test_extract_obj_keeps_coherence_after_equipment_drop():
    """Same contract for an equipped object."""
    from mud.game_loop import _extract_obj

    ch = Character(name="Eve", level=10)
    ch.carry_weight = 0
    ch.carry_number = 0

    shield = _mk_obj(weight=8, item_type=int(ItemType.ARMOR))
    ch.add_object(shield)
    ch.equip_object(shield, str(int(WearLocation.SHIELD)))
    _assert_coherent(ch)

    shield.carried_by = ch
    _extract_obj(shield)

    assert shield not in ch.inventory
    assert shield not in ch.equipment.values()
    _assert_coherent(ch)
