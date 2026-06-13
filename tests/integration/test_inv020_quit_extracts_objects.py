"""INV-020 step (v) — every PC-extract path must extract carried objects.

ROM `extract_char` (`src/handler.c:2123-2127`) walks `ch->carrying` and calls
`extract_obj` on every object the character holds — which, in ROM, includes
**worn** items (equipment carries a `wear_loc` but still lives on the
`carrying` list). `do_quit` calls `extract_char(ch, TRUE)` *after*
`save_char_obj(ch)`, so the in-memory objects are freed (removed from the global
`object_list`) once their state is persisted; the next login re-creates fresh
instances.

The Python port loads a PC's saved inventory/equipment via `_deserialize_object`
→ `spawn_object`, which appends each object to `object_registry`. But the
quit/disconnect extract legs (`game_loop._auto_quit_character`,
`connection._disconnect_extract_cleanup`) never extracted those objects, so a
quitting player left every carried + worn object lingering in `object_registry`
forever — a phantom-object leak observable via `ofind` / `do_dump` /
`get_obj_world` (the INV-046 phantom-registry class, on the extract path).

Python stores worn items in a separate `equipment` dict (not `inventory`), so a
faithful "extract all carrying" must drain BOTH.
"""

from __future__ import annotations

import pytest

from mud.models.character import Character, character_registry
from mud.models.constants import Position, WearLocation
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.room import Room


@pytest.fixture
def isolated_registries():
    saved_chars = list(character_registry)
    saved_objs = list(object_registry)
    character_registry.clear()
    object_registry.clear()
    yield
    character_registry[:] = saved_chars
    object_registry[:] = saved_objs


def _registered_object(vnum: int, name: str) -> Object:
    """Build an object and register it the way spawn_object / _deserialize_object
    do on login, so it is a live `object_registry` member."""
    proto = ObjIndex(vnum=vnum, short_descr=name)
    obj = Object(instance_id=None, prototype=proto)
    object_registry.append(obj)
    return obj


def test_void_quit_extracts_inventory_objects(isolated_registries) -> None:
    """Link-dead quit must drain carried inventory from object_registry —
    ROM extract_char (src/handler.c:2123-2127) extract_obj's every carried obj.
    """
    from mud import game_loop

    room = Room(vnum=9860, name="Quit inv-extract room")
    quitter = Character(name="Quitter", is_npc=False, position=Position.STANDING)
    quitter.desc = None
    quitter.connection = None
    room.add_character(quitter)
    character_registry.append(quitter)

    sword = _registered_object(9861, "a test sword")
    quitter.add_object(sword)

    assert sword in object_registry

    game_loop._auto_quit_character(quitter)

    assert sword not in object_registry, (
        "ROM extract_char (handler.c:2123-2127) extracts every carried object; "
        "the link-dead quit leg left the inventory object in object_registry "
        "(phantom-object leak, INV-046 class)."
    )


def test_void_quit_extracts_equipped_objects(isolated_registries) -> None:
    """Worn items live on ch->carrying in ROM, so extract_char frees them too.
    Python keeps them in a separate equipment dict — the extract must drain it.
    """
    from mud import game_loop

    room = Room(vnum=9862, name="Quit eq-extract room")
    quitter = Character(name="Quitter", is_npc=False, position=Position.STANDING)
    quitter.desc = None
    quitter.connection = None
    room.add_character(quitter)
    character_registry.append(quitter)

    shield = _registered_object(9863, "a test shield")
    quitter.equip_object(shield, int(WearLocation.SHIELD))

    assert shield in object_registry

    game_loop._auto_quit_character(quitter)

    assert shield not in object_registry, (
        "ROM extract_char frees worn items (they sit on ch->carrying); the quit "
        "leg left the equipped object in object_registry."
    )


def test_disconnect_extracts_carried_objects(isolated_registries) -> None:
    """The clean-disconnect teardown must drain both inventory and equipment,
    same step (v) of the extract_char chain, different trigger.
    """
    from mud.net.connection import _disconnect_extract_cleanup

    room = Room(vnum=9864, name="Disconnect obj-extract room")
    leaver = Character(name="Leaver", is_npc=False, position=Position.STANDING)
    room.add_character(leaver)
    character_registry.append(leaver)

    potion = _registered_object(9865, "a test potion")
    helm = _registered_object(9866, "a test helm")
    leaver.add_object(potion)
    leaver.equip_object(helm, int(WearLocation.HEAD))

    assert potion in object_registry and helm in object_registry

    _disconnect_extract_cleanup(leaver)

    assert potion not in object_registry, "disconnect leg leaked carried inventory object."
    assert helm not in object_registry, "disconnect leg leaked equipped object."


def test_mob_extract_drains_inventory_and_equipment(isolated_registries) -> None:
    """The mob/purge extract leg (`mob_cmds._extract_character`, the do_purge
    chokepoint) must also drain BOTH inventory and equipment — same step (v) of
    the extract_char chain. ROM extract_char (src/handler.c:2123-2127) frees all
    of ch->carrying, which includes worn items; an inventory-only loop leaked the
    equipped object into object_registry on the non-death extract path.
    """
    from mud.mob_cmds import _extract_character

    room = Room(vnum=9867, name="Purge obj-extract room")
    victim = Character(name="Purgee", is_npc=True, position=Position.STANDING)
    room.add_character(victim)
    character_registry.append(victim)

    dagger = _registered_object(9868, "a test dagger")
    armor = _registered_object(9869, "a test breastplate")
    victim.add_object(dagger)
    victim.equip_object(armor, int(WearLocation.BODY))

    assert dagger in object_registry and armor in object_registry

    _extract_character(victim, fPull=True)

    assert dagger not in object_registry, "mob extract leg leaked carried inventory object."
    assert armor not in object_registry, (
        "mob extract leg leaked equipped object — extract_char (handler.c:2123-2127) "
        "frees worn items too (INV-020 step (v))."
    )
