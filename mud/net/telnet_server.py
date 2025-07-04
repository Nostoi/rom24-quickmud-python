from __future__ import annotations
import asyncio

from mud.world.world_state import initialize_world
from .connection import handle_connection


async def start_server(host: str = "0.0.0.0", port: int = 4000) -> None:
    initialize_world("area/area.lst")
    server = await asyncio.start_server(handle_connection, host, port)
    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
