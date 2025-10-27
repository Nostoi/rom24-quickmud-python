from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any
from pathlib import Path
import socket
import time

import pytest

import mud.game_loop as game_loop
from mud.commands import process_command
from mud.imc import (
    IMCCHAN_LOG,
    IMC_HISTORY_LIMIT,
    IMCChannel,
    IMCColor,
    IMCState,
    _UCACHE_REFRESH_INTERVAL,
    _handle_disconnect,
    _load_channel_history,
    _parse_channels,
    get_state,
    imc_enabled,
    maybe_open_socket,
    pump_idle,
    reset_state,
    save_channel_history,
)
from mud.imc.commands import IMCPacket
from mud.imc.protocol import Frame, parse_frame, serialize_frame
from mud.loaders.social_loader import load_socials
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
                "   * Default IMC2 broadcast configuration",
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


def test_parse_channels_skips_comments(tmp_path):
    channel_path = tmp_path / "imc.channels"
    channel_path.write_text(
        "\n".join(
            [
                "#IMCCHAN",
                "* Leading comment",
                "ChanName Foo",
                " ChanLocal bar",  # include leading space to ensure trim
                "* Another comment",  # should be ignored
                "ChanRegF [$n] $t",
                "ChanEmoF * $n $t",
                "ChanSocF [$n socials] $t",
                "ChanLevel 101",
                "End",
                "#END",
            ]
        )
        + "\n",
        encoding="latin-1",
    )

    channels = _parse_channels(channel_path)

    assert len(channels) == 1
    channel = channels[0]
    assert channel.name == "Foo"
    assert channel.local_name == "bar"
    assert channel.reg_format == "[$n] $t"


def _write_ban_and_ucache(tmp_path: Path) -> tuple[Path, Path]:
    ignores = tmp_path / "imc.ignores"
    ignores.write_text("#IGNORES\nrouter.bad\nworse@mud\n#END\n", encoding="latin-1")

    ucache = tmp_path / "imc.ucache"
    ucache.write_text(
        "\n".join(
            [
                "#UCACHE",
                "Name Test@Mud",
                "Sex 1",
                "Time 1690000000",
                "End",
                "#UCACHE",
                "Name Another@Mud",
                "Sex 2",
                "Time 1680000000",
                "End",
                "#END",
            ]
        )
        + "\n",
        encoding="latin-1",
    )

    return ignores, ucache


def _install_fake_imc_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    import mud.imc.network as network

    class DummySocket:
        def close(self) -> None:
            pass

    def fake_connect(config: Mapping[str, str]) -> network.IMCConnection:
        handshake = network.build_handshake_frame(config)
        port_raw = config.get("ServerPort", "0")
        try:
            port = int(port_raw) if port_raw else 0
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            port = 0
        return network.IMCConnection(
            socket=DummySocket(),
            address=(config.get("ServerAddr", ""), port),
            handshake_frame=handshake,
            handshake_complete=True,
        )

    monkeypatch.setattr("mud.imc.connect_and_handshake", fake_connect)


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


def test_load_channel_history_limits_entries(tmp_path):
    channel = IMCChannel(
        name="IMC2",
        local_name="QuickMud",
        level=101,
        reg_format="[$n] $t",
        emote_format="* $n $t",
        social_format="[$n socials] $t",
    )
    history_dir = tmp_path
    history_path = history_dir / "QuickMud.hist"
    raw_entries = [f"[{i:02d}] stored" for i in range(IMC_HISTORY_LIMIT + 5)]
    serialized: list[str] = ["", "   ", "\t"]
    for idx, entry in enumerate(raw_entries):
        if idx == 0:
            serialized.append(f"   {entry}")
        elif idx == 1:
            serialized.append(f"{entry}~")
        else:
            serialized.append(entry)
        if idx < len(raw_entries) - 1:
            serialized.append("  ")
    serialized.append("")
    history_path.write_text("\n".join(serialized) + "\n", encoding="latin-1")

    history = _load_channel_history([channel], history_dir)

    assert history == {"QuickMud": raw_entries[:IMC_HISTORY_LIMIT]}
    assert all(not line.endswith("~") for line in history["QuickMud"])
    assert all(line == line.lstrip() for line in history["QuickMud"])
    assert not history_path.exists()


def test_save_channel_history_writes_per_channel(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    history_dir.mkdir()

    channel = IMCChannel(
        name="IMC2",
        local_name="QuickMud",
        level=101,
        reg_format="[$n] $t",
        emote_format="* $n $t",
        social_format="[$n socials] $t",
    )
    empty_channel = IMCChannel(
        name="Other",
        local_name="OtherMud",
        level=101,
        reg_format="[$n] $t",
        emote_format="* $n $t",
        social_format="[$n socials] $t",
    )

    entries = [f"[{i:02d}] entry" for i in range(IMC_HISTORY_LIMIT)]
    stale_path = history_dir / "OtherMud.hist"
    stale_path.write_text("stale\n", encoding="latin-1")

    state = IMCState(
        config={},
        channels=[channel, empty_channel],
        helps={},
        commands={},
        packet_handlers={},
        connected=False,
        config_path=tmp_path / "imc.config",
        channels_path=tmp_path / "imc.channels",
        help_path=tmp_path / "imc.help",
        commands_path=tmp_path / "imc.commands",
        ignores_path=tmp_path / "imc.ignores",
        ucache_path=tmp_path / "imc.ucache",
        history_dir=history_dir,
        router_bans=[],
        colors={},
        who_template=None,
        user_cache={},
        channel_history={"QuickMud": entries, "OtherMud": []},
        connection=None,
        outgoing_queue=[],
    )

    save_channel_history(state)

    history_file = history_dir / "QuickMud.hist"
    assert history_file.read_text(encoding="latin-1") == "\n".join(entries) + "\n"
    assert not stale_path.exists()


def test_append_channel_history_formats_and_limits_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import mud.imc.__init__ as imc_module

    fixed_time = time.struct_time((1997, 12, 3, 4, 5, 0, 0, 337, -1))
    monkeypatch.setattr(imc_module.time, "time", lambda: 0, raising=False)
    monkeypatch.setattr(imc_module.time, "localtime", lambda _: fixed_time, raising=False)

    channel = IMCChannel(
        name="IMC2",
        local_name="QuickMud",
        level=101,
        reg_format="[$n] $t",
        emote_format="* $n $t",
        social_format="[$n socials] $t",
    )
    state = IMCState(
        config={},
        channels=[channel],
        helps={},
        commands={},
        packet_handlers={},
        connected=True,
        config_path=tmp_path / "imc.config",
        channels_path=tmp_path / "imc.channels",
        help_path=tmp_path / "imc.help",
        commands_path=tmp_path / "imc.commands",
        ignores_path=tmp_path / "imc.ignores",
        ucache_path=tmp_path / "imc.ucache",
        history_dir=tmp_path,
        router_bans=[],
        colors={},
        who_template=None,
        user_cache={},
        channel_history={"QuickMud": []},
        connection=None,
        outgoing_queue=[],
    )

    state.append_channel_history("QuickMud", "First")
    assert state.channel_history["QuickMud"] == ["~R[12/03 04:05] ~GFirst"]

    for index in range(IMC_HISTORY_LIMIT):
        state.append_channel_history("QuickMud", f"Msg {index}")

    history = state.channel_history["QuickMud"]
    assert len(history) == IMC_HISTORY_LIMIT
    assert history[0].endswith("Msg 0")
    assert history[-1].endswith(f"Msg {IMC_HISTORY_LIMIT - 1}")

    state.append_channel_history("Unknown", "Ignored")
    assert "Unknown" not in state.channel_history


def test_append_channel_history_logs_when_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import mud.imc.__init__ as imc_module

    fixed_time = time.struct_time((2001, 2, 3, 4, 5, 0, 0, 34, -1))
    monkeypatch.setattr(imc_module.time, "time", lambda: 0, raising=False)
    monkeypatch.setattr(imc_module.time, "localtime", lambda _: fixed_time, raising=False)

    channel = IMCChannel(
        name="IMC2",
        local_name="QuickMud",
        level=101,
        reg_format="[$n] $t",
        emote_format="* $n $t",
        social_format="[$n socials] $t",
        flags=IMCCHAN_LOG,
    )
    colors = {
        "red": IMCColor(name="Red", mud_tag="{R", imc_tag="~R"),
        "green": IMCColor(name="Green", mud_tag="{G", imc_tag="~G"),
    }
    state = IMCState(
        config={},
        channels=[channel],
        helps={},
        commands={},
        packet_handlers={},
        connected=True,
        config_path=tmp_path / "imc.config",
        channels_path=tmp_path / "imc.channels",
        help_path=tmp_path / "imc.help",
        commands_path=tmp_path / "imc.commands",
        ignores_path=tmp_path / "imc.ignores",
        ucache_path=tmp_path / "imc.ucache",
        history_dir=tmp_path,
        router_bans=[],
        colors=colors,
        who_template=None,
        user_cache={},
        channel_history={"QuickMud": []},
        connection=None,
        outgoing_queue=[],
    )

    state.append_channel_history("QuickMud", "Logged message")

    log_path = tmp_path / "QuickMud.log"
    assert log_path.read_text(encoding="latin-1") == "[02/03 04:05] Logged message\n"
    assert state.channel_history["QuickMud"][-1].endswith("Logged message")


def test_imc_channel_command_shows_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(_default_imc_dir() / "imc.commands"))
    monkeypatch.setenv("IMC_HISTORY_DIR", str(tmp_path))
    history_entry = "~R[12/03 04:05] ~GFirst"
    (tmp_path / "quickmud.hist").write_text(f"{history_entry}\n", encoding="latin-1")
    reset_state()

    state = maybe_open_socket(force_reload=True)
    assert state is not None
    channel = state.channels[0]

    ch = create_test_character("IMCImm", 3001)
    ch.level = 200
    ch.trust = 200
    ch.imc_permission = "Imp"

    response = process_command(ch, channel.local_name)
    assert f"~cThe last 1 {channel.local_name} messages:\r\n" in response
    assert history_entry in response

    reply = process_command(ch, f"{channel.local_name} message")
    assert "IMC channel messaging is not available" in reply


def _enable_imc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[IMCState, IMCChannel]:
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_HISTORY_DIR", str(tmp_path))
    _install_fake_imc_connection(monkeypatch)
    reset_state()
    state = maybe_open_socket(force_reload=True)
    assert state is not None
    assert state.channels
    return state, state.channels[0]


def _prepare_imc_character(state: IMCState) -> Any:
    initialize_world("area/area.lst")
    load_socials("data/socials.json")
    ch = create_test_character("IMCSpeaker", 3001)
    ch.level = 200
    ch.trust = 200
    ch.imc_permission = "Imp"
    return ch


def test_imc_channel_command_sends_message(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, channel = _enable_imc(monkeypatch, tmp_path)
    ch = _prepare_imc_character(state)
    ch.imc_listen = {channel.local_name}

    response = process_command(ch, f"{channel.local_name} Hello IMC")

    assert response == ""
    assert state.outgoing_queue, "channel send should queue a router frame"
    frame = state.outgoing_queue[-1]
    parsed = parse_frame(frame)
    assert parsed.type == "ice-msg-b"
    assert parsed.target == "*@*"
    assert parsed.source == f"{ch.name}@{state.config.get('LocalName')}"
    payload = parsed.message
    assert f"channel={channel.name}" in payload
    assert "text=Hello IMC" in payload
    assert "emote=0" in payload
    assert payload.endswith("echo=1")


def test_imc_channel_command_sends_emote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, channel = _enable_imc(monkeypatch, tmp_path)
    ch = _prepare_imc_character(state)
    ch.imc_listen = {channel.local_name}

    response = process_command(ch, f"{channel.local_name} ,waves")

    assert response == ""
    assert state.outgoing_queue, "channel emote should queue a router frame"
    frame = state.outgoing_queue[-1]
    parsed = parse_frame(frame)
    assert parsed.type == "ice-msg-b"
    assert parsed.target == "*@*"
    payload = parsed.message
    assert f"channel={channel.name}" in payload
    assert "text=waves" in payload
    assert "emote=1" in payload


def test_imc_channel_command_sends_social(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, channel = _enable_imc(monkeypatch, tmp_path)
    ch = _prepare_imc_character(state)
    ch.imc_listen = {channel.local_name}

    response = process_command(ch, f"{channel.local_name} @wave Ruff@OtherMud")

    assert response == ""
    assert state.outgoing_queue, "channel social should queue a router frame"
    frame = state.outgoing_queue[-1]
    parsed = parse_frame(frame)
    assert parsed.type == "ice-msg-b"
    assert parsed.target == "*@*"
    payload = parsed.message
    assert f"channel={channel.name}" in payload
    assert "emote=2" in payload
    assert "text=IMCSpeaker waves goodbye to Ruff@OtherMud." in payload


def test_imc_channel_command_requires_listen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, channel = _enable_imc(monkeypatch, tmp_path)
    ch = _prepare_imc_character(state)

    blocked = process_command(ch, f"{channel.local_name} Hello")

    assert "not currently listening" in blocked
    assert "imclisten" in blocked
    assert not state.outgoing_queue

    ch.imc_listen = {channel.local_name}
    allowed = process_command(ch, f"{channel.local_name} Hello")

    assert allowed == ""
    assert state.outgoing_queue


def test_imc_channel_command_toggles_logging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state, channel = _enable_imc(monkeypatch, tmp_path)
    ch = _prepare_imc_character(state)

    enable_message = process_command(ch, f"{channel.local_name} log")

    assert "~RFile logging enabled" in enable_message
    assert state.channels[0].flags & IMCCHAN_LOG
    contents = state.channels_path.read_text(encoding="latin-1")
    assert f"ChanFlags {IMCCHAN_LOG}" in contents

    disable_message = process_command(ch, f"{channel.local_name} log")

    assert "~GFile logging disabled" in disable_message
    assert not (state.channels[0].flags & IMCCHAN_LOG)
    contents = state.channels_path.read_text(encoding="latin-1")
    assert "ChanFlags 0" in contents
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
    _install_fake_imc_connection(monkeypatch)
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
    _install_fake_imc_connection(monkeypatch)
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
    _install_fake_imc_connection(monkeypatch)
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
    _install_fake_imc_connection(monkeypatch)
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
    _install_fake_imc_connection(monkeypatch)
    reset_state()

    initialize_world("area/area.lst")

    state = get_state()
    assert state is not None and state.connected is True
    assert state.config["LocalName"] == "QuickMUD"
    assert state.channels and state.channels[0].name == "IMC2"
    assert "imc2" in state.helps
    assert state.connection is not None
    assert state.connection.handshake_frame.startswith("PW QuickMUD")


def test_idle_pump_runs_when_enabled(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    _install_fake_imc_connection(monkeypatch)
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


class _FakeSocket:
    def __init__(self, chunks: list[bytes], block_on_empty: bool = False):
        self._chunks = list(chunks)
        self._block_on_empty = block_on_empty
        self.sent: list[bytes] = []
        self.closed = False
        self._fd = id(self) & 0xFFFF

    def recv(self, _size: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)
        if self._block_on_empty:
            raise BlockingIOError
        return b""

    def sendall(self, payload: bytes) -> None:
        self.sent.append(payload)

    def close(self) -> None:
        self.closed = True
        self._fd = -1

    def fileno(self) -> int:
        return self._fd


def test_pump_idle_processes_pending_packets(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))

    fake_socket = _FakeSocket([b"who QuickMUD *@* :payload\n"], block_on_empty=True)

    def fake_select(read_list, _write_list, _error_list, _timeout):
        return list(read_list), [], []

    monkeypatch.setattr("mud.imc.select.select", fake_select)

    import mud.imc.network as network

    connect_calls: list[Mapping[str, str]] = []

    def fake_connect(config: Mapping[str, str]) -> network.IMCConnection:
        connect_calls.append(config)
        frame = network.build_handshake_frame(config)
        port_raw = config.get("ServerPort", "0")
        try:
            port = int(port_raw) if port_raw else 0
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            port = 0
        return network.IMCConnection(
            socket=fake_socket,
            address=(config.get("ServerAddr", ""), port),
            handshake_frame=frame,
            handshake_complete=True,
        )

    monkeypatch.setattr("mud.imc.connect_and_handshake", fake_connect)

    reset_state()
    maybe_open_socket(force_reload=True)
    state = get_state()
    assert state is not None
    assert connect_calls, "connect_and_handshake should be invoked"
    assert state.connected is True
    assert state.connection is not None

    handled: list[str] = []

    def recorder(packet: IMCPacket) -> None:
        handled.append(packet.payload["raw"])  # type: ignore[index]

    state.packet_handlers["who"] = recorder

    pump_idle()

    assert handled == ["who QuickMUD *@* :payload"]
    assert fake_socket.closed is False


def test_pump_idle_flushes_outgoing_queue(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))

    fake_socket = _FakeSocket([], block_on_empty=True)

    def fake_select(read_list, write_list, _error_list, _timeout):
        return [], list(write_list), []

    monkeypatch.setattr("mud.imc.select.select", fake_select)

    import mud.imc.network as network

    def fake_connect(config: Mapping[str, str]) -> network.IMCConnection:
        frame = network.build_handshake_frame(config)
        port_raw = config.get("ServerPort", "0")
        try:
            port = int(port_raw) if port_raw else 0
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            port = 0
        return network.IMCConnection(
            socket=fake_socket,
            address=(config.get("ServerAddr", ""), port),
            handshake_frame=frame,
            handshake_complete=True,
        )

    monkeypatch.setattr("mud.imc.connect_and_handshake", fake_connect)

    reset_state()
    maybe_open_socket(force_reload=True)
    state = get_state()
    assert state is not None
    assert state.connection is not None

    state.outgoing_queue.extend(
        [
            "chat QuickMUD *@* :Hello there",
            "who QuickMUD *@* :payload",
        ]
    )

    pump_idle()

    assert fake_socket.sent == [
        b"chat QuickMUD *@* :Hello there\n",
        b"who QuickMUD *@* :payload\n",
    ]
    assert state.outgoing_queue == []
    assert fake_socket.closed is False


def test_pump_idle_refreshes_user_cache(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    ignores = tmp_path / "imc.ignores"
    ignores.write_text("#IGNORES\n#END\n", encoding="latin-1")

    ucache = tmp_path / "imc.ucache"
    now = 1_700_000_000
    stale_seconds = 60 * 60 * 24 * 30
    fresh_time = now - 60
    stale_time = now - stale_seconds - 1
    ucache.write_text(
        "\n".join(
            [
                "#UCACHE",
                "Name Fresh@Mud",
                "Sex  2",
                f"Time {fresh_time}",
                "End",
                "",
                "#UCACHE",
                "Name Old@Mud",
                "Sex  1",
                f"Time {stale_time}",
                "End",
                "",
                "#END",
            ]
        )
        + "\n",
        encoding="latin-1",
    )

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_IGNORES_PATH", str(ignores))
    monkeypatch.setenv("IMC_UCACHE_PATH", str(ucache))
    _install_fake_imc_connection(monkeypatch)

    monkeypatch.setattr("mud.imc.select.select", lambda *_: ([], [], []))
    monkeypatch.setattr("mud.imc.time.time", lambda: now)

    reset_state()
    maybe_open_socket(force_reload=True)
    state = get_state()
    assert state is not None

    # Force refresh on next idle pulse
    state.ucache_refresh_deadline = state.idle_pulses + 1

    pump_idle()

    refreshed = get_state()
    assert refreshed is not None
    assert "fresh@mud" in refreshed.user_cache
    assert refreshed.user_cache["fresh@mud"].last_seen == fresh_time
    assert "old@mud" not in refreshed.user_cache

    expected_deadline = refreshed.idle_pulses + _UCACHE_REFRESH_INTERVAL
    assert refreshed.ucache_refresh_deadline == expected_deadline

    contents = ucache.read_text(encoding="latin-1")
    assert "Fresh@Mud" in contents
    assert "Old@Mud" not in contents
    assert contents.strip().endswith("#END")


def test_pump_idle_handles_socket_disconnect(monkeypatch, tmp_path):
    config, channels, helps = _write_imc_fixture(tmp_path)
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))

    disconnecting_socket = _FakeSocket([b""], block_on_empty=False)
    replacement_socket = _FakeSocket([], block_on_empty=True)

    def fake_select(read_list, _write_list, _error_list, _timeout):
        return list(read_list), [], []

    monkeypatch.setattr("mud.imc.select.select", fake_select)

    import mud.imc.network as network
    from mud.imc import _KEEPALIVE_INTERVAL

    sockets = [disconnecting_socket, replacement_socket]

    connect_calls: list[Mapping[str, str]] = []

    def fake_connect(config: Mapping[str, str]) -> network.IMCConnection:
        connect_calls.append(config)
        frame = network.build_handshake_frame(config)
        port_raw = config.get("ServerPort", "0")
        try:
            port = int(port_raw) if port_raw else 0
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            port = 0
        sock = sockets.pop(0)
        return network.IMCConnection(
            socket=sock,
            address=(config.get("ServerAddr", ""), port),
            handshake_frame=frame,
            handshake_complete=True,
        )

    monkeypatch.setattr("mud.imc.connect_and_handshake", fake_connect)

    reset_state()
    maybe_open_socket(force_reload=True)
    state = get_state()
    assert state is not None
    assert connect_calls, "connect_and_handshake should be invoked"

    state.idle_pulses = _KEEPALIVE_INTERVAL - 1
    state.last_keepalive_pulse = 0

    pump_idle()

    assert disconnecting_socket.closed is True
    assert state.connection is not None
    assert state.connection.socket is replacement_socket
    assert replacement_socket.sent, "keepalive frame should be sent after reconnect"
    assert b"keepalive-request" in replacement_socket.sent[0]
@pytest.fixture
def imc_default_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    root = _default_imc_dir()
    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(root / "imc.config"))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(root / "imc.channels"))
    monkeypatch.setenv("IMC_HELP_PATH", str(root / "imc.help"))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(root / "imc.commands"))
    monkeypatch.setenv("IMC_COLOR_PATH", str(root / "imc.color"))
    monkeypatch.setenv("IMC_WHO_PATH", str(root / "imc.who"))
    reset_state()
    try:
        yield
    finally:
        reset_state()


def test_maybe_open_socket_loads_commands(imc_default_environment: None) -> None:
    state = maybe_open_socket(force_reload=True)
    assert state is not None

    command = state.commands["imc"]
    assert command.function == "imc_other"
    assert command.permission == "Mort"
    assert command.requires_connection is False

    alias = state.commands["ichan"]
    assert alias.name == "imclisten"
    assert "ichan" in alias.aliases


def test_maybe_open_socket_registers_packet_handlers(
    imc_default_environment: None,
) -> None:
    state = maybe_open_socket(force_reload=True)
    assert state is not None
    packet = IMCPacket(type="who", payload={})

    state.dispatch_packet(packet)

    assert packet.handled_by == "imc_recv_who"
    assert state.packet_handlers["keepalive-request"].__name__ == "imc_send_keepalive"


def test_maybe_open_socket_loads_bans(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config, channels, helps = _write_imc_fixture(tmp_path)
    ignores, ucache = _write_ban_and_ucache(tmp_path)

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(_default_imc_dir() / "imc.commands"))
    monkeypatch.setenv("IMC_IGNORES_PATH", str(ignores))
    monkeypatch.setenv("IMC_UCACHE_PATH", str(ucache))
    monkeypatch.setenv("IMC_HISTORY_DIR", str(tmp_path))
    _install_fake_imc_connection(monkeypatch)

    reset_state()
    try:
        state = maybe_open_socket(force_reload=True)
        assert state is not None

        assert [ban.name for ban in state.router_bans] == ["router.bad", "worse@mud"]

        key = "test@mud"
        assert key in state.user_cache
        entry = state.user_cache[key]
        assert entry.gender == 1
        assert entry.last_seen == 1_690_000_000

        state.idle_pulses = 7
        state.ucache_refresh_deadline = 99_999
        entry.last_seen = 1_690_009_999

        reloaded = maybe_open_socket(force_reload=True)
        assert reloaded is not None
        assert reloaded.idle_pulses == 7
        assert reloaded.ucache_refresh_deadline == 99_999
        assert reloaded.user_cache[key].last_seen == 1_690_009_999
    finally:
        reset_state()


def test_maybe_open_socket_loads_color_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config, channels, helps = _write_imc_fixture(tmp_path)
    color_path = tmp_path / "imc.color"
    color_path.write_text(
        "\n".join(
            [
                "#COLOR",
                "Name Alert",
                "Mudtag {R",
                "IMCtag ~R",
                "End",
                "#COLOR",
                "Name Calm",
                "Mudtag {g",
                "IMCtag ~g",
                "End",
                "#END",
            ]
        )
        + "\n",
        encoding="latin-1",
    )

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(_default_imc_dir() / "imc.commands"))
    monkeypatch.setenv("IMC_COLOR_PATH", str(color_path))
    _install_fake_imc_connection(monkeypatch)
    reset_state()

    state = maybe_open_socket(force_reload=True)
    assert state is not None
    assert "alert" in state.colors
    entry = state.colors["alert"]
    assert entry.name == "Alert"
    assert entry.mud_tag == "{R"
    assert entry.imc_tag == "~R"

    calm = state.colors["calm"]
    assert calm.mud_tag == "{g"
    assert calm.imc_tag == "~g"


def test_maybe_open_socket_loads_who_template(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config, channels, helps = _write_imc_fixture(tmp_path)
    who_path = tmp_path / "imc.who"
    who_path.write_text(
        "\n".join(
            [
                "Head: ~RHead",
                "Tail: ~GTail",
                "Plrline: player",
                "Immline: immortal",
                "Plrheader: players",
                "Immheader: immortals",
                "Master: master template",
            ]
        )
        + "\n",
        encoding="latin-1",
    )

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(_default_imc_dir() / "imc.commands"))
    monkeypatch.setenv("IMC_WHO_PATH", str(who_path))
    _install_fake_imc_connection(monkeypatch)
    reset_state()

    state = maybe_open_socket(force_reload=True)
    assert state is not None
    template = state.who_template
    assert template is not None
    assert template.head == "~RHead"
    assert template.tail == "~GTail"
    assert template.plrline == "player"
    assert template.immline == "immortal"
    assert template.plrheader == "players"
    assert template.immheader == "immortals"
    assert template.master == "master template"


def test_maybe_open_socket_opens_connection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config, channels, helps = _write_imc_fixture(tmp_path)

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))

    captured_peers: list[socket.socket] = []

    def fake_create_connection(address: tuple[str, int]) -> socket.socket:
        sock1, sock2 = socket.socketpair()
        captured_peers.append(sock2)
        return sock1

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)

    reset_state()
    state = maybe_open_socket(force_reload=True)
    assert state is not None
    assert state.connected is True
    assert state.connection is not None
    assert state.connection.address == ("router.quickmud", 4000)

    peer = captured_peers.pop()
    try:
        handshake_line = peer.recv(256).decode("latin-1").strip()
    finally:
        peer.close()

    assert handshake_line == "PW QuickMUD clientpw version=2 autosetup serverpw SHA256"
    assert state.connection.handshake_frame == handshake_line

    reset_state()


def test_disconnect_fallback_switches_auth_mode(monkeypatch, tmp_path):
    import mud.imc.network as network

    config, channels, helps = _write_imc_fixture(tmp_path)
    ignores, ucache = _write_ban_and_ucache(tmp_path)

    monkeypatch.setenv("IMC_ENABLED", "true")
    monkeypatch.setenv("IMC_CONFIG_PATH", str(config))
    monkeypatch.setenv("IMC_CHANNELS_PATH", str(channels))
    monkeypatch.setenv("IMC_HELP_PATH", str(helps))
    monkeypatch.setenv("IMC_COMMANDS_PATH", str(_default_imc_dir() / "imc.commands"))
    monkeypatch.setenv("IMC_IGNORES_PATH", str(ignores))
    monkeypatch.setenv("IMC_UCACHE_PATH", str(ucache))
    monkeypatch.setenv("IMC_HISTORY_DIR", str(tmp_path))
    monkeypatch.setenv("IMC_COLOR_PATH", str(_default_imc_dir() / "imc.color"))
    monkeypatch.setenv("IMC_WHO_PATH", str(_default_imc_dir() / "imc.who"))

    class DummySocket:
        def close(self) -> None:
            pass

    attempts: list[str] = []

    def conditional_connect(cfg: dict[str, str]) -> network.IMCConnection:
        attempts.append(cfg.get("SHA256", ""))
        if cfg.get("SHA256") != "0":
            raise network.IMCConnectionError("router refused SHA-256 handshake")
        port_raw = cfg.get("ServerPort", "0")
        try:
            port = int(port_raw) if port_raw else 0
        except ValueError:
            port = 0
        return network.IMCConnection(
            socket=DummySocket(),
            address=(cfg.get("ServerAddr", ""), port),
            handshake_frame="PW",
            handshake_complete=True,
        )

    monkeypatch.setattr("mud.imc.connect_and_handshake", conditional_connect)

    reset_state()
    try:
        state = maybe_open_socket(force_reload=True)
        assert state is not None
        assert state.connected is False
        assert state.config.get("SHA256") == "1"

        for _ in range(4):
            _handle_disconnect(state)

        assert state.config.get("SHA256") == "0"
        assert "SHA256         0" in config.read_text()
        assert state.reconnect_attempts == 0
        assert state.reconnect_abandoned is False

        _handle_disconnect(state)

        assert state.connected is True
        assert state.connection is not None
        assert state.reconnect_attempts == 0
        assert attempts.count("1") >= 4
        assert attempts[-1] == "0"
    finally:
        reset_state()
