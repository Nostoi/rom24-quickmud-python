import asyncio

import typer

from mud.db.migrations import run_migrations
from mud.net.telnet_server import start_server as start_telnet
from mud.network.websocket_server import run as start_websocket
from mud.server import run_game_loop

cli = typer.Typer()


@cli.command()
def runserver():
    """Start the main game server."""
    run_game_loop()


@cli.command()
def migrate():
    """Run database migrations."""
    run_migrations()


@cli.command()
def loadtestuser():
    """Load a default test account and character."""
    from mud.scripts.load_test_data import load_test_user

    load_test_user()


@cli.command()
def socketserver(host: str = "0.0.0.0", port: int = 5000):
    """Start the telnet server."""
    asyncio.run(start_telnet(host=host, port=port))


@cli.command()
def websocketserver(host: str = "0.0.0.0", port: int = 8000):
    """Start the websocket server."""
    start_websocket(host=host, port=port)


@cli.command()
def sshserver(host: str = "0.0.0.0", port: int = 2222):
    """Start the SSH server.

    Players can connect with: ssh -p 2222 player@hostname
    SSH credentials are ignored; authentication happens via MUD account login.
    """
    from mud.net.ssh_server import start_server as start_ssh

    asyncio.run(start_ssh(host=host, port=port))


if __name__ == "__main__":
    cli()
