from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Tuple


@dataclass(frozen=True)
class IMCCommand:
    """Single IMC command definition loaded from ``imc.commands``."""

    name: str
    function: str
    permission: str
    requires_connection: bool
    aliases: Tuple[str, ...] = ()


PacketHandler = Callable[["IMCPacket"], None]


@dataclass
class IMCPacket:
    """Minimal packet container used for handler registration tests."""

    type: str
    payload: Dict[str, Any] | None = None
    handled_by: str | None = None


def _normalise_key(value: str) -> str:
    return value.strip().lower()


def _finalise_command(fields: Dict[str, Any]) -> IMCCommand | None:
    name = fields.get("name")
    function = fields.get("function")
    permission = fields.get("permission")
    if not name or not function or not permission:
        return None
    aliases: Iterable[str] = fields.get("aliases", [])
    connected_value = fields.get("connected", 0)
    try:
        requires_connection = bool(int(connected_value))
    except (TypeError, ValueError):
        requires_connection = False
    return IMCCommand(
        name=name.strip(),
        function=function.strip(),
        permission=permission.strip(),
        requires_connection=requires_connection,
        aliases=tuple(alias.strip() for alias in aliases if alias.strip()),
    )


def load_command_table(path: Path) -> Dict[str, IMCCommand]:
    """Parse ``imc.commands`` into a lookup keyed by name and aliases."""

    if not path.exists():
        raise FileNotFoundError(path)

    commands: Dict[str, IMCCommand] = {}
    current: Dict[str, Any] | None = None

    def store(command: IMCCommand) -> None:
        key = _normalise_key(command.name)
        commands[key] = command
        for alias in command.aliases:
            commands[_normalise_key(alias)] = command

    with path.open(encoding="latin-1") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("*"):
                continue
            upper = line.upper()
            if upper == "#COMMAND":
                if current:
                    command = _finalise_command(current)
                    if command:
                        store(command)
                current = {}
                continue
            if upper == "#END":
                break
            if current is None:
                continue
            if line == "End":
                command = _finalise_command(current)
                if command:
                    store(command)
                current = None
                continue
            parts = line.split(maxsplit=1)
            if not parts:
                continue
            key = parts[0].lower()
            value = parts[1].strip() if len(parts) > 1 else ""
            if key == "name":
                current["name"] = value
            elif key == "code":
                current["function"] = value
            elif key == "perm":
                current["permission"] = value
            elif key == "connected":
                current["connected"] = value
            elif key == "alias":
                current.setdefault("aliases", []).append(value)
    if current:
        command = _finalise_command(current)
        if command:
            store(command)
    return commands


def _make_handler(target: str) -> PacketHandler:
    def handler(packet: IMCPacket) -> None:
        packet.handled_by = target

    handler.__name__ = target
    return handler


def build_default_packet_handlers() -> Dict[str, PacketHandler]:
    """Return ROM's default packet handlers keyed by packet type."""

    bindings = {
        "keepalive-request": "imc_send_keepalive",
        "is-alive": "imc_recv_isalive",
        "ice-update": "imc_recv_iceupdate",
        "ice-msg-r": "imc_recv_pbroadcast",
        "ice-msg-b": "imc_recv_broadcast",
        "user-cache": "imc_recv_ucache",
        "user-cache-request": "imc_recv_ucache_request",
        "user-cache-reply": "imc_recv_ucache_reply",
        "tell": "imc_recv_tell",
        "emote": "imc_recv_emote",
        "ice-destroy": "imc_recv_icedestroy",
        "who": "imc_recv_who",
        "who-reply": "imc_recv_whoreply",
        "whois": "imc_recv_whois",
        "whois-reply": "imc_recv_whoisreply",
        "beep": "imc_recv_beep",
        "ice-chan-who": "imc_recv_chanwho",
        "ice-chan-whoreply": "imc_recv_chanwhoreply",
        "channel-notify": "imc_recv_channelnotify",
        "close-notify": "imc_recv_closenotify",
    }
    return {packet: _make_handler(func) for packet, func in bindings.items()}
