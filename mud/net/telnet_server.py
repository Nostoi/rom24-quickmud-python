from __future__ import annotations

import asyncio

from mud.config import get_qmconfig, load_qmconfig
from mud.db.migrations import run_migrations
from mud.security import bans
from mud.world.world_state import initialize_world
from mud.game_tick_scheduler import start_game_tick_scheduler

from .connection import handle_connection


async def create_server(
    host: str = "0.0.0.0", port: int = 4000, area_list: str = "area/area.lst"
) -> asyncio.AbstractServer:
    """Return a started telnet server without blocking the loop."""
    # Initialize database tables
    load_qmconfig()
    qmconfig = get_qmconfig()
    run_migrations()
    # Initialize world data (resets transient ban/account state)
    initialize_world(area_list)
    # Reload persistent ban entries after world bootstrap clears runtime registries
    bans.load_bans_file()
    configured_host = (qmconfig.ip_address or "").strip()
    bind_host = host.strip() if isinstance(host, str) else ""
    if not bind_host or bind_host == "0.0.0.0":
        bind_host = configured_host or "0.0.0.0"
    return await asyncio.start_server(handle_connection, bind_host, port)


async def start_server(host: str = "0.0.0.0", port: int = 4000, area_list: str = "area/area.lst") -> None:
    server = await create_server(host, port, area_list)
    sockets = getattr(server, "sockets", None)
    if sockets:
        addr = sockets[0].getsockname()
        print(f"Serving on {addr}")

    # Start shared game tick scheduler
    await start_game_tick_scheduler()


if __name__ == "__main__":
    asyncio.run(start_server())
