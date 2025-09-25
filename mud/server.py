import asyncio

from mud.config import HOST, PORT
from mud.net.telnet_server import start_server


def run_game_loop():
    print("\U0001f30d Starting MUD server...")
    asyncio.run(start_server(host=HOST, port=PORT))
