from pathlib import Path
from datetime import datetime

from mud.logging.admin import log_admin_command, rotate_admin_log
from mud import game_loop
from mud.models.character import Character, character_registry
from mud.time import time_info
from mud import config as mud_config


def test_rotate_admin_log_by_function(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Write an entry
    log_admin_command("Admin", "wiznet", "")
    # Rotate to a fixed date
    target = datetime(2099, 1, 2)
    active = rotate_admin_log(today=target)
    assert active.name == 'admin.log'
    rolled = Path('log') / 'admin-20990102.log'
    assert rolled.exists()
    # New active file should be empty
    assert active.read_text(encoding='utf-8') == ''


def test_rotate_on_midnight_tick(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    character_registry.clear()
    # Speed up time so one pulse advances an hour
    monkeypatch.setattr('mud.config.TIME_SCALE', 60 * 4)
    # Ensure a log file exists before midnight
    log_admin_command("Admin", "wiznet", "")
    # Set time to 23h and tick once to midnight
    time_info.hour = 23
    ch = Character(name="Watcher")
    character_registry.append(ch)
    game_loop._pulse_counter = 0
    game_loop.game_tick()
    # After midnight, admin.log should be rotated to today's date
    # Use current UTC date for naming
    today = datetime.utcnow().strftime('%Y%m%d')
    assert (Path('log') / f'admin-{today}.log').exists()
