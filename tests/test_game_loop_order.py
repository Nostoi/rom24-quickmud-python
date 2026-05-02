"""Tests that game_tick() fires subsystems in ROM C update_handler order.

ROM src/update.c:update_handler order:
    area → music → mobile → violence → point(time/weather/char/obj) → aggr
"""

from mud import config as mud_config
from mud.game_loop import game_tick


def test_rom_order_when_all_cadence_boundaries_coincide(monkeypatch):
    """All counters fire on this tick — verify exact ROM C ordering."""
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
    monkeypatch.setattr(gl, "violence_tick", lambda **_kw: order.append("violence"))
    monkeypatch.setattr(gl, "time_tick", lambda: order.append("time"))
    monkeypatch.setattr(gl, "weather_tick", lambda: order.append("weather"))
    monkeypatch.setattr(gl, "char_update", lambda: order.append("char"))
    monkeypatch.setattr(gl, "obj_update", lambda: order.append("obj"))
    monkeypatch.setattr(gl, "aggressive_update", lambda: order.append("aggr"))
    monkeypatch.setattr(gl, "event_tick", lambda: None)
    monkeypatch.setattr(gl, "run_npc_specs", lambda: None)
    monkeypatch.setattr(gl, "pump_idle", lambda: None)

    gl.game_tick()

    # ROM C src/update.c:update_handler exact order
    assert order == ["area", "music", "mobile", "violence", "time", "weather", "char", "obj", "aggr"]


def test_only_violence_fires(monkeypatch):
    """Only the violence counter expires — area/music/mobile/point stay silent."""
    order: list[str] = []

    import mud.game_loop as gl

    gl._pulse_counter = 0
    gl._point_counter = 999
    gl._area_counter = 999
    gl._music_counter = 999
    gl._mobile_counter = 999
    gl._violence_counter = 1

    monkeypatch.setattr(gl, "reset_tick", lambda: order.append("area"))
    monkeypatch.setattr(gl, "song_update", lambda: order.append("music"))
    monkeypatch.setattr(gl, "mobile_update", lambda: order.append("mobile"))
    monkeypatch.setattr(gl, "violence_tick", lambda **_kw: order.append("violence"))
    monkeypatch.setattr(gl, "time_tick", lambda: order.append("time"))
    monkeypatch.setattr(gl, "weather_tick", lambda: order.append("weather"))
    monkeypatch.setattr(gl, "char_update", lambda: order.append("char"))
    monkeypatch.setattr(gl, "obj_update", lambda: order.append("obj"))
    monkeypatch.setattr(gl, "aggressive_update", lambda: order.append("aggr"))
    monkeypatch.setattr(gl, "event_tick", lambda: None)
    monkeypatch.setattr(gl, "run_npc_specs", lambda: None)
    monkeypatch.setattr(gl, "pump_idle", lambda: None)

    gl.game_tick()

    assert order == ["violence", "aggr"]
