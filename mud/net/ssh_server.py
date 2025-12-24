"""SSH server for QuickMUD using asyncssh.

Players connect via: ssh -p 2222 player@hostname
SSH credentials are ignored; MUD account authentication happens after connection.
ANSI color codes are fully supported.
"""

from __future__ import annotations

import asyncio
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

import asyncssh

from mud.config import get_qmconfig, load_qmconfig
from mud.db.migrations import run_migrations
from mud.game_tick_scheduler import start_game_tick_scheduler
from mud.security import bans
from mud.world.world_state import initialize_world

if TYPE_CHECKING:
    pass

# Default paths for SSH host key
DEFAULT_HOST_KEY_PATH = Path("data/ssh_host_key")

MAX_INPUT_LENGTH = 256


def _ensure_host_key(path: Path | None = None) -> Path:
    """Ensure SSH host key exists, generating one if necessary."""
    key_path = path or DEFAULT_HOST_KEY_PATH
    key_path = Path(key_path)

    if not key_path.exists():
        key_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[SSH] Generating new SSH host key at {key_path}")
        key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)
        key_path.write_bytes(key.export_private_key())
        key_path.chmod(0o600)
        print("[SSH] Host key generated successfully")

    return key_path


class SSHStream:
    """SSH stream wrapper matching TelnetStream interface for MUD connections.

    This class provides the same interface as TelnetStream so the existing
    connection handling code (login, character selection, game loop) can
    work unchanged with SSH connections.
    """

    def __init__(self, process: asyncssh.SSHServerProcess) -> None:
        self.process = process
        self._echo_enabled = True
        self.ansi_enabled = True
        self.peer_host: str | None = None
        self._go_ahead_enabled = True  # Not used for SSH, but kept for interface compat
        self._input_buffer: deque[str] = deque()
        self._closed = False

        # Extract peer host from connection
        try:
            conn = process.channel.get_connection()
            peername = conn.get_extra_info("peername")
            if peername and isinstance(peername, tuple):
                self.peer_host = peername[0]
        except Exception:
            pass

    def set_ansi(self, enabled: bool) -> None:
        """Enable or disable ANSI color code rendering."""
        self.ansi_enabled = bool(enabled)

    def _render(self, message: str) -> str:
        """Render ANSI codes based on current setting."""
        from mud.net.ansi import render_ansi

        return render_ansi(message, self.ansi_enabled)

    async def flush(self) -> None:
        """Flush output buffer (no-op for SSH as writes are immediate)."""
        pass

    async def negotiate(self) -> None:
        """Perform connection negotiation (no-op for SSH)."""
        pass

    async def disable_echo(self) -> None:
        """Disable local echo (for password input).

        For SSH, echo is controlled by the terminal. We track state internally
        and avoid echoing input characters during readline when disabled.
        """
        self._echo_enabled = False

    async def enable_echo(self) -> None:
        """Enable local echo."""
        self._echo_enabled = True

    async def send_text(self, message: str, *, newline: bool = False) -> None:
        """Send text to the client."""
        if self._closed:
            return

        rendered = self._render(message)
        # Normalize newlines for terminal display
        normalized = rendered.replace("\r\n", "\n").replace("\n\r", "\n")
        normalized = normalized.replace("\n", "\r\n")

        if newline and not normalized.endswith("\r\n"):
            normalized += "\r\n"

        try:
            self.process.stdout.write(normalized)
            await self.process.stdout.drain()
        except Exception:
            self._closed = True

    async def send_line(self, message: str) -> None:
        """Send text followed by a newline."""
        await self.send_text(message, newline=True)

    def set_go_ahead_enabled(self, enabled: bool) -> None:
        """Set go-ahead mode (no-op for SSH, telnet-specific)."""
        self._go_ahead_enabled = bool(enabled)

    async def send_prompt(self, prompt: str, *, go_ahead: bool | None = None) -> None:
        """Send a prompt without trailing newline."""
        if self._closed:
            return

        rendered = self._render(prompt)
        try:
            self.process.stdout.write(rendered)
            await self.process.stdout.drain()
        except Exception:
            self._closed = True

    async def readline(self, *, max_length: int = MAX_INPUT_LENGTH) -> str | None:
        """Read a line of input from the client."""
        if self._closed:
            return None

        buffer = []
        try:
            while True:
                data = await self.process.stdin.read(1)
                if not data:
                    # EOF
                    if not buffer:
                        return None
                    break

                char = data

                # Handle special characters
                if char in ("\r", "\n"):
                    # End of line
                    # Consume trailing LF after CR if present
                    break

                if char in ("\x08", "\x7f"):
                    # Backspace or delete
                    if buffer:
                        buffer.pop()
                        # Echo backspace if echo enabled
                        if self._echo_enabled:
                            try:
                                self.process.stdout.write("\x08 \x08")
                                await self.process.stdout.drain()
                            except Exception:
                                pass
                    continue

                # Skip control characters except tab
                if ord(char) < 32 and char != "\t":
                    continue

                # Check length limit
                if len(buffer) >= max_length - 2:
                    await self.send_line("Line too long.")
                    buffer.clear()
                    continue

                buffer.append(char)

        except asyncssh.BreakReceived:
            return None
        except asyncssh.TerminalSizeChanged:
            # Terminal resized, continue reading
            pass
        except Exception:
            self._closed = True
            return None

        return "".join(buffer)

    async def close(self) -> None:
        """Close the SSH connection."""
        if self._closed:
            return
        self._closed = True
        try:
            self.process.exit(0)
        except Exception:
            pass


class MUDSSHServer(asyncssh.SSHServer):
    """SSH server that skips SSH-level authentication.

    MUD account authentication is handled by the game's login flow
    after the SSH connection is established.
    """

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        """Called when an SSH connection is established."""
        peername = conn.get_extra_info("peername")
        host = peername[0] if peername else "unknown"
        print(f"[SSH] Connection received from {host}")

    def connection_lost(self, exc: Exception | None) -> None:
        """Called when an SSH connection is lost."""
        if exc:
            print(f"[SSH] Connection error: {exc}")

    def begin_auth(self, username: str) -> bool:
        """Skip SSH authentication - MUD handles auth after connection."""
        # Return False to indicate no authentication is required
        return False

    def password_auth_supported(self) -> bool:
        """Indicate password auth is supported (but we accept anything)."""
        return True

    def validate_password(self, username: str, password: str) -> bool:
        """Accept any password - real auth happens in MUD login flow."""
        return True

    def public_key_auth_supported(self) -> bool:
        """Indicate public key auth is supported."""
        return True

    def validate_public_key(self, username: str, key: asyncssh.SSHKey) -> bool:
        """Accept any public key - real auth happens in MUD login flow."""
        return True


async def handle_ssh_session(process: asyncssh.SSHServerProcess) -> None:
    """Handle an SSH session using the existing MUD connection flow."""
    from mud.net.connection import handle_connection_with_stream

    # Create SSH stream wrapper
    stream = SSHStream(process)
    host_for_ban = stream.peer_host

    try:
        # Use the shared connection handler (handles bans internally)
        await handle_connection_with_stream(stream, host_for_ban, connection_type="SSH")
    except Exception as exc:
        print(f"[SSH] Session error: {exc}")
    finally:
        await stream.close()


async def create_server(
    host: str = "0.0.0.0",
    port: int = 2222,
    area_list: str = "area/area.lst",
    host_key_path: Path | str | None = None,
) -> asyncssh.SSHAcceptor:
    """Create and return an SSH server without blocking."""
    # Initialize database and world
    load_qmconfig()
    qmconfig = get_qmconfig()
    run_migrations()
    initialize_world(area_list)
    bans.load_bans_file()

    # Ensure host key exists
    key_path = _ensure_host_key(Path(host_key_path) if host_key_path else None)

    # Determine bind address
    configured_host = (qmconfig.ip_address or "").strip()
    bind_host = host.strip() if isinstance(host, str) else ""
    if not bind_host or bind_host == "0.0.0.0":
        bind_host = configured_host or "0.0.0.0"

    # Create SSH server
    server = await asyncssh.create_server(
        MUDSSHServer,
        bind_host,
        port,
        server_host_keys=[str(key_path)],
        process_factory=handle_ssh_session,
    )

    return server


async def start_server(
    host: str = "0.0.0.0",
    port: int = 2222,
    area_list: str = "area/area.lst",
    host_key_path: Path | str | None = None,
) -> None:
    """Start the SSH server and run forever."""
    server = await create_server(host, port, area_list, host_key_path)

    # Get listening address
    sockets = server.sockets
    if sockets:
        for sock in sockets:
            addr = sock.getsockname()
            print(f"[SSH] Serving on {addr[0]}:{addr[1]}")
            print(f"[SSH] Connect with: ssh -p {addr[1]} player@{addr[0]}")

    # Start game tick scheduler
    await start_game_tick_scheduler()


if __name__ == "__main__":
    asyncio.run(start_server())
