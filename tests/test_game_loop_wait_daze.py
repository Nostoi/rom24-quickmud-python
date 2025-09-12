from mud.game_loop import game_tick
from mud.models.character import Character, character_registry
from mud import config as mud_config


def setup_function(_):
    character_registry.clear()
    # Speed up pulses in tests
    mud_config.TIME_SCALE = 12  # so PULSE_VIOLENCE= (3*4)/12 = 1


def teardown_function(_):
    # Reset scale after test
    mud_config.TIME_SCALE = 1


def test_wait_and_daze_decrement_on_violence_pulse():
    ch = Character(name="Fighter", wait=2, daze=2)
    character_registry.append(ch)
    # With TIME_SCALE=12, every game_tick triggers a violence tick
    game_tick()
    assert ch.wait == 1 and ch.daze == 1
    game_tick()
    assert ch.wait == 0 and ch.daze == 0
    # Do not go below zero
    game_tick()
    assert ch.wait == 0 and ch.daze == 0
