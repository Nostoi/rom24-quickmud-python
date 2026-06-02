"""INV-033 — FURNITURE-ON-POINTER-COHERENCE.

A character's ``ch->on`` furniture pointer must be cleared whenever the
furniture object leaves the character's room. ROM enforces this in TWO
cross-file primitives:

- ``src/handler.c:1530-1532 char_from_room`` — when the *character* leaves,
  ``ch->on = NULL`` ("sanity check!"). Python: ``Room.remove_character``
  already clears ``char.on`` (``mud/models/room.py:163-165``). ✅

- ``src/handler.c:1904-1917 obj_from_room`` — when the *furniture* leaves the
  room, every occupant pointing at it is cleared::

      for (ch = in_room->people; ch != NULL; ch = ch->next_in_room)
          if (ch->on == obj)
              ch->on = NULL;

  ROM ``extract_obj`` (``src/handler.c:2052-2058``) routes room objects through
  ``obj_from_room``, so decay, purge, and recursive extract all clear the
  occupant pointer. Python's canonical ``mud/game_loop.py:_extract_obj`` removed
  the object from ``room.contents`` but never cleared occupants' ``on`` — this
  test pins that gap.

Why it matters (the cross-file payoff): the dangling pointer keeps feeding the
furniture heal/mana regen bonus at ``mud/game_loop.py:hit_gain``/``mana_gain``
(``ch->on->value[3]``/``value[4]`` — ROM ``src/update.c:217-218,299-300``) from
a furniture that no longer exists, and the no-arg ``do_rest``/``do_sit``/
``do_sleep`` branches default ``obj = ch->on``.

The guarded cousins (``do_get`` / ``do_sacrifice``) refuse to remove furniture
someone is ``on`` (ROM occupancy check, ``src/act_obj.c:126-134`` /
``do_sacrifice``; Python ``mud/commands/inventory.py:254-264`` and
``mud/commands/obj_manipulation.py:419-425``), so they never reach the
stranding state. The unguarded room-removal vectors — decay/purge/extract —
all funnel through ``_extract_obj``, which is the single enforcement point.
"""

from __future__ import annotations

import pytest

from mud.game_loop import _extract_obj, obj_update
from mud.models.character import Character
from mud.models.constants import ItemType, Position
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room


@pytest.fixture(autouse=True)
def _isolated_registry():
    snapshot = list(object_registry)
    object_registry.clear()
    yield
    object_registry.clear()
    object_registry.extend(snapshot)


def _make_furniture(*, vnum: int = 8100, heal_bonus: int = 100, timer: int = 0) -> Object:
    """A furniture object registered in object_registry (so obj_update sees it).

    value = [capacity, weight, position-flags, heal_mult, mana_mult].
    """
    proto = ObjIndex(
        vnum=vnum,
        name="couch",
        short_descr="a comfortable couch",
        item_type=int(ItemType.FURNITURE),
        value=[4, 100, 0, heal_bonus, heal_bonus],
    )
    obj = Object(instance_id=vnum, prototype=proto)
    obj.short_descr = "a comfortable couch"
    obj.value = list(proto.value)  # Object.__post_init__ does not auto-sync value
    obj.timer = timer
    object_registry.append(obj)
    return obj


def _seat(room: Room, name: str, furniture: Object) -> Character:
    ch = Character(name=name, is_npc=False)
    ch.position = Position.SITTING
    room.add_character(ch)
    ch.on = furniture
    return ch


def test_inv033_extract_furniture_clears_occupant_on():
    """ROM obj_from_room (handler.c:1915-1917): extract clears every ch->on==obj."""
    room = Room(vnum=8000, name="Lounge")
    couch = _make_furniture()
    room.add_object(couch)

    alice = _seat(room, "Alice", couch)
    bob = _seat(room, "Bob", couch)

    assert alice.on is couch
    assert bob.on is couch

    _extract_obj(couch)

    assert alice.on is None, "extract_obj must clear occupant's on pointer (ROM handler.c:1916-1917)"
    assert bob.on is None, "every occupant on the extracted furniture must be cleared"
    assert couch not in room.contents


def test_inv033_decay_tick_clears_occupant_on():
    """Furniture that decays out from under a sitter must clear ch->on (obj_update)."""
    room = Room(vnum=8000, name="Lounge")
    couch = _make_furniture(timer=1)
    room.add_object(couch)

    sitter = _seat(room, "Sitter", couch)
    assert sitter.on is couch

    obj_update()  # timer 1 -> 0 -> decay -> _extract_obj

    assert not any(o is couch for o in object_registry), "couch should have decayed out of the registry"
    assert sitter.on is None, "decayed furniture must not leave a dangling ch->on pointer"


def test_inv033_extract_unrelated_object_does_not_clear_on():
    """No-op safety: extracting some other object must not touch an occupant's on."""
    room = Room(vnum=8000, name="Lounge")
    couch = _make_furniture(vnum=8100)
    room.add_object(couch)
    sitter = _seat(room, "Sitter", couch)

    # An unrelated object (e.g. a potion) decays/extracts in the same room.
    other = ObjIndex(vnum=8200, name="potion", short_descr="a potion", item_type=int(ItemType.POTION))
    other_obj = Object(instance_id=8200, prototype=other)
    object_registry.append(other_obj)
    room.add_object(other_obj)

    _extract_obj(other_obj)

    assert sitter.on is couch, "extracting an unrelated object must not clear the sitter's furniture pointer"


def test_inv033_regen_bonus_stops_after_furniture_extracted():
    """Cross-file payoff: the heal-rate furniture bonus must stop once on is cleared."""
    from mud.game_loop import hit_gain

    room = Room(vnum=8000, name="Lounge", heal_rate=100)
    couch = _make_furniture(heal_bonus=200)  # value[3]=200 -> 2x heal gain
    room.add_object(couch)

    # NPC regen branch is deterministic (gain = 5 + level, RESTING keeps full
    # gain); the furniture value[3] multiply is applied to NPC and PC alike.
    ch = Character(name="Resting", is_npc=True)
    ch.level = 10
    ch.position = Position.RESTING
    ch.max_hit = 100
    ch.hit = 1
    room.add_character(ch)
    ch.on = couch

    gain_on_furniture = hit_gain(ch)

    _extract_obj(couch)
    assert ch.on is None
    gain_off_furniture = hit_gain(ch)

    assert gain_on_furniture > gain_off_furniture, (
        "furniture heal bonus (value[3]) should apply while seated and stop once the "
        "furniture is extracted and ch.on cleared (ROM src/update.c:217-218)"
    )
