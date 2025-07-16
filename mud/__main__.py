import asyncio
import typer
from mud.server import run_game_loop
from mud.db.migrations import run_migrations
from mud.net.telnet_server import start_server as start_telnet
from mud.network.websocket_server import run as start_websocket

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

if __name__ == "__main__":
    cli()
