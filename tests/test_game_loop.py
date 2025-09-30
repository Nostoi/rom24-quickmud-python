import mud.game_loop as gl
from mud.config import get_pulse_tick
from mud.game_loop import events, game_tick, schedule_event, weather
from mud.models.area import Area
from mud.models.character import Character, character_registry
from mud.models.constants import ActFlag, Position
from mud.models.room import Room
from mud.utils import rng_mm


def setup_function(_):
    character_registry.clear()
    events.clear()
    weather.sky = "sunny"
    gl._pulse_counter = 0
    gl._point_counter = 0
    gl._violence_counter = 0
    gl._area_counter = 0


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
    pulses = get_pulse_tick()
    game_tick()
    assert ch.hit == 6 and ch.mana == 4 and ch.move == 5
    for _ in range(max(0, pulses - 1)):
        game_tick()
    assert ch.hit == 6 and ch.mana == 4 and ch.move == 5
    game_tick()
    assert ch.hit == 7 and ch.mana == 5 and ch.move == 6


def test_weather_cycles_states():
    game_tick()
    assert weather.sky == "cloudy"
    for _ in range(max(0, get_pulse_tick() - 1)):
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


def test_aggressive_mobile_attacks_player(monkeypatch):
    area = Area(name="Arena")
    room = Room(vnum=42, area=area)

    hero = Character(
        name="Hero",
        level=5,
        hit=20,
        max_hit=20,
        mana=10,
        max_mana=10,
        move=10,
        max_move=10,
        is_npc=False,
        position=int(Position.STANDING),
    )
    brute = Character(
        name="Brute",
        level=5,
        hit=20,
        max_hit=20,
        act=int(ActFlag.AGGRESSIVE),
        position=int(Position.STANDING),
    )

    room.add_character(hero)
    room.add_character(brute)
    character_registry.extend([hero, brute])

    monkeypatch.setattr(rng_mm, "number_bits", lambda _: 1)

    game_tick()

    assert brute.fighting is hero
    assert hero.fighting is brute
