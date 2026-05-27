"""ARITH-106/108/109/112/113 — obj_from_char carry-counter floors.

ROM `obj_from_char` at src/handler.c:1678-1679 performs bare subtraction:

    ch->carry_number -= get_obj_number (obj);
    ch->carry_weight -= get_obj_weight (obj);

with NO floor and no upstream guard preventing the result from going
negative. Python wraps both subtractions in `max(0, ...)` at five sites,
which silently absorbs double-extract / over-subtract bugs that ROM
would surface as a negative carry counter.

This test pins the contract for all five sites: when the counters start
at 0 and a non-empty object is removed, the counters MUST go negative.

Sites covered:
- ARITH-106  mud/models/character.py            Character.remove_object  (carry_number only — carry_weight is recomputed from inventory in this path)
- ARITH-108  mud/commands/obj_manipulation.py   _obj_from_char           (carry_weight)
- ARITH-109  mud/commands/obj_manipulation.py   _obj_from_char           (carry_number)
- ARITH-112  mud/commands/consumption.py        _destroy_object          (carry_weight)
- ARITH-113  mud/commands/consumption.py        _destroy_object          (carry_number)
"""

from __future__ import annotations

from mud.commands.consumption import _destroy_object
from mud.commands.obj_manipulation import _obj_from_char
from mud.models.character import Character
from mud.models.constants import ItemType
from mud.models.obj import ObjIndex
from mud.models.object import Object


def _mk_obj(*, weight: int = 5) -> Object:
    proto = ObjIndex(
        vnum=92100,
        short_descr="a test object",
        weight=weight,
        item_type=int(ItemType.TRASH),
    )
    return Object(instance_id=None, prototype=proto)


def test_character_remove_object_allows_negative_carry_number() -> None:
    """ARITH-106: Character.remove_object must not floor carry_number at 0."""
    ch = Character(name="tester")
    obj = _mk_obj(weight=5)
    ch.inventory.append(obj)
    obj.carried_by = ch
    ch.carry_number = 0  # simulate desynced counter

    ch.remove_object(obj)

    assert ch.carry_number == -1, (
        f"carry_number={ch.carry_number}; ROM src/handler.c:1678 does "
        "bare subtraction with no floor"
    )


def test_obj_from_char_allows_negative_carry_weight_and_number() -> None:
    """ARITH-108/109: _obj_from_char must not floor either counter at 0."""
    ch = Character(name="tester")
    obj = _mk_obj(weight=5)
    ch.inventory.append(obj)
    obj.carried_by = ch
    ch.carry_weight = 0
    ch.carry_number = 0

    _obj_from_char(ch, obj)

    assert ch.carry_weight == -5, (
        f"carry_weight={ch.carry_weight}; ROM src/handler.c:1679 does "
        "bare subtraction with no floor"
    )
    assert ch.carry_number == -1, (
        f"carry_number={ch.carry_number}; ROM src/handler.c:1678 does "
        "bare subtraction with no floor"
    )


def test_destroy_object_allows_negative_carry_weight_and_number() -> None:
    """ARITH-112/113: _destroy_object must not floor either counter at 0."""
    ch = Character(name="tester")
    obj = _mk_obj(weight=5)
    obj.weight = 5  # type: ignore[attr-defined]  # _destroy_object reads obj.weight directly
    ch.inventory.append(obj)
    obj.carried_by = ch
    ch.carry_weight = 0
    ch.carry_number = 0

    _destroy_object(ch, obj)

    assert ch.carry_weight == -5, (
        f"carry_weight={ch.carry_weight}; ROM src/handler.c:1679 does "
        "bare subtraction with no floor"
    )
    assert ch.carry_number == -1, (
        f"carry_number={ch.carry_number}; ROM src/handler.c:1678 does "
        "bare subtraction with no floor"
    )
