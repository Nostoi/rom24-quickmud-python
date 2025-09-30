from datetime import UTC, datetime
from pathlib import Path

from mud import game_loop
from mud.admin_logging.admin import log_admin_command, rotate_admin_log
from mud.models.character import Character, character_registry
from mud.time import time_info


def test_rotate_admin_log_by_function(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Write an entry
    log_admin_command("Admin", "wiznet")
    # Rotate to a fixed date
    target = datetime(2099, 1, 2)
    active = rotate_admin_log(today=target)
    assert active.name == "admin.log"
    rolled = Path("log") / "admin-20990102.log"
    assert rolled.exists()
    # New active file should be empty
    assert active.read_text(encoding="utf-8") == ""


def test_rotate_no_active_returns_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # No log directory or file yet
    from mud.admin_logging.admin import rotate_admin_log

    path = rotate_admin_log(today=datetime(2099, 1, 2))
    assert path == Path("log") / "admin.log"
    # Path not created by early-return branch
    assert not path.exists()


def test_rotate_on_midnight_tick(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    character_registry.clear()
    # Speed up time so one pulse advances an hour
    monkeypatch.setattr("mud.config.TIME_SCALE", 60 * 4)
    # Ensure a log file exists before midnight
    log_admin_command("Admin", "wiznet")
    # Set time to 23h and tick once to midnight
    time_info.hour = 23
    ch = Character(name="Watcher")
    character_registry.append(ch)
    game_loop._pulse_counter = 0
    game_loop._point_counter = 0
    game_loop._violence_counter = 0
    game_loop._area_counter = 0
    game_loop.game_tick()
    # After midnight, admin.log should be rotated to today's date
    # Use current UTC date for naming
    today = datetime.now(UTC).strftime("%Y%m%d")
    assert (Path("log") / f"admin-{today}.log").exists()


def test_rotate_appends_when_dated_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from mud.admin_logging.admin import rotate_admin_log

    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)
    active = log_dir / "admin.log"
    dated = log_dir / "admin-20990102.log"
    dated.write_text("old\n", encoding="utf-8")
    active.write_text("new\n", encoding="utf-8")

    rotate_admin_log(today=datetime(2099, 1, 2))
    # Dated file now contains both
    assert dated.read_text(encoding="utf-8") == "old\nnew\n"
    # Active removed then recreated empty
    assert active.exists()
    assert active.read_text(encoding="utf-8") == ""
