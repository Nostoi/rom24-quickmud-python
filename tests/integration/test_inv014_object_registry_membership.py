"""INV-014 OBJECT-REGISTRY-MEMBERSHIP enforcement.

ROM ``src/db.c:create_object`` appends every freshly built OBJ_DATA to
the global ``object_list``. ROM ``src/magic.c:3737 spell_locate_object``
walks that list. After INV-012 consolidated the dual ``Object``/
``ObjectData`` runtime into one class, ``mud.models.obj.object_registry``
became the canonical Python equivalent of ``object_list`` — populated
by ``spawn_object`` and drained by ``mud.game_loop._extract_obj``.

Production sites that constructed ``Object`` instances WITHOUT appending
to the registry left those objects invisible to any
``object_registry``-driven world scan. The symptom shipped against
``spell_locate_object``: a freshly-created corpse, gore object, money
pile, shop clone, or DB-restored inventory was not findable by
``locate object`` despite being live in the world.

These tests pin every known construction path to the registry contract.
Add a test here when introducing a new ``Object(...)`` construction
site.
"""

from __future__ import annotations

from mud.combat.death import _fallback_corpse, _fallback_gore
from mud.commands.shop import _clone_inventory_object
from mud.db.models import Character as DBCharacter
from mud.db.models import ObjectInstance as DBObjectInstance
from mud.handler import create_money
from mud.models.character import Character, character_registry
from mud.models.constants import LEVEL_IMMORTAL, ItemType
from mud.models.obj import ObjIndex, object_registry
from mud.models.object import Object
from mud.models.conversion import load_objects_for_character
from mud.registry import obj_registry, room_registry
from mud.rom_api import recursive_clone
from mud.skills.handlers import locate_object
from mud.spawning.obj_spawner import spawn_object


def _registry_contains(obj: Object) -> bool:
    """Identity-based membership check.

    ``Object`` is a dataclass with default ``__eq__``; two distinct
    instances sharing the same prototype and default field values compare
    equal, so ``obj in object_registry`` can falsely succeed when an
    *unrelated* like-shaped object happens to be in the registry. Use
    ``id`` to verify the actual instance was registered.
    """

    return any(o is obj for o in object_registry)


def test_inv014_spawn_object_registers() -> None:
    """``spawn_object`` is the original ROM-faithful ``create_object`` mirror."""

    proto = ObjIndex(vnum=4001, name="anvil", short_descr="an anvil")
    obj_registry[4001] = proto
    try:
        obj = spawn_object(4001)
    finally:
        obj_registry.pop(4001, None)

    assert obj is not None
    assert _registry_contains(obj)


def test_inv014_create_money_registers() -> None:
    """ROM ``create_money`` (``src/handler.c``) emits an OBJ_DATA via ``create_object``."""

    obj = create_money(gold=100, silver=0)
    assert _registry_contains(obj)


def test_inv014_recursive_clone_registers() -> None:
    """ROM ``act_obj.c:do_clone`` builds clones through ``create_object``."""

    proto = ObjIndex(vnum=4100, name="staff", short_descr="a staff")
    template = Object(instance_id=None, prototype=proto)
    object_registry.append(template)

    clone = recursive_clone(template)
    assert _registry_contains(clone)
    assert clone is not template


def test_inv014_fallback_corpse_registers() -> None:
    """``make_corpse`` fallback path still goes through ``create_object`` in ROM."""

    corpse = _fallback_corpse(0, item_type=ItemType.CORPSE_NPC)
    assert _registry_contains(corpse)


def test_inv014_fallback_gore_registers() -> None:
    """Gore fallback in ``death_cry`` constructs an OBJ_DATA — must register."""

    gore = _fallback_gore(
        0,
        short_template="a bloody hunk",
        description_template="A bloody hunk lies here.",
        item_type=ItemType.FOOD,
    )
    assert _registry_contains(gore)


def test_inv014_clone_inventory_object_registers() -> None:
    """Shop stocking clones a template — ROM ``act_obj.c:do_buy`` calls ``create_object``."""

    proto = ObjIndex(vnum=4200, name="potion", short_descr="a potion")
    template = Object(instance_id=None, prototype=proto)
    object_registry.append(template)

    clone = _clone_inventory_object(template)
    assert clone is not None
    assert _registry_contains(clone)


def test_inv014_load_objects_for_character_registers() -> None:
    """Restoring a character's inventory from DB must put each obj on ``object_list``."""

    proto = ObjIndex(vnum=4300, name="ring", short_descr="a ring")
    obj_registry[4300] = proto
    db_char = DBCharacter(name="Restored", level=1, hp=10, room_vnum=3001)
    db_char.objects = [DBObjectInstance(prototype_vnum=4300, location="inventory")]

    try:
        inventory, _equipment = load_objects_for_character(db_char)
    finally:
        obj_registry.pop(4300, None)

    assert len(inventory) == 1
    assert _registry_contains(inventory[0])


def test_inv014_locate_object_finds_homeless_object() -> None:
    """ROM ``spell_locate_object`` iterates ``object_list``; an unplaced
    object (``in_room == NULL``, ``carried_by == NULL``, ``in_obj == NULL``)
    is reported as "one is in somewhere" rather than skipped.
    """

    caster = Character(
        name="Diviner",
        level=LEVEL_IMMORTAL,
        trust=LEVEL_IMMORTAL,
        is_npc=False,
    )
    character_registry.append(caster)

    proto = ObjIndex(vnum=4400, name="orphan widget", short_descr="an orphan widget")
    obj_registry[4400] = proto
    try:
        widget = spawn_object(4400)
    finally:
        obj_registry.pop(4400, None)
    assert widget is not None
    # Spawned but never placed — in_room/carried_by/in_obj all None.
    assert widget.in_room is None
    assert widget.carried_by is None
    assert widget.in_obj is None

    caster.messages.clear()
    assert locate_object(caster, "widget") is True
    # ROM's "in_room == NULL" branch prints "one is in somewhere\n\r"
    # uppercased to "One is in somewhere".
    assert any("somewhere" in msg for msg in caster.messages)

    # Cleanup — autouse fixtures handle object_registry; character_registry
    # is not auto-cleared in unit tests, so be explicit.
    character_registry.remove(caster)
    room_registry.clear()
