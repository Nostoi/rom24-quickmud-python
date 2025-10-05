from mud.models.constants import AffectFlag, ItemType, Sector
from mud.registry import room_registry
from mud.time import Sunlight, time_info
from mud.world import create_test_character, initialize_world
from mud.world import move_character as move


def setup_world_at(vnum_from: int, vnum_to: int) -> tuple:
    initialize_world("area/area.lst")
    time_info.sunlight = Sunlight.LIGHT
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
    boat = object_factory(
        {"vnum": 9999, "name": "boat", "short_descr": "a small boat", "item_type": int(ItemType.BOAT)}
    )
    ch.add_object(boat)
    ch.move = 20
    out = move(ch, "north")
    assert "You walk north" in out
    assert ch.room is room_to
    # Cost average of CITY(2) and WATER_NOSWIM(1) = 1
    assert ch.move == 19


def test_flying_bypasses_water():
    """AFF_FLYING should let characters cross no-swim sectors without a boat."""

    ch, room_from, room_to = setup_world_at(3001, 3054)
    room_to.sector_type = int(Sector.WATER_NOSWIM)
    ch.add_affect(AffectFlag.FLYING)
    ch.move = 20

    out = move(ch, "north")

    assert "You walk north" in out
    assert ch.room is room_to
    # Flying halves the already minimal movement cost → zero deduction
    assert ch.move == 20
    assert ch.wait == 1


def test_unknown_sector_defaults_to_highest_loss():
    ch, room_from, room_to = setup_world_at(3001, 3054)
    room_from.sector_type = 999
    room_to.sector_type = -12
    ch.move = 20

    out = move(ch, "north")

    assert "You walk north" in out
    assert ch.room is room_to
    assert ch.move == 14
    assert ch.wait == 1
