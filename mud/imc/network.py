"""Helpers for establishing IMC router connections."""

from __future__ import annotations

import socket
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

IMC_VERSION = 2


class IMCConnectionError(RuntimeError):
    """Raised when the router connection or handshake fails."""


@dataclass
class IMCConnection:
    """Holds metadata about the active router socket."""

    socket: Any
    address: tuple[str, int]
    handshake_frame: str
    handshake_complete: bool = False

    def close(self) -> None:
        """Best-effort close of the underlying socket."""

        close = getattr(self.socket, "close", None)
        if callable(close):
            try:
                close()
            except OSError:
                pass


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def autoconnect_enabled(config: Mapping[str, str]) -> bool:
    """Return True if the configuration requests an automatic connection."""

    return _is_truthy(config.get("Autoconnect"))


def build_handshake_frame(config: Mapping[str, str]) -> str:
    """Return the ROM-authored handshake string for the configured router."""

    local_name = config.get("LocalName")
    client_pwd = config.get("ClientPwd")
    server_pwd = config.get("ServerPwd")
    if not local_name or not client_pwd or not server_pwd:
        raise IMCConnectionError("IMC configuration missing handshake credentials")

    sha_enabled = _is_truthy(config.get("SHA256"))
    sha_has_pass = _is_truthy(config.get("SHA256Pwd")) or _is_truthy(config.get("SHA256Pass"))

    if sha_enabled and sha_has_pass:
        return f"SHA256-AUTH-REQ {local_name}"

    frame = f"PW {local_name} {client_pwd} version={IMC_VERSION} autosetup {server_pwd}"
    if sha_enabled:
        frame += " SHA256"
    return frame


def connect_and_handshake(config: Mapping[str, str]) -> IMCConnection:
    """Open a TCP socket to the router and perform the initial handshake."""

    host = config.get("ServerAddr")
    port_raw = config.get("ServerPort")
    if not host or not port_raw:
        raise IMCConnectionError("IMC configuration missing ServerAddr/ServerPort")

    try:
        port = int(port_raw)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
        raise IMCConnectionError("Invalid IMC ServerPort") from exc

    try:
        sock = socket.create_connection((host, port))
        try:
            sock.setblocking(False)
        except OSError:
            # Non-blocking mode mirrors ROM but is not critical for handshake.
            pass
        frame = build_handshake_frame(config)
        try:
            sock.sendall((frame + "\n").encode("latin-1"))
        except OSError as exc:
            raise IMCConnectionError("Failed to send IMC handshake") from exc
    except OSError as exc:
        raise IMCConnectionError("Unable to open IMC router socket") from exc

    return IMCConnection(socket=sock, address=(host, port), handshake_frame=frame, handshake_complete=True)
