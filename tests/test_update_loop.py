from mud.update import (
    update_tick,
    schedule_event,
    weather,
    events,
)
from mud.models.character import Character, character_registry
from mud.spawning.reset_handler import RESET_TICKS
from mud.models.area import Area
from mud.models.room import Room
from mud.registry import area_registry, room_registry


def setup_function(function):
    character_registry.clear()
    events.clear()
    area_registry.clear()
    room_registry.clear()
    weather.index = 0


def test_regen_weather_and_events():
    char = Character(
        hit=5, max_hit=10, mana=3, max_mana=10, move=1, max_move=10
    )
    character_registry.append(char)

    triggered: list[bool] = []

    def mark():
        triggered.append(True)

    schedule_event(2, mark)
    update_tick()
    update_tick()

    assert char.hit == 7
    assert char.mana == 5
    assert char.move == 3
    assert weather.sunlight == "day"
    assert triggered


def test_reset_tick_from_update():
    area = Area(vnum=1)
    area.age = RESET_TICKS - 1
    area_registry[1] = area
    room_registry[1] = Room(vnum=1, area=area)

    update_tick()

    assert area.age == 0
