from datetime import datetime
from pathlib import Path

import mud.persistence as persistence
from mud.commands import process_command
from mud.logging.admin import (
    is_log_all_enabled,
    log_admin_command,
    rotate_admin_log,
    set_log_all,
)
from mud.models.character import character_registry
from mud.net.session import SESSIONS
from mud.world import create_test_character, initialize_world


def setup_module(module):
    initialize_world("area/area.lst")


def teardown_function(function):
    for character in list(character_registry):
        if getattr(character, "room", None):
            character.room.remove_character(character)
    character_registry.clear()
    SESSIONS.clear()
    set_log_all(False)


def _create_admin_and_player():
    admin = create_test_character("Admin", 3001)
    admin.is_admin = True
    player = create_test_character("Player", 3001)
    player.is_admin = False
    return admin, player


def test_log_toggles_per_character_logging(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log Player")
    assert out_on == "LOG set."
    assert player.log_commands is True

    process_command(player, "look")
    log_path = Path("log") / "admin.log"
    first_lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = next(line for line in first_lines if "\tPlayer\tlook" in line)
    fields = entry.split("\t")
    assert len(fields) == 3
    timestamp = fields[0]
    assert timestamp.endswith("Z")
    assert "+00:00" not in timestamp
    assert fields[1] == "Player"
    assert fields[2] == "look"

    out_off = process_command(admin, "log Player")
    assert out_off == "LOG removed."
    assert player.log_commands is False

    lines_after_disable = log_path.read_text(encoding="utf-8").splitlines()

    process_command(player, "look")
    final_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert final_lines == lines_after_disable


def test_log_all_rotation_retains_flag(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log all")
    assert out_on == "Log ALL on."
    assert is_log_all_enabled() is True

    process_command(player, "look")
    log_path = Path("log") / "admin.log"
    initial_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert any("\tPlayer\tlook" in line for line in initial_lines)

    rotate_admin_log(today=datetime(2099, 1, 2))
    active_path = Path("log") / "admin.log"
    assert active_path.exists()
    assert active_path.read_text(encoding="utf-8") == ""
    assert is_log_all_enabled() is True

    process_command(player, "look")
    rotated_lines = active_path.read_text(encoding="utf-8").splitlines()
    assert any("\tPlayer\tlook" in line for line in rotated_lines)

    out_off = process_command(admin, "log all")
    assert out_off == "Log ALL off."
    assert is_log_all_enabled() is False


def test_log_all_accepts_trailing_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    admin, _player = _create_admin_and_player()

    out_on = process_command(admin, "log all now please")
    assert out_on == "Log ALL on."
    assert is_log_all_enabled() is True

    out_off = process_command(admin, "log all later")
    assert out_off == "Log ALL off."
    assert is_log_all_enabled() is False


def test_log_command_allows_prefix_lookup(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log pla")
    assert out_on == "LOG set."
    assert player.log_commands is True

    out_off = process_command(admin, "log p")
    assert out_off == "LOG removed."
    assert player.log_commands is False


def test_log_flag_persists_in_save(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(persistence, "PLAYERS_DIR", tmp_path / "players")
    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log Player")
    assert out_on == "LOG set."
    assert player.log_commands is True

    persistence.save_character(player)

    character_registry.clear()
    loaded = persistence.load_character("Player")
    assert loaded is not None
    assert loaded.log_commands is True


def test_log_all_captures_unknown_command_and_sanitizes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log all")
    assert out_on == "Log ALL on."

    response = process_command(player, "frobnicate$  42\n")
    assert response == "Huh?"

    log_path = Path("log") / "admin.log"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    entry = next(line for line in lines if "\tPlayer\t" in line and "frobnicate" in line)
    assert entry.endswith("frobnicateS  42")


def test_logging_logs_alias_expansion(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    admin, player = _create_admin_and_player()

    out_on = process_command(admin, "log Player")
    assert out_on == "LOG set."

    player.aliases["x"] = "look"

    process_command(player, " x  ")

    log_path = Path("log") / "admin.log"
    entry = log_path.read_text(encoding="utf-8").splitlines()[-1]
    fields = entry.split("\t")
    assert fields[1] == "Player"
    assert fields[2] == "look  "


def test_log_sanitization_preserves_user_spacing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    log_admin_command("Admin", "echo hi  ")

    log_path = Path("log") / "admin.log"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert lines[-1].endswith("echo hi  ")


def test_log_sanitization_strips_control_edges(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    noisy = "\x00\x01say\x02hi\x03\x04"
    log_admin_command("Admin", noisy)

    log_path = Path("log") / "admin.log"
    entry = log_path.read_text(encoding="utf-8").splitlines()[-1]
    assert entry.endswith("say hi")


def test_log_never_skips_unless_log_all(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    admin, _ = _create_admin_and_player()

    process_command(admin, "north")

    log_path = Path("log") / "admin.log"
    assert not log_path.exists()

    set_log_all(True)
    try:
        process_command(admin, "north")
    finally:
        set_log_all(False)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert any(line.endswith("\tnorth") for line in lines)


def test_log_always_logs_for_mortals(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    _, player = _create_admin_and_player()

    response = process_command(player, "ban suspicious.com")
    assert response == "You do not have permission to use this command."

    log_path = Path("log") / "admin.log"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert any(line.endswith("\tban suspicious.com") for line in lines)
