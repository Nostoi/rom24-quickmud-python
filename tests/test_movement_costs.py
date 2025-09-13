from pathlib import Path

from mud.world import initialize_world, create_test_character
from mud.world import move_character as move
from mud.registry import room_registry
from mud.models.constants import Sector, AffectFlag, ItemType


def setup_world_at(vnum_from: int, vnum_to: int) -> tuple:
    initialize_world("area/area.lst")
    ch = create_test_character("Walker", vnum_from)
    # Ensure a simple north exit exists in test data
    room_from = room_registry[vnum_from]
    room_to = room_registry[vnum_to]
    room_from.sector_type = int(Sector.CITY)
    room_to.sector_type = int(Sector.FOREST)
    ch.move = 20
    return ch, room_from, room_to


def test_sector_move_cost_and_wait():
    ch, room_from, room_to = setup_world_at(3001, 3054)

    # CITY (2) to FOREST (3) → average floor((2+3)/2)=2
    out = move(ch, "north")
    assert "You walk north" in out
    assert ch.room is room_to
    assert ch.move == 18
    assert ch.wait == 1


def test_water_noswim_requires_boat():
    ch, room_from, room_to = setup_world_at(3001, 3054)
    room_from.sector_type = int(Sector.WATER_NOSWIM)
    ch.move = 20
    out = move(ch, "north")
    assert out == "You need a boat to go there."
    assert ch.room is room_from


def test_air_requires_flying():
    ch, room_from, room_to = setup_world_at(3001, 3054)
    room_to.sector_type = int(Sector.AIR)
    ch.move = 20
    out = move(ch, "north")
    assert out == "You can't fly."
    assert ch.room is room_from


def test_boat_allows_water_noswim(object_factory):
    ch, room_from, room_to = setup_world_at(3001, 3054)
    room_to.sector_type = int(Sector.WATER_NOSWIM)
    # Add a BOAT object to inventory via object factory
    boat = object_factory({"vnum": 9999, "name": "boat", "short_descr": "a small boat", "item_type": int(ItemType.BOAT)})
    ch.add_object(boat)
    ch.move = 20
    out = move(ch, "north")
    assert "You walk north" in out
    assert ch.room is room_to
    # Cost average of CITY(2) and WATER_NOSWIM(1) = 1
    assert ch.move == 19
