"""GL-039 — obj_update spill gate must use wear_loc, not prototype wear_flags.

ROM update.c:1025-1026:
    if ((obj->item_type == ITEM_CORPSE_PC || obj->wear_loc == WEAR_FLOAT)
        && obj->contains)
        { /* spill */ }

The spill check is a runtime-state test (``obj->wear_loc == WEAR_FLOAT``), not
a prototype-capability test (``CAN_WEAR(obj, ITEM_WEAR_FLOAT)``).  A floating-
disc-capable CONTAINER that is NOT currently floating (e.g. dropped in a room,
so ``wear_loc == WEAR_NONE``) must NOT spill its contents on decay — ROM
silently destroys them alongside the container via the recursive ``extract_obj``
call.

Before the fix, Python's ``obj_update`` had an extra branch:

    elif item_type == ItemType.CONTAINER and wear_flags & WearFlag.WEAR_FLOAT:
        should_spill = True

This used the prototype's ``wear_flags`` instead of the live ``wear_loc``, so
a non-floating disc in a room would incorrectly dump its contents into the room
rather than destroying them with the disc.
"""

from __future__ import annotations

import pytest

from mud.game_loop import obj_update
from mud.models.constants import ItemType, WearFlag, WearLocation
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _clean_registry():
    object_registry.clear()
    yield
    object_registry.clear()


def _make_disc_with_gem(wear_loc: int) -> tuple[Object, Object, Room]:
    """Return (disc, gem, room) with disc at the given wear_loc."""
    room = Room(vnum=3001, name="Test Room", description="A test.")

    disc_proto = ObjIndex(
        vnum=1001,
        short_descr="a floating disc",
        item_type=int(ItemType.CONTAINER),
        wear_flags=int(WearFlag.WEAR_FLOAT),
    )
    disc = Object(instance_id=None, prototype=disc_proto, timer=1)
    disc.wear_loc = wear_loc
    disc.in_room = room
    room.contents = [disc]

    gem_proto = ObjIndex(vnum=1002, short_descr="a gem", item_type=int(ItemType.TREASURE))
    gem = Object(instance_id=None, prototype=gem_proto, timer=0)
    gem.in_obj = disc
    disc.contained_items = [gem]

    object_registry.append(disc)
    object_registry.append(gem)
    return disc, gem, room


def test_non_floating_container_contents_destroyed_not_spilled():
    """
    ROM update.c:1025-1026 — spill gate is wear_loc, not prototype flag.

    When a CONTAINER with WEAR_FLOAT prototype flag is NOT currently floating
    (wear_loc != WEAR_FLOAT), its contents must be DESTROYED with it, not
    spilled into the room.
    mirrors ROM: obj->wear_loc == WEAR_FLOAT is FALSE → no spill block →
    extract_obj(obj) recurses into the gem and removes it from object_list.
    """
    disc, gem, room = _make_disc_with_gem(wear_loc=-1)  # WEAR_NONE

    obj_update()

    # Disc extracted (timer hit 0)
    assert disc not in object_registry, "disc should be extracted on decay"
    # Gem destroyed with disc — NOT spilled into the room
    assert gem not in object_registry, "gem should be destroyed with non-floating disc"
    room_contents = getattr(room, "contents", []) or []
    assert gem not in room_contents, "gem must not appear in room (spill must not fire)"


def test_currently_floating_container_contents_spilled():
    """
    ROM update.c:1025-1026 — wear_loc == WEAR_FLOAT triggers the spill.

    Confirms the positive case: a disc actively worn at WEAR_FLOAT DOES spill
    when it decays.
    """
    disc, gem, room = _make_disc_with_gem(wear_loc=int(WearLocation.FLOAT))

    obj_update()

    # Disc extracted
    assert disc not in object_registry, "disc should be extracted on decay"
    # Gem spilled into the room (still exists in registry / room)
    room_contents = getattr(room, "contents", []) or []
    # gem either in room or still in registry (spilled, not destroyed)
    assert gem in room_contents or gem in object_registry, (
        "gem should be spilled into the room when disc was actively floating"
    )
