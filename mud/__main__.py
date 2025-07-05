import asyncio
import typer
from mud.net.telnet_server import start_server as start_telnet
from mud.network.websocket_server import run as start_websocket

cli = typer.Typer()

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
