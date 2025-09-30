from __future__ import annotations

from pathlib import Path

import pytest

import mud.game_loop as game_loop
from mud.commands import process_command
from mud.imc import get_state, imc_enabled, maybe_open_socket, reset_state
from mud.imc.protocol import Frame, parse_frame, serialize_frame
from mud.world import create_test_character, initialize_world


def _default_imc_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "imc"


def _write_imc_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    config = tmp_path / "imc.config"
    config.write_text(
        "\n".join(
            [
                "LocalName QuickMUD",
                "Autoconnect 1",
                "MinPlayerLevel 10",
                "MinImmLevel 101",
                "AdminLevel 113",
                "Implevel 115",
                "InfoName QuickMUD Python Port",
                "InfoHost localhost",
                "InfoPort 4000",
                "InfoEmail quickmud@example.com",
                "InfoWWW https://quickmud",
                "InfoBase ROM",
                "InfoDetails Test configuration",
                "ServerAddr router.quickmud",
                "ServerPort 4000",
                "ClientPwd clientpw",
                "ServerPwd serverpw",
                "SHA256 1",
                "End",
                "$END",
            ]
        )
        + "\n"
    )

    channels = tmp_path / "imc.channels"
    channels.write_text(
        "\n".join(
            [
                "#IMCCHAN",
                "ChanName IMC2",
                "ChanLocal quickmud",
                "ChanRegF [$n] $t",
                "ChanEmoF * $n $t",
                "ChanSocF [$n socials] $t",
                "ChanLevel 101",
                "End",
                "#END",
            ]
        )
        + "\n"
    )

    helps = tmp_path / "imc.help"
    helps.write_text(
        "\n".join(
            [
                "Name IMC2",
                "Perm Mort",
                "Text Welcome to the IMC2 network.",
                "End",
                "#HELP",
                "Name IMCInfo",
                "Perm Mort",
                "Text IMC info commands.",
                "End",
                "#HELP",
                "Name IMCList",
                "Perm Mort",
                "Text List current IMC channels.",
                "End",
                "#HELP",
                "Name IMCNote",
                "Perm Mort",
                "Text Review IMC network notes.",
                "End",
                "#HELP",
                "Name IMCPing",
                "Perm Mort",
                "Text Check connectivity to the IMC network.",
                "End",
                "#HELP",
                "Name IMCReply",
                "Perm Mort",
                "Text Reply to the last IMC tell.",
                "End",
                "#HELP",
                "Name IMCSubscribe",
                "Perm Mort",
                "Text Subscribe to an IMC channel.",
                "End",
                "#HELP",
                "Name IMCBan",
                "Perm Imm",
                "Text Immortals may ban network sites.",
                "End",
                "#HELP",
                "Name IMCDebug",
                "Perm Admin",
                "Text Debug commands are restricted.",
                "End",
                "#END",
            ]
        )
        + "\n"
    )

    return config, channels, helps


def test_imc_disabled_by_default(monkeypatch):
    monkeypatch.delenv("IMC_ENABLED", raising=False)
    reset_state()
    assert imc_enabled() is False
    # Must not open sockets when disabled
    assert maybe_open_socket() is None


def test_parse_serialize_roundtrip():
    sample = "chat alice@quickmud * :Hello world"
    frame = parse_frame(sample)
    assert frame == Frame(type="chat", source="alice@quickmud", target="*", message="Hello world")
    assert serialize_frame(frame) == sample


def test_parse_frame_accepts_additional_whitespace():
    frame = parse_frame("chat   alice@quickmud    *   :Hello there")
    assert frame == Frame(type="chat", source="alice@quickmud", target="*", message="Hello there")


def test_parse_frame_preserves_message_leading_spaces():
    frame = parse_frame("chat alice@quickmud * :  Leading space")
    assert frame.message == "  Leading space"


def test_parse_frame_rejects_missing_colon_even_with_whitespace():
    with pytest.raises(ValueError):
        parse_frame("chat   alice@quickmud    *   Hello there")


def test_parse_invalid_raises():
    for s in ["", "badframe", "chat onlytwo", "chat a b c"]:
        try:
            parse_frame(s)
            assert False
        except ValueError:
            pass


def test_imc_command_gated(monkeypatch):
    monkeypatch.delenv("IMC_ENABLED", raising=False)
    initialize_world("area/area.lst")
    ch = create_test_character("IMCUser", 3001)
    out = process_command(ch, "imc")
    assert "disabled" in out.lower()


def test_imc_command_enabled_lists_topics(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()
    initialize_world("area/area.lst")
    ch = create_test_character("IMCUser", 3001)

    summary = process_command(ch, "imc")
    assert "Help is available for the following commands." in summary
    assert (
        "For information about a specific command, see imchelp <command>." in summary
    )
    assert "Mort helps:" in summary
    assert "imc2" in summary.lower()
    # Mortal users should not see immortal or admin-only topics.
    assert "Imm helps:" not in summary
    assert "Admin helps:" not in summary
    assert "imcdebug" not in summary.lower()

    state = maybe_open_socket()
    assert state is not None and state.connected is True


def test_imc_help_topic_returns_entry(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()
    initialize_world("area/area.lst")
    ch = create_test_character("IMCUser", 3001)

    response = process_command(ch, "imc help imc2")
    assert "IMC2 (Mort)" in response
    assert "Welcome to the IMC2 network." in response


def test_imc_help_missing_topic(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()
    initialize_world("area/area.lst")
    ch = create_test_character("IMCUser", 3001)

    response = process_command(ch, "imc help missing")
    assert "no imc help entry" in response.lower()


def test_help_summary_matches_rom_permissions(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()
    initialize_world("area/area.lst")

    mortal = create_test_character("IMCUser", 3001)
    mortal_summary = process_command(mortal, "imc")

    assert "Mort helps:" in mortal_summary
    assert "Imm helps:" not in mortal_summary
    assert "Admin helps:" not in mortal_summary

    mortal_lines = mortal_summary.splitlines()
    mort_index = mortal_lines.index("Mort helps:")

    mortal_rows: list[str] = []
    for line in mortal_lines[mort_index + 1 :]:
        if not line.strip():
            break
        mortal_rows.append(line)

    assert len(mortal_rows) == 2
    first_row = [col.strip() for col in _split_columns(mortal_rows[0])]
    second_row = [col.strip() for col in _split_columns(mortal_rows[1])]

    assert first_row == [
        "IMC2",
        "IMCInfo",
        "IMCList",
        "IMCNote",
        "IMCPing",
        "IMCReply",
    ]
    assert second_row == ["IMCSubscribe"]

    admin = create_test_character("IMCAdmin", 3001)
    admin.imc_permission = "Admin"
    admin_summary = process_command(admin, "imc")

    assert "Imm helps:" in admin_summary
    assert "Admin helps:" in admin_summary
    assert "imcban" in admin_summary.lower()
    assert "imcdebug" in admin_summary.lower()


def _split_columns(line: str) -> list[str]:
    width = 15
    return [line[i : i + width] for i in range(0, len(line), width) if line[i : i + width].strip()]


def test_startup_reads_config_and_connects(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()

    initialize_world("area/area.lst")

    state = get_state()
    assert state is not None and state.connected is True
    assert state.config["LocalName"] == "QuickMUD"
    assert state.channels and state.channels[0].name == "IMC2"
    assert "imc2" in state.helps


def test_idle_pump_runs_when_enabled(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    reset_state()

    initialize_world("area/area.lst")
    state = get_state()
    assert state is not None

    previous_counter = game_loop._point_counter
    game_loop._point_counter = 1
    try:
        before = state.idle_pulses
        game_loop.game_tick()
        after = get_state().idle_pulses
    finally:
        game_loop._point_counter = previous_counter

    assert after == before + 1
