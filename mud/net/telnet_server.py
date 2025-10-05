from __future__ import annotations

import asyncio

from mud.db.migrations import run_migrations
from mud.security import bans
from mud.world.world_state import initialize_world

from .connection import handle_connection


async def create_server(
    host: str = "0.0.0.0", port: int = 4000, area_list: str = "area/area.lst"
) -> asyncio.AbstractServer:
    """Return a started telnet server without blocking the loop."""
    # Initialize database tables
    run_migrations()
    # Initialize world data (resets transient ban/account state)
    initialize_world(area_list)
    # Reload persistent ban entries after world bootstrap clears runtime registries
    bans.load_bans_file()
    return await asyncio.start_server(handle_connection, host, port)


async def start_server(host: str = "0.0.0.0", port: int = 4000, area_list: str = "area/area.lst") -> None:
    server = await create_server(host, port, area_list)
    sockets = getattr(server, "sockets", None)
    if sockets:
        addr = sockets[0].getsockname()
        print(f"Serving on {addr}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(start_server())
