"""INV-013 OBJECT-LOCATION-COHERENCE enforcement test.

ROM `src/handler.c` keeps three location fields on `OBJ_DATA` mutually
exclusive: `in_room`, `carried_by`, `in_obj`. Every transition through
`obj_to_room` (line 1953), `obj_to_char` (line 1626), or `obj_to_obj`
(line 1968) sets the destination field and clears the other two.
`obj_from_room` / `obj_from_char` / `obj_from_obj` each clear exactly
one field.

Before INV-013, Python's `Object` carried a separate polymorphic
`location` field independent of the three ROM fields, and callers had
to remember to keep them in sync (some did, some did not — see
`mud/handler.py:638` `getattr(obj, "in_room", None) or getattr(obj,
"location", None)` which was a defensive bridge for the known
divergence).

INV-013 collapses `Object.location` into a property dispatching to the
canonical ROM fields. Setting `location` to a Room, Character, or
Object routes to `in_room` / `carried_by` / `in_obj` respectively,
clearing the other two; setting `None` clears all three. Reads return
whichever ROM field is non-None.
"""

from __future__ import annotations

from mud.models.character import Character
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room


def _proto() -> ObjIndex:
    return ObjIndex(vnum=99001, name="probe", short_descr="a probe", description="A probe.")


def _make_obj() -> Object:
    return Object(instance_id=None, prototype=_proto())


def test_setting_location_to_room_clears_carried_by_and_in_obj():
    obj = _make_obj()
    room = Room(vnum=99000, name="R", description="", room_flags=0, sector_type=0)
    char = Character(name="X")
    holder = _make_obj()

    obj.carried_by = char
    obj.in_obj = holder

    obj.location = room

    assert obj.in_room is room
    assert obj.carried_by is None
    assert obj.in_obj is None
    assert obj.location is room


def test_setting_location_to_character_clears_in_room_and_in_obj():
    obj = _make_obj()
    room = Room(vnum=99000, name="R", description="", room_flags=0, sector_type=0)
    holder = _make_obj()
    char = Character(name="X")

    obj.in_room = room
    obj.in_obj = holder

    obj.location = char

    assert obj.carried_by is char
    assert obj.in_room is None
    assert obj.in_obj is None
    assert obj.location is char


def test_setting_location_to_object_clears_in_room_and_carried_by():
    obj = _make_obj()
    room = Room(vnum=99000, name="R", description="", room_flags=0, sector_type=0)
    char = Character(name="X")
    holder = _make_obj()

    obj.in_room = room
    obj.carried_by = char

    obj.location = holder

    assert obj.in_obj is holder
    assert obj.in_room is None
    assert obj.carried_by is None
    assert obj.location is holder


def test_setting_location_to_none_clears_all_three():
    obj = _make_obj()
    obj.in_room = Room(vnum=99000, name="R", description="", room_flags=0, sector_type=0)

    obj.location = None

    assert obj.in_room is None
    assert obj.carried_by is None
    assert obj.in_obj is None
    assert obj.location is None


def test_setting_in_room_directly_is_visible_through_location():
    obj = _make_obj()
    room = Room(vnum=99000, name="R", description="", room_flags=0, sector_type=0)

    obj.in_room = room

    assert obj.location is room


def test_setting_carried_by_directly_is_visible_through_location():
    obj = _make_obj()
    char = Character(name="X")

    obj.carried_by = char

    assert obj.location is char


def test_setting_in_obj_directly_is_visible_through_location():
    obj = _make_obj()
    holder = _make_obj()

    obj.in_obj = holder

    assert obj.location is holder
