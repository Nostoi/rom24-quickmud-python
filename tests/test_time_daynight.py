from mud import config as mud_config
from mud import game_loop
from mud.config import get_pulse_tick
from mud.models.character import Character, character_registry
from mud.models.constants import Position, RoomFlag
from mud.models.room import Room
from mud.time import Sunlight, time_info


def setup_function(func):
    character_registry.clear()
    time_info.hour = 0
    time_info.day = 0
    time_info.month = 0
    time_info.year = 0
    time_info.sunlight = Sunlight.DARK
    game_loop._pulse_counter = 0
    game_loop._point_counter = 0
    game_loop._violence_counter = 0
    game_loop._area_counter = 0


def teardown_function(func):
    character_registry.clear()


def test_time_tick_advances_hour_and_triggers_sunrise():
    ch = Character(name="Tester")
    room = Room(vnum=100)
    room.add_character(ch)
    character_registry.append(ch)
    time_info.hour = 4
    # Advance exactly one ROM hour (PULSE_TICK pulses)
    for _ in range(get_pulse_tick()):
        game_loop.game_tick()
    assert time_info.hour == 5
    assert time_info.sunlight == Sunlight.LIGHT
    assert "The day has begun." in ch.messages


def test_sunrise_broadcast_targets_awake_outdoor_characters():
    outdoor_room = Room(vnum=101)
    indoor_room = Room(vnum=102, room_flags=int(RoomFlag.ROOM_INDOORS))

    awake_outdoor = Character(name="Awake")
    indoor_char = Character(name="Indoor")
    sleeping_outdoor = Character(name="Sleeper", position=Position.SLEEPING)

    outdoor_room.add_character(awake_outdoor)
    outdoor_room.add_character(sleeping_outdoor)
    indoor_room.add_character(indoor_char)

    character_registry.extend([awake_outdoor, indoor_char, sleeping_outdoor])
    time_info.hour = 4
    for _ in range(get_pulse_tick()):
        game_loop.game_tick()
    assert "The day has begun." in awake_outdoor.messages
    assert "The day has begun." not in indoor_char.messages
    assert "The day has begun." not in sleeping_outdoor.messages


def test_rom_sunlight_transitions():
    """Test all 4 ROM sunlight state transitions match C code exactly."""
    from mud.time import Sunlight, TimeInfo

    # Hour 5: SUN_LIGHT, "The day has begun."
    t = TimeInfo(hour=4)
    msgs = t.advance_hour()
    assert t.hour == 5
    assert t.sunlight == Sunlight.LIGHT
    assert msgs == ["The day has begun."]

    # Hour 6: SUN_RISE, "The sun rises in the east."
    msgs = t.advance_hour()
    assert t.hour == 6
    assert t.sunlight == Sunlight.RISE
    assert msgs == ["The sun rises in the east."]

    # Hour 19: SUN_SET, "The sun slowly disappears in the west."
    t = TimeInfo(hour=18)
    msgs = t.advance_hour()
    assert t.hour == 19
    assert t.sunlight == Sunlight.SET
    assert msgs == ["The sun slowly disappears in the west."]

    # Hour 20: SUN_DARK, "The night has begun."
    msgs = t.advance_hour()
    assert t.hour == 20
    assert t.sunlight == Sunlight.DARK
    assert msgs == ["The night has begun."]


def test_sunset_and_night_messages_and_wraparound():
    from mud.time import TimeInfo

    # Directly exercise TimeInfo transitions
    t = TimeInfo(hour=18, day=0, month=0, year=0)
    msgs = t.advance_hour()
    assert msgs == ["The sun slowly disappears in the west."]
    msgs = t.advance_hour()
    assert msgs == ["The night has begun."]

    # Wrap day→month→year at boundaries: day 34→0, month 16→0, year++
    t = TimeInfo(hour=23, day=34, month=16, year=5)
    _ = t.advance_hour()
    assert t.hour == 0 and t.day == 0 and t.month == 0 and t.year == 6


def test_time_scale_accelerates_tick(monkeypatch):
    character_registry.clear()
    time_info.hour = 4
    game_loop._pulse_counter = 0
    # Speed up tick so that a single pulse triggers an hour advance
    monkeypatch.setattr("mud.config.TIME_SCALE", 60 * 4)
    # Sanity: scaled tick should be 1
    assert mud_config.get_pulse_tick() == 1

    ch = Character(name="Scaler")
    room = Room(vnum=103)
    room.add_character(ch)
    character_registry.append(ch)
    game_loop.game_tick()  # one pulse with scaling
    assert time_info.hour == 5
    assert time_info.sunlight == Sunlight.LIGHT
    assert "The day has begun." in ch.messages
