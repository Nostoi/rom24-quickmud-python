"""Integration tests for ``do_mpoload`` (MOBprog ``oload`` script command).

ROM C reference: ``src/mob_cmds.c:538-614`` — ROM signature is
``mob oload <vnum> [level] [R|W]``. The level argument is passed to
``create_object(pObjIndex, level)`` so the loaded object's level matches the
script's specification rather than the prototype default.

Closes MOBCMD-005.
"""

from __future__ import annotations

import pytest

from mud.mob_cmds import do_mpoload
from mud.models.character import Character
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry, room_registry

_TEST_VNUM = 91500
_ROOM_VNUM = 9501


@pytest.fixture
def oload_room() -> Room:
    room = room_registry.get(_ROOM_VNUM)
    if room is None:
        room = Room(vnum=_ROOM_VNUM, name="Oload Test Room")
        room_registry[_ROOM_VNUM] = room
    room.contents.clear()
    room.people.clear()
    return room


@pytest.fixture(autouse=True)
def _register_proto():
    proto = ObjIndex(
        vnum=_TEST_VNUM,
        name="widget",
        short_descr="a widget",
        description="A test widget.",
        item_type=1,
        level=5,  # prototype default level
        value=[0, 0, 0, 0, 0],
    )
    obj_registry[_TEST_VNUM] = proto
    yield
    obj_registry.pop(_TEST_VNUM, None)


@pytest.fixture
def script_mob(oload_room: Room) -> Character:
    mob = Character(name="ScriptMob", is_npc=True)
    mob.level = 30
    mob.trust = 30
    oload_room.add_character(mob)
    return mob


def _find_inv_obj(ch: Character) -> Object | None:
    for obj in getattr(ch, "inventory", []) or []:
        return obj
    return None


class TestMpOloadLevelArgument:
    """MOBCMD-005: ``do_mpoload`` must accept the level argument from
    ``mob oload <vnum> <level> [R|W]`` and apply it to the loaded object,
    mirroring ROM ``src/mob_cmds.c:574-601``::

        level = atoi(arg2);
        ...
        obj = create_object(pObjIndex, level);
    """

    def test_explicit_level_sets_object_level(self, script_mob):
        # mirrors ROM src/mob_cmds.c:574,601 — `obj = create_object(pObjIndex, level)`
        do_mpoload(script_mob, f"{_TEST_VNUM} 17")

        obj = _find_inv_obj(script_mob)
        assert obj is not None, "expected widget in mob inventory"
        assert obj.level == 17, (
            f"obj.level={obj.level}; expected the script-specified level 17."
            " Old implementation ignored arg2 and left the prototype default (5)."
        )

    def test_omitted_level_defaults_to_get_trust(self, script_mob):
        # mirrors ROM src/mob_cmds.c:559-562 — when arg2 is empty,
        # `level = get_trust(ch)`.
        do_mpoload(script_mob, f"{_TEST_VNUM}")

        obj = _find_inv_obj(script_mob)
        assert obj is not None
        # script_mob has level=30, trust=30 → get_trust returns 30
        assert obj.level == 30, (
            f"obj.level={obj.level}; expected get_trust(mob)=30 when level"
            " arg is omitted."
        )

    def test_room_mode_with_explicit_level(self, script_mob, oload_room):
        # mirrors ROM src/mob_cmds.c:589-592 — 'R' loads to room.
        do_mpoload(script_mob, f"{_TEST_VNUM} 22 R")

        # Object should be in the room, not the mob's inventory.
        assert not getattr(script_mob, "inventory", []), "object should be in room, not inventory"
        assert oload_room.contents, "room should contain the loaded object"
        assert oload_room.contents[0].level == 22
