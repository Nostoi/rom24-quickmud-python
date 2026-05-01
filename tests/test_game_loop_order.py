from mud import config as mud_config
from mud.game_loop import game_tick


def test_weather_time_reset_order_on_point_pulse(monkeypatch):
    # Force both violence and point pulses to trigger every call
    mud_config.TIME_SCALE = 240
    mud_config.GAME_LOOP_STRICT_POINT = True

    order: list[str] = []

    import mud.game_loop as gl

    gl._pulse_counter = 0
    gl._point_counter = 0
    gl._violence_counter = 0
    gl._area_counter = 0

    monkeypatch.setattr(gl, "violence_tick", lambda: order.append("violence"))
    monkeypatch.setattr(gl, "time_tick", lambda: order.append("time"))
    monkeypatch.setattr(gl, "weather_tick", lambda: order.append("weather"))
    monkeypatch.setattr(gl, "reset_tick", lambda: order.append("reset"))

    game_tick()

    # Expect violence first, then time, weather, reset in that order
    assert order[:4] == ["violence", "time", "weather", "reset"]

    # Reset flags
    mud_config.TIME_SCALE = 1
    mud_config.GAME_LOOP_STRICT_POINT = False


def test_rom_order_when_all_cadence_boundaries_coincide(monkeypatch):
    order: list[str] = []

    import mud.game_loop as gl

    gl._pulse_counter = 0
    gl._point_counter = 1
    gl._area_counter = 1
    gl._music_counter = 1
    gl._mobile_counter = 1
    gl._violence_counter = 1

    monkeypatch.setattr(gl, "reset_tick", lambda: order.append("area"))
    monkeypatch.setattr(gl, "song_update", lambda: order.append("music"))
    monkeypatch.setattr(gl, "mobile_update", lambda: order.append("mobile"))
    monkeypatch.setattr(gl, "violence_tick", lambda: order.append("violence"))
    monkeypatch.setattr(gl, "weather_tick", lambda: order.append("weather"))
    monkeypatch.setattr(gl, "char_update", lambda: order.append("char"))
    monkeypatch.setattr(gl, "obj_update", lambda: order.append("obj"))
    monkeypatch.setattr(gl, "aggressive_update", lambda: order.append("aggr"))
    monkeypatch.setattr(gl, "time_tick", lambda: None)
    monkeypatch.setattr(gl, "event_tick", lambda: None)
    monkeypatch.setattr(gl, "run_npc_specs", lambda: None)
    monkeypatch.setattr(gl, "pump_idle", lambda: None)

    gl.game_tick()

    assert order[:8] == ["area", "music", "mobile", "violence", "weather", "char", "obj", "aggr"]
