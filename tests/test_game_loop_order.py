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
