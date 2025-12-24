"""SSH server for QuickMUD.

Provides SSH connectivity alongside telnet and websocket options.
SSH authentication is handled by accepting any credentials at the SSH protocol level,
then using the MUD's existing account/character authentication flow.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

try:
    import asyncssh

    ASYNCSSH_AVAILABLE = True
except ImportError:
    asyncssh = None  # type: ignore
    ASYNCSSH_AVAILABLE = False

from mud.config import load_qmconfig
from mud.db.migrations import run_migrations
from mud.security import bans
from mud.world.world_state import initialize_world
from mud.game_tick_scheduler import start_game_tick_scheduler

if TYPE_CHECKING:
    if ASYNCSSH_AVAILABLE:
        from asyncssh import SSHReader, SSHWriter


if ASYNCSSH_AVAILABLE:

    class SSHStreamAdapter:
        """Adapter to make asyncssh SSHReader/SSHWriter work like asyncio streams.

        This bridges the asyncssh stream API to the interface expected by
        handle_connection() which was designed for asyncio StreamReader/Writer.
        """

        def __init__(self, stdin: SSHReader[Any], stdout: SSHWriter[Any], stderr: SSHWriter[Any]) -> None:
            self._stdin = stdin
            self._stdout = stdout
            self._stderr = stderr
            self._closed = False

        async def read(self, n: int = -1) -> bytes:
            """Read bytes from stdin."""
            if self._closed:
                return b""
            try:
                # Read from SSH stdin
                data = await self._stdin.read(n if n > 0 else 65536)
                if data is None or data == "":
                    return b""
                # asyncssh may return str or bytes depending on encoding
                if isinstance(data, str):
                    return data.encode("utf-8", errors="replace")
                return data
            except (asyncssh.BreakReceived, asyncssh.TerminalSizeChanged):
                # Handle special SSH events - just continue
                return b""
            except Exception:
                return b""

        def write(self, data: bytes) -> None:
            """Write bytes to stdout."""
            if self._closed:
                return
            try:
                # Convert bytes to string for SSH writer
                if isinstance(data, bytes):
                    text = data.decode("utf-8", errors="replace")
                else:
                    text = data
                self._stdout.write(text)
            except Exception:
                pass

        async def drain(self) -> None:
            """Drain write buffer."""
            if self._closed:
                return
            try:
                await self._stdout.drain()
            except Exception:
                pass

        def close(self) -> None:
            """Close the streams."""
            self._closed = True
            try:
                self._stdout.close()
            except Exception:
                pass

        async def wait_closed(self) -> None:
            """Wait for streams to close."""
            try:
                await self._stdout.wait_closed()
            except Exception:
                pass

        def get_extra_info(self, name: str, default: Any = None) -> Any:
            """Get connection metadata."""
            # Special marker for SSH connections - skip telnet negotiation
            if name == "ssh_connection":
                return True
            try:
                return self._stdout.get_extra_info(name, default)
            except Exception:
                return default

    class MUDSSHServer(asyncssh.SSHServer):  # type: ignore
        """SSH server that accepts all connections.

        Authentication happens at the MUD level (account/character login),
        not at the SSH protocol level. This allows users to connect via SSH
        and then go through the normal MUD authentication flow.
        """

        def __init__(self) -> None:
            self._conn: Any = None

        def connection_made(self, conn: Any) -> None:
            """Called when a connection is established."""
            self._conn = conn
            peer = conn.get_extra_info("peername")
            print(f"[SSH] Connection from {peer}")

        def connection_lost(self, exc: Exception | None) -> None:
            """Called when connection is lost."""
            if exc:
                print(f"[SSH] Connection lost: {exc}")

        def begin_auth(self, username: str) -> bool:
            """Accept all SSH connections - MUD auth happens after."""
            # Return True to require authentication, but we accept anything
            return True

        def password_auth_supported(self) -> bool:
            """Support password auth at SSH level."""
            return True

        def public_key_auth_supported(self) -> bool:
            """Support public key auth at SSH level."""
            return True

        def validate_password(self, username: str, password: str) -> bool:
            """Accept any SSH credentials - MUD handles real authentication."""
            return True

        def validate_public_key(self, username: str, key: Any) -> bool:
            """Accept any SSH key - MUD handles real authentication."""
            return True

        def session_requested(self) -> Any:
            """Handle session request by returning the stream handler.

            This is the key method - we return an async function that will
            receive (stdin, stdout, stderr) SSHReader/SSHWriter objects.
            """
            return handle_ssh_session

    async def handle_ssh_session(stdin: SSHReader[Any], stdout: SSHWriter[Any], stderr: SSHWriter[Any]) -> None:
        """Handle an SSH session using stream-based I/O.

        This function is called by asyncssh when a client requests a shell.
        It bridges the SSH streams to our existing MUD connection handler.

        Args:
            stdin: SSHReader for reading client input
            stdout: SSHWriter for writing output to client
            stderr: SSHWriter for error output (unused for MUD)
        """
        print("[SSH] Session started - running MUD connection handler")

        try:
            # Import here to avoid circular dependencies
            from mud.net.connection import handle_connection

            # Create stream adapter that bridges SSH streams to our expected interface
            adapter = SSHStreamAdapter(stdin, stdout, stderr)

            # Run the existing MUD connection handler
            # The adapter provides both read and write functionality
            await handle_connection(adapter, adapter)  # type: ignore

        except asyncio.CancelledError:
            print("[SSH] Session cancelled")
            raise
        except Exception as exc:
            print(f"[SSH] Session error: {exc}")
            import traceback

            traceback.print_exc()
        finally:
            print("[SSH] Session ended")
            try:
                stdout.close()
                await stdout.wait_closed()
            except Exception:
                pass


async def start_server(
    host: str = "0.0.0.0",
    port: int = 2222,
    area_list: str = "area/area.lst",
    host_keys: list[str] | None = None,
) -> None:
    """Start the SSH server for MUD connections.

    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 2222)
        area_list: Path to area list file
        host_keys: List of paths to SSH host key files. If None, generates a temporary key.

    Example:
        python -m mud sshserver
        python -m mud sshserver --port 2222
        ssh -p 2222 username@localhost
    """
    if not ASYNCSSH_AVAILABLE:
        print("[ERROR] asyncssh is not installed. Run: pip install asyncssh")
        return

    # Initialize database and world
    load_qmconfig()
    run_migrations()
    initialize_world(area_list)
    bans.load_bans_file()

    # Generate or load host keys
    if host_keys is None:
        # Generate a temporary RSA key for development
        print("[SSH] Generating temporary host key (use persistent keys in production)")
        server_key = asyncssh.generate_private_key("ssh-rsa")  # type: ignore
        host_keys_param: Any = [server_key]
    else:
        # Load keys from files
        host_keys_param = host_keys

    print(f"[SSH] Starting SSH server on {host}:{port}")

    await asyncssh.create_server(  # type: ignore
        MUDSSHServer,
        host,
        port,
        server_host_keys=host_keys_param,
        encoding="utf-8",  # Let asyncssh handle encoding for streams
    )

    print(f"[SSH] Server started on {host}:{port}")
    print(f"[SSH] Players can connect with: ssh -p {port} player@{host}")

    # Start shared game tick scheduler
    await start_game_tick_scheduler()


if __name__ == "__main__":
    asyncio.run(start_server())
