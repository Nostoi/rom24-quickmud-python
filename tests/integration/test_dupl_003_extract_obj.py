"""DUPL-003 regression: `_extract_obj` must remove from canonical inventory.

ROM ``src/handler.c:extract_obj`` (lines 2051-2096) takes only an ``OBJ_DATA*``,
unlinks it from whichever location holds it (``in_room`` / ``carried_by`` /
``in_obj``), recursively extracts its ``contains`` list, and removes it
from the global ``object_list``.

The pre-fix Python copies in ``mud/commands/obj_manipulation.py`` and
``mud/commands/imm_load.py`` were non-recursive AND looked at
``char.carrying`` — an attribute that does not exist on ``Character``
(canonical is ``Character.inventory``, see AGENTS.md ROM Parity Rules).
Result: ``do_quaff`` and ``do_sacrifice`` produced their flavor message
but never actually removed the potion/object from the player's inventory.
Players could quaff the same potion infinitely.

See ``docs/parity/audits/DUPLICATE_IMPLEMENTATIONS.md`` (DUPL-003).
"""

from __future__ import annotations

import pytest

from mud.commands.obj_manipulation import do_quaff, do_sacrifice
from mud.models.character import Character
from mud.models.constants import ItemType, WearFlag
from mud.models.room import Room
from mud.registry import area_registry, mob_registry, obj_registry, room_registry
from mud.world import create_test_character


@pytest.fixture(autouse=True)
def _clear_registries():
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()
    yield
    area_registry.clear()
    room_registry.clear()
    obj_registry.clear()
    mob_registry.clear()


@pytest.fixture
def room() -> Room:
    r = Room(vnum=3001, name="Test Room", description="A test room.")
    room_registry[3001] = r
    return r


@pytest.fixture
def actor(room) -> Character:
    char = create_test_character("Tester", room_vnum=3001)
    char.is_npc = False
    char.silver = 0
    char.level = 50
    return char


def test_do_quaff_actually_removes_potion_from_inventory(actor, object_factory) -> None:
    """ROM src/act_obj.c:1865-1906 — quaff consumes the potion.

    The bug: the local _extract_obj used char.carrying (a non-existent
    attribute) instead of char.inventory. The potion stayed in
    inventory, making it infinitely consumable.
    """
    potion = object_factory({
        "vnum": 9100,
        "name": "potion blue",
        "short_descr": "a blue potion",
        "item_type": int(ItemType.POTION),
        "value": [1, 0, 0, 0, 0],
        "level": 1,
    })
    potion.item_type = int(ItemType.POTION)
    potion.level = 1
    potion.value = [1, 0, 0, 0, 0]
    potion.wear_flags = int(WearFlag.TAKE)
    actor.inventory.append(potion)
    potion.carried_by = actor

    assert potion in actor.inventory

    do_quaff(actor, "potion")

    assert potion not in actor.inventory, (
        "DUPL-003: do_quaff did not remove potion from inventory — "
        "_extract_obj used char.carrying (nonexistent) instead of "
        "char.inventory, so the potion is infinitely consumable."
    )


def test_do_sacrifice_recursively_extracts_container_contents(actor, room, object_factory) -> None:
    """ROM src/handler.c:2063-2067 — extract_obj recurses over contains.

    DUPL-003 bug: the pre-fix obj_manipulation copy was non-recursive.
    Sacrificing a container left its contents dangling with in_obj
    still pointing at the (now-extracted) parent — orphaned objects
    leaked into the world state.
    """
    chest = object_factory({
        "vnum": 9101,
        "name": "chest",
        "short_descr": "a wooden chest",
        "item_type": int(ItemType.CONTAINER),
        "value": [0, 0, 0, 0, 0],
        "level": 1,
        "cost": 10,
    })
    chest.item_type = int(ItemType.CONTAINER)
    chest.wear_flags = int(WearFlag.TAKE)
    chest.cost = 10
    chest.level = 1

    coin = object_factory({
        "vnum": 9102,
        "name": "coin",
        "short_descr": "a copper coin",
        "item_type": int(ItemType.TRASH),
        "value": [0, 0, 0, 0, 0],
        "level": 1,
        "cost": 1,
    })
    chest.contained_items.append(coin)
    coin.in_obj = chest

    room.contents.append(chest)
    chest.in_room = room

    do_sacrifice(actor, "chest")

    assert chest not in room.contents
    assert coin.in_obj is None, (
        "DUPL-003: do_sacrifice extracted the chest but left its coin "
        "dangling with in_obj still set — the local _extract_obj copy "
        "was non-recursive."
    )
