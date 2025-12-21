from __future__ import annotations

from mud.game_loop import SkyState, weather
from mud.models.character import Character
from mud.models.constants import (
    ExtraFlag,
    ItemType,
    LIQ_WATER,
    OBJ_VNUM_DISC,
    OBJ_VNUM_LIGHT_BALL,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_ROSE,
    OBJ_VNUM_SPRING,
    Sex,
    WearFlag,
    WearLocation,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry
from mud.utils import rng_mm
import mud.skills.handlers as skill_handlers
from mud.skills.handlers import (
    continual_light,
    create_food,
    create_rose,
    create_spring,
    create_water,
)


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


def test_continual_light_glows_object_in_inventory() -> None:
    room = _make_room()
    caster = Character(name="Elowen", level=12, is_npc=False, sex=int(Sex.FEMALE))
    observer = Character(name="Watcher", is_npc=False)
    room.add_character(caster)
    room.add_character(observer)

    amulet_proto = ObjIndex(vnum=5000, short_descr="a silver amulet")
    amulet = Object(instance_id=None, prototype=amulet_proto)
    caster.add_object(amulet)

    assert continual_light(caster, amulet) is True
    assert amulet.extra_flags & int(ExtraFlag.GLOW)

    glow_message = "a silver amulet glows with a white light."
    assert caster.messages[-1] == glow_message
    assert glow_message in observer.messages

    assert continual_light(caster, amulet) is False
    assert caster.messages[-1] == "a silver amulet is already glowing."


def test_continual_light_conjures_light_ball_in_room() -> None:
    original = obj_registry.get(OBJ_VNUM_LIGHT_BALL)
    try:
        proto = ObjIndex(vnum=OBJ_VNUM_LIGHT_BALL, short_descr="a ball of light")
        obj_registry[OBJ_VNUM_LIGHT_BALL] = proto

        room = _make_room()
        caster = Character(name="Invoker", level=20, is_npc=False, sex=int(Sex.MALE))
        observer = Character(name="Witness", is_npc=False)
        room.add_character(caster)
        room.add_character(observer)
        observer.messages.clear()

        conjured = continual_light(caster)

        assert conjured is not None
        assert conjured in room.contents
        assert conjured.location is room
        assert caster.messages[-1] == "You twiddle your thumbs and a ball of light appears."
        assert observer.messages[-1] == "Invoker twiddles his thumbs and a ball of light appears."
    finally:
        if original is None:
            obj_registry.pop(OBJ_VNUM_LIGHT_BALL, None)
        else:
            obj_registry[OBJ_VNUM_LIGHT_BALL] = original


def test_create_rose_conjures_rose_into_caster_inventory() -> None:
    original = obj_registry.get(OBJ_VNUM_ROSE)
    try:
        proto = ObjIndex(vnum=OBJ_VNUM_ROSE, short_descr="a red rose")
        obj_registry[OBJ_VNUM_ROSE] = proto

        room = _make_room()
        caster = Character(name="Lyssa", level=15, is_npc=False, sex=int(Sex.FEMALE))
        observer = Character(name="Onlooker", is_npc=False)
        room.add_character(caster)
        room.add_character(observer)
        observer.messages.clear()

        rose = create_rose(caster)

        assert rose is not None
        assert rose in caster.inventory
        assert caster.messages[-1] == "You create a beautiful red rose."
        assert observer.messages[-1] == "Lyssa has created a beautiful red rose."
    finally:
        if original is None:
            obj_registry.pop(OBJ_VNUM_ROSE, None)
        else:
            obj_registry[OBJ_VNUM_ROSE] = original


def _register_disc() -> ObjIndex:
    proto = ObjIndex(
        vnum=OBJ_VNUM_DISC,
        short_descr="a floating disc",
        wear_flags=int(WearFlag.WEAR_FLOAT),
        value=[0, 0, 0, 0, 0],
        weight=1,
    )
    obj_registry[OBJ_VNUM_DISC] = proto
    return proto


def test_floating_disc_creates_disc_with_capacity() -> None:
    original = obj_registry.get(OBJ_VNUM_DISC)
    try:
        _register_disc()
        caster = Character(name="Invoker", level=12, is_npc=False)
        witness = Character(name="Watcher", level=10, is_npc=False)
        room = Room(vnum=3000, name="Summoning Hall", description="Glowing sigils cover the floor.")
        room.add_character(caster)
        room.add_character(witness)
        witness.messages.clear()

        rng_mm.seed_mm(1234)
        disc = skill_handlers.floating_disc(caster)

        assert disc is not None
        assert caster.equipment["float"] is disc
        assert disc.value[0] == caster.level * 10
        assert disc.value[3] == caster.level * 5
        assert caster.messages[-1] == "You create a floating disc."
        assert witness.messages[-1] == "Invoker has created a floating black disc."

        # Timer should be between level * 2 - level // 2 and level * 2 per ROM formula.
        min_timer = caster.level * 2 - caster.level // 2
        assert min_timer <= disc.timer <= caster.level * 2
        assert disc.wear_loc == int(WearLocation.FLOAT)
    finally:
        if original is None:
            obj_registry.pop(OBJ_VNUM_DISC, None)
        else:
            obj_registry[OBJ_VNUM_DISC] = original


def test_floating_disc_respects_noremove_items() -> None:
    original = obj_registry.get(OBJ_VNUM_DISC)
    try:
        _register_disc()
        caster = Character(name="Invoker", level=20, is_npc=False)
        room = Room(vnum=3001, name="Arcane Loft")
        room.add_character(caster)

        prototype = ObjIndex(vnum=9000, short_descr="an amulet", wear_flags=int(WearFlag.WEAR_FLOAT))
        existing = Object(instance_id=None, prototype=prototype)
        existing.extra_flags = int(ExtraFlag.NOREMOVE)
        existing.wear_loc = int(WearLocation.FLOAT)
        caster.equipment["float"] = existing

        result = skill_handlers.floating_disc(caster)

        assert result is False
        assert caster.equipment["float"] is existing
        assert caster.messages[-1] == "You can't remove an amulet."
    finally:
        if original is None:
            obj_registry.pop(OBJ_VNUM_DISC, None)
        else:
            obj_registry[OBJ_VNUM_DISC] = original
