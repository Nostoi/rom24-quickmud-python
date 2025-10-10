from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import os
import select
import time

from .commands import (
    IMCCommand,
    IMCPacket,
    PacketHandler,
    build_default_packet_handlers,
    load_command_table,
)
from .network import (
    IMCConnection,
    IMCConnectionError,
    autoconnect_enabled,
    connect_and_handshake,
)

@dataclass(frozen=True)
class IMCChannel:
    """Snapshot of an IMC channel entry from `imc.channels`."""

    name: str
    local_name: str
    level: Optional[int]
    reg_format: str
    emote_format: str
    social_format: str


@dataclass(frozen=True)
class IMCHelp:
    """Single IMC help entry loaded from `imc.help`."""

    name: str
    permission: str
    text: str


@dataclass(frozen=True)
class IMCBan:
    """Router ban entry from `imc.ignores`."""

    name: str


@dataclass(frozen=True)
class IMCColor:
    """Single IMC color mapping from `imc.color`."""

    name: str
    mud_tag: str
    imc_tag: str


@dataclass(frozen=True)
class IMCWhoTemplate:
    """Who-list template loaded from `imc.who`."""

    head: str
    tail: str
    plrline: str
    immline: str
    plrheader: str
    immheader: str
    master: str


@dataclass
class IMCUserCacheEntry:
    """Cached router metadata from `imc.ucache`."""

    name: str
    gender: Optional[int]
    last_seen: int


@dataclass
class IMCState:
    """Runtime IMC state used by the Python port."""

    config: Dict[str, str]
    channels: List[IMCChannel]
    helps: Dict[str, IMCHelp]
    commands: Dict[str, IMCCommand]
    packet_handlers: Dict[str, PacketHandler]
    connected: bool
    config_path: Path
    channels_path: Path
    help_path: Path
    commands_path: Path
    ignores_path: Path
    ucache_path: Path
    history_dir: Path
    router_bans: List[IMCBan]
    colors: Dict[str, IMCColor]
    who_template: Optional[IMCWhoTemplate]
    user_cache: Dict[str, IMCUserCacheEntry]
    channel_history: Dict[str, List[str]]
    connection: Optional[IMCConnection]
    outgoing_queue: List[str]
    idle_pulses: int = 0
    ucache_refresh_deadline: int = 0
    color_path: Path | None = None
    who_path: Path | None = None
    incoming_buffer: str = ""
    last_keepalive_pulse: int = 0
    reconnect_attempts: int = 0
    reconnect_abandoned: bool = False

    def dispatch_packet(self, packet: IMCPacket) -> None:
        handler = self.packet_handlers.get(packet.type)
        if handler:
            handler(packet)


_state: Optional[IMCState] = None

_REQUIRED_CONFIG_FIELDS = {
    "LocalName",
    "ServerAddr",
    "ServerPort",
    "ClientPwd",
    "ServerPwd",
}

_MAX_READ_BYTES = 4096
_KEEPALIVE_INTERVAL = 60
_UCACHE_REFRESH_INTERVAL = 60 * 24  # Once per 24 in-game hours (pump runs once per tick minute)
_UCACHE_STALE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_imc_dir() -> Path:
    return _repo_root() / "imc"


def _resolve_path(env_name: str, default_filename: str) -> Path:
    override = os.getenv(env_name)
    if override:
        return Path(override)
    return _default_imc_dir() / default_filename


def _parse_config(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(path)

    config: Dict[str, str] = {}
    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line == "End":
                break
            if line.startswith("$"):
                # IMC Freedom exports sometimes wrap config in $IMCCONFIG/$END.
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            key, value = parts
            config[key] = value.strip()

    missing = sorted(field for field in _REQUIRED_CONFIG_FIELDS if not config.get(field))
    if missing:
        raise ValueError(f"IMC configuration missing required fields: {', '.join(missing)}")

    return config


def _config_truthy(config: Dict[str, str], key: str) -> bool:
    value = config.get(key)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _persist_config_value(path: Path, key: str, value: str) -> None:
    if not path.exists():
        return

    try:
        with path.open(encoding="latin-1") as handle:
            lines = handle.readlines()
    except OSError:
        return

    updated = False
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("$"):
            parts = stripped.split(maxsplit=1)
            if parts and parts[0] == key:
                new_lines.append(f"{key}         {value}\n")
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        for index, line in enumerate(new_lines):
            if line.strip() == "End":
                new_lines.insert(index, f"{key}         {value}\n")
                updated = True
                break
        if not updated:
            new_lines.append(f"{key}         {value}\n")

    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="latin-1") as handle:
        handle.writelines(new_lines)
    os.replace(tmp_path, path)


def _parse_channels(path: Path) -> List[IMCChannel]:
    if not path.exists():
        return []

    channels: List[IMCChannel] = []
    current: Dict[str, str] = {}

    def finalize() -> None:
        if "ChanName" not in current:
            return
        level_value = current.get("ChanLevel")
        try:
            level = int(level_value) if level_value is not None else None
        except ValueError:
            level = None
        channels.append(
            IMCChannel(
                name=current.get("ChanName", ""),
                local_name=current.get("ChanLocal", current.get("ChanName", "")),
                level=level,
                reg_format=current.get("ChanRegF", ""),
                emote_format=current.get("ChanEmoF", ""),
                social_format=current.get("ChanSocF", ""),
            )
        )

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("#"):
                if upper == "#END":
                    break
                if upper in {"#IMCCHAN", "#CHANNEL"}:
                    finalize()
                    current = {}
                continue
            if line == "End":
                finalize()
                current = {}
                continue
            key, *value = line.split(maxsplit=1)
            current[key] = value[0].strip() if value else ""

    finalize()
    return channels


def _parse_helps(path: Path) -> Dict[str, IMCHelp]:
    if not path.exists():
        return {}

    helps: Dict[str, IMCHelp] = {}
    name: Optional[str] = None
    permission: str = ""
    text_lines: List[str] = []
    capturing_text = False

    def flush() -> None:
        nonlocal name, permission, text_lines, capturing_text
        if name:
            helps[name.lower()] = IMCHelp(name=name, permission=permission, text="\n".join(text_lines).strip())
        name = None
        permission = ""
        text_lines = []
        capturing_text = False

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped and capturing_text:
                text_lines.append("")
                continue
            if stripped.startswith("#"):
                upper = stripped.upper()
                if upper == "#HELP":
                    flush()
                elif upper == "#END":
                    break
                continue
            if stripped == "End":
                flush()
                continue
            if stripped.startswith("Name "):
                name = stripped[5:].strip()
                continue
            if stripped.startswith("Perm "):
                permission = stripped[5:].strip()
                continue
            if stripped.startswith("Text "):
                text_lines = [stripped[5:].rstrip()]
                capturing_text = True
                continue
            if capturing_text:
                text_lines.append(line.rstrip("\n"))

    flush()
    return helps


def _parse_color_table(path: Path) -> Dict[str, IMCColor]:
    if not path.exists():
        return {}

    colors: Dict[str, IMCColor] = {}
    current: Dict[str, str] = {}

    def store_current() -> None:
        if "Name" not in current:
            return
        name = current.get("Name", "")
        mud_tag = current.get("Mudtag", "")
        imc_tag = current.get("IMCtag", "")
        if name:
            colors[name.lower()] = IMCColor(name=name, mud_tag=mud_tag, imc_tag=imc_tag)

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("#"):
                if upper == "#COLOR":
                    current = {}
                elif upper == "#END":
                    break
                continue
            if line == "End":
                store_current()
                current = {}
                continue
            key, *value = line.split(maxsplit=1)
            current[key] = value[0].strip() if value else ""

    store_current()
    return colors


def _parse_who_template(path: Path) -> Optional[IMCWhoTemplate]:
    if not path.exists():
        return None

    head = ""
    tail = ""
    plrline = ""
    immline = ""
    plrheader = ""
    immheader = ""
    master = ""

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized = key.strip().lower()
            content = value.lstrip()
            if normalized == "head":
                head = content
            elif normalized == "tail":
                tail = content
            elif normalized == "plrline":
                plrline = content
            elif normalized == "immline":
                immline = content
            elif normalized == "plrheader":
                plrheader = content
            elif normalized == "immheader":
                immheader = content
            elif normalized == "master":
                master = content

    if not any([head, tail, plrline, immline, plrheader, immheader, master]):
        return None

    return IMCWhoTemplate(
        head=head,
        tail=tail,
        plrline=plrline,
        immline=immline,
        plrheader=plrheader,
        immheader=immheader,
        master=master,
    )


def _parse_router_bans(path: Path) -> List[IMCBan]:
    if not path.exists():
        return []

    bans: List[IMCBan] = []
    with path.open(encoding="latin-1") as handle:
        header = handle.readline().strip()
        if header.upper() != "#IGNORES":
            return []
        for raw in handle:
            name = raw.strip()
            if not name:
                continue
            if name.upper() == "#END":
                break
            bans.append(IMCBan(name=name))
    return bans


def _parse_ucache(path: Path, previous: Optional[Dict[str, IMCUserCacheEntry]] = None) -> Dict[str, IMCUserCacheEntry]:
    if not path.exists():
        return previous.copy() if previous else {}

    entries: Dict[str, IMCUserCacheEntry] = {}
    current_name: Optional[str] = None
    gender: Optional[int] = None
    last_seen = 0

    def flush() -> None:
        nonlocal current_name, gender, last_seen
        if not current_name:
            return
        key = current_name.lower()
        if previous and key in previous:
            # Preserve runtime counters recorded on the existing entry.
            entries[key] = previous[key]
        else:
            entries[key] = IMCUserCacheEntry(name=current_name, gender=gender, last_seen=last_seen)
        current_name = None
        gender = None
        last_seen = 0

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("#"):
                if upper == "#UCACHE":
                    flush()
                    current_name = None
                    gender = None
                    last_seen = 0
                elif upper == "#END":
                    break
                continue
            if line == "End":
                flush()
                continue
            key, *value = line.split(maxsplit=1)
            data = value[0].strip() if value else ""
            if key.lower() == "name":
                current_name = data
            elif key.lower() == "sex":
                try:
                    gender = int(data)
                except ValueError:
                    gender = None
            elif key.lower() == "time":
                try:
                    last_seen = int(data)
                except ValueError:
                    last_seen = 0

    flush()

    if previous:
        # Ensure runtime entries survive even if absent from disk.
        for key, entry in previous.items():
            entries.setdefault(key, entry)

    return entries


def _load_channel_history(channels: List[IMCChannel], history_dir: Path) -> Dict[str, List[str]]:
    history: Dict[str, List[str]] = {}
    for channel in channels:
        if not channel.local_name:
            continue
        path = history_dir / f"{channel.local_name}.hist"
        if not path.exists():
            continue
        with path.open(encoding="latin-1") as handle:
            lines = [line.rstrip("\n") for line in handle]
        history[channel.local_name.lower()] = [line for line in lines if line]
    return history


def imc_enabled() -> bool:
    """Feature flag for IMC. Disabled by default."""

    return os.getenv("IMC_ENABLED", "false").lower() in {"1", "true", "yes"}


def reset_state() -> None:
    """Helper for tests to clear cached IMC state."""

    global _state
    if _state and _state.connection:
        _state.connection.close()
    _state = None


def get_state() -> Optional[IMCState]:
    return _state


def maybe_open_socket(force_reload: bool = False) -> Optional[IMCState]:
    """Load configuration tables when IMC is enabled."""

    if not imc_enabled():
        return None

    global _state

    config_path = _resolve_path("IMC_CONFIG_PATH", "imc.config")
    channels_path = _resolve_path("IMC_CHANNELS_PATH", "imc.channels")
    help_path = _resolve_path("IMC_HELP_PATH", "imc.help")
    commands_path = _resolve_path("IMC_COMMANDS_PATH", "imc.commands")
    ignores_path = _resolve_path("IMC_IGNORES_PATH", "imc.ignores")
    ucache_path = _resolve_path("IMC_UCACHE_PATH", "imc.ucache")
    color_path = _resolve_path("IMC_COLOR_PATH", "imc.color")
    who_path = _resolve_path("IMC_WHO_PATH", "imc.who")
    history_dir = Path(os.getenv("IMC_HISTORY_DIR", str(_default_imc_dir())))

    if (
        _state
        and _state.connected
        and not force_reload
        and _state.config_path == config_path
        and _state.channels_path == channels_path
        and _state.help_path == help_path
        and _state.commands_path == commands_path
        and _state.ignores_path == ignores_path
        and _state.ucache_path == ucache_path
        and _state.history_dir == history_dir
        and _state.color_path == color_path
        and _state.who_path == who_path
    ):
        return _state

    previous_state = _state
    commands = load_command_table(commands_path)
    config = _parse_config(config_path)
    channels = _parse_channels(channels_path)
    helps = _parse_helps(help_path)
    colors = _parse_color_table(color_path)
    who_template = _parse_who_template(who_path)
    packet_handlers = build_default_packet_handlers()
    router_bans = _parse_router_bans(ignores_path)
    previous_cache = previous_state.user_cache if previous_state else None
    user_cache = _parse_ucache(ucache_path, previous_cache)
    channel_history = _load_channel_history(channels, history_dir)

    idle_pulses = previous_state.idle_pulses if previous_state else 0
    if previous_state and not force_reload:
        ucache_refresh_deadline = previous_state.ucache_refresh_deadline
    else:
        ucache_refresh_deadline = idle_pulses + _UCACHE_REFRESH_INTERVAL
    autoconnect = autoconnect_enabled(config)
    connection: Optional[IMCConnection] = None
    connected = False

    if autoconnect:
        if (
            previous_state
            and previous_state.connected
            and not force_reload
            and previous_state.connection
        ):
            connection = previous_state.connection
            connected = previous_state.connected
        else:
            if previous_state and previous_state.connection:
                previous_state.connection.close()
            try:
                connection = connect_and_handshake(config)
                connected = connection.handshake_complete
            except IMCConnectionError:
                connection = None
                connected = False
    else:
        if previous_state and previous_state.connection:
            previous_state.connection.close()

    _state = IMCState(
        config=config,
        channels=channels,
        helps=helps,
        commands=commands,
        packet_handlers=packet_handlers,
        connected=connected,
        config_path=config_path,
        channels_path=channels_path,
        help_path=help_path,
        commands_path=commands_path,
        ignores_path=ignores_path,
        ucache_path=ucache_path,
        history_dir=history_dir,
        router_bans=router_bans,
        colors=colors,
        who_template=who_template,
        user_cache=user_cache,
        channel_history=channel_history,
        connection=connection,
        idle_pulses=idle_pulses,
        ucache_refresh_deadline=ucache_refresh_deadline,
        color_path=color_path,
        who_path=who_path,
        outgoing_queue=list(previous_state.outgoing_queue) if previous_state else [],
        reconnect_attempts=previous_state.reconnect_attempts if previous_state else 0,
        reconnect_abandoned=previous_state.reconnect_abandoned if previous_state else False,
    )
    return _state


def _handle_disconnect(state: IMCState) -> None:
    """Close the current socket and try to re-establish the connection."""

    connection = state.connection
    if connection:
        connection.close()
    state.connection = None
    state.connected = False
    state.incoming_buffer = ""

    if not autoconnect_enabled(state.config) or state.reconnect_abandoned:
        return

    try:
        new_connection = connect_and_handshake(state.config)
    except IMCConnectionError:
        state.reconnect_attempts += 1
        if state.reconnect_attempts > 3:
            if _config_truthy(state.config, "SHA256"):
                state.config["SHA256"] = "0"
                _persist_config_value(state.config_path, "SHA256", "0")
                state.reconnect_attempts = 0
            else:
                state.reconnect_abandoned = True
        return

    state.connection = new_connection
    state.connected = new_connection.handshake_complete
    state.last_keepalive_pulse = max(0, state.idle_pulses - _KEEPALIVE_INTERVAL)
    state.reconnect_attempts = 0


def _dispatch_buffered_packets(state: IMCState, chunk: str) -> None:
    """Split router frames on newlines and hand them to registered handlers."""

    buffer = state.incoming_buffer + chunk
    lines = buffer.split("\n")
    if buffer.endswith("\n"):
        state.incoming_buffer = ""
    else:
        state.incoming_buffer = lines.pop()

    for raw_line in lines:
        line = raw_line.rstrip("\r").strip()
        if not line:
            continue
        packet_type = line.split(maxsplit=1)[0].lower()
        packet = IMCPacket(type=packet_type, payload={"raw": line})
        state.dispatch_packet(packet)


def _poll_router_socket(state: IMCState) -> None:
    """Read any queued bytes from the router and dispatch resulting packets."""

    connection = state.connection
    if not connection:
        return

    sock = getattr(connection, "socket", None)
    if sock is None:
        _handle_disconnect(state)
        return

    fileno_method = getattr(sock, "fileno", None)
    if fileno_method is None or not callable(fileno_method):
        # Test doubles without file descriptors cannot be polled.
        return

    try:
        if fileno_method() < 0:
            _handle_disconnect(state)
            return
    except (OSError, ValueError):
        _handle_disconnect(state)
        return

    try:
        readable, _, _ = select.select([sock], [], [], 0)
    except (OSError, ValueError):
        _handle_disconnect(state)
        return

    if not readable:
        return

    try:
        payload = sock.recv(_MAX_READ_BYTES)
    except BlockingIOError:
        return
    except OSError:
        _handle_disconnect(state)
        return

    if not payload:
        _handle_disconnect(state)
        return

    chunk = payload.decode("latin-1", errors="ignore")
    _dispatch_buffered_packets(state, chunk)


def _flush_outgoing_queue(state: IMCState) -> None:
    """Write queued frames to the router socket when it is writable."""

    if not state.outgoing_queue:
        return

    connection = state.connection
    if not connection:
        return

    sock = getattr(connection, "socket", None)
    if sock is None:
        _handle_disconnect(state)
        return

    fileno_method = getattr(sock, "fileno", None)
    if fileno_method is None or not callable(fileno_method):
        # Without a file descriptor we cannot poll writability; leave queue intact.
        return

    try:
        if fileno_method() < 0:
            _handle_disconnect(state)
            return
    except (OSError, ValueError):
        _handle_disconnect(state)
        return

    try:
        _, writable, _ = select.select([], [sock], [], 0)
    except (OSError, ValueError):
        _handle_disconnect(state)
        return

    if sock not in writable:
        return

    while state.outgoing_queue:
        frame = state.outgoing_queue[0]
        payload = frame if frame.endswith("\n") else f"{frame}\n"
        try:
            sock.sendall(payload.encode("latin-1"))
        except BlockingIOError:
            return
        except OSError:
            _handle_disconnect(state)
            return

        state.outgoing_queue.pop(0)

        if not state.outgoing_queue:
            break

        try:
            _, writable, _ = select.select([], [sock], [], 0)
        except (OSError, ValueError):
            _handle_disconnect(state)
            return

        if sock not in writable:
            return


def _save_user_cache(state: IMCState) -> None:
    """Persist the current IMC user cache to disk like ROM's imc_save_ucache."""

    path = state.ucache_path
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for entry in sorted(
        state.user_cache.values(), key=lambda item: (item.name or "").lower()
    ):
        entry_name = entry.name or ""
        try:
            gender = int(entry.gender) if entry.gender is not None else -1
        except (TypeError, ValueError):
            gender = -1
        try:
            last_seen = int(entry.last_seen)
        except (TypeError, ValueError):
            last_seen = 0
        lines.extend(
            [
                "#UCACHE",
                f"Name {entry_name}",
                f"Sex  {gender}",
                f"Time {last_seen}",
                "End",
                "",
            ]
        )
    lines.append("#END")
    path.write_text("\n".join(lines) + "\n", encoding="latin-1")


def _refresh_user_cache(state: IMCState) -> None:
    """Prune stale IMC user cache entries and reschedule the next refresh."""

    now = int(time.time())
    retained: Dict[str, IMCUserCacheEntry] = {}
    for key, entry in state.user_cache.items():
        try:
            last_seen = int(entry.last_seen)
        except (TypeError, ValueError):
            last_seen = 0
        if last_seen > 0 and now - last_seen < _UCACHE_STALE_SECONDS:
            retained[key] = entry
    state.user_cache = retained
    _save_user_cache(state)
    state.ucache_refresh_deadline = state.idle_pulses + _UCACHE_REFRESH_INTERVAL


def _send_keepalive(state: IMCState) -> None:
    """Emit a lightweight keepalive packet to mirror ROM's idle loop."""

    connection = state.connection
    if not connection:
        return

    sock = getattr(connection, "socket", None)
    if sock is None:
        _handle_disconnect(state)
        return

    local = state.config.get("LocalName", "*")
    frame = f"keepalive-request {local} *@* :ping"
    try:
        sock.sendall((frame + "\n").encode("latin-1"))
    except OSError:
        _handle_disconnect(state)
        return

    state.last_keepalive_pulse = state.idle_pulses


def pump_idle() -> None:
    """Mirror ROM's imc_loop() idle pump by tracking pulse cadence."""

    if not imc_enabled():
        return

    state = maybe_open_socket()
    if not state:
        return
    state.idle_pulses += 1

    if not state.connected or not state.connection:
        if autoconnect_enabled(state.config):
            _handle_disconnect(state)
        return

    if not state.connection.handshake_complete:
        return

    if (
        state.ucache_refresh_deadline
        and state.idle_pulses >= state.ucache_refresh_deadline
    ):
        _refresh_user_cache(state)

    _poll_router_socket(state)
    _flush_outgoing_queue(state)

    if (
        state.connected
        and state.connection
        and state.idle_pulses - state.last_keepalive_pulse >= _KEEPALIVE_INTERVAL
    ):
        _send_keepalive(state)
