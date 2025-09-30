import mud.game_loop as gl
from mud import config as mud_config
from mud.game_loop import game_tick
from mud.models.character import Character, character_registry


def setup_function(_):
    character_registry.clear()
    mud_config.TIME_SCALE = 1
    gl._pulse_counter = 0
    gl._point_counter = 0
    gl._violence_counter = 0
    gl._area_counter = 0


def teardown_function(_):
    mud_config.TIME_SCALE = 1
    gl._pulse_counter = 0
    gl._point_counter = 0
    gl._violence_counter = 0
    gl._area_counter = 0


def test_wait_and_daze_decrement_on_violence_pulse():
    ch = Character(name="Fighter", wait=2, daze=2)
    character_registry.append(ch)
    game_tick()
    assert ch.wait == 1 and ch.daze == 1
    game_tick()
    assert ch.wait == 0 and ch.daze == 0
    # Do not go below zero
    game_tick()
    assert ch.wait == 0 and ch.daze == 0
