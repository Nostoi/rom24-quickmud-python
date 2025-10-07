from __future__ import annotations

from mud.game_loop import SkyState, weather
from mud.models.character import Character
from mud.models.constants import (
    ItemType,
    LIQ_WATER,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_SPRING,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry
from mud.skills.handlers import create_food, create_spring, create_water


def _make_room() -> Room:
    return Room(vnum=1000, name="Glade of Growth")


def test_create_food_conjures_mushroom_with_level_values():
    obj_registry.clear()
    try:
        mushroom_proto = ObjIndex(
            vnum=OBJ_VNUM_MUSHROOM,
            name="mushroom",
            short_descr="a mushroom",
            item_type=int(ItemType.FOOD),
        )
        obj_registry[mushroom_proto.vnum] = mushroom_proto

        room = _make_room()
        caster = Character(name="Aleron", level=12, is_npc=False)
        observer = Character(name="Witness", is_npc=False)
        room.add_character(caster)
        room.add_character(observer)

        conjured = create_food(caster)

        assert conjured is not None
        assert conjured in room.contents
        assert conjured.location is room
        assert conjured.value[0] == 6  # level // 2 using C division semantics
        assert conjured.value[1] == 12
        assert caster.messages[-1] == "a mushroom suddenly appears."
        assert "a mushroom suddenly appears." in observer.messages
    finally:
        obj_registry.clear()


def test_create_spring_creates_timed_fountain_in_room():
    obj_registry.clear()
    try:
        spring_proto = ObjIndex(
            vnum=OBJ_VNUM_SPRING,
            name="spring",
            short_descr="a spring",
            item_type=int(ItemType.FOUNTAIN),
        )
        obj_registry[spring_proto.vnum] = spring_proto

        room = _make_room()
        caster = Character(name="Lyssa", level=8, is_npc=False)
        room.add_character(caster)

        spring = create_spring(caster)

        assert spring is not None
        assert spring in room.contents
        assert spring.location is room
        assert spring.timer == 8
        assert caster.messages[-1] == "a spring flows from the ground."
    finally:
        obj_registry.clear()


def test_create_water_fills_drink_container_respecting_capacity():
    original_sky = weather.sky
    try:
        weather.sky = SkyState.RAINING

        room = _make_room()
        caster = Character(name="Theron", level=10, is_npc=False)
        room.add_character(caster)

        container_proto = ObjIndex(
            vnum=12345,
            name="waterskin",
            short_descr="a waterskin",
            item_type=int(ItemType.DRINK_CON),
        )
        container = Object(instance_id=None, prototype=container_proto)
        container.value = [10, 2, LIQ_WATER, 0, 0]

        assert create_water(caster, container) is True
        assert container.value[1] == 10  # capacity reached in rain (level * 4)
        assert caster.messages[-1] == "a waterskin is filled."
    finally:
        weather.sky = original_sky
