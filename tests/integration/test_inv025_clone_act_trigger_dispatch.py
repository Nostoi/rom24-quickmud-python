"""INV-025 sweep - do_clone act() room lines dispatch TRIG_ACT.

ROM ``src/comm.c:2384`` dispatches ``mp_act_trigger`` from inside ``act()``
for NPC recipients when ``MOBtrigger`` is true. The clone room broadcasts in
``src/act_wiz.c`` have no ``MOBtrigger = FALSE`` wrapper.
"""

from __future__ import annotations

import pytest

from mud import registry as global_registry
from mud.models.character import character_registry
from mud.models.mob import MobIndex
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import mob_registry, obj_registry, room_registry
from mud.spawning.mob_spawner import spawn_mob
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clean_state():
    rooms = set(room_registry)
    char_ids = {id(c) for c in character_registry}
    prev_mob_registry = dict(mob_registry)
    prev_obj_registry = dict(obj_registry)
    yield
    for vnum in list(room_registry):
        if vnum not in rooms:
            room_registry.pop(vnum, None)
    character_registry[:] = [c for c in character_registry if id(c) in char_ids]
    mob_registry.clear()
    mob_registry.update(prev_mob_registry)
    obj_registry.clear()
    obj_registry.update(prev_obj_registry)
    for attr in ("players", "char_list", "descriptor_list"):
        if hasattr(global_registry, attr):
            delattr(global_registry, attr)


def _room(vnum: int) -> Room:
    room = Room(vnum=vnum, name=f"Room {vnum}", description="")
    room.people = []
    room.contents = []
    room_registry[vnum] = room
    return room


def _imm(name: str, room_vnum: int, *, trust: int = 60):
    char = create_test_character(name, room_vnum)
    char.level = trust
    char.trust = trust
    return char


def _npc_witness(name: str, room: Room):
    npc = create_test_character(name, room.vnum)
    npc.is_npc = True
    npc.level = 1
    return npc


def _recorded_act_triggers(monkeypatch, call):
    import mud.mobprog as mobprog

    fired: list[tuple[str, str, object | None, object | None]] = []

    def _probe(argument, mob, ch, arg1=None, arg2=None, trigger=None):
        fired.append((getattr(mob, "name", "?"), str(argument), arg1, arg2))

    monkeypatch.setattr(mobprog, "mp_act_trigger", _probe)
    call()
    return fired


def test_clone_object_room_broadcast_fires_act_trigger(monkeypatch) -> None:
    """ROM src/act_wiz.c:2405 - clone object TO_ROOM act() fires TRIG_ACT."""
    from mud.commands.imm_search import do_clone

    room = _room(40750)
    admin = _imm("Admin", 40750)
    _npc_witness("watcher", room)
    proto = ObjIndex(vnum=88760, name="amulet", short_descr="a silver amulet")
    obj_registry[88760] = proto
    original = Object(instance_id=None, prototype=proto)
    original.in_room = room
    room.contents.append(original)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_clone(admin, "amulet"))

    assert len(fired) == 1
    mob_name, message, arg1, arg2 = fired[0]
    assert mob_name == "watcher"
    assert message == "Admin has created a silver amulet."
    assert getattr(arg1, "prototype", None) is proto
    assert arg2 is None


def test_clone_mobile_room_broadcast_fires_act_trigger(monkeypatch) -> None:
    """ROM src/act_wiz.c:2449 - clone mobile TO_ROOM act() fires TRIG_ACT."""
    from mud.commands.imm_search import do_clone

    room = _room(40850)
    admin = _imm("Admin", 40850)
    _npc_witness("watcher", room)
    proto = MobIndex(vnum=88860, short_descr="a clonable rat", level=1)
    mob_registry[88860] = proto
    target = spawn_mob(88860)
    target.room = room
    room.people.append(target)

    fired = _recorded_act_triggers(monkeypatch, lambda: do_clone(admin, "rat"))

    watcher_fires = [entry for entry in fired if entry[0] == "watcher"]
    assert len(watcher_fires) == 1
    mob_name, message, arg1, arg2 = watcher_fires[0]
    assert mob_name == "watcher"
    assert message == "Admin has created a clonable rat."
    assert arg1 is None
    assert getattr(arg2, "prototype", None) is proto
