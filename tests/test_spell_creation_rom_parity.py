"""ROM parity tests for creation/utility spells.

Spells covered (ROM src/magic.c references):
- continual_light:  src/magic.c:2232
- create_food:      src/magic.c:2303
- create_rose:      src/magic.c:2330
- create_spring:    src/magic.c:2350
- create_water:     src/magic.c:2373
- ventriloquate:    src/magic.c:7642

These tests target the Python implementations in `mud/skills/handlers.py`.
"""

from __future__ import annotations

import pytest

from mud.game_loop import SkyState, weather
from mud.math.c_compat import c_div
from mud.models.character import Character
from mud.models.constants import (
    ExtraFlag,
    ItemType,
    LIQ_WATER,
    OBJ_VNUM_LIGHT_BALL,
    OBJ_VNUM_MUSHROOM,
    OBJ_VNUM_ROSE,
    OBJ_VNUM_SPRING,
    Position,
    Sex,
)
from mud.models.obj import ObjIndex
from mud.models.object import Object
from mud.models.room import Room
from mud.registry import obj_registry
from mud.skills.handlers import (
    continual_light,
    create_food,
    create_rose,
    create_spring,
    create_water,
    ventriloquate,
)
from mud.utils import rng_mm


@pytest.fixture(autouse=True)
def _seed_rng() -> None:
    """Ensure deterministic RNG for parity tests."""

    rng_mm.seed_mm(42)


@pytest.fixture(autouse=True)
def _restore_obj_registry() -> None:
    """Keep `obj_registry` isolated across tests."""

    snapshot = dict(obj_registry)
    try:
        yield
    finally:
        obj_registry.clear()
        obj_registry.update(snapshot)


def make_character(**overrides) -> Character:
    """Helper to create test characters with common defaults."""

    base = {
        "name": overrides.get("name", "TestChar"),
        "level": overrides.get("level", 30),
        "hit": overrides.get("hit", 100),
        "max_hit": overrides.get("max_hit", 100),
        "mana": overrides.get("mana", 100),
        "max_mana": overrides.get("max_mana", 100),
        "move": overrides.get("move", 100),
        "max_move": overrides.get("max_move", 100),
        "position": overrides.get("position", Position.STANDING),
        "is_npc": overrides.get("is_npc", True),
        "sex": overrides.get("sex", int(Sex.MALE)),
    }
    ch = Character(**base)
    for key, value in overrides.items():
        setattr(ch, key, value)
    return ch


def _make_room(**overrides) -> Room:
    base = {
        "vnum": overrides.get("vnum", 1000),
        "name": overrides.get("name", "Test Room"),
        "description": overrides.get("description", "A test room."),
    }
    room = Room(**base)
    for key, value in overrides.items():
        setattr(room, key, value)
    return room


def _register_object_proto(vnum: int, **kwargs) -> ObjIndex:
    proto = ObjIndex(vnum=vnum, **kwargs)
    obj_registry[vnum] = proto
    return proto


# ---------------------------------------------------------------------------
# create_food
# ---------------------------------------------------------------------------


def test_create_food_creates_mushroom_in_room_and_messages() -> None:
    _register_object_proto(
        OBJ_VNUM_MUSHROOM,
        name="mushroom",
        short_descr="a mushroom",
        item_type=int(ItemType.FOOD),
        weight=55,
        cost=3,
        value=[9, 9, 9, 9, 9],
    )

    room = _make_room()
    caster = make_character(name="Caster", level=12, is_npc=False, room=room)
    observer = make_character(name="Observer", level=5, is_npc=False, room=room)
    room.add_character(observer)

    mushroom = create_food(caster)

    assert mushroom is not None
    assert mushroom in room.contents
    assert mushroom.location is room

    # ROM-style messaging uses short_descr.
    assert caster.messages[-1] == "a mushroom suddenly appears."
    assert "a mushroom suddenly appears." in observer.messages


def test_create_food_sets_value_slots_from_level_and_preserves_rest() -> None:
    _register_object_proto(
        OBJ_VNUM_MUSHROOM,
        name="mushroom",
        short_descr="a mushroom",
        item_type=int(ItemType.FOOD),
        value=[9, 9, 9, 9, 9],
    )

    room = _make_room()
    caster = make_character(level=11, is_npc=False)
    room.add_character(caster)

    mushroom = create_food(caster)

    assert mushroom is not None
    assert mushroom.value[0] == c_div(11, 2)
    assert mushroom.value[1] == 11
    assert mushroom.value[2:] == [9, 9, 9]


def test_create_food_uses_zero_for_negative_caster_level() -> None:
    _register_object_proto(
        OBJ_VNUM_MUSHROOM,
        name="mushroom",
        short_descr="a mushroom",
        item_type=int(ItemType.FOOD),
        value=[0, 0, 0, 0, 0],
    )

    room = _make_room()
    caster = make_character(level=-5, is_npc=False)
    room.add_character(caster)

    mushroom = create_food(caster)

    assert mushroom is not None
    assert mushroom.value[0] == 0
    assert mushroom.value[1] == 0


def test_create_food_returns_none_without_room() -> None:
    _register_object_proto(
        OBJ_VNUM_MUSHROOM,
        name="mushroom",
        short_descr="a mushroom",
        item_type=int(ItemType.FOOD),
    )

    caster = make_character(room=None)

    assert create_food(caster) is None


def test_create_food_returns_none_when_prototype_missing() -> None:
    room = _make_room()
    caster = make_character(room=room)

    assert create_food(caster) is None


# ---------------------------------------------------------------------------
# create_rose
# ---------------------------------------------------------------------------


def test_create_rose_creates_rose_in_inventory_and_updates_weight_and_cost() -> None:
    proto = _register_object_proto(
        OBJ_VNUM_ROSE,
        name="rose",
        short_descr="a red rose",
        item_type=int(ItemType.TREASURE),
        weight=120,
        cost=7,
    )

    room = _make_room()
    caster = make_character(name="Lyssa", is_npc=False, sex=int(Sex.FEMALE))
    observer = make_character(name="Onlooker", is_npc=False)
    room.add_character(caster)
    room.add_character(observer)
    observer.messages.clear()

    rose = create_rose(caster)

    assert rose is not None
    assert rose in caster.inventory
    assert rose.cost == proto.cost
    assert caster.carry_weight == proto.weight

    assert caster.messages[-1] == "You create a beautiful red rose."
    assert observer.messages[-1] == "Lyssa has created a beautiful red rose."


def test_create_rose_raises_when_prototype_missing() -> None:
    caster = make_character(is_npc=False)

    with pytest.raises(ValueError, match="OBJ_VNUM_ROSE prototype is required"):
        create_rose(caster)


# ---------------------------------------------------------------------------
# create_spring
# ---------------------------------------------------------------------------


def test_create_spring_creates_spring_in_room_with_timer() -> None:
    _register_object_proto(
        OBJ_VNUM_SPRING,
        name="spring",
        short_descr="a spring",
        item_type=int(ItemType.FOUNTAIN),
    )

    room = _make_room()
    caster = make_character(level=8, is_npc=False)
    room.add_character(caster)

    spring = create_spring(caster)

    assert spring is not None
    assert spring in room.contents
    assert spring.location is room
    assert spring.timer == 8
    assert caster.messages[-1] == "a spring flows from the ground."


def test_create_spring_clamps_negative_level_timer_to_zero() -> None:
    _register_object_proto(
        OBJ_VNUM_SPRING,
        name="spring",
        short_descr="a spring",
        item_type=int(ItemType.FOUNTAIN),
    )

    room = _make_room()
    caster = make_character(level=-10, is_npc=False)
    room.add_character(caster)

    spring = create_spring(caster)

    assert spring is not None
    assert spring.timer == 0


def test_create_spring_returns_none_without_room() -> None:
    _register_object_proto(
        OBJ_VNUM_SPRING,
        name="spring",
        short_descr="a spring",
        item_type=int(ItemType.FOUNTAIN),
    )

    caster = make_character(room=None)

    assert create_spring(caster) is None


# ---------------------------------------------------------------------------
# create_water
# ---------------------------------------------------------------------------


def _make_drink_container(*, capacity: int, current: int, liquid: int) -> Object:
    proto = ObjIndex(
        vnum=9999,
        name="waterskin",
        short_descr="a waterskin",
        item_type=int(ItemType.DRINK_CON),
    )
    obj = Object(instance_id=None, prototype=proto)
    obj.value = [capacity, current, liquid, 0, 0]
    return obj


def test_create_water_fills_drink_container_raining_uses_x4_multiplier() -> None:
    original_sky = weather.sky
    try:
        weather.sky = SkyState.RAINING

        room = _make_room()
        caster = make_character(level=10, is_npc=False)
        room.add_character(caster)

        container = _make_drink_container(capacity=20, current=0, liquid=0)

        assert create_water(caster, container) is True
        assert container.value[2] == LIQ_WATER
        assert container.value[1] == 20  # min(level*4=40, capacity)
    finally:
        weather.sky = original_sky


def test_create_water_fills_drink_container_nonraining_uses_x2_multiplier_partial_fill() -> None:
    original_sky = weather.sky
    try:
        weather.sky = SkyState.CLOUDLESS

        room = _make_room()
        caster = make_character(level=10, is_npc=False)
        room.add_character(caster)

        container = _make_drink_container(capacity=25, current=10, liquid=LIQ_WATER)

        assert create_water(caster, container) is True
        assert container.value[1] == 25  # adds min(level*2=20, space_remaining=15)
    finally:
        weather.sky = original_sky


def test_create_water_rejects_non_drink_container() -> None:
    room = _make_room()
    caster = make_character(is_npc=False)
    room.add_character(caster)

    proto = ObjIndex(vnum=9998, name="box", short_descr="a box", item_type=int(ItemType.CONTAINER))
    target = Object(instance_id=None, prototype=proto)

    assert create_water(caster, target) is False
    assert caster.messages[-1] == "It is unable to hold water."


def test_create_water_rejects_other_liquid_when_not_empty() -> None:
    room = _make_room()
    caster = make_character(level=10, is_npc=False)
    room.add_character(caster)

    container = _make_drink_container(capacity=20, current=5, liquid=1)  # non-water and non-zero

    assert create_water(caster, container) is False
    assert caster.messages[-1] == "It contains some other liquid."


def test_create_water_rejects_when_already_full() -> None:
    room = _make_room()
    caster = make_character(level=10, is_npc=False)
    room.add_character(caster)

    container = _make_drink_container(capacity=10, current=10, liquid=LIQ_WATER)

    assert create_water(caster, container) is False
    assert caster.messages[-1] == "It is already full of water."


# ---------------------------------------------------------------------------
# continual_light
# ---------------------------------------------------------------------------


def test_continual_light_adds_glow_flag_to_target_and_blocks_duplicate() -> None:
    room = _make_room()
    caster = make_character(is_npc=False)
    room.add_character(caster)

    proto = ObjIndex(vnum=5555, name="amulet", short_descr="a silver amulet", item_type=int(ItemType.TREASURE))
    amulet = Object(instance_id=None, prototype=proto)
    caster.add_object(amulet)

    assert continual_light(caster, amulet) is True
    assert amulet.extra_flags & int(ExtraFlag.GLOW)
    assert caster.messages[-1] == "a silver amulet glows with a white light."

    caster.messages.clear()
    assert continual_light(caster, amulet) is False
    assert caster.messages[-1] == "a silver amulet is already glowing."


def test_continual_light_conjures_light_ball_value_cost_level_and_messages() -> None:
    proto = _register_object_proto(
        OBJ_VNUM_LIGHT_BALL,
        name="light ball",
        short_descr="a ball of light",
        item_type=int(ItemType.LIGHT),
        level=13,
        cost=99,
        value=[1, 2, 3, 4, 5],
    )

    room = _make_room()
    caster = make_character(name="Invoker", level=20, is_npc=False, sex=int(Sex.MALE))
    observer = make_character(name="Witness", is_npc=False)
    room.add_character(caster)
    room.add_character(observer)
    observer.messages.clear()

    light = continual_light(caster)

    assert light is not None
    assert light in room.contents
    assert light.location is room

    # Spawned instances copy these fields from the prototype.
    assert light.level == proto.level
    assert light.cost == proto.cost
    assert light.value == proto.value

    assert caster.messages[-1] == "You twiddle your thumbs and a ball of light appears."
    assert observer.messages[-1] == "Invoker twiddles his thumbs and a ball of light appears."


# ---------------------------------------------------------------------------
# ventriloquate
# ---------------------------------------------------------------------------


def test_ventriloquate_returns_false_without_room_or_argument() -> None:
    caster = make_character(level=20, is_npc=False, room=None)

    assert ventriloquate(caster, "Bob hello") is False

    room = _make_room()
    caster.room = room
    assert ventriloquate(caster, "") is False


def test_ventriloquate_delivers_messages_excludes_speaker_and_sleepers_and_varies_by_save() -> None:
    # Keep the caster OUT of room.people to avoid consuming RNG rolls.
    room = _make_room()
    caster = make_character(level=20, is_npc=False, room=room)

    speaker = make_character(name="Bob", level=10, is_npc=False)
    low_listener = make_character(name="Low", level=1, is_npc=False)
    high_listener = make_character(name="High", level=60, is_npc=False)
    sleeper = make_character(name="Sleeper", level=60, is_npc=False, position=Position.SLEEPING)

    room.add_character(speaker)
    room.add_character(low_listener)
    room.add_character(high_listener)
    room.add_character(sleeper)

    for ch in (speaker, low_listener, high_listener, sleeper):
        ch.messages.clear()

    assert ventriloquate(caster, "Bob hello") is True

    # Speaker is excluded when name matches.
    assert speaker.messages == []

    # Sleeping characters are excluded.
    assert sleeper.messages == []

    # With rng seeded to 42, the first save roll (low_listener) fails and the second (high_listener) succeeds.
    assert low_listener.messages[-1] == "Bob says 'hello'."
    assert high_listener.messages[-1] == "Someone makes Bob say 'hello'."
