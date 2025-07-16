import asyncio
from mud.net.telnet_server import start_server
from mud.config import HOST, PORT


def run_game_loop():
    print("\U0001F30D Starting MUD server...")
    asyncio.run(start_server(host=HOST, port=PORT))
