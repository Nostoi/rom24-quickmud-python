import mud.game_loop as gl
from mud import config as mud_config
from mud.config import get_pulse_violence
from mud.game_loop import game_tick
from mud.models.character import Character, character_registry
from mud.models.constants import Position


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


def test_wait_and_daze_decrement_each_pulse_before_violence_combat(monkeypatch):
    room = object()
    fighter = Character(name="Fighter", wait=3, daze=3, position=int(Position.FIGHTING))
    target = Character(name="Target", position=int(Position.FIGHTING))
    fighter.desc = object()
    target.desc = object()
    fighter.room = room
    target.room = room
    fighter.fighting = target
    target.fighting = fighter
    character_registry[:] = [fighter, target]

    gl._pulse_counter = 0
    gl._point_counter = 999999
    gl._area_counter = 999999
    gl._music_counter = 999999
    gl._mobile_counter = 999999
    gl._violence_counter = get_pulse_violence()

    calls: list[int] = []
    monkeypatch.setattr("mud.combat.engine.multi_hit", lambda attacker, victim, dt=None: calls.append(gl._pulse_counter))
    monkeypatch.setattr("mud.combat.engine.stop_fighting", lambda ch, both=False: None)

    game_tick()

    assert (fighter.wait, fighter.daze, calls) == (2, 2, [])
