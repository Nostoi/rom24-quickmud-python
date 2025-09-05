from mud.game_loop import (
    game_tick,
    weather,
    schedule_event,
    events,
)
from mud.models.character import Character, character_registry


def setup_function(_):
    character_registry.clear()
    events.clear()
    weather.sky = "sunny"


def test_regen_tick_increases_resources():
    ch = Character(
        name="Bob",
        hit=5,
        max_hit=10,
        mana=3,
        max_mana=10,
        move=4,
        max_move=10,
    )
    character_registry.append(ch)
    game_tick()
    assert ch.hit == 6 and ch.mana == 4 and ch.move == 5


def test_weather_cycles_states():
    game_tick()
    assert weather.sky == "cloudy"
    game_tick()
    assert weather.sky == "rainy"


def test_timed_event_fires_after_delay():
    triggered: list[int] = []
    schedule_event(2, lambda: triggered.append(1))
    game_tick()
    assert not triggered
    game_tick()
    assert triggered == [1]
