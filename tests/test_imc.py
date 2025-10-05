from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path
import socket

import pytest

import mud.game_loop as game_loop
from mud.commands import process_command
from mud.imc import get_state, imc_enabled, maybe_open_socket, reset_state
from mud.imc.commands import IMCPacket
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

    monkeypatch.setattr("mud.imc.network.connect_and_handshake", fake_connect)


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
