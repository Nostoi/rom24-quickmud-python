from mud.models.character import Character, character_registry
from mud.time import time_info, Sunlight
from mud import game_loop


def setup_function(func):
    character_registry.clear()
    time_info.hour = 0
    time_info.day = 0
    time_info.month = 0
    time_info.year = 0
    time_info.sunlight = Sunlight.DARK
    game_loop._pulse_counter = 0


def teardown_function(func):
    character_registry.clear()


def test_time_tick_advances_hour_and_triggers_sunrise():
    ch = Character(name="Tester")
    character_registry.append(ch)
    time_info.hour = 4
    for _ in range(4):
        game_loop.game_tick()
    assert time_info.hour == 5
    assert time_info.sunlight == Sunlight.LIGHT
    assert "The sun rises in the east." in ch.messages


def test_sunrise_broadcasts_to_all_characters():
    ch1 = Character(name="A")
    ch2 = Character(name="B")
    character_registry.extend([ch1, ch2])
    time_info.hour = 4
    for _ in range(4):
        game_loop.game_tick()
    assert "The sun rises in the east." in ch1.messages
    assert "The sun rises in the east." in ch2.messages
